import os
import shutil
import cv2
from moviepy.editor import ImageSequenceClip, AudioFileClip, VideoFileClip
from tqdm import tqdm
import whisper_timestamped
from django.conf import settings

FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_SCALE = 0.8
FONT_THICKNESS = 2

class DjangoVideoTranscriber:
    def __init__(self, model_path, video_path):
        self.model = whisper_timestamped.load_model(model_path)
        self.video_path = video_path
        self.media_root = settings.MEDIA_ROOT
        self.temp_dir = os.path.join(self.media_root, 'temp')
        self.processed_dir = os.path.join(self.media_root, 'processed')
        self.videos_dir = os.path.join(self.media_root, 'videos')
        
        # Create directories if they don't exist
        for directory in [self.temp_dir, self.processed_dir, self.videos_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
        
        # Set up paths
        self.video_filename = os.path.basename(video_path)
        self.video_name = os.path.splitext(self.video_filename)[0]
        self.audio_path = os.path.join(self.temp_dir, f"{self.video_name}_audio.mp3")
        self.frames_dir = os.path.join(self.temp_dir, f"{self.video_name}_frames")
        
        self.text_array = []
        self.fps = 0
        self.char_width = 0

    def transcribe_video(self):
        print('Transcribing video')
        result = self.model.transcribe(self.audio_path, word_timestamps=True)
        text = result["segments"][0]["text"]
        textsize = cv2.getTextSize(text, FONT, FONT_SCALE, FONT_THICKNESS)[0]
        
        cap = cv2.VideoCapture(self.video_path)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        asp = 16 / 9
        ret, frame = cap.read()
        width = frame[:, int((width - int(width / asp) * height) / 2):width - int((width - int(width / asp) * height) / 2)].shape[1]
        width = width - (width * 0.1)
        self.fps = cap.get(cv2.CAP_PROP_FPS)
        self.char_width = int(textsize[0] / len(text))

        for j in tqdm(result["segments"]):
            lines = []
            text = j["text"]
            end = j["end"]
            start = j["start"]
            total_frames = int((end - start) * self.fps)
            start = start * self.fps
            total_chars = len(text)
            words = text.split(" ")
            i = 0

            while i < len(words):
                words[i] = words[i].strip()
                if words[i] == "":
                    i += 1
                    continue
                length_in_pixels = (len(words[i]) + 1) * self.char_width
                remaining_pixels = width - length_in_pixels
                line = words[i]

                while remaining_pixels > 0:
                    i += 1
                    if i >= len(words):
                        break
                    length_in_pixels = (len(words[i]) + 1) * self.char_width
                    remaining_pixels -= length_in_pixels
                    if remaining_pixels < 0:
                        continue
                    else:
                        line += " " + words[i]

                line_array = [line, int(start), int(len(line) / total_chars * total_frames) + int(start)]
                start = int(len(line) / total_chars * total_frames) + int(start)
                lines.append(line_array)
                self.text_array.append(line_array)

        cap.release()
        print('Transcription complete')

    def extract_audio(self):
        print('Extracting audio')
        video = VideoFileClip(self.video_path)
        audio = video.audio
        audio.write_audiofile(self.audio_path)
        print('Audio extracted')

    def extract_frames(self, max_words_per_caption=3, font_scale=2, thickness=3, line_height=80):
        print('Extracting frames')
        if not os.path.exists(self.frames_dir):
            os.makedirs(self.frames_dir)
            
        cap = cv2.VideoCapture(self.video_path)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        aspect_ratio = width / height
        frame_count = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame = frame[:, int((width - aspect_ratio * height) / 2):width - int((width - aspect_ratio * height) / 2)]

            for segment in self.text_array:
                if segment[1] <= frame_count < segment[2]:
                    full_text = segment[0]
                    start_frame = segment[1]
                    end_frame = segment[2]
                    segment_duration = end_frame - start_frame

                    words = full_text.split()
                    word_chunks = [
                        words[i:i + max_words_per_caption]
                        for i in range(0, len(words), max_words_per_caption)
                    ]

                    chunk_duration = segment_duration / len(word_chunks)
                    current_chunk_index = int((frame_count - start_frame) / chunk_duration)
                    current_chunk_index = min(current_chunk_index, len(word_chunks) - 1)

                    current_text = " ".join(word_chunks[current_chunk_index])

                    y_position = int(height * 0.85)
                    x_position = int((frame.shape[1] - cv2.getTextSize(current_text, FONT, font_scale, thickness)[0][0]) / 2)
                    cv2.putText(frame, current_text, (x_position, y_position), FONT, font_scale, (255, 255, 255), thickness)
                    break

            frame_path = os.path.join(self.frames_dir, f"{frame_count:06d}.jpg")
            cv2.imwrite(frame_path, frame)
            frame_count += 1

        cap.release()
        print('Frames extracted')

    def process_video(self):
        """Main method to process the video"""
        output_video_path = os.path.join(self.processed_dir, f"processed_{self.video_filename}")
        
        try:
            # Process the video
            self.extract_audio()
            self.transcribe_video()
            self.extract_frames()

            # Create final video
            print('Creating final video')
            images = sorted(
                [img for img in os.listdir(self.frames_dir) if img.endswith(".jpg")],
                key=lambda x: int(x.split(".")[0])
            )

            clip = ImageSequenceClip([os.path.join(self.frames_dir, image) for image in images], fps=self.fps)
            audio = AudioFileClip(self.audio_path)
            clip = clip.set_audio(audio)
            clip.write_videofile(output_video_path)

            # Clean up temporary files
            self._cleanup()
            
            return output_video_path
            
        except Exception as e:
            self._cleanup()
            raise e

    def _cleanup(self):
        """Clean up temporary files and directories"""
        print('Cleaning up temporary files')
        if os.path.exists(self.frames_dir):
            shutil.rmtree(self.frames_dir)
        if os.path.exists(self.audio_path):
            os.remove(self.audio_path)