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
# Import better translation libraries
from deep_translator import GoogleTranslator
import re

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
        self.source_language = None  # Will store detected language
        
        # Face detection cascade classifier for smart positioning
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Initialize translator (will be set after language detection)
        self.translator = None
        # Cache for translated segments to avoid repeated translations
        self.translation_cache = {}

    def transcribe_video(self):
        """Transcribe the video audio and create word-level segments with timestamps"""
        print('Detecting language and transcribing video with word-level timestamps')
        
        # First detect the language
        audio_result = whisper_timestamped.transcribe(self.model, self.audio_path)
        self.source_language = audio_result.get("language", "en")
        
        print(f'Detected language: {self.source_language}')
        
        # Now transcribe with the detected language
        result = whisper_timestamped.transcribe(self.model, self.audio_path, language=self.source_language)
        print("transcription: ", result)
        
        # Initialize translator
        if self.source_language != "en":
            self.translator = GoogleTranslator(source=self.source_language, target='en')
            print(f'Translating from {self.source_language} to English')
        
        # Get video properties
        cap = cv2.VideoCapture(self.video_path)
        self.fps = cap.get(cv2.CAP_PROP_FPS)
        self.frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        
        # Process each segment first for better translation context
        for segment in result["segments"]:
            self.process_segment(segment)
        
        print(f'Transcription complete: {len(self.word_segments)} words processed')

    def process_segment(self, segment):
        """Process a segment with improved translation handling"""
        segment_text = segment["text"].strip()
        segment_words = []
        current_sentence = []
        
        # Skip empty segments
        if not segment_text:
            return
        
        # For non-English sources, translate the whole segment for context
        translated_segment = None
        if self.source_language != "en" and segment_text:
            # Check cache first
            if segment_text in self.translation_cache:
                translated_segment = self.translation_cache[segment_text]
            else:
                translated_segment = self.translator.translate(segment_text)
                self.translation_cache[segment_text] = translated_segment
        
        # First pass: collect all words in the segment
        for word in segment["words"]:
            word_text = word["text"].strip()
            
            # Skip empty words or just punctuation
            if not word_text or all(c in ",.?!:;-\"'" for c in word_text):
                continue
                
            start_time = word["start"]
            end_time = word["end"]
            start_frame = int(start_time * self.fps)
            end_frame = int(end_time * self.fps)
            
            segment_words.append({
                "original_text": word_text,
                "start_time": start_time,
                "end_time": end_time,
                "start_frame": start_frame,
                "end_frame": end_frame
            })
            
        # Second pass: improve translation by aligning with translated segment
        if self.source_language != "en" and translated_segment:
            # Use improved word alignment for translation
            self.align_translations(segment_words, segment_text, translated_segment)
        else:
            # For English, just use the original text
            for word in segment_words:
                word["text"] = word["original_text"]
                
        # Add words to the global list and build sentences
        for word in segment_words:
            self.word_segments.append(word)
            current_sentence.append(word)
            
            # Check if word ends with punctuation to create a sentence
            if len(word["original_text"]) > 0 and word["original_text"][-1] in ".?!":
                if current_sentence:
                    self.sentence_segments.append(current_sentence.copy())
                    current_sentence = []
        
        # End of segment can also be end of a sentence
        if current_sentence:
            self.sentence_segments.append(current_sentence.copy())

    def align_translations(self, words, source_text, translated_text):
        """
        Improved alignment method that distributes the translated text
        across the original words more intelligently.
        """
        # Clean up special characters for better matching
        clean_source = re.sub(r'[^\w\s]', '', source_text.lower())
        source_words = clean_source.split()
        
        # If there's a major mismatch in word count, use statistical distribution
        translated_words = re.sub(r'[^\w\s]', '', translated_text.lower()).split()
        
        # Improved quality by using translation mapping
        if len(words) > 0 and len(translated_words) > 0:
            # Simple case: if word counts match, direct mapping
            if len(words) == len(translated_words):
                for i, word in enumerate(words):
                    word["text"] = self.preserve_capitalization(translated_words[i], word["original_text"])
            else:
                # Complex case: need to align words
                # Try to preserve timing by distributing translation
                ratio = len(translated_words) / len(words)
                
                # Handle multi-word translations
                current_translated_idx = 0
                for i, word in enumerate(words):
                    # Calculate how many translated words to assign to this original word
                    start_idx = int(i * ratio)
                    end_idx = int((i + 1) * ratio)
                    
                    # Ensure we capture at least one word
                    if end_idx <= start_idx:
                        end_idx = start_idx + 1
                    
                    # Get slice of translated words
                    assigned_words = translated_words[start_idx:end_idx]
                    
                    if assigned_words:
                        combined = " ".join(assigned_words)
                        word["text"] = self.preserve_capitalization(combined, word["original_text"])
                    else:
                        # Fallback
                        word["text"] = word["original_text"]

    def preserve_capitalization(self, new_text, original_text):
        """Preserve capitalization pattern from original text in new text"""
        if not original_text or not new_text:
            return new_text
            
        # If original starts with uppercase, capitalize new text
        if original_text[0].isupper():
            return new_text[0].upper() + new_text[1:] if len(new_text) > 1 else new_text.upper()
        return new_text

    def extract_audio(self):
        """Extract audio from the video file"""
        print('Extracting audio')
        video = VideoFileClip(self.video_path)
        audio = video.audio
        audio.write_audiofile(self.audio_path)
        print('Audio extracted')

    def _get_current_and_previous_words(self, current_frame):
        """Get words from current sentence only, ensuring fresh start for new sentences"""
        # Find the active word
        active_word = next((w for w in self.word_segments 
                        if w["start_frame"] <= current_frame < w["end_frame"]), None)
        
        if not active_word:
            return []

        # Find which sentence contains the active word
        current_sentence = next((s for s in self.sentence_segments 
                                if s[0]["start_frame"] <= active_word["start_frame"] <= s[-1]["end_frame"]), [])
        
        if not current_sentence:
            return [active_word]

        # Get words up to and including the active word in this sentence
        display_words = []
        for word in current_sentence:
            display_words.append(word)
            if word["start_frame"] == active_word["start_frame"]:
                break
                
        return display_words

    def _find_optimal_text_position_pil(self, frame, text_height, text_width, face_padding=50):
        """
        Return default position for captions - bottom center of the frame
        """
        frame_height, frame_width = frame.shape[:2]
            
        # Calculate default position (bottom center)
        default_y = frame_height - 300  # Fixed position from bottom
        
        # Center text horizontally
        text_x = max(30, (frame_width - text_width) // 2)
        
        # Return fixed position regardless of face detection
        return text_x, default_y

    def _format_text_two_rows(self, words):
        """Group words into chunks of up to 2 lines. Reset when second line is filled."""
        if not words:
            return []

        max_row_width = self.frame_width * 0.85  # 85% of frame width
        font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
        
        chunks = []
        current_chunk = []
        current_lines = []
        current_line = []
        current_line_width = 0

        for word in words:
            text = word["text"]
            # Calculate dimensions using PIL
            bbox = font.getbbox(text)
            word_width = bbox[2] - bbox[0]
            space_width = font.getbbox(" ")[2] - font.getbbox(" ")[0] if current_line else 0
            
            # Check if word fits in current line
            if current_line_width + space_width + word_width <= max_row_width:
                current_line.append(word)
                current_line_width += space_width + word_width
            else:
                # Finalize current line
                current_lines.append(current_line)
                current_line = [word]
                current_line_width = word_width
                
                # When we have 2 lines, finalize chunk
                if len(current_lines) >= 2:
                    chunks.append(current_lines)
                    current_lines = []
        
        # Add remaining lines
        if current_line:
            current_lines.append(current_line)
        if current_lines:
            chunks.append(current_lines)
        
        # Return the last chunk (max 2 lines)
        return chunks[-1][-2:] if chunks else []

    def _add_dynamic_captions(self, frame, current_frame):
        """
        Add captions with proper highlighting for the active word.
        Only show English captions (translated text).
        """
        display_words = self._get_current_and_previous_words(current_frame)

        if not display_words:
            return frame

        pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_img)
        font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
        
        text_rows = self._format_text_two_rows(display_words)
        frame_height, frame_width = frame.shape[:2]

        test_bbox = font.getbbox("Test")
        line_height = test_bbox[3] - test_bbox[1] + 10
        
        # Calculate total height - English only
        total_height = len(text_rows) * line_height

        # Find text position
        text_x, text_y_base = self._find_optimal_text_position_pil(frame, total_height, frame_width * 0.8)

        # Draw each row
        for i, row in enumerate(text_rows):
            current_y = text_y_base - ((len(text_rows) - 1 - i) * line_height)
            current_x = text_x
            
            for word in row:
                is_active = word["start_frame"] <= current_frame < word["end_frame"]

                word_bbox = font.getbbox(word["text"])
                word_width = word_bbox[2] - word_bbox[0]

                # Draw text with shadow for better visibility
                shadow_offsets = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
                for offset_x, offset_y in shadow_offsets:
                    draw.text(
                        (current_x + offset_x, current_y + offset_y),
                        word["text"],
                        font=font,
                        fill=TEXT_SHADOW_COLOR
                    )

                text_color = ACTIVE_TEXT_COLOR if is_active else (255, 255, 255)
                draw.text(
                    (current_x, current_y),
                    word["text"],
                    font=font,
                    fill=text_color
                )

                space_bbox = font.getbbox(" ")
                space_width = space_bbox[2] - space_bbox[0]
                current_x += word_width + space_width

        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

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