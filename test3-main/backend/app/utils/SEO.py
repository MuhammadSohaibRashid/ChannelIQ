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
from typing import Optional, Dict, Any, List, Tuple
import openai
from django.core.exceptions import ValidationError
import requests
from bs4 import BeautifulSoup
import tiktoken
import numpy as np
from datetime import timedelta

class EnhancedYouTubeSEOGenerator:
    def __init__(self, youtube_api_key: Optional[str] = None, openai_api_key: Optional[str] = None):
        """
        Initialize the Enhanced YouTube SEO Generator with API keys.
        If not provided, will attempt to get from Django settings.
        """
        self.youtube_api_key = youtube_api_key or getattr(settings, 'YOUTUBE_API_KEY', None)
        self.openai_api_key = openai_api_key or getattr(settings, 'OPENAI_API_KEY', None)
        
        if not self.youtube_api_key:
            raise ValidationError("YouTube API key is required")
        if not self.openai_api_key:
            raise ValidationError("OpenAI API key is required")
        
        # Initialize token counter for OpenAI
        self.encoder = tiktoken.encoding_for_model("gpt-4o")

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

    def get_video_details(self, video_id: str) -> Dict[str, Any]:
        """Get comprehensive video details including title, channel, views, etc."""
        try:
            youtube = googleapiclient.discovery.build(
                "youtube", "v3", 
                developerKey=self.youtube_api_key
            )
            request = youtube.videos().list(
                part="snippet,contentDetails,statistics", 
                id=video_id
            )
            response = request.execute()
            
            if not response.get("items"):
                raise ValidationError("Video not found")
                
            video_data = response["items"][0]
            
            # Extract duration
            duration = video_data["contentDetails"]["duration"]
            match = re.match(r'PT(\d+H)?(\d+M)?(\d+S)?', duration)
            hours = int(match.group(1).replace('H', '') if match.group(1) else 0)
            minutes = int(match.group(2).replace('M', '') if match.group(2) else 0)
            seconds = int(match.group(3).replace('S', '') if match.group(3) else 0)
            duration_minutes = hours * 60 + minutes + seconds / 60
            total_seconds = hours * 3600 + minutes * 60 + seconds
            
            # Get channel details
            channel_id = video_data["snippet"]["channelId"]
            channel_request = youtube.channels().list(
                part="snippet,statistics",
                id=channel_id
            )
            channel_response = channel_request.execute()
            channel_data = channel_response["items"][0] if channel_response.get("items") else {}
            
            return {
                "title": video_data["snippet"]["title"],
                "description": video_data["snippet"]["description"],
                "tags": video_data["snippet"].get("tags", []),
                "published_at": video_data["snippet"]["publishedAt"],
                "channel_title": video_data["snippet"]["channelTitle"],
                "duration_minutes": duration_minutes,
                "duration_seconds": total_seconds,
                "view_count": int(video_data["statistics"].get("viewCount", 0)),
                "like_count": int(video_data["statistics"].get("likeCount", 0)),
                "comment_count": int(video_data["statistics"].get("commentCount", 0)),
                "channel_subscribers": int(channel_data.get("statistics", {}).get("subscriberCount", 0)),
                "channel_videos": int(channel_data.get("statistics", {}).get("videoCount", 0)),
                "thumbnail_url": video_data["snippet"]["thumbnails"]["high"]["url"]
            }
            
        except Exception as e:
            raise ValidationError(f"Error getting video details: {str(e)}")

    def transcribe_video(self, file_path: str) -> Dict[str, Any]:
        """Transcribe video/audio file using Faster Whisper and return transcript with timestamps."""
        try:
            # Convert audio to WAV using pydub
            audio = AudioSegment.from_file(file_path)
            wav_file = file_path + ".wav"
            audio.export(wav_file, format="wav")

            # Load Whisper model - using larger model for better accuracy
            model = WhisperModel("medium", device="cpu")
            
            # Transcribe with improved settings and get word timestamps
            segments, _ = model.transcribe(wav_file, beam_size=5, vad_filter=True)
            
            # Create full transcript text
            transcript_text = " ".join([segment.text for segment in segments])
            
            # Create segments with timestamps
            transcript_segments = []
            for segment in segments:
                transcript_segments.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text
                })

            # Cleanup
            os.remove(wav_file)

            if not transcript_text:
                raise ValidationError("No speech detected in the video")

            return {
                "text": transcript_text,
                "segments": transcript_segments
            }

        except Exception as e:
            raise ValidationError(f"Error transcribing video: {str(e)}")

    def download_and_transcribe(self, youtube_url: str) -> Dict[str, Any]:
        """Download and transcribe video using Faster Whisper with timestamps."""
        try:
            ydl_opts = {
                'format': 'bestaudio/best',
                'extractaudio': True,
                'audioquality': 0,  # Better quality
                'outtmpl': tempfile.mktemp(),
                'quiet': True
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(youtube_url, download=True)
                audio_file = ydl.prepare_filename(info_dict)

            audio = AudioSegment.from_file(audio_file)
            wav_file = audio_file + ".wav"
            audio.export(wav_file, format="wav")

            # Using larger model for better accuracy
            model = WhisperModel("medium", device="cpu")
            segments, _ = model.transcribe(wav_file, beam_size=5, vad_filter=True)
            
            # Create full transcript text
            transcript_text = " ".join([segment.text for segment in segments])
            
            # Create segments with timestamps
            transcript_segments = []
            for segment in segments:
                transcript_segments.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text
                })

            # Cleanup
            os.remove(audio_file)
            os.remove(wav_file)

            return {
                "text": transcript_text,
                "segments": transcript_segments
            }

        except Exception as e:
            raise ValidationError(f"Error in transcription: {str(e)}")

    def get_youtube_transcript_with_timestamps(self, video_id: str) -> Dict[str, Any]:
        """Get transcript with timestamps from YouTube API."""
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Try to get manual English transcript first
            segments = []
            transcript_text = ""
            
            for transcript in transcript_list:
                if not transcript.is_generated and transcript.language_code == 'en':
                    transcript_data = transcript.fetch()
                    if isinstance(transcript_data, list):
                        transcript_text = " ".join([segment['text'] for segment in transcript_data])
                        segments = transcript_data
                        break

            # Try auto-generated English transcript if no manual transcript
            if not transcript_text:
                auto_transcript = transcript_list.find_generated_transcript(['en'])
                if auto_transcript:
                    transcript_data = auto_transcript.fetch()
                    transcript_text = " ".join([segment['text'] for segment in transcript_data])
                    segments = transcript_data
            
            # Try other languages and translate if needed
            if not transcript_text:
                for transcript in transcript_list:
                    translated_data = transcript.translate('en').fetch()
                    if translated_data:
                        transcript_text = " ".join([segment['text'] for segment in translated_data])
                        segments = translated_data
                        break
            
            if not transcript_text:
                return None
                
            # Convert YouTube transcript format to our format
            formatted_segments = []
            for segment in segments:
                formatted_segments.append({
                    "start": segment['start'],
                    "end": segment['start'] + segment['duration'],
                    "text": segment['text']
                })
                
            return {
                "text": transcript_text,
                "segments": formatted_segments
            }

        except Exception as e:
            # Return None to allow fallback to Whisper transcription
            return None

    def validate_file(self, file_path: str) -> None:
        """Validate if the file exists and is a valid media file."""
        if not os.path.exists(file_path):
            raise ValidationError("File does not exist")
        
        # Add comprehensive media file validation
        valid_extensions = {'.mp4', '.mp3', '.wav', '.avi', '.mov', '.m4a', '.aac', '.mkv', '.flv', '.webm'}
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext not in valid_extensions:
            raise ValidationError(f"Unsupported file format. Supported formats: {', '.join(valid_extensions)}")
            
        # Check file size limit (500MB)
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > 500:
            raise ValidationError(f"File too large: {file_size_mb:.2f}MB. Maximum file size: 500MB")

    def get_competitor_videos(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Get top competitor videos for a given query."""
        try:
            youtube = googleapiclient.discovery.build(
                "youtube", "v3",
                developerKey=self.youtube_api_key
            )
            
            request = youtube.search().list(
                part="snippet",
                q=query,
                type="video",
                maxResults=max_results,
                order="viewCount"
            )
            
            response = request.execute()
            competitor_videos = []
            
            for item in response.get("items", []):
                video_id = item["id"]["videoId"]
                
                # Get full video details
                video_details = self.get_video_details(video_id)
                competitor_videos.append({
                    "video_id": video_id,
                    "title": video_details["title"],
                    "description": video_details["description"],
                    "tags": video_details.get("tags", []),
                    "view_count": video_details["view_count"],
                    "channel_title": video_details["channel_title"]
                })
                
            return competitor_videos
                
        except Exception as e:
            # Log error but continue with process
            print(f"Error fetching competitor videos: {str(e)}")
            return []

    

    def analyze_comments(self, video_id: str) -> List[str]:
        """Analyze top comments to extract user engagement and sentiment."""
        try:
            youtube = googleapiclient.discovery.build(
                "youtube", "v3",
                developerKey=self.youtube_api_key
            )
            
            # Get the top 100 comments
            request = youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=100,
                order="relevance"
            )
            
            response = request.execute()
            comments = []
            
            for item in response.get("items", []):
                comment_text = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
                comments.append(comment_text)
                
            return comments
                
        except Exception:
            # Return empty list if comments are disabled or error occurs
            return []

    def trim_to_token_limit(self, text: str, max_tokens: int = 128000) -> str:
        """Trim text to fit within token limit for OpenAI."""
        tokens = self.encoder.encode(text)
        if len(tokens) <= max_tokens:
            return text
        
        # Trim to token limit with margin for other content
        return self.encoder.decode(tokens[:max_tokens])
    
    def extract_chapters_from_description(self, description: str) -> List[Dict[str, Any]]:
        """Extract existing chapter timestamps from a video description."""
        # Look for timestamp patterns like 0:00, 01:23, 1:23:45
        timestamp_pattern = r'(\d+:)?(\d+:\d+)\s*[-–—:]\s*(.+?)(?=\n|$)'
        matches = re.finditer(timestamp_pattern, description)
        
        chapters = []
        for match in matches:
            timestamp = match.group(1) + match.group(2) if match.group(1) else match.group(2)
            title = match.group(3).strip()
            
            # Convert timestamp to seconds
            parts = timestamp.split(':')
            if len(parts) == 2:
                seconds = int(parts[0]) * 60 + int(parts[1])
            else:
                seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                
            chapters.append({
                "time": timestamp,
                "title": title,
                "seconds": seconds
            })
            
        return chapters

    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds to MM:SS or HH:MM:SS format."""
        time_obj = timedelta(seconds=int(seconds))
        if time_obj.total_seconds() < 3600:
            # MM:SS format
            minutes, seconds = divmod(time_obj.total_seconds(), 60)
            return f"{int(minutes):01d}:{int(seconds):02d}"
        else:
            # HH:MM:SS format
            hours, remainder = divmod(time_obj.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{int(hours):01d}:{int(minutes):02d}:{int(seconds):02d}"

    

    def format_chapters_for_description(self, chapters: List[Dict[str, Any]]) -> str:
        """Format chapters for YouTube description."""
        description_chapters = "\n\n📋 CHAPTERS\n"
        for chapter in chapters:
            description_chapters += f"{chapter['time']} - {chapter['title']}\n"
        return description_chapters
    
    def generate_optimized_seo_content(self, 
                                 transcript_data: Dict[str, Any], 
                                 video_details: Dict[str, Any],
                                 competitor_videos: List[Dict[str, Any]],
                                 comments: List[str],
                                 ) -> Dict[str, Any]:
        """Generate highly optimized SEO content using OpenAI API with enhanced prompting and chapters."""
        try:
            client = openai.OpenAI(api_key=self.openai_api_key)
            
            # Prepare competitor analysis
            competitor_analysis = ""
            if competitor_videos:
                competitor_analysis = "Top competitor videos:\n"
                for idx, video in enumerate(competitor_videos[:3], 1):
                    competitor_analysis += f"{idx}. Title: {video['title']}\n"
                    competitor_analysis += f"   Tags: {', '.join(video['tags'][:10])}\n"
                    competitor_analysis += f"   Views: {video['view_count']}\n"
                    
            # Prepare comment insights
            comment_insights = ""
            if comments:
                sample_comments = comments[:10]
                comment_insights = "Sample comments:\n" + "\n".join(f"- {comment}" for comment in sample_comments)
                
            # Trim transcript if too long
            transcript_summary = transcript_data["text"]
            
                
            system_prompt = """You are an expert YouTube SEO strategist with deep understanding of:
    1. YouTube ranking algorithms
    2. Click-through rate optimization
    3. Viewer engagement metrics
    4. Keyword research and optimization
    5. YouTube metadata optimization

    Your task is to analyze video content and create highly optimized YouTube SEO elements that will maximize:
    - Search visibility
    - Click-through rates
    - Viewer engagement
    - Watch time
    - Overall performance

    Apply proven YouTube SEO strategies that balance:
    - Clickability (high CTR without being clickbait)
    - Searchability (right keywords in the right places)
    - Engagement (content that encourages likes, comments, shares)
    - Watch time optimization (content that keeps viewers watching)
    """
            
            prompt = f"""
    ## VIDEO CONTENT ANALYSIS

    ### Transcript:
    {transcript_summary}

    ### Video Details:
    - Current Title: {video_details.get('title', 'N/A')}
    - Current Description: {video_details.get('description', 'N/A')}
    - Current Tags: {', '.join(video_details.get('tags', ['N/A']))}
    - Channel: {video_details.get('channel_title', 'N/A')}
    - Duration: {video_details.get('duration_minutes', 0):.1f} minutes
    - Views: {video_details.get('view_count', 0)}

    
    ### Competitive Analysis:
    {competitor_analysis}

    ### Audience Insights:
    {comment_insights}

    ## SEO OPTIMIZATION REQUIREMENTS:

    1. TITLE:
    - Create 1 title optimized for search and click-through
    - Keep under 60 characters
    - Include primary keywords early
    - Create curiosity or value proposition
    - Avoid clickbait but ensure high appeal

   2. DESCRIPTION:
- Write a compelling, SEO-optimized description (1500-2000 characters)
- First 150 characters should be highly optimized (visible in search)
- Include primary and secondary keywords naturally
- Include the chapters I provided exactly as formatted
- Include chapters in the following format:
   CHAPTERS
  00:00 - Chapter Title
  05:30 - Next Chapter Title
  etc.
- Add clear call-to-action
- Include relevant hashtags (5-10)

    3. TAGS:
    - Identify as many high-performing tags
    - Mix of:
    * Primary keywords (exact match)
    * Long-tail variations
    * Related topics
    * Trending terms
    * Competitor-targeting tags

    4. KEYWORD ANALYSIS:
    - Identify 5-7 primary keywords to target

    Format your response as JSON with the following structure:
    {{
        "title": "Optimized title for search and CTR",
        "description": "Full optimized description with proper line breaks, timestamps, and CTAs",
        "tags": ["tag1", "tag2", ... "tag20"],
        "keywords": ["keyword1", "keyword2", ...]
    }}

    IMPORTANT: For the description field, use literal newline characters (\\n) where line breaks should appear.
    """
            

            completion = client.chat.completions.create(
                model="gpt-4o-mini",  # Using the most capable model
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            response_content = completion.choices[0].message.content
            seo_content = json.loads(response_content)
            
            # Process description to ensure proper formatting is preserved
            if "description" in seo_content:
                # Make sure we're using the actual newline characters in the output
                # This step is crucial - JSON strings escape newlines as \n
                # but we need to ensure they're preserved when used in your application
                seo_content["description"] = seo_content["description"].replace("\\n", "\n")
            return seo_content

        except Exception as e:
            raise ValidationError(f"Error generating SEO content: {str(e)}")

    def process_video(self, youtube_url: str) -> Dict[str, Any]:
        """Enhanced main method to process a YouTube video and generate SEO content with chapters."""
        try:
            # Extract video ID
            video_id = self.extract_video_id(youtube_url)
            if not video_id:
                raise ValidationError("Could not extract video ID")

            # Get comprehensive video details
            video_details = self.get_video_details(video_id)
            if not video_details:
                raise ValidationError("Could not retrieve video details")

            # Try to get transcript with timestamps from YouTube first
            transcript_data = self.get_youtube_transcript_with_timestamps(video_id)
            
            # If no YouTube transcript and video is short enough, use Whisper
            if not transcript_data and video_details["duration_minutes"] <= 30:
                transcript_data = self.download_and_transcribe(youtube_url)

            if not transcript_data:
                raise ValidationError("Could not obtain transcript - please provide a video with captions or clear audio")

           

            # Get competitor videos based on video title
            competitor_videos = self.get_competitor_videos(video_details["title"])
            
            # Get video comments for additional context
            comments = self.analyze_comments(video_id)
            
            # Generate enhanced SEO content with chapters
            seo_content = self.generate_optimized_seo_content(
                transcript_data=transcript_data,
                video_details=video_details,
                competitor_videos=competitor_videos,
                comments=comments
            )
            
            if not seo_content:
                raise ValidationError("Could not generate SEO content")

            # Add original data for reference
            
            
            

            return seo_content

        except ValidationError as e:
            raise e
        except Exception as e:
            raise ValidationError(f"Error processing video: {str(e)}")
            
    def process_video_shortform_enhanced(self, 
                                  file_path: str, 
                                  original_video_details: Dict[str, Any] = None,
                                  original_transcript: Dict[str, Any] = None,
                                  competitor_videos: List[Dict[str, Any]] = None,
                                  comments: List[str] = None) -> Dict[str, Any]:
        """
        Enhanced method to process a short-form video with context from the original video.
        
        Args:
            file_path: Path to the shortform video file
            original_video_details: Details of the original video (if available)
            original_transcript: Transcript of the original video (if available)
            competitor_videos: List of competitor videos (if available)
            comments: List of comments from the original video (if available)
            
        Returns:
            Dict with optimized SEO content
        """
        try:
            # Validate file
            self.validate_file(file_path)
            
            # Get transcript for the shortform video
            shortform_transcript = self.transcribe_video(file_path)
            print("Transcript: ",shortform_transcript)
            # Extract additional context from original video data if available
            video_title = original_video_details.get('title', '') if original_video_details else ''
            video_description = original_video_details.get('description', '') if original_video_details else ''
            original_tags = original_video_details.get('tags', []) if original_video_details else []
            
            # Prepare competitor analysis
            competitor_analysis = ""
            if competitor_videos:
                competitor_analysis = "Top competitor videos:"
                for idx, video in enumerate(competitor_videos[:3], 1):
                    competitor_analysis += f"{idx}. Title: {video.get('title', 'Unknown')}"
                    competitor_analysis += f"   Tags: {', '.join(video.get('tags', [])[:10])}"
                    competitor_analysis += f"   Views: {video.get('view_count', 0)}"
            
            # Prepare comment insights
            comment_insights = ""
            if comments:
                sample_comments = comments[:10]
                comment_insights = "Sample comments:" + "".join(f"- {comment}" for comment in sample_comments)
            
            # Get original transcript summary if available
            original_transcript_text = ""
            if original_transcript and 'text' in original_transcript:
                original_transcript_text = original_transcript['text'][:1000] + "..." if len(original_transcript['text']) > 1000 else original_transcript['text']
            
            # Process with special considerations for short-form content with enhanced context
            system_prompt = """You are an expert in short-form video SEO optimization for platforms like YouTube Shorts, TikTok, and Instagram Reels. 
    Your goal is to maximize discoverability, engagement, and virality potential while maintaining content relevance and brand consistency."""
            
            client = openai.OpenAI(api_key=self.openai_api_key)
            
            prompt = f"""
    Analyze this short-form video clip transcript and create optimized metadata that's aligned with the original content:

    SHORTFORM TRANSCRIPT:
    {shortform_transcript["text"]}

    ORIGINAL VIDEO CONTEXT:
    Title: {video_title}
    Description: {video_description[:500]}... (truncated)
    Tags: {', '.join(original_tags[:15])}

    {f"ORIGINAL TRANSCRIPT EXCERPT:{original_transcript_text}" if original_transcript_text else ""}

    {competitor_analysis}

    {comment_insights}

    CREATE:
    1. 1 attention-grabbing title (under 60 chars)
    2. Engaging description with hooks and clear CTAs (under 150 chars)
    3. 15-20 trending hashtags in this niche
    4. 5-7 primary keywords to target
    5. A brief content strategy note (what works well in this niche)

    FORMAT RESPONSE AS JSON:
    {{
        "title", "Engaging title under 60 chars",
        "description": "Engaging description with hooks",
        "hashtags": ["#tag1", "#tag2", ...],
        "keywords": ["keyword1", "keyword2", ...],
        "content_strategy": "Brief strategy note on content optimization"
    }}

    OPTIMIZATION STRATEGY:
    - Ensure consistency with the original video's topic and branding
    - Focus on trending sounds/topics
    - Use hook-based titles ("Wait for it", "Watch until end")
    - Include emotion-triggering elements
    - Target algorithm-favored terms
    - Optimize for high CTR and completion rate
    - Leverage the original video's successful keywords/themes
    """

            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            response_content = completion.choices[0].message.content
            return json.loads(response_content)

        except ValidationError as e:
            raise e
        except Exception as e:
            raise ValidationError(f"Error processing short-form video with enhanced context: {str(e)}")