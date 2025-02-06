from ultralytics import YOLO
import cv2
import numpy as np
import wave
import os
import webrtcvad
import collections
import contextlib
import wave
from array import array
from struct import pack
from django.conf import settings  # Import Django settings

class VideoSpeakerDiarization:
    def __init__(self, yolo_model_path=None):
        # Use Django's MEDIA_ROOT if yolo_model_path is not provided
        if yolo_model_path is None:
            yolo_model_path = os.path.join(settings.BASE_DIR, "models", "yolov8n.pt")

        # Ensure the model file exists
        if not os.path.exists(yolo_model_path):
            raise FileNotFoundError(f"YOLO model file not found at: {yolo_model_path}")

        self.face_detector = YOLO(yolo_model_path)
        self.vad = webrtcvad.Vad(3)
        self.sample_rate = 16000
        self.frame_duration = 30
        self.face_tracker = {}  # Dictionary to track faces
        self.face_history = {}  # Dictionary to store face detection history
        self.track_threshold = 15  # Number of frames to track a face
        self.iou_threshold = 0.5  # IOU threshold for face tracking

    def calculate_iou(self, box1, box2):
        """Calculate Intersection over Union between two bounding boxes."""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])

        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - intersection

        return intersection / union if union > 0 else 0

    def update_face_tracker(self, current_faces, frame_index):
        """Update face tracking information."""
        # Update existing tracks
        current_tracks = {}
        used_faces = set()

        # Match current faces with existing tracks
        for track_id, track_info in self.face_tracker.items():
            last_box = track_info['boxes'][-1]
            best_iou = 0
            best_face = None

            for face in current_faces:
                if face not in used_faces:
                    iou = self.calculate_iou(last_box, face)
                    if iou > self.iou_threshold and iou > best_iou:
                        best_iou = iou
                        best_face = face

            if best_face is not None:
                current_tracks[track_id] = {
                    'boxes': track_info['boxes'][-self.track_threshold:] + [best_face],
                    'last_seen': frame_index
                }
                used_faces.add(best_face)

        # Create new tracks for unmatched faces
        next_track_id = max(self.face_tracker.keys(), default=-1) + 1
        for face in current_faces:
            if face not in used_faces:
                current_tracks[next_track_id] = {
                    'boxes': [face],
                    'last_seen': frame_index
                }
                next_track_id += 1

        self.face_tracker = current_tracks

    def is_face_speaking(self, face_box, current_time, speech_segments, frame_index):
        """Determine if a face is speaking based on tracking history and speech segments."""
        # Find the track ID for this face
        track_id = None
        for tid, track_info in self.face_tracker.items():
            if face_box in track_info['boxes']:
                track_id = tid
                break

        if track_id is None:
            return False

        # Check if the face is in a speech segment
        is_in_speech = any(
            segment["start"] <= current_time <= segment["end"]
            for segment in speech_segments
        )

        if not is_in_speech:
            return False

        # Check face stability
        track_info = self.face_tracker[track_id]
        if len(track_info['boxes']) < 5:  # Require minimum tracking history
            return False

        # Calculate face movement
        boxes = track_info['boxes']
        centers = [(((b[0] + b[2]) / 2), ((b[1] + b[3]) / 2)) for b in boxes]
        movements = [np.sqrt((centers[i][0] - centers[i - 1][0]) ** 2 +
                             (centers[i][1] - centers[i - 1][1]) ** 2)
                     for i in range(1, len(centers))]

        avg_movement = np.mean(movements) if movements else float('inf')

        # Face should be relatively stable during speech
        movement_threshold = 30  # pixels
        return avg_movement < movement_threshold

    def extract_audio(self, video_path, audio_path):
        """Extract audio from video."""
        command = f"ffmpeg -i {video_path} -acodec pcm_s16le -ar {self.sample_rate} -ac 1 {audio_path} -y"
        os.system(command)

    def read_wave(self, path):
        """Read a .wav file and return the bytes."""
        with contextlib.closing(wave.open(path, 'rb')) as wf:
            num_channels = wf.getnchannels()
            assert num_channels == 1
            sample_width = wf.getsampwidth()
            assert sample_width == 2
            sample_rate = wf.getframerate()
            assert sample_rate == self.sample_rate
            pcm_data = wf.readframes(wf.getnframes())
            return pcm_data, sample_rate

    def frame_generator(self, audio, sample_rate):
        """Generate audio frames from raw PCM audio data."""
        n = int(sample_rate * (self.frame_duration / 1000.0) * 2)
        offset = 0
        while offset + n < len(audio):
            yield audio[offset:offset + n]
            offset += n

    def process_audio(self, audio_path):
        """Process audio to detect speech segments."""
        audio, sample_rate = self.read_wave(audio_path)
        frames = list(self.frame_generator(audio, sample_rate))

        speech_segments = []
        is_speech_started = False
        speech_start = 0
        frame_length = self.frame_duration / 1000.0

        # Use a sliding window to smooth VAD decisions
        window_size = 3
        speech_window = collections.deque(maxlen=window_size)

        for i, frame in enumerate(frames):
            is_speech = self.vad.is_speech(frame, sample_rate)
            speech_window.append(is_speech)

            # Consider it speech only if majority of frames in window are speech
            is_speech_smooth = sum(speech_window) > window_size / 2

            if is_speech_smooth and not is_speech_started:
                speech_start = max(0, (i - window_size // 2)) * frame_length
                is_speech_started = True
            elif not is_speech_smooth and is_speech_started:
                speech_end = (i + window_size // 2) * frame_length
                speech_segments.append({
                    "start": speech_start,
                    "end": speech_end,
                    "speaker": "SPEECH"
                })
                is_speech_started = False

        if is_speech_started:
            speech_segments.append({
                "start": speech_start,
                "end": len(frames) * frame_length,
                "speaker": "SPEECH"
            })

        # Merge very close segments (gaps less than 0.3 seconds)
        merged_segments = []
        if speech_segments:
            current_segment = speech_segments[0]
            for segment in speech_segments[1:]:
                if segment["start"] - current_segment["end"] < 0.3:
                    current_segment["end"] = segment["end"]
                else:
                    merged_segments.append(current_segment)
                    current_segment = segment
            merged_segments.append(current_segment)

        return merged_segments

    def detect_faces(self, frame):
        """Detect faces in the video frame using YOLOv8."""
        results = self.face_detector(frame)
        face_boxes = []
        for detection in results[0].boxes:
            if detection.conf.item() > 0.5:
                x1, y1, x2, y2 = map(int, detection.xyxy[0])
                face_boxes.append((x1, y1, x2, y2))
        return face_boxes

    def run(self, video_path, output_path):
        """Process the video and synchronize face detection with voice activity."""
        temp_audio_path = "temp_audio.wav"
        self.extract_audio(video_path, temp_audio_path)
        speech_segments = self.process_audio(temp_audio_path)

        cap = cv2.VideoCapture(video_path)
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))

        frame_index = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            current_time = frame_index / fps
            face_boxes = self.detect_faces(frame)

            # Update face tracking
            self.update_face_tracker(face_boxes, frame_index)

            # Draw detections and speaking status
            for face_box in face_boxes:
                is_speaking = self.is_face_speaking(face_box, current_time, speech_segments, frame_index)
                color = (0, 255, 0) if is_speaking else (0, 0, 255)
                label = "Speaking" if is_speaking else "Not Speaking"

                x1, y1, x2, y2 = face_box
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, label, (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            out.write(frame)
            frame_index += 1

            if frame_index % 30 == 0:
                print(f"Processed {frame_index} frames")

        cap.release()
        out.release()
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)

        print("Processing complete. Output saved to:", output_path)
        return speech_segments