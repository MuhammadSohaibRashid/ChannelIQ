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

    def analyze_trending_keywords(self, topic: str) -> List[str]:
        """Get trending keywords related to the topic from Google Trends."""
        try:
            # This would ideally use pytrends, but for illustration we'll use a simpler approach
            # This is a placeholder - would be implemented with proper API access
            return []
        except Exception:
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

    def generate_chapters(self, 
                     transcript_data: Dict[str, Any], 
                     video_length_seconds: float,
                     num_chapters: int = 8) -> List[Dict[str, Any]]:
        """Generate optimal chapter markers based on transcript segments."""
        segments = transcript_data["segments"]
        
        # Check if segments is empty and handle appropriately
        if not segments:
            # Return basic chapter structure if no segments
            return [{"time": "00:00", "seconds": 0, "segment_index": 0}]
        
        if len(segments) < num_chapters:
            # Not enough segments for meaningful chapters
            num_chapters = max(3, len(segments) // 2)
        
        # Option 1: Equal time distribution
        chapter_length = video_length_seconds / num_chapters
        chapter_times = [i * chapter_length for i in range(num_chapters)]
        chapter_times.append(video_length_seconds)  # Add end marker
        
        # Find segments closest to desired chapter times
        chapters = []
        for i in range(num_chapters):
            target_time = chapter_times[i]
            
            # Find segment closest to target time
            # Add check to ensure segments is not empty
            if segments:
                closest_segment = min(segments, key=lambda x: abs(x["start"] - target_time))
                
                # Don't use the very first segment for chapter 1 (that's always "introduction")
                if i == 0:
                    chapters.append({
                        "time": self._format_timestamp(0),
                        "seconds": 0,
                        "segment_index": 0
                    })
                else:
                    chapters.append({
                        "time": self._format_timestamp(closest_segment["start"]),
                        "seconds": closest_segment["start"],
                        "segment_index": segments.index(closest_segment)
                    })
            else:
                # Fallback if segments is somehow empty
                chapters.append({
                    "time": self._format_timestamp(target_time),
                    "seconds": target_time,
                    "segment_index": 0
                })
        
        return chapters

    def generate_chapter_titles(self, 
                          transcript_data: Dict[str, Any],
                          chapters: List[Dict[str, Any]],
                          video_title: str) -> List[Dict[str, Any]]:
        """Generate descriptive chapter titles based on content."""
        try:
            client = openai.OpenAI(api_key=self.openai_api_key)
            
            segments = transcript_data["segments"]
            if not segments:
                # Return basic titles if no segments
                return [{"time": ch["time"], "title": "Introduction" if i == 0 else f"Key Point {i}", "seconds": ch["seconds"]} 
                        for i, ch in enumerate(chapters)]
                        
            chapter_contexts = []
            
            # Prepare context segments for each chapter
            for i, chapter in enumerate(chapters):
                start_idx = chapter.get("segment_index", 0)
                
                # Determine end index (next chapter or end of video)
                if i < len(chapters) - 1 and i + 1 < len(chapters) and "segment_index" in chapters[i+1]:
                    end_idx = chapters[i+1]["segment_index"]
                else:
                    end_idx = len(segments) - 1
                
                # Ensure indices are valid
                start_idx = max(0, min(start_idx, len(segments) - 1))
                end_idx = max(0, min(end_idx, len(segments) - 1))
                
                # Get segment text for context
                # Take a sample of segments (not just first 5)
                sample_size = min(5, max(1, end_idx - start_idx + 1))
                
                # Get evenly distributed sample if segment range is large
                if end_idx - start_idx + 1 > sample_size:
                    sample_indices = np.linspace(start_idx, end_idx, sample_size, dtype=int)
                    context_segments = [segments[idx] for idx in sample_indices]
                else:
                    context_segments = segments[start_idx:end_idx+1]
                    
                context_text = " ".join([seg["text"] for seg in context_segments])
                
                # Format for prompt
                chapter_contexts.append({
                    "timestamp": chapter["time"],
                    "context": context_text[:500]  # Limit context length 
                })
            
            # Create enhanced prompt with more detailed instructions
            prompt = f"""
    Create descriptive and engaging chapter titles for a video with the following timestamps.
    The video title is: "{video_title}"

    Guidelines:
    - Create SPECIFIC and DESCRIPTIVE titles (3-6 words) that clearly tell viewers what each section covers
    - Use active, engaging language that creates interest
    - AVOID generic titles like "Introduction" (except for 00:00), "Conclusion", or just "Chapter X"
    - Each title should communicate a clear benefit or topic
    - Make titles helpful for navigation and skimming

    Here are the timestamps with context from each section:

    {json.dumps(chapter_contexts, indent=2)}

    Return ONLY a JSON array with objects containing:
    - time: the timestamp string
    - title: your descriptive title (3-6 words)

    Example format:
    [
    {{"time": "00:00", "title": "The Hidden Cost of Bad Habits"}},
    {{"time": "03:45", "title": "Reward-Based Learning Cycle"}},
    ...
    ]
    """

            # Use more capable model with better instructions
            completion = client.chat.completions.create(
                model="gpt-4o-mini",  # Use more capable model for better titles
                messages=[
                    {"role": "system", "content": "You are an expert YouTube content creator who specializes in creating highly descriptive, specific chapter titles that perfectly summarize video sections."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7  # Slightly higher creativity
            )
            
            response_content = completion.choices[0].message.content
            try:
                chapter_data = json.loads(response_content)
                
                # Make sure we got an array (handle different response formats)
                if isinstance(chapter_data, dict) and "chapters" in chapter_data:
                    chapter_data = chapter_data["chapters"]
                elif isinstance(chapter_data, dict):
                    # Convert dictionary to list if needed
                    chapter_data = [{"time": k, "title": v} for k, v in chapter_data.items()]
                    
                # Merge chapter titles with existing chapter data
                result_chapters = []
                for i, chapter in enumerate(chapters):
                    if i < len(chapter_data):
                        matched_chapter = next((ch for ch in chapter_data if ch["time"] == chapter["time"]), None)
                        if matched_chapter:
                            title = matched_chapter["title"]
                        else:
                            title = chapter_data[i]["title"]
                    else:
                        # Fallback with meaningful titles instead of just "Chapter X"
                        if i == 0:
                            title = "Introduction & Overview"
                        elif i == len(chapters) - 1:
                            title = "Key Takeaways & Conclusion"
                        else:
                            title = f"Key Concept {i}"
                    
                    result_chapters.append({
                        "time": chapter["time"],
                        "title": title,
                        "seconds": chapter["seconds"]
                    })
                    
                return result_chapters
                
            except (json.JSONDecodeError, KeyError, TypeError, IndexError) as json_err:
                print(f"Error parsing chapter titles JSON: {str(json_err)}")
                print(f"Raw response: {response_content}")
                # Fall through to fallback below
                
        except Exception as e:
            print(f"Error generating chapter titles: {str(e)}")
            
        # Fallback to more descriptive generic titles rather than just "Chapter X"
        fallback_titles = [
            "Introduction & Overview",
            "Problem Definition",
            "Key Concept Explained", 
            "Practical Application",
            "Research Findings",
            "Expert Insights",
            "Case Study Example",
            "Summary & Takeaways"
        ]
        
        return [{"time": ch["time"], 
             "title": fallback_titles[i] if i < len(fallback_titles) else f"Key Point {i+1}", 
             "seconds": ch["seconds"]} 
            for i, ch in enumerate(chapters)]

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
    - Primary keyword (most important target)
    - Secondary keywords (5-7 supporting terms)
    - Long-tail variations (3-5 specific phrases)
    - Trending keywords related to topic

    Format your response as JSON with the following structure:
    {{
        "title": "Optimized title for search and CTR",
        "description": "Full optimized description with proper line breaks, timestamps, and CTAs",
        "tags": ["tag1", "tag2", ... "tag20"],
        "keywords": {{
            "primary": "main keyword",
            "secondary": ["keyword1", "keyword2", ... "keyword7"],
            "long_tail": ["long tail phrase 1", "long tail phrase 2", ... "long tail phrase 5"]
        }}
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
            
    def process_video_shortform(self, file_path: str) -> Dict[str, Any]:
        """Enhanced method to process a video file and generate SEO content for short-form videos."""
        try:
            # Validate file
            self.validate_file(file_path)
            
            # Get transcript
            transcript_data = self.transcribe_video(file_path)
            
            # Process with special considerations for short-form content
            # For short-form, we use a different prompt strategy
            system_prompt = """You are an expert in short-form video SEO optimization for platforms like YouTube Shorts, TikTok, and Instagram Reels. 
Your goal is to maximize discoverability, engagement, and virality potential."""
            
            client = openai.OpenAI(api_key=self.openai_api_key)
            
            prompt = f"""
Analyze this short-form video transcript and create optimized metadata:

TRANSCRIPT:
{transcript_data["text"]}

CREATE:
1. 1 attention-grabbing title (under 60 chars)
2. Engaging description with hooks (under 150 chars)
3. 15-20 trending hashtags in this niche
4. 5-7 primary keywords to target

FORMAT RESPONSE AS JSON:
{{
    "title", "Engaging title under 60 chars",
    "description": "Engaging description with hooks",
    "hashtags": ["#tag1", "#tag2", ...],
    "keywords": ["keyword1", "keyword2", ...]
}}

OPTIMIZATION STRATEGY:
- Focus on trending sounds/topics
- Use hook-based titles ("Wait for it", "Watch until end")
- Include emotion-triggering elements
- Target algorithm-favored terms
- Optimize for high CTR and completion rate
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
            raise ValidationError(f"Error processing short-form video: {str(e)}")