# seo_utils/youtube_seo.py

import googleapiclient.discovery
import re
import yt_dlp
from faster_whisper import WhisperModel
from pydub import AudioSegment
import tempfile
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
import json
import os
from django.conf import settings
from typing import Optional, Dict, Any
import openai
from django.core.exceptions import ValidationError

class YouTubeSEOGenerator:
    def __init__(self, youtube_api_key: Optional[str] = None, openai_api_key: Optional[str] = None):
        """
        Initialize the YouTube SEO Generator with API keys.
        If not provided, will attempt to get from Django settings.
        """
        self.youtube_api_key = youtube_api_key or getattr(settings, 'YOUTUBE_API_KEY', None)
        self.openai_api_key = openai_api_key or getattr(settings, 'OPENAI_API_KEY', None)
        
        if not self.youtube_api_key:
            raise ValidationError("YouTube API key is required")
        if not self.openai_api_key:
            raise ValidationError("OpenAI API key is required")

    def extract_video_id(self, url: str) -> Optional[str]:
        """Extracts the video ID from a YouTube URL."""
        try:
            parsed_url = urlparse(url)
            if "youtube.com" in parsed_url.netloc:
                query_params = parse_qs(parsed_url.query)
                return query_params.get('v', [None])[0]
            elif "youtu.be" in parsed_url.netloc:
                return parsed_url.path.strip("/")
            else:
                raise ValidationError("Invalid YouTube URL")
        except Exception as e:
            raise ValidationError(f"Error parsing URL: {str(e)}")

    def get_video_duration(self, video_id: str) -> Optional[float]:
        """Get video duration in minutes."""
        try:
            youtube = googleapiclient.discovery.build(
                "youtube", "v3", 
                developerKey=self.youtube_api_key
            )
            request = youtube.videos().list(part="contentDetails", id=video_id)
            response = request.execute()
            
            if not response.get("items"):
                raise ValidationError("Video not found")
                
            video_details = response["items"][0]
            duration = video_details["contentDetails"]["duration"]
            match = re.match(r'PT(\d+H)?(\d+M)?(\d+S)?', duration)
            hours = int(match.group(1).replace('H', '') if match.group(1) else 0)
            minutes = int(match.group(2).replace('M', '') if match.group(2) else 0)
            seconds = int(match.group(3).replace('S', '') if match.group(3) else 0)
            
            return hours * 60 + minutes + seconds / 60
            
        except Exception as e:
            raise ValidationError(f"Error getting video duration: {str(e)}")
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
    def process_video_shortform(self, file_path: str) -> Dict[str, Any]:
        """Main method to process a video file and generate SEO content."""
        try:
            # Validate file
            self.validate_file(file_path)
            
            # Get transcript
            transcript = self.transcribe_video(file_path)
            
            # Generate SEO content
            seo_content = self.generate_seo_content(transcript)
            
            return seo_content

        except ValidationError as e:
            raise e
        except Exception as e:
            raise ValidationError(f"Error processing video: {str(e)}")
    def download_and_transcribe(self, youtube_url: str) -> Optional[str]:
        """Download and transcribe video using Faster Whisper."""
        try:
            ydl_opts = {
                'format': 'bestaudio/best',
                'extractaudio': True,
                'audioquality': 1,
                'outtmpl': tempfile.mktemp(),
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(youtube_url, download=True)
                audio_file = ydl.prepare_filename(info_dict)

            audio = AudioSegment.from_file(audio_file)
            wav_file = audio_file + ".wav"
            audio.export(wav_file, format="wav")

            model = WhisperModel("base", device="cpu")
            segments, _ = model.transcribe(wav_file, beam_size=5)
            transcript = " ".join([segment.text for segment in segments])

            # Cleanup
            os.remove(audio_file)
            os.remove(wav_file)

            return transcript

        except Exception as e:
            raise ValidationError(f"Error in transcription: {str(e)}")

    def get_youtube_transcript(self, video_id: str, video_length: float) -> Optional[str]:
        """Get transcript from YouTube API."""
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Try to get manual English transcript first
            for transcript in transcript_list:
                if not transcript.is_generated and transcript.language_code == 'en':
                    manual_transcript = transcript.fetch()
                    if isinstance(manual_transcript, list):
                        return " ".join([segment['text'] for segment in manual_transcript])

            # Fall back to auto-generated transcript for longer videos
            if video_length > 15:
                auto_transcript = transcript_list.find_generated_transcript(['en'])
                if auto_transcript:
                    return " ".join([segment['text'] for segment in auto_transcript.fetch()])
            
            return None

        except Exception as e:
            raise ValidationError(f"Error fetching YouTube transcript: {str(e)}")
    def validate_file(self, file_path: str) -> None:
        """Validate if the file exists and is a valid media file."""
        if not os.path.exists(file_path):
            raise ValidationError("File does not exist")
        
        # Add basic media file validation
        valid_extensions = {'.mp4', '.mp3', '.wav', '.avi', '.mov', '.m4a', '.aac'}
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext not in valid_extensions:
            raise ValidationError(f"Unsupported file format. Supported formats: {', '.join(valid_extensions)}")
    def generate_seo_content(self, transcript: str) -> Dict[str, Any]:
        """Generate SEO content using OpenAI API."""
        try:
            client = openai.OpenAI(api_key=self.openai_api_key)
            prompt = f"""
                Analyze the following YouTube video transcript and:
                1. Extract the top 10 keywords.
                2. Generate an optimized title (less than 65 characters).
                3. Create an engaging description.
                4. Generate related tags for the video.

                Summarized Transcript:
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
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an SEO expert."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            response_content = completion.choices[0].message.content
            if response_content.startswith("```"):
                response_content = response_content.strip("```json").strip("```")

            return json.loads(response_content)

        except Exception as e:
            raise ValidationError(f"Error generating SEO content: {str(e)}")

    def process_video(self, youtube_url: str) -> Dict[str, Any]:
        """Main method to process a YouTube video and generate SEO content."""
        try:
            video_id = self.extract_video_id(youtube_url)
            if not video_id:
                raise ValidationError("Could not extract video ID")

            video_length = self.get_video_duration(video_id)
            if not video_length:
                raise ValidationError("Could not get video duration")

            # Try to get transcript from YouTube first
            transcript = self.get_youtube_transcript(video_id, video_length)
            
            # If no YouTube transcript and video is short, use Whisper
            if not transcript and video_length <= 15:
                transcript = self.download_and_transcribe(youtube_url)

            if not transcript:
                raise ValidationError("Could not obtain transcript")

            # Generate SEO content
            seo_content = self.generate_seo_content(transcript)
            if not seo_content:
                raise ValidationError("Could not generate SEO content")

            return seo_content

        except ValidationError as e:
            raise e
        except Exception as e:
            raise ValidationError(f"Error processing video: {str(e)}")