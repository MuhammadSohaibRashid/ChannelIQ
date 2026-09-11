from ultralytics import YOLO
from moviepy.editor import VideoFileClip
from multiprocessing import Manager, Pool
from collections import deque
import cv2
import numpy as np
import os
from .Speaker import VideoSpeakerDiarization


class PositionBuffer:
    def __init__(self, buffer_size=30):
        self.positions = deque(maxlen=buffer_size)

    def add_and_smooth(self, pos, frame_width):
        self.positions.append(pos)
        if len(self.positions) == 0:
            return pos

        weights = np.exp(-np.arange(len(self.positions)) / 5.0)
        weights /= weights.sum()
        smoothed_pos = int(np.sum(np.array(self.positions) * weights))

        if len(self.positions) > 1:
            max_movement = int(frame_width * 0.1)
            prev_pos = self.positions[-2]
            smoothed_pos = np.clip(smoothed_pos, prev_pos - max_movement, prev_pos + max_movement)

        return int(smoothed_pos)
class SceneAnalyzer:
    def __init__(self, model):
        self.model = model
        self.object_classes = model.names
        self.interesting_classes = ['person', 'car', 'dog', 'cat', 'tv', 'laptop', 'cell phone']

    def detect_objects(self, frame):
        results = self.model(frame)
        detections = []
        for box in results[0].boxes:
            if box.conf[0] > 0.5:
                xyxy = [int(x) for x in box.xyxy[0].tolist()]  # Convert to integers
                cls = int(box.cls[0].item())
                conf = float(box.conf[0].item())
                detections.append((xyxy, cls, conf))
        return detections

    def get_scene_composition(self, frame):
        detections = self.detect_objects(frame)
        faces = []
        objects = []

        for box, cls, conf in detections:
            if cls == 0:  # face class
                faces.append(box)
            elif self.object_classes[int(cls)] in self.interesting_classes:
                objects.append(box)

        return {
            'faces': faces,
            'objects': objects,
            'total_detections': len(detections)
        }


class SmartCropper:
    def __init__(self, original_width, original_height):
        self.original_width = int(original_width)
        self.original_height = int(original_height)
        self.vertical_width = int(original_height * 9 / 16)
        self.position_buffer = PositionBuffer()

    def get_face_crop_region(self, frame, face, position='center'):
        try:
            # Ensure face coordinates are integers
            x1, y1, x2, y2 = map(int, face)
            face_center_x = int((x1 + x2) / 2)
            face_center_y = int((y1 + y2) / 2)
            face_height = int(y2 - y1)

            # Calculate crop boundaries based on position
            if position == 'top':
                y_start = max(0, int(face_center_y - face_height))
                height = self.original_height // 2
            elif position == 'bottom':
                y_start = min(self.original_height - face_height, int(face_center_y))
                height = self.original_height // 2
            else:  # center
                y_start = 0
                height = self.original_height

            # Calculate x position with smoothing
            desired_x = int(max(0, min(self.original_width - self.vertical_width,
                                       face_center_x - self.vertical_width // 2)))
            x_start = self.position_buffer.add_and_smooth(desired_x, self.original_width)

            # Ensure boundaries are within frame
            y_end = min(self.original_height, y_start + height)
            x_end = min(self.original_width, x_start + self.vertical_width)

            # Extract region
            region = frame[y_start:y_end, x_start:x_end]

            # Resize if necessary
            if region.shape[:2] != (height, self.vertical_width):
                region = cv2.resize(region, (self.vertical_width, height))

            return region

        except Exception as e:
            print(f"Error in get_face_crop_region: {str(e)}")
            # Return center crop as fallback
            x_start = (self.original_width - self.vertical_width) // 2
            return frame[:, x_start:x_start + self.vertical_width]

    def create_blur_borders(self, frame):
        try:
            target_width = self.vertical_width
            center_x = self.original_width // 2
            x_start = center_x - (target_width // 2)
            x_end = x_start + target_width

            # Ensure boundaries are within frame
            x_start = max(0, x_start)
            x_end = min(self.original_width, x_end)

            # Create blurred version
            blurred = cv2.GaussianBlur(frame, (99, 99), 0)

            # Create mask
            mask = np.zeros((self.original_height, self.original_width), dtype=np.uint8)
            mask[:, x_start:x_end] = 255

            # Add gradient
            gradient_width = min(50, x_start, self.original_width - x_end)
            for i in range(gradient_width):
                alpha = i / gradient_width
                if x_start - i >= 0:
                    mask[:, x_start - i - 1] = int(255 * alpha)
                if x_end + i < self.original_width:
                    mask[:, x_end + i] = int(255 * (1 - alpha))

            # Apply mask
            mask = cv2.merge([mask, mask, mask]) / 255.0
            result = frame * mask + blurred * (1 - mask)

            # Crop to target width
            result = result[:, x_start:x_end].astype(np.uint8)

            # Ensure correct dimensions
            if result.shape[1] != self.vertical_width:
                result = cv2.resize(result, (self.vertical_width, self.original_height))

            return result

        except Exception as e:
            print(f"Error in create_blur_borders: {str(e)}")
            # Return simple center crop as fallback
            x_start = (self.original_width - self.vertical_width) // 2
            return frame[:, x_start:x_start + self.vertical_width]

    def get_optimal_crop(self, frame, scene_data, is_speaking):
        try:
            if not scene_data['faces'] and not scene_data['objects']:
                return self.create_blur_borders(frame)

            if len(scene_data['faces']) > 1:
                return self.handle_multiple_faces(frame, scene_data['faces'])
            elif len(scene_data['faces']) == 1:
                return self.handle_single_face(frame, scene_data['faces'][0], is_speaking)
            else:
                return self.handle_objects(frame, scene_data['objects'])

        except Exception as e:
            print(f"Error in get_optimal_crop: {str(e)}")
            # Return center crop as fallback
            x_start = (self.original_width - self.vertical_width) // 2
            return frame[:, x_start:x_start + self.vertical_width]

    def handle_multiple_faces(self, frame, faces):
        try:
            # Input validation
            if frame is None or frame.size == 0:
                print("Invalid input frame")
                return self.create_blur_borders(frame)

            if len(faces) >= 2:
                # For multiple faces, use a center-weighted approach instead of splitting
                # Calculate the bounding box that encompasses all faces
                min_x = min(face[0] for face in faces)
                max_x = max(face[2] for face in faces)
                center_x = (min_x + max_x) // 2

                # Calculate crop boundaries
                half_width = self.vertical_width // 2
                x_start = max(0, min(self.original_width - self.vertical_width,
                                     center_x - half_width))
                x_end = min(self.original_width, x_start + self.vertical_width)

                # Verify crop dimensions
                if x_start >= x_end or x_end > frame.shape[1]:
                    print(f"Invalid crop dimensions: {x_start}, {x_end}")
                    return self.create_blur_borders(frame)

                # Extract the crop
                crop = frame[:, x_start:x_end].copy()

                # Verify crop is valid
                if crop is None or crop.size == 0:
                    print("Invalid crop result")
                    return self.create_blur_borders(frame)

                # Ensure correct dimensions
                if crop.shape[1] != self.vertical_width:
                    try:
                        crop = cv2.resize(crop, (self.vertical_width, self.original_height))
                    except Exception as resize_error:
                        print(f"Resize error: {resize_error}")
                        return self.create_blur_borders(frame)

                return crop

            else:
                # Fallback for single face or error cases
                return self.create_blur_borders(frame)

        except Exception as e:
            print(f"Error in handle_multiple_faces: {str(e)}")
            return self.create_blur_borders(frame)
    def handle_single_face(self, frame, face, is_speaking):
        try:
            padding = 1.2 if is_speaking else 1.5
            return self.get_face_crop_region(frame, face, position='center')
        except Exception as e:
            print(f"Error in handle_single_face: {str(e)}")
            return self.create_blur_borders(frame)

    def handle_objects(self, frame, objects):
        try:
            if not objects:
                return self.create_blur_borders(frame)

            # Find the most prominent object
            objects_sorted = sorted(objects, key=lambda x: (x[2] - x[0]) * (x[3] - x[1]), reverse=True)
            main_object = objects_sorted[0]

            object_center_x = int((main_object[0] + main_object[2]) / 2)
            x_start = int(max(0, min(self.original_width - self.vertical_width,
                                     object_center_x - self.vertical_width / 2)))

            return frame[:, x_start:x_start + self.vertical_width]

        except Exception as e:
            print(f"Error in handle_objects: {str(e)}")
            return self.create_blur_borders(frame)

from django.conf import settings 
def process_video_clip(input_path, output_path, yolo_model_path=None):
    try:
        # Use Django's MEDIA_ROOT if yolo_model_path is not provided
        if yolo_model_path is None:
            yolo_model_path = os.path.join(settings.BASE_DIR, "models", "yolov8n.pt")

        # Ensure the model file exists
        if not os.path.exists(yolo_model_path):
            raise FileNotFoundError(f"YOLO model file not found at: {yolo_model_path}")

        model = YOLO(yolo_model_path)
        speaker_processor = VideoSpeakerDiarization(yolo_model_path)

        # Use speaker_processor.run() to get speech segments
        speech_segments = speaker_processor.run(input_path, "temp_speaker_output.mp4")

        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise Exception("Could not open input video")

        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        vertical_width = int(height * 9 / 16)

        scene_analyzer = SceneAnalyzer(model)
        smart_cropper = SmartCropper(width, height)

        codecs = [
            ('mp4v', '.mp4'),
            ('XVID', '.avi'),
            ('MJPG', '.avi'),
            ('H264', '.mp4')
        ]

        out = None
        for codec, ext in codecs:
            try:
                temp_output = os.path.splitext(output_path)[0] + ext
                fourcc = cv2.VideoWriter_fourcc(*codec)
                out = cv2.VideoWriter(temp_output, fourcc, fps, (vertical_width, height), True)
                if out.isOpened():
                    output_path = temp_output
                    break
            except Exception:
                if out is not None:
                    out.release()
                continue

        if out is None or not out.isOpened():
            raise Exception("Could not create output video with any supported codec")

        frame_count = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            current_time = frame_count / fps
            is_speaking = any(
                segment["start"] <= current_time <= segment["end"]
                for segment in speech_segments
            )

            scene_data = scene_analyzer.get_scene_composition(frame)
            cropped_frame = smart_cropper.get_optimal_crop(frame, scene_data, is_speaking)

            if cropped_frame.size == 0:
                raise ValueError(f"Empty frame detected at frame {frame_count}")

            if len(cropped_frame.shape) == 2:
                cropped_frame = cv2.cvtColor(cropped_frame, cv2.COLOR_GRAY2BGR)

            cropped_frame = cropped_frame.astype(np.uint8)

            if cropped_frame.shape[:2] != (height, vertical_width):
                cropped_frame = cv2.resize(cropped_frame, (vertical_width, height))

            try:
                out.write(cropped_frame)
            except cv2.error as e:
                print(f"Error writing frame {frame_count}: {str(e)}")
                continue

            frame_count += 1
            if frame_count % 30 == 0:
                print(f"Processed {frame_count} frames")

        cap.release()
        out.release()
        if os.path.exists("temp_speaker_output.mp4"):
            os.remove("temp_speaker_output.mp4")

        return fps

    except Exception as e:
        print(f"Error in process_video: {str(e)}")
        if 'cap' in locals():
            cap.release()
        if 'out' in locals() and out is not None:
            out.release()
        if os.path.exists("temp_speaker_output.mp4"):
            os.remove("temp_speaker_output.mp4")
        raise


def combine_videos(video_with_audio, video_without_audio, output_filename, fps):
    try:
        clip_with_audio = VideoFileClip(video_with_audio)
        clip_without_audio = VideoFileClip(video_without_audio)

        min_duration = min(clip_with_audio.duration, clip_without_audio.duration)
        clip_with_audio = clip_with_audio.subclip(0, min_duration)
        clip_without_audio = clip_without_audio.subclip(0, min_duration)

        final_clip = clip_without_audio.set_audio(clip_with_audio.audio)

        final_clip.write_videofile(
            output_filename,
            codec='libx264',
            audio_codec='aac',
            fps=fps,
            preset='slow',
            bitrate='4000k',
            audio_bitrate='192k'
        )

        clip_with_audio.close()
        clip_without_audio.close()
        final_clip.close()

    except Exception as e:
        print(f"Error in video combination: {str(e)}")


