# seo_utils/local_video_seo.py

from faster_whisper import WhisperModel
from pydub import AudioSegment
import os
import json
import openai
from django.core.exceptions import ValidationError
from django.conf import settings
from typing import Optional, Dict, Any

class LocalVideoSEOGenerator:
    def __init__(self, openai_api_key: Optional[str] = None):
        """
        Initialize the Local Video SEO Generator with OpenAI API key.
        If not provided, will attempt to get from Django settings.
        """
        self.openai_api_key = openai_api_key or getattr(settings, 'OPENAI_API_KEY', None)
        
        if not self.openai_api_key:
            raise ValidationError("OpenAI API key is required")

    def validate_file(self, file_path: str) -> None:
        """Validate if the file exists and is a valid media file."""
        if not os.path.exists(file_path):
            raise ValidationError("File does not exist")
        
        # Add basic media file validation
        valid_extensions = {'.mp4', '.mp3', '.wav', '.avi', '.mov', '.m4a', '.aac'}
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext not in valid_extensions:
            raise ValidationError(f"Unsupported file format. Supported formats: {', '.join(valid_extensions)}")

    def transcribe_video(self, file_path: str) -> str:
        """Transcribe video/audio file using Faster Whisper."""
        try:
            # Convert audio to WAV using pydub
            audio = AudioSegment.from_file(file_path)
            wav_file = file_path + ".wav"
            audio.export(wav_file, format="wav")

            # Load Whisper model
            model = WhisperModel("base", device="cpu")
            
            # Transcribe
            segments, _ = model.transcribe(wav_file, beam_size=5)
            transcript = " ".join([segment.text for segment in segments])

            # Cleanup
            os.remove(wav_file)

            if not transcript:
                raise ValidationError("No speech detected in the video")

            return transcript

        except Exception as e:
            raise ValidationError(f"Error transcribing video: {str(e)}")

    def generate_seo_content(self, transcript: str) -> Dict[str, Any]:
        """Generate SEO content using OpenAI API."""
        try:
            client = openai.OpenAI(api_key=self.openai_api_key)
            prompt = f"""
                Analyze the following video transcript and:
                1. Extract the top 10 keywords.
                2. Generate an optimized title (less than 65 characters).
                3. Create an engaging description.
                4. Generate related tags for the video.

                Transcript:
                {transcript}

                Provide the results in the following JSON format:
                {{
                    "keywords": ["keyword1", "keyword2", ..., "keyword10"],
                    "title": "Generated Title",
                    "description": "Generated Description",
                    "tags": ["tag1", "tag2", ..., "tag10"]
                }}
                """

            completion = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an SEO expert."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            response_content = completion.choices[0].message.content
            if response_content.startswith("```"):
                response_content = response_content.strip("```json").strip("```")

            content = json.loads(response_content)
            
            # Validate response structure
            required_keys = {"keywords", "title", "description", "tags"}
            if not all(key in content for key in required_keys):
                raise ValidationError("Invalid response format from OpenAI API")

            return content

        except json.JSONDecodeError as e:
            raise ValidationError(f"Error parsing OpenAI response: {str(e)}")
        except Exception as e:
            raise ValidationError(f"Error generating SEO content: {str(e)}")

    def process_video(self, file_path: str) -> Dict[str, Any]:
        """Main method to process a video file and generate SEO content."""
        try:
            # Validate file
            self.validate_file(file_path)
            
            # Get transcript
            transcript = self.transcribe_video(file_path)
            
            # Generate SEO content
            seo_content = self.generate_seo_content(transcript)
            
            return {
                "success": True,
                "transcript": transcript,
                "seo_content": seo_content
            }

        except ValidationError as e:
            raise e
        except Exception as e:
            raise ValidationError(f"Error processing video: {str(e)}")