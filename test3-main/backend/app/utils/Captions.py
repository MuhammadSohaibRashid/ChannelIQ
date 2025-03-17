import os
import shutil
import cv2
import numpy as np
from moviepy.editor import ImageSequenceClip, AudioFileClip, VideoFileClip
from tqdm import tqdm
import whisper_timestamped
from django.conf import settings
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# Updated font settings for bolder appearance
FONT = cv2.FONT_HERSHEY_DUPLEX  # More bold font
FONT_PATH = os.path.join(settings.MEDIA_ROOT, "fonts", "Poppins-Bold.ttf")
FONT_SCALE = 1.2  # Slightly larger for better visibility
FONT_THICKNESS = 3  # Increased thickness for bolder appearance
ACTIVE_TEXT_COLOR = (0, 255, 255)  # Yellow for active word
TEXT_SHADOW_COLOR = (0, 0, 0)  # Black shadow/outline
FONT_SIZE = 40 # Font size for captions

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
        
        self.word_segments = []  # To store word-level segments
        self.sentence_segments = []  # To store sentences for context
        self.fps = 0
        self.frame_width = 0
        self.frame_height = 0
        
        # Face detection cascade classifier for smart positioning
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    def transcribe_video(self):
        """Transcribe the video audio and create word-level segments with timestamps"""
        print('Transcribing video with word-level timestamps')
        result = whisper_timestamped.transcribe(self.model, self.audio_path, language="en")
        
        # Get video properties
        cap = cv2.VideoCapture(self.video_path)
        self.fps = cap.get(cv2.CAP_PROP_FPS)
        self.frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        
        # Process each word from the transcription
        current_sentence = []
        for segment in result["segments"]:
            for word in segment["words"]:
                word_text = word["text"].strip()
                # Skip punctuation-only words
                if word_text and not all(c in ",.?!:;-\"'" for c in word_text):
                    start_time = word["start"]
                    end_time = word["end"]
                    start_frame = int(start_time * self.fps)
                    end_frame = int(end_time * self.fps)
                    
                    word_info = {
                        "text": word_text,
                        "start_time": start_time,
                        "end_time": end_time,
                        "start_frame": start_frame,
                        "end_frame": end_frame
                    }
                    
                    self.word_segments.append(word_info)
                    current_sentence.append(word_info)
                    
                    # Check if word ends with punctuation to create a sentence
                    if word_text[-1] in ".?!" if len(word_text) > 0 else False:
                        if current_sentence:
                            self.sentence_segments.append(current_sentence.copy())
                            current_sentence = []
            
            # End of segment can also be end of a sentence
            if current_sentence:
                self.sentence_segments.append(current_sentence.copy())
                current_sentence = []
        
        print(f'Transcription complete: {len(self.word_segments)} words processed')

    def extract_audio(self):
        """Extract audio from the video file"""
        print('Extracting audio')
        video = VideoFileClip(self.video_path)
        audio = video.audio
        audio.write_audiofile(self.audio_path)
        print('Audio extracted')

    def _get_current_and_previous_words(self, current_frame, history_length=8):
        """
        Get the current active word and a history of previous words
        Returns words that should be displayed in the caption
        """
        active_words = []
        
        # Find the active word for the current frame
        active_word_index = None
        for i, word in enumerate(self.word_segments):
            if word["start_frame"] <= current_frame < word["end_frame"]:
                active_word_index = i
                active_words.append(self.word_segments[i])
                break
        
        # If no active word was found, no words to display
        if active_word_index is None:
            return []
            
        # Get previous words for context, but only from the current sentence
        # Find which sentence the active word belongs to
        sentence_index = None
        word_in_sentence_index = None
        
        for s_idx, sentence in enumerate(self.sentence_segments):
            for w_idx, word in enumerate(sentence):
                if word["start_frame"] == self.word_segments[active_word_index]["start_frame"]:
                    sentence_index = s_idx
                    word_in_sentence_index = w_idx
                    break
            if sentence_index is not None:
                break
        
        # If we found the sentence, get words from it
        if sentence_index is not None:
            # Only include words from the beginning of the sentence or up to history_length
            start_idx = max(0, word_in_sentence_index - history_length + 1)
            
            # Reset active_words to only include words from the current sentence
            active_words = []
            
            # Add words from current sentence
            for i in range(start_idx, word_in_sentence_index + 1):
                active_words.append(self.sentence_segments[sentence_index][i])
        
        return active_words

    def _find_optimal_text_position_pil(self, frame, text_height, text_width, face_padding=50):
        """
        Find the optimal position for text based on content analysis using PIL measurements:
        1. Detect faces
        2. Position text to avoid faces, preferring the bottom of the frame
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = self.face_cascade.detectMultiScale(
            gray, 
            scaleFactor=1.1, 
            minNeighbors=5, 
            minSize=(30, 30)
        )
        
        frame_height, frame_width = frame.shape[:2]
        
        # Default position (bottom center)
        default_y = frame_height - 300  # Raised position from bottom
        best_y = default_y  # Initialize best_y with default value
        
        # Ensure text doesn't go off-screen horizontally
        text_margin = 30  # Margin from screen edges
        
        # Horizontal positioning (center text but ensure it fits)
        text_x = max(text_margin, (frame_width - text_width) // 2)
        if text_x + text_width > frame_width - text_margin:
            text_x = frame_width - text_width - text_margin
        
        # If no faces detected, return default position
        if len(faces) == 0:
            return text_x, best_y
        
        # Calculate the lower third of the frame
        lower_third_start = frame_height * 2 // 3
        
        # Check if any faces are in the lower third
        faces_in_lower_third = [face for face in faces if (face[1] + face[3]) > lower_third_start]
        
        # If no faces in lower third, use default bottom position
        if len(faces_in_lower_third) == 0:
            return text_x, best_y
        
        # We have faces in lower third, so let's find alternative position
        # Try top of the frame
        top_y = 80
        
        # Check if there are faces at the top
        faces_at_top = [face for face in faces if face[1] < text_height + top_y + face_padding]
        
        if len(faces_at_top) == 0:
            # No faces at top, position there
            best_y = top_y
            return text_x, best_y
        
        # Both top and bottom have faces
        # Calculate best position that maximizes distance from faces
        
        # Create a heat map of face positions
        heat_map = np.zeros(frame_height)
        
        for (x, y, w, h) in faces:
            # Add heat to the areas where faces are located
            face_center_y = y + h // 2
            
            # Add decreasing heat as we move away from the face
            for i in range(frame_height):
                distance = abs(i - face_center_y)
                if distance < face_padding * 2:
                    heat_map[i] += 1 - (distance / (face_padding * 2))
        
        # Find the coolest spot with enough space for text
        min_heat = float('inf')
        
        # Adjust the starting point to account for text being drawn from its baseline in PIL
        # With PIL, text is positioned from the top-left corner, not from the baseline as in cv2
        for y in range(text_height, frame_height - 30):
            # Calculate average heat in the text area
            avg_heat = np.mean(heat_map[y - text_height:y])
            
            if avg_heat < min_heat:
                min_heat = avg_heat
                best_y = y
        
        # Final safety check to ensure text is visible
        if best_y + text_height > frame_height - text_margin:
            best_y = frame_height - text_height - text_margin
        
        return text_x, best_y

    def _format_text_two_rows(self, words):
        """Format text into a maximum of two rows, resetting when full"""
        if not words:
            return []
            
        frame_width = self.frame_width
        max_row_width = frame_width * 0.85  # 85% of frame width for better margin
        
        # Load font for measurements
        font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
        
        # First pass: calculate all word widths
        word_objects = []
        for word in words:
            word_bbox = font.getbbox(word["text"])
            word_width = word_bbox[2] - word_bbox[0]
            space_bbox = font.getbbox(" ")
            space_width = space_bbox[2] - space_bbox[0]
            word_objects.append({
                "word": word,
                "width": word_width,
                "space_width": space_width
            })
        
        # If we have more words than can fit in two rows, trim from the beginning
        # Start with the most recent word (last in the list)
        rows = [[], []]
        current_row = 1  # Start filling the second row (bottom row)
        current_width = 0
        
        # Work backwards from the most recent word
        for i in range(len(word_objects) - 1, -1, -1):
            word_obj = word_objects[i]
            total_width = word_obj["width"] + (word_obj["space_width"] if current_width > 0 else 0)
            
            # If adding this word would exceed max width, move to the next row up
            if current_width + total_width > max_row_width:
                current_row -= 1
                current_width = 0
                
                # If we've filled both rows, stop adding words
                if current_row < 0:
                    break
            
            # Add word to the current row (at the beginning since we're going backwards)
            rows[current_row].insert(0, word_obj["word"])
            current_width += total_width
        
        # Return only the rows that have content
        return [row for row in rows if row]

    def _add_dynamic_captions(self, frame, current_frame):
        """Add captions with the current spoken word and context using PIL for custom font"""
        # Get the active and previous words for this frame
        display_words = self._get_current_and_previous_words(current_frame)
        
        if not display_words:
            return frame
            
        # Convert OpenCV image to PIL format
        pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_img)
        
        # Load the Poppin font
        font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
        
        # Format into maximum of two rows
        text_rows = self._format_text_two_rows(display_words)
        
        frame_height, frame_width = frame.shape[:2]
        
        # Calculate line height for positioning using getbbox instead of getsize
        test_bbox = font.getbbox("Test")
        line_height = test_bbox[3] - test_bbox[1] + 10
        total_height = len(text_rows) * line_height
        
        # Find widest row for positioning
        widest_row = 0
        for row in text_rows:
            row_width = 0
            for word in row:
                word_bbox = font.getbbox(word["text"])
                word_width = word_bbox[2] - word_bbox[0]
                space_bbox = font.getbbox(" ")
                space_width = space_bbox[2] - space_bbox[0]
                row_width += word_width + space_width
            widest_row = max(widest_row, row_width)
        
        # Find optimal position
        text_x, text_y_base = self._find_optimal_text_position_pil(frame, total_height, widest_row)
        
        # Draw each row
        for i, row in enumerate(text_rows):
            current_y = text_y_base - ((len(text_rows) - 1 - i) * line_height)
            current_x = text_x
            
            # Draw each word in the row
            for word in row:
                word_text = word["text"]
                # Determine if this is the active word for the current frame
                is_active = word["start_frame"] <= current_frame < word["end_frame"]
                
                # Calculate word width using getbbox
                word_bbox = font.getbbox(word_text)
                word_width = word_bbox[2] - word_bbox[0]
                
                # Draw text shadow for better visibility
                shadow_offsets = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
                for offset_x, offset_y in shadow_offsets:
                    draw.text(
                        (current_x + offset_x, current_y + offset_y),
                        word_text,
                        font=font,
                        fill=TEXT_SHADOW_COLOR
                    )
                
                # Draw the actual text - highlight active word in yellow
                text_color = ACTIVE_TEXT_COLOR if is_active else (255, 255, 255)
                draw.text(
                    (current_x, current_y),
                    word_text,
                    font=font,
                    fill=text_color
                )
                
                # Move to next word position (add space)
                space_bbox = font.getbbox(" ")
                space_width = space_bbox[2] - space_bbox[0]
                current_x += word_width + space_width
        
        # Convert back to OpenCV format
        frame = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        return frame


    def extract_frames(self):
        """Extract frames and add captions that show words as they're spoken"""
        print('Extracting frames with dynamic captions')
        if not os.path.exists(self.frames_dir):
            os.makedirs(self.frames_dir)
            
        cap = cv2.VideoCapture(self.video_path)
        
        frame_count = 0
        
        # For progress reporting 
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        progress_interval = max(1, total_frames // 100)
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Add captions with current word and context
            frame = self._add_dynamic_captions(frame, frame_count)
            
            # Save the frame
            frame_path = os.path.join(self.frames_dir, f"{frame_count:06d}.jpg")
            cv2.imwrite(frame_path, frame)
            frame_count += 1
            
            # Progress indicator
            if frame_count % progress_interval == 0:
                progress = (frame_count / total_frames) * 100
                print(f"Processed {frame_count}/{total_frames} frames ({progress:.1f}%)")
        
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