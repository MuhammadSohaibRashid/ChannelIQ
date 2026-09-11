import os
import tempfile
import re
import math
import base64
import cv2
import numpy as np
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import yt_dlp
from openai import OpenAI
from pydub import AudioSegment
from moviepy.editor import VideoFileClip
import ffmpeg
import logging
import requests
from PIL import Image
from io import BytesIO
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedVideoAnalyzer:
    """Improved class to handle comprehensive video analysis with context understanding"""
    
    def __init__(self, youtube_credentials=None, openai_api_key=None):
        self.youtube_credentials = youtube_credentials
        self.openai_api_key = openai_api_key
        
        if not openai_api_key:
            logger.warning("OpenAI API key not provided, some features won't work")
        
        # Create OpenAI client if key is provided
        self.client = OpenAI(api_key=openai_api_key) if openai_api_key else None
        
        # Initialize YouTube API client if credentials provided
        self.youtube = None
        if youtube_credentials:
            try:
                self.youtube = build('youtube', 'v3', credentials=youtube_credentials)
                logger.info("YouTube API client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize YouTube API client: {str(e)}")
    
    def analyze_video(self, video_url):
        """Main function to analyze video with improved context awareness"""
        if not self.openai_api_key:
            return {'status': 'error', 'message': 'OpenAI API key required'}

        # Create a temporary directory for files
        temp_dir = tempfile.mkdtemp()
        logger.info(f"Created temporary directory: {temp_dir}")
        
        try:
            # Extract video ID
            video_id = self._extract_video_id(video_url)
            if not video_id:
                return {'status': 'error', 'message': 'Invalid YouTube URL or could not extract video ID'}
            
            # Get video metadata using YouTube API
            logger.info(f"Getting video metadata for {video_id}")
            metadata = self._get_video_metadata(video_id)
            
            # Download video
            logger.info(f"Downloading video from {video_url}")
            video_path = self._download_video(video_url, temp_dir)
            
            # Extract audio
            logger.info("Extracting audio from video")
            audio_path = self._extract_audio(video_path, temp_dir)
            
            # Download thumbnail for analysis
            logger.info("Downloading thumbnail for analysis")
            thumbnail_path = self._download_thumbnail(metadata.get('thumbnail_url', ''), temp_dir)
            
            # Get transcript
            logger.info("Getting video transcript")
            transcript_result = self._get_video_transcript(video_url)
            if transcript_result['status'] != 'success':
                return transcript_result
                
            # Identify video content type
            logger.info("Identifying video content type")
            content_type_result = self._identify_content_type(
                transcript_result['transcript'], 
                metadata.get('title', ''), 
                metadata.get('description', '')
            )
            
            # Analyze video frames for quality and context
            logger.info("Analyzing video quality and context")
            video_analysis = self._enhanced_video_analysis(video_path, content_type_result['content_type'])
            
            # Analyze audio quality with context
            logger.info("Analyzing audio quality with context")
            audio_analysis = self._enhanced_audio_analysis(
                audio_path, 
                content_type_result['content_type']
            )
            
            # Analyze SEO metadata with context
            logger.info("Analyzing SEO metadata with context")
            seo_analysis = self._enhanced_seo_analysis(
                metadata, 
                thumbnail_path, 
                content_type_result['content_type'],
                transcript_result['transcript']
            )

            # Enhanced contextual transcript analysis
            logger.info("Performing enhanced transcript analysis")
            enhanced_transcript_analysis = self._enhanced_transcript_analysis(
                transcript_result['transcript'], 
                content_type_result['content_type'],
                metadata
            )
            
            # Generate comprehensive report
            logger.info("Generating comprehensive report")
            report = self._generate_comprehensive_report(
                metadata,
                content_type_result,
                enhanced_transcript_analysis,
                video_analysis,
                audio_analysis,
                seo_analysis
            )

            return {
                'status': 'success',
                'report': report,
                'content_type': content_type_result['content_type'],
                'content_details': content_type_result['details'],
                'transcript': self._truncate_text(transcript_result['transcript'], 1000),
                'transcript_analysis': enhanced_transcript_analysis,
                'video_analysis': video_analysis,
                'audio_analysis': audio_analysis,
                'seo_analysis': seo_analysis,
                'metadata': metadata
            }

        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}", exc_info=True)
            return {'status': 'error', 'message': f'Analysis failed: {str(e)}'}
        finally:
            # Cleanup
            try:
                self._cleanup_directory(temp_dir)
                logger.info(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as e:
                logger.error(f"Failed to clean up directory: {str(e)}")
    
    def _identify_content_type(self, transcript, title, description):
        """Identify the video content type and context-specific details"""
        if not self.client:
            return {
                'content_type': 'unknown',
                'details': 'Content type identification skipped: OpenAI API key not provided'
            }
            
        try:
            # Create a prompt to analyze content type
            prompt = f"""
Analyze this YouTube video's title, description, and transcript to determine its exact content type and context.

TITLE: {title}
DESCRIPTION: {self._truncate_text(description, 300)}
TRANSCRIPT SAMPLE: {self._truncate_text(transcript, 1000)}

First, identify which SINGLE PRIMARY content type this video belongs to:
1. Music/Song Video
2. Tutorial/How-to
3. Vlog/Personal
4. Review/Product
5. Educational/Informational
6. Gaming
7. Interview/Podcast
8. Comedy/Entertainment
9. News/Current Events
10. Marketing/Promotional
11. Documentary
12. Live Stream/Event
13. Unboxing
14. Q&A/AMA
15. Other (specify)

Then provide SPECIFIC CONTEXT about the video:
- If music video: genre, mood, artist type
- If tutorial: topic, complexity level, target audience
- If educational: subject, academic level, teaching style
- And so on for other content types

Format your response as a JSON object with these fields:
1. "content_type": The primary content type (ONE OF THE OPTIONS ABOVE)
2. "subtype": More specific categorization within that type
3. "target_audience": Who this content is for (age group, interest group, etc.)
4. "tone": The overall tone (formal, casual, energetic, serious, etc.)
5. "key_elements": Top 3 important elements in this content
6. "production_level": Amateur, semi-professional, or professional 
7. "context_notes": Any other important context about this content
"""

            # Get content type analysis
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert in video content analysis who can accurately identify content types and contexts from transcript and metadata. You always return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                max_tokens=800
            )
            
            # Extract content type analysis
            content_analysis = response.choices[0].message.content
            
            # Safely parse JSON response
            try:
                import json
                content_data = json.loads(content_analysis)
                return {
                    'content_type': content_data.get('content_type', 'unknown'),
                    'details': content_data
                }
            except Exception as e:
                logger.error(f"Error parsing content type JSON: {str(e)}")
                return {
                    'content_type': 'unknown',
                    'details': f"Error parsing content analysis: {str(e)}"
                }
                
        except Exception as e:
            logger.error(f"Content type identification failed: {str(e)}")
            return {
                'content_type': 'unknown',
                'details': f"Content type identification failed: {str(e)}"
            }
    
    def _get_video_metadata(self, video_id):
        """Get comprehensive video metadata with enhanced fields"""
        metadata = {
            'id': video_id,
            'title': '',
            'description': '',
            'tags': [],
            'category': '',
            'thumbnail_url': f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg',
            'view_count': 0,
            'like_count': 0,
            'comment_count': 0,
            'published_at': '',
            'channel_title': '',
            'channel_id': '',
            'duration': '',
            'privacy_status': '',
            'is_live': False,
            'length_seconds': 0,  # Added numeric duration
            'engagement_ratio': 0  # Added engagement metric
        }
        
        # Try to get metadata from YouTube API if available
        if self.youtube:
            try:
                video_response = self.youtube.videos().list(
                    part='snippet,contentDetails,statistics,status',
                    id=video_id
                ).execute()
                
                if video_response.get('items'):
                    video_data = video_response['items'][0]
                    snippet = video_data.get('snippet', {})
                    statistics = video_data.get('statistics', {})
                    content_details = video_data.get('contentDetails', {})
                    status = video_data.get('status', {})
                    
                    # Basic info
                    metadata['title'] = snippet.get('title', '')
                    metadata['description'] = snippet.get('description', '')
                    metadata['tags'] = snippet.get('tags', [])
                    metadata['category'] = snippet.get('categoryId', '')
                    metadata['published_at'] = snippet.get('publishedAt', '')
                    metadata['channel_title'] = snippet.get('channelTitle', '')
                    metadata['channel_id'] = snippet.get('channelId', '')
                    
                    # Statistics
                    metadata['view_count'] = int(statistics.get('viewCount', 0))
                    metadata['like_count'] = int(statistics.get('likeCount', 0))
                    metadata['comment_count'] = int(statistics.get('commentCount', 0))
                    
                    # Calculate engagement ratio (likes + comments per view)
                    if metadata['view_count'] > 0:
                        metadata['engagement_ratio'] = (metadata['like_count'] + metadata['comment_count']) / metadata['view_count']
                    
                    # Content details
                    metadata['duration'] = content_details.get('duration', '')
                    
                    # Convert ISO 8601 duration to seconds
                    try:
                        duration_str = content_details.get('duration', 'PT0S')
                        # Extract hours, minutes, seconds
                        hours = re.search(r'(\d+)H', duration_str)
                        minutes = re.search(r'(\d+)M', duration_str)
                        seconds = re.search(r'(\d+)S', duration_str)
                        
                        total_seconds = 0
                        if hours:
                            total_seconds += int(hours.group(1)) * 3600
                        if minutes:
                            total_seconds += int(minutes.group(1)) * 60
                        if seconds:
                            total_seconds += int(seconds.group(1))
                            
                        metadata['length_seconds'] = total_seconds
                    except Exception as e:
                        logger.error(f"Error parsing duration: {str(e)}")
                    
                    # Status
                    metadata['privacy_status'] = status.get('privacyStatus', '')
                    metadata['is_live'] = snippet.get('liveBroadcastContent', 'none') == 'live'
                    
                    # Get best thumbnail
                    thumbnails = snippet.get('thumbnails', {})
                    best_thumb = thumbnails.get('maxres') or thumbnails.get('high') or thumbnails.get('medium') or thumbnails.get('default')
                    if best_thumb:
                        metadata['thumbnail_url'] = best_thumb.get('url', metadata['thumbnail_url'])
                    
                    # Get video category name
                    try:
                        if metadata['category']:
                            category_response = self.youtube.videoCategories().list(
                                part='snippet',
                                id=metadata['category']
                            ).execute()
                            
                            if category_response.get('items'):
                                metadata['category_name'] = category_response['items'][0]['snippet'].get('title', '')
                    except Exception as e:
                        logger.error(f"Error getting category name: {str(e)}")
                    
                    logger.info(f"Successfully retrieved metadata for video {video_id}")
                else:
                    logger.warning(f"No metadata found for video {video_id}")
                    
            except Exception as e:
                logger.error(f"Failed to get video metadata from YouTube API: {str(e)}")
                # Fall back to scraping if API fails
        else:
            logger.warning("YouTube API client not available, using fallback methods")
            
            # Try to get basic info using yt-dlp as fallback
            try:
                ydl_opts = {'quiet': True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    video_info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
                    
                    metadata['title'] = video_info.get('title', '')
                    metadata['description'] = video_info.get('description', '')
                    metadata['tags'] = video_info.get('tags', [])
                    metadata['channel_title'] = video_info.get('uploader', '')
                    metadata['channel_id'] = video_info.get('channel_id', '')
                    metadata['view_count'] = int(video_info.get('view_count', 0))
                    metadata['like_count'] = int(video_info.get('like_count', 0))
                    metadata['comment_count'] = int(video_info.get('comment_count', 0))
                    metadata['published_at'] = video_info.get('upload_date', '')
                    metadata['length_seconds'] = int(video_info.get('duration', 0))
                    
                    # Calculate engagement ratio
                    if metadata['view_count'] > 0:
                        metadata['engagement_ratio'] = (metadata['like_count'] + metadata['comment_count']) / metadata['view_count']
                    
                    # Format duration as readable string
                    total_seconds = metadata['length_seconds']
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60
                    
                    if hours > 0:
                        metadata['duration'] = f"{hours}:{minutes:02d}:{seconds:02d}"
                    else:
                        metadata['duration'] = f"{minutes}:{seconds:02d}"
                    
                    # Get best thumbnail
                    thumbnails = video_info.get('thumbnails', [])
                    if thumbnails:
                        # Sort by resolution (width * height) if available
                        sorted_thumbs = sorted(
                            [t for t in thumbnails if 'width' in t and 'height' in t],
                            key=lambda x: x.get('width', 0) * x.get('height', 0),
                            reverse=True
                        )
                        if sorted_thumbs:
                            metadata['thumbnail_url'] = sorted_thumbs[0].get('url', metadata['thumbnail_url'])
                            
                    logger.info(f"Retrieved basic metadata using yt-dlp for video {video_id}")
            except Exception as e:
                logger.error(f"Failed to get metadata with yt-dlp: {str(e)}")
        
        return metadata
    
    def _download_thumbnail(self, thumbnail_url, output_dir):
        """Download thumbnail for analysis"""
        if not thumbnail_url:
            logger.warning("No thumbnail URL provided")
            return None
            
        try:
            thumbnail_path = os.path.join(output_dir, 'thumbnail.jpg')
            response = requests.get(thumbnail_url)
            
            if response.status_code == 200:
                with open(thumbnail_path, 'wb') as f:
                    f.write(response.content)
                    
                # Verify the image is valid
                try:
                    img = Image.open(thumbnail_path)
                    img.verify()  # Verify it's a valid image
                    logger.info(f"Successfully downloaded thumbnail to {thumbnail_path}")
                    return thumbnail_path
                except Exception as e:
                    logger.error(f"Downloaded file is not a valid image: {str(e)}")
                    return None
            else:
                logger.error(f"Failed to download thumbnail: HTTP status {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error downloading thumbnail: {str(e)}")
            return None

    def _enhanced_seo_analysis(self, metadata, thumbnail_path, content_type, transcript):
        """Analyze video metadata for SEO optimization with context awareness"""
        if not self.client:
            return {
                'status': 'error',
                'message': "⚠️ SEO analysis skipped: OpenAI API key not provided"
            }
            
        try:
            # Extract key phrases from transcript for keyword analysis
            keywords = self._extract_keywords_from_transcript(transcript)
            
            # Prepare prompt with metadata and content type context
            prompt = f"""
Analyze this YouTube video's metadata for SEO optimization specific to {content_type} content:

TITLE: {metadata.get('title', 'N/A')}
DESCRIPTION: {self._truncate_text(metadata.get('description', 'N/A'), 500)}
TAGS: {', '.join(metadata.get('tags', [])[:20]) if metadata.get('tags') else 'None'}
CONTENT TYPE: {content_type}
CHANNEL: {metadata.get('channel_title', 'N/A')}
VIEWS: {metadata.get('view_count', 'N/A')}
KEY PHRASES FROM TRANSCRIPT: {', '.join(keywords[:10])}

Provide detailed analysis on:

1. Title Analysis: Does it match {content_type} best practices? Include:
   - Keyword placement and optimization
   - Length (optimal for this content type)
   - Emotional appeal and clickability
   - How it compares to top-performing {content_type} titles

2. Description Effectiveness: Is it optimized for {content_type}? Include:
   - Keyword density and placement
   - Links and calls-to-action
   - Structure and readability
   - Missing elements that would boost SEO

3. Tags Quality: Are they ideal for {content_type}? Include:
   - Relevance to content
   - Competition level
   - Comprehensiveness
   - Missing high-value tags

4. Content-Specific SEO: Special considerations for {content_type} content:
   - Industry-specific metadata practices
   - Algorithm preferences for this content type
   - Competitive landscape observations

5. Metadata Gaps and Opportunities: What's missing?
   - Critical metadata elements not being utilized
   - Content-specific optimization opportunities

Format your analysis as concise, actionable bulletpoints.
"""
            # Get main SEO analysis
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": f"You are an expert in YouTube SEO specifically for {content_type} content. Provide practical, specific advice for improving video discoverability and engagement."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000
            )
            
            seo_analysis = response.choices[0].message.content
            
            # Add thumbnail analysis if available
            thumbnail_analysis = self._analyze_thumbnail(thumbnail_path, content_type)
            
            # Combine analyses
            if thumbnail_analysis.get('status') == 'success':
                combined_analysis = {
                    'status': 'success',
                    'metadata_analysis': seo_analysis,
                    'thumbnail_analysis': thumbnail_analysis.get('analysis', ''),
                    'combined': f"""
## Metadata SEO Analysis
{seo_analysis}

## Thumbnail Analysis
{thumbnail_analysis.get('analysis', '')}
"""
                }
                return combined_analysis
            else:
                return {
                    'status': 'success',
                    'metadata_analysis': seo_analysis,
                    'thumbnail_analysis': thumbnail_analysis.get('message', ''),
                    'combined': seo_analysis
                }
                
        except Exception as e:
            logger.error(f"Enhanced SEO metadata analysis failed: {str(e)}")
            return {
                'status': 'error',
                'message': f"⚠️ SEO analysis failed: {str(e)}"
            }
    
    def _analyze_thumbnail(self, thumbnail_path, content_type):
        """Analyze thumbnail with context awareness"""
        if not self.client or not thumbnail_path or not os.path.exists(thumbnail_path):
            return {
                'status': 'error',
                'message': "⚠️ Thumbnail analysis skipped: Image not available or API key missing"
            }
            
        try:
            with open(thumbnail_path, "rb") as img_file:
                encoded_image = base64.b64encode(img_file.read()).decode('utf-8')
                
            # Context-aware thumbnail analysis
            thumbnail_response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"""Analyze this YouTube thumbnail for a {content_type} video:

1. Visual appeal and professional quality
   - Image resolution and clarity
   - Color grading and visual aesthetics
   - Overall production value

2. Content type appropriateness
   - How well it represents {content_type} content
   - Industry-specific thumbnail conventions
   - Competitive differentiation

3. Text elements
   - Readability and font choice
   - Message clarity and impact
   - Text placement and design

4. Click-through potential
   - Emotional/curiosity triggers
   - Visual hierarchy and focus points
   - Competitive advantage in search results

5. Brand consistency
   - Channel identity elements
   - Recognition factors

Provide specific, actionable recommendations to improve CTR specifically for {content_type} content.
"""},
                         {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}}
                    ]
                }],
                max_tokens=600
            )
            
            return {
                'status': 'success',
                'analysis': thumbnail_response.choices[0].message.content
            }
            
        except Exception as e:
            logger.error(f"Thumbnail analysis failed: {str(e)}")
            return {
                'status': 'error',
                'message': f"⚠️ Thumbnail analysis failed: {str(e)}"
            }

    def _extract_keywords_from_transcript(self, transcript):
        """Extract key phrases from transcript for SEO analysis"""
        if not self.client or not transcript:
            return []
            
        try:
            # Extract keywords from transcript
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Extract the top 15 most important keywords or key phrases from this transcript, focusing on specific topics, not generic words. Return as a comma-separated list with no numbering or bullets."},
                    {"role": "user", "content": self._truncate_text(transcript, 4000)}
                ],
                max_tokens=200
            )
            
            # Process response
            keywords_text = response.choices[0].message.content
            # Clean up any formatting
            keywords_text = re.sub(r'^\s*\d+\.\s*', '', keywords_text, flags=re.MULTILINE)
            keywords_text = re.sub(r'^\s*-\s*', '', keywords_text, flags=re.MULTILINE)
            
            # Split into list and clean
            keywords = [k.strip() for k in keywords_text.split(',')]
            return [k for k in keywords if k]
            
        except Exception as e:
            logger.error(f"Keyword extraction failed: {str(e)}")
            return []

    def _download_video(self, video_url, output_dir):
        """Download video using yt-dlp with better error handling"""
        try:
            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
                'outtmpl': os.path.join(output_dir, 'video.%(ext)s'),
                'quiet': True
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
                return ydl.prepare_filename(info)
        except Exception as e:
            logger.error(f"Failed to download video: {str(e)}")
            raise RuntimeError(f"Video download failed: {str(e)}")

    def _extract_audio(self, video_path, output_dir):
        """Extract audio as WAV using ffmpeg with error checking"""
        try:
            audio_path = os.path.join(output_dir, 'audio.wav')
            (
                ffmpeg.input(video_path)
                .output(audio_path, ac=1, ar=16000)
                .run(quiet=True, overwrite_output=True)
            )
            
            # Verify file was created
            if not os.path.exists(audio_path):
                raise RuntimeError("Audio extraction completed but file not found")
                
            return audio_path
        except Exception as e:
            logger.error(f"Failed to extract audio: {str(e)}")
            raise RuntimeError(f"Audio extraction failed: {str(e)}")

    def _enhanced_video_analysis(self, video_path, content_type):
        """Context-aware video frame analysis with scene detection"""
        if not self.client:
            return {
                'status': 'error',
                'message': "⚠️ Video analysis skipped: OpenAI API key not provided"
            }
            
        frame_paths = []
        frame_dir = tempfile.mkdtemp()
        
        try:
            clip = VideoFileClip(video_path)
            duration = clip.duration
            
            # Adaptive frame selection based on content type
            frame_selections = {
                'Music/Song Video': [0.1, 0.25, 0.5, 0.75, 0.9],  # More complete coverage for music videos
                'Tutorial/How-to': [0.05, 0.25, 0.5, 0.75, 0.95],  # Beginning, middle, end for tutorials
                'Vlog/Personal': [0.1, 0.3, 0.5, 0.7, 0.9],  # Distributed throughout
                'Gaming': [0.1, 0.4, 0.7, 0.9],  # Focus on action sequences
                'Review/Product': [0.1, 0.3, 0.5, 0.7, 0.9]  # Product shots throughout
            }
            
            # Get frame selection strategy based on content type, or use default
            frame_times = frame_selections.get(
                content_type, 
                [0.1, 0.3, 0.5, 0.7, 0.9]  # Default frame distribution
            )
            
            # Apply frame times to duration
            frame_times = [t * duration for t in frame_times]
            
            # Save frames temporarily
            for i, t in enumerate(frame_times):
                frame = clip.get_frame(t)
                frame_path = os.path.join(frame_dir, f"frame_{i}.jpg")
                cv2.imwrite(frame_path, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
                frame_paths.append(frame_path)
            
            # Analyze video statistics
            width, height = clip.size
            fps = clip.fps
            
            # Calculate bitrate
            video_size = os.path.getsize(video_path) * 8  # bits
            bitrate = video_size / duration if duration > 0 else 0  # bits per second
            
            # Analyze scene transitions using OpenCV
            scene_count = self._count_scene_transitions(video_path)
            
            # Technical stats analysis
            tech_analysis = {
                'resolution': f"{width}x{height}",
                'fps': f"{fps:.2f}",
                'bitrate': f"{bitrate/1000000:.2f} Mbps",
                'duration': f"{duration:.2f} seconds",
                'scene_transitions': scene_count
            }
            
            # Encode images as base64 for vision analysis
            encoded_images = []
            for path in frame_paths:
                with open(path, "rb") as img_file:
                    encoded_images.append(base64.b64encode(img_file.read()).decode('utf-8'))
            
            # Context-aware frame analysis
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": f"""Analyze these frames from a {content_type} video with these technical specs:
- Resolution: {tech_analysis['resolution']}
- FPS: {tech_analysis['fps']}
- Bitrate: {tech_analysis['bitrate']}
- Duration: {int(duration//60)}:{int(duration%60):02d}
- Scene transitions: {tech_analysis['scene_transitions']}

Focus your analysis on:

1. Visual quality
   - Resolution and clarity appropriateness for {content_type}
   - Lighting quality and consistency
   - Focus and depth of field
   - Color grading and balance

2. Composition and framing
   - Subject positioning and rule of thirds
   - Background elements and environment
   - Visual hierarchy and eye flow
3. Content-specific elements for {content_type}
   - Presence of genre-specific visual elements
   - Visual storytelling effectiveness
   - Brand consistency and visual identity

4. Production value assessment
   - Professional vs. amateur indicators
   - Visual effects and transitions quality
   - Graphics and text overlay quality

5. Viewer engagement potential
   - Visual hook elements
   - Retention-driving visual cues
   - Thumbnail consistency with content

Provide an overall quality score (1-10) with detailed justification.
"""
                            }
                        ] + [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img}"}} for img in encoded_images]
                    }
                ],
                max_tokens=800
            )
            
            visual_analysis = response.choices[0].message.content
            
            # Clean up
            for path in frame_paths:
                try:
                    os.remove(path)
                except:
                    pass
            try:
                os.rmdir(frame_dir)
            except:
                pass
            
            # Final analysis
            result = {
                'status': 'success',
                'technical_specs': tech_analysis,
                'visual_analysis': visual_analysis,
                'combined': f"""
## Technical Specifications
- Resolution: {tech_analysis['resolution']}
- FPS: {tech_analysis['fps']}
- Bitrate: {tech_analysis['bitrate']}
- Duration: {int(duration//60)}:{int(duration%60):02d}
- Scene Transitions: {tech_analysis['scene_transitions']}

## Visual Analysis
{visual_analysis}
"""
            }
            return result
            
        except Exception as e:
            logger.error(f"Enhanced video analysis failed: {str(e)}")
            # Clean up on error
            for path in frame_paths:
                try:
                    os.remove(path)
                except:
                    pass
            try:
                os.rmdir(frame_dir)
            except:
                pass
                
            return {
                'status': 'error',
                'message': f"⚠️ Video analysis failed: {str(e)}"
            }

    def _count_scene_transitions(self, video_path):
        """Count number of scene transitions using OpenCV"""
        try:
            cap = cv2.VideoCapture(video_path)
            
            # Get total frames
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # If video is large, sample every nth frame
            sample_rate = max(1, int(total_frames / 500))  # Sample at most 500 frames
            
            prev_frame = None
            scene_changes = 0
            threshold = 30.0  # Adjust based on sensitivity needed
            
            frame_count = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_count += 1
                if frame_count % sample_rate != 0:
                    continue
                
                # Convert to grayscale
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                if prev_frame is not None:
                    # Calculate difference
                    diff = cv2.absdiff(gray, prev_frame)
                    
                    # Calculate mean difference
                    mean_diff = np.mean(diff)
                    
                    # If difference is above threshold, count as scene change
                    if mean_diff > threshold:
                        scene_changes += 1
                
                prev_frame = gray
            
            cap.release()
            
            # Scale scene changes based on sample rate
            estimated_changes = scene_changes * sample_rate
            
            # Normalize based on video length
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration_seconds = total_frames / fps if fps > 0 else 0
            
            # Convert to changes per minute for easier comparison
            if duration_seconds > 0:
                changes_per_minute = (estimated_changes / duration_seconds) * 60
                return int(changes_per_minute)
            else:
                return 0
                
        except Exception as e:
            logger.error(f"Scene transition counting failed: {str(e)}")
            return 0

    def _enhanced_audio_analysis(self, audio_path, content_type):
        """Context-aware audio analysis"""
        if not self.client:
            return {
                'status': 'error',
                'message': "⚠️ Audio analysis skipped: OpenAI API key not provided"
            }
            
        try:
            # Load audio and extract basic properties
            audio = AudioSegment.from_file(audio_path)
            
            # Basic audio properties
            duration_seconds = len(audio) / 1000
            channels = audio.channels
            sample_rate = audio.frame_rate
            bit_depth = audio.sample_width * 8
            
            # Calculate RMS volume (loudness)
            rms = audio.rms
            max_possible_amplitude = float(2 ** (bit_depth - 1))
            normalized_rms = rms / max_possible_amplitude
            
            # Calculate volume dynamics
            chunk_length_ms = 1000  # 1 second chunks
            chunks = [audio[i:i+chunk_length_ms] for i in range(0, len(audio), chunk_length_ms)]
            chunk_volumes = [chunk.rms for chunk in chunks]
            
            if chunk_volumes:
                volume_variance = np.var(chunk_volumes) / (max(chunk_volumes) ** 2) if max(chunk_volumes) > 0 else 0
                volume_min = min(chunk_volumes) / max_possible_amplitude if chunk_volumes else 0
                volume_max = max(chunk_volumes) / max_possible_amplitude if chunk_volumes else 0
            else:
                volume_variance = 0
                volume_min = 0
                volume_max = 0
            
            # Technical analysis
            tech_analysis = {
                'duration': f"{duration_seconds:.2f} seconds",
                'channels': channels,
                'sample_rate': f"{sample_rate/1000:.1f} kHz",
                'bit_depth': f"{bit_depth}-bit",
                'avg_volume': f"{(normalized_rms * 100):.2f}%",
                'volume_min': f"{(volume_min * 100):.2f}%",
                'volume_max': f"{(volume_max * 100):.2f}%",
                'volume_dynamics': f"{(volume_variance * 100):.2f}%"
            }
            
            # Calculate frequency distribution (simplified analysis)
            has_low_frequencies = any(chunk.low_pass_filter(300).rms > chunk.rms * 0.3 for chunk in chunks[:10])
            has_high_frequencies = any(chunk.high_pass_filter(3000).rms > chunk.rms * 0.2 for chunk in chunks[:10])
            
            # Transcribe a short segment for voice quality assessment
            sample_length = min(30000, len(audio))  # 30 seconds or full audio if shorter
            sample_audio = audio[:sample_length]
            
            # Export sample for transcription
            sample_path = os.path.splitext(audio_path)[0] + "_sample.wav"
            sample_audio.export(sample_path, format="wav")
            
            # Transcribe audio sample
            with open(sample_path, "rb") as audio_file:
                transcription_result = self.client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=audio_file
                )
            
            # Remove temporary sample file
            try:
                os.remove(sample_path)
            except:
                pass
            
            # Generate context-aware analysis
            prompt = f"""
Analyze audio quality for this {content_type} video with the following technical specifications:

AUDIO SPECS:
- Duration: {tech_analysis['duration']}
- Channels: {tech_analysis['channels']}
- Sample Rate: {tech_analysis['sample_rate']}
- Bit Depth: {tech_analysis['bit_depth']}
- Average Volume: {tech_analysis['avg_volume']}
- Volume Range: {tech_analysis['volume_min']} to {tech_analysis['volume_max']}
- Volume Dynamics: {tech_analysis['volume_dynamics']}
- Low Frequencies: {"Present" if has_low_frequencies else "Limited"}
- High Frequencies: {"Present" if has_high_frequencies else "Limited"}

SHORT TRANSCRIPT SAMPLE:
"{transcription_result.text[:300]}..."

Based on this data and the transcript sample, provide a detailed audio quality assessment for this {content_type} video:

1. Sound clarity and quality
   - Voice clarity (if applicable)
   - Background noise level
   - Audio compression artifacts

2. Audio engineering
   - EQ and frequency balance
   - Dynamic range and leveling
   - Stereo imaging and spatial quality

3. Content-specific audio assessment for {content_type}
   - Genre-appropriate audio characteristics
   - Professional quality level compared to industry standards
   - Background music and sound effects (if detected)

4. Voice characteristics (if present)
   - Vocal delivery and articulation
   - Microphone quality assessment
   - Room acoustics detection

5. Overall listening experience
   - Listener fatigue factors
   - Engagement potential

Provide specific recommendations for improvement based on {content_type} best practices.
"""

            # Get detailed audio analysis
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": f"You are an expert audio engineer specializing in {content_type} content. Provide detailed technical analysis with specific recommendations."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800
            )
            
            audio_analysis = response.choices[0].message.content
            
            # Final analysis
            result = {
                'status': 'success',
                'technical_specs': tech_analysis,
                'audio_analysis': audio_analysis,
                'combined': f"""
## Technical Audio Specifications
- Duration: {tech_analysis['duration']}
- Channels: {tech_analysis['channels']}
- Sample Rate: {tech_analysis['sample_rate']}
- Bit Depth: {tech_analysis['bit_depth']}
- Average Volume: {tech_analysis['avg_volume']}
- Volume Range: {tech_analysis['volume_min']} to {tech_analysis['volume_max']}
- Volume Dynamics: {tech_analysis['volume_dynamics']}

## Audio Quality Analysis
{audio_analysis}
"""
            }
            return result
            
        except Exception as e:
            logger.error(f"Enhanced audio analysis failed: {str(e)}")
            return {
                'status': 'error',
                'message': f"⚠️ Audio analysis failed: {str(e)}"
            }

    def _get_video_transcript(self, video_url):
        """Get video transcript with improved handling"""
        try:
            # Use yt-dlp to get available subtitles
            ydl_opts = {
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['en'],
                'skip_download': True,
                'quiet': True
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                
                # Check for available subtitles
                subtitles = info.get('subtitles', {})
                auto_subtitles = info.get('automatic_captions', {})
                
                # Prefer manual subtitles over auto-generated
                if 'en' in subtitles:
                    logger.info("Found manual English subtitles")
                    sub_formats = subtitles['en']
                elif 'en' in auto_subtitles:
                    logger.info("Found auto-generated English subtitles")
                    sub_formats = auto_subtitles['en']
                else:
                    logger.warning("No subtitles found, attempting audio transcription")
                    return self._transcribe_video_audio(video_url)
                
                # Try to get vtt or srt format
                sub_url = None
                for fmt in sub_formats:
                    if fmt.get('ext') in ['vtt', 'srt']:
                        sub_url = fmt.get('url')
                        break
                
                if not sub_url:
                    logger.warning("No usable subtitle format found")
                    return self._transcribe_video_audio(video_url)
                
                # Download subtitles
                response = requests.get(sub_url)
                if response.status_code != 200:
                    logger.error(f"Failed to download subtitles: HTTP {response.status_code}")
                    return self._transcribe_video_audio(video_url)
                
                # Parse subtitles
                subtitle_text = response.text
                
                # Extract text from VTT or SRT
                clean_text = self._clean_subtitle_text(subtitle_text)
                
                if not clean_text:
                    logger.warning("Subtitle parsing produced empty text")
                    return self._transcribe_video_audio(video_url)
                
                logger.info("Successfully retrieved and parsed video transcript")
                return {
                    'status': 'success',
                    'transcript': clean_text,
                    'source': 'youtube_subtitles'
                }
                
        except Exception as e:
            logger.error(f"Failed to get video transcript: {str(e)}")
            # Fall back to audio transcription
            return self._transcribe_video_audio(video_url)
    
    def _transcribe_video_audio(self, video_url):
        """Fall back to transcribing audio from video"""
        if not self.client:
            return {
                'status': 'error',
                'message': "⚠️ Transcription failed: OpenAI API key not provided"
            }
            
        try:
            # Create temporary directory
            temp_dir = tempfile.mkdtemp()
            
            try:
                # Download video
                logger.info("Downloading video for audio transcription")
                video_path = self._download_video(video_url, temp_dir)
                
                # Extract audio
                logger.info("Extracting audio for transcription")
                audio_path = self._extract_audio(video_path, temp_dir)
                
                # Use OpenAI Whisper API for transcription
                logger.info("Transcribing audio with OpenAI API")
                with open(audio_path, "rb") as audio_file:
                    transcription = self.client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file
                    )
                
                logger.info("Successfully transcribed video audio")
                return {
                    'status': 'success',
                    'transcript': transcription.text,
                    'source': 'openai_whisper'
                }
                
            finally:
                # Clean up
                self._cleanup_directory(temp_dir)
                
        except Exception as e:
            logger.error(f"Audio transcription failed: {str(e)}")
            return {
                'status': 'error',
                'message': f"⚠️ Transcription failed: {str(e)}"
            }
    
    def _clean_subtitle_text(self, subtitle_text):
        """Clean and format subtitle text from VTT or SRT format"""
        # Remove timestamps and formatting
        clean_text = re.sub(r'\d{2}:\d{2}:\d{2}[,.]\d{3} --> \d{2}:\d{2}:\d{2}[,.]\d{3}', '', subtitle_text)
        clean_text = re.sub(r'^\d+$', '', clean_text, flags=re.MULTILINE)  # Remove caption numbers
        clean_text = re.sub(r'<[^>]+>', '', clean_text)  # Remove HTML tags
        clean_text = re.sub(r'\[[^\]]+\]', '', clean_text)  # Remove [Sound effects]
        clean_text = re.sub(r'\([^)]+\)', '', clean_text)  # Remove (Sound effects)
        clean_text = re.sub(r'^\s*$', '', clean_text, flags=re.MULTILINE)  # Remove empty lines
        clean_text = re.sub(r'\n{2,}', '\n', clean_text)  # Compress multiple newlines
        
        return clean_text.strip()
    
    def _enhanced_transcript_analysis(self, transcript, content_type, metadata):
        """Analyze transcript with content-specific context"""
        if not self.client or not transcript:
            return {
                'status': 'error',
                'message': "⚠️ Transcript analysis skipped: Text or API key not available"
            }
            
        try:
            # Prepare prompt with content type context
            prompt = f"""
Analyze this transcript from a {content_type} video titled "{metadata.get('title', 'N/A')}".

The transcript is approximately {len(transcript.split())} words long.

Provide a detailed content analysis focusing on these aspects, tailored specifically for {content_type} content:

1. Content Structure & Flow
   - Introduction effectiveness (first 10%)
   - Mid-content engagement strategies
   - Conclusion and call-to-action (last 10%)
   - Overall narrative arc and pacing

2. Audience Engagement
   - Hook effectiveness and retention triggers
   - Question and engagement techniques
   - Emotional appeals and connection points
   - Content-to-audience match assessment

3. {content_type}-Specific Content Analysis
   - Industry-standard content elements
   - Subject matter expertise indicators
   - Competitive differentiation factors
   - Target audience appropriateness

4. Content Density & Clarity
   - Information-to-runtime ratio
   - Key message clarity and repetition
   - Technical language appropriateness
   - Explanation quality of complex concepts

5. SEO Optimization
   - Keyword usage and placement
   - Topic coverage completeness
   - Search-optimized language patterns

TRANSCRIPT:
{self._truncate_text(transcript, 4000)}

Provide actionable insights for improving this {content_type} content based on current best practices.
"""

            # Get enhanced analysis
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": f"You are an expert content analyst specializing in {content_type} videos. Provide detailed, actionable insights."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000
            )
            
            content_analysis = response.choices[0].message.content
            
            # Calculate readability metrics
            try:
                words = transcript.split()
                sentences = re.split(r'[.!?]+', transcript)
                sentences = [s for s in sentences if s.strip()]
                
                # Word count and sentence count
                word_count = len(words)
                sentence_count = len(sentences)
                
                # Average words per sentence
                avg_words_per_sentence = word_count / sentence_count if sentence_count > 0 else 0
                
                # Calculate average word length
                avg_word_length = sum(len(word) for word in words) / word_count if word_count > 0 else 0
                
                # Approximate Flesch Reading Ease
                if sentence_count > 0 and word_count > 0:
                    flesch = 206.835 - (1.015 * (word_count / sentence_count)) - (84.6 * (sum(len(word) for word in words) / word_count))
                    flesch = max(0, min(100, flesch))  # Clamp between 0-100
                else:
                    flesch = 0
                
                readability = {
                    'word_count': word_count,
                    'sentence_count': sentence_count,
                    'avg_words_per_sentence': f"{avg_words_per_sentence:.1f}",
                    'avg_word_length': f"{avg_word_length:.1f}",
                    'flesch_reading_ease': f"{flesch:.1f}/100"
                }
            except Exception as e:
                logger.error(f"Readability calculation failed: {str(e)}")
                readability = {
                    'word_count': len(transcript.split()),
                    'error': str(e)
                }
            
            # Return combined analysis
            return {
                'status': 'success',
                'content_analysis': content_analysis,
                'readability_metrics': readability,
                'combined': f"""
## Content Analysis
{content_analysis}

## Readability Metrics
- Word Count: {readability.get('word_count', 'N/A')}
- Sentence Count: {readability.get('sentence_count', 'N/A')}
- Avg Words Per Sentence: {readability.get('avg_words_per_sentence', 'N/A')}
- Avg Word Length: {readability.get('avg_word_length', 'N/A')}
- Flesch Reading Ease: {readability.get('flesch_reading_ease', 'N/A')}
"""
            }
            
        except Exception as e:
            logger.error(f"Enhanced transcript analysis failed: {str(e)}")
            return {
                'status': 'error',
                'message': f"⚠️ Transcript analysis failed: {str(e)}"
            }
            
    def _generate_comprehensive_report(self, metadata, content_type_info, transcript_analysis, 
                                     video_analysis, audio_analysis, seo_analysis):
        """Generate a comprehensive analysis report with recommendations"""
        if not self.client:
            return "⚠️ Report generation skipped: OpenAI API key not provided"
            
        try:
            # Create a simplified summary of all analyses for context
            content_type = content_type_info.get('content_type', 'unknown')
            
            # Extract key insights from each analysis section
            video_insights = "Not available"
            if video_analysis.get('status') == 'success':
                video_insights = video_analysis.get('visual_analysis', 'Not available')
                
            audio_insights = "Not available"
            if audio_analysis.get('status') == 'success':
                audio_insights = audio_analysis.get('audio_analysis', 'Not available')
                
            seo_insights = "Not available"
            if seo_analysis.get('status') == 'success':
                seo_insights = seo_analysis.get('metadata_analysis', 'Not available')
                
            transcript_insights = "Not available"
            if transcript_analysis.get('status') == 'success':
                transcript_insights = transcript_analysis.get('content_analysis', 'Not available')
            
            # Create summary for report context
            summary = f"""
VIDEO: {metadata.get('title', 'Unknown')}
CHANNEL: {metadata.get('channel_title', 'Unknown')}
TYPE: {content_type}
DURATION: {metadata.get('duration', 'Unknown')}
VIEWS: {metadata.get('view_count', 'Unknown')}
ENGAGEMENT: {metadata.get('like_count', 'Unknown')} likes, {metadata.get('comment_count', 'Unknown')} comments

CONTENT DETAILS: {str(content_type_info.get('details', {}))}

VIDEO QUALITY INSIGHTS: {self._truncate_text(video_insights, 300)}

AUDIO QUALITY INSIGHTS: {self._truncate_text(audio_insights, 300)}

SEO & METADATA INSIGHTS: {self._truncate_text(seo_insights, 300)}

CONTENT & TRANSCRIPT INSIGHTS: {self._truncate_text(transcript_insights, 300)}
"""

            # Create comprehensive report prompt
            prompt = f"""
Based on this detailed analysis of a {content_type} video, create a comprehensive but concise performance report with specific, actionable recommendations.

ANALYSIS SUMMARY:
{summary}

Structure the report with these sections:

1. EXECUTIVE SUMMARY
   - Brief overview of overall content quality and performance
   - 3 most critical findings across all categories
   - Content's competitive position for {content_type} category

2. STRENGTHS ASSESSMENT
   - Top 3 most effective elements of this content
   - Areas where the content excels compared to typical {content_type} videos
   - Valuable assets worth preserving in future content

3. PRIORITIZED IMPROVEMENT OPPORTUNITIES
   - Rank the top 5 highest-impact improvement opportunities
   - For each, include:
     a) Current issue and its impact on performance
     b) Specific, actionable solution tailored for {content_type} content
     c) Expected benefit from implementing the change

4. AUDIENCE RETENTION STRATEGY
   - Specific recommendations to improve viewer retention
   - Hook and introduction enhancements
   - Content pacing improvements
   - End screen and call-to-action optimization

5. CONTENT DISTRIBUTION RECOMMENDATIONS
   - Platform-specific optimization tips
   - Metadata enhancements for discoverability
   - Cross-promotion strategies

Format this as a professional report that a content creator can immediately use to improve their video performance. Focus on practical, high-impact recommendations specific to {content_type} content.
"""

            # Generate comprehensive report
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": f"You are an expert video content strategist specializing in {content_type} videos. Create a professional, actionable report based on comprehensive analysis data."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500
            )
            
            report = response.choices[0].message.content
            
            # Format the report with metadata header
            final_report = f"""
# Video Analysis Report: {metadata.get('title', 'Unknown Video')}

*Analysis performed on {datetime.now().strftime('%Y-%m-%d')} · {content_type} Video · {metadata.get('duration', '?')} Duration*

{report}
"""
            return final_report
            
        except Exception as e:
            logger.error(f"Report generation failed: {str(e)}")
            return f"⚠️ Report generation failed: {str(e)}"
    
    def _extract_video_id(self, url):
        """Extract YouTube video ID from URL with support for more formats"""
        patterns = [
            r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([^&\s]+)',  # Standard watch URL
            r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([^\?\&\s]+)',  # Embed URL
            r'(?:https?:\/\/)?(?:www\.)?youtu\.be\/([^\?\&\s]+)',           # Short URL
            r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/v\/([^\?\&\s]+)',     # Old embed URL
            r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/user\/[^\/]+\/([^\?\&\s]+)',  # User URL
            r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/shorts\/([^\?\&\s]+)'  # Shorts URL
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # If pattern matching failed, try to extract from the URL directly
        if 'youtube.com' in url or 'youtu.be' in url:
            url_parts = url.split('/')
            for part in url_parts:
                if len(part) == 11 and re.match(r'^[A-Za-z0-9_-]{11}$', part):
                    return part
        
        return None
    
    def _truncate_text(self, text, max_chars):
        """Truncate text to a maximum character length"""
        if not text:
            return ""
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "..."
    
    def _cleanup_directory(self, directory):
        """Clean up all files in a directory"""
        for root, dirs, files in os.walk(directory, topdown=False):
            for name in files:
                try:
                    os.remove(os.path.join(root, name))
                except Exception as e:
                    logger.warning(f"Failed to delete file {name}: {str(e)}")
            for name in dirs:
                try:
                    os.rmdir(os.path.join(root, name))
                except Exception as e:
                    logger.warning(f"Failed to delete directory {name}: {str(e)}")
        try:
            os.rmdir(directory)
        except Exception as e:
            logger.warning(f"Failed to delete root directory: {str(e)}")


class VideoAnalyzerCLI:
    """Command-line interface for the EnhancedVideoAnalyzer"""
    
    def __init__(self):
        self.analyzer = None
    
    def setup_credentials(self):
        """Set up credentials for analysis"""
        print("\nSetting up VideoAnalyzer...\n")
        
        # Get OpenAI API key
        openai_key = input("Enter your OpenAI API key (or press Enter to skip): ").strip()
        if not openai_key:
            openai_key = os.environ.get('OPENAI_API_KEY')
            if openai_key:
                print("Using OpenAI API key from environment variables.")
            else:
                print("WARNING: No OpenAI API key provided. Some features will be limited.")
        
        # Initialize analyzer
        self.analyzer = EnhancedVideoAnalyzer(openai_api_key=openai_key)
        print("\nVideoAnalyzer initialized successfully!\n")
    
    def run_analysis(self):
        """Run video analysis from command line"""
        if not self.analyzer:
            self.setup_credentials()
        
        # Get video URL
        video_url = input("\nEnter YouTube video URL to analyze: ").strip()
        if not video_url:
            print("Error: No URL provided.")
            return
        
        print("\nAnalyzing video... This may take a few minutes depending on video length.\n")
        
        # Perform analysis
        try:
            result = self.analyzer.analyze_video(video_url)
            
            if result['status'] == 'success':
                print("\n" + "="*80)
                print(f"ANALYSIS COMPLETE: {result.get('metadata', {}).get('title', 'Unknown video')}")
                print("="*80)
                
                # Print report
                print("\n" + result['report'] + "\n")
                
                # Ask if user wants to see detailed sections
                sections = {
                    '1': ('Video Quality Analysis', result.get('video_analysis', {}).get('combined', 'Not available')),
                    '2': ('Audio Quality Analysis', result.get('audio_analysis', {}).get('combined', 'Not available')),
                    '3': ('Content & Transcript Analysis', result.get('transcript_analysis', {}).get('combined', 'Not available')),
                    '4': ('SEO & Metadata Analysis', result.get('seo_analysis', {}).get('combined', 'Not available')),
                    '5': ('Raw Transcript', result.get('transcript', 'Not available'))
                }
                
                while True:
                    print("\nDetailed analysis sections available:")
                    print("1. Video Quality Analysis")
                    print("2. Audio Quality Analysis")
                    print("3. Content & Transcript Analysis")
                    print("4. SEO & Metadata Analysis")
                    print("5. Raw Transcript")
                    print("0. Exit")
                    
                    choice = input("\nEnter section number to view (0 to exit): ").strip()
                    
                    if choice == '0':
                        break
                    elif choice in sections:
                        print("\n" + "="*80)
                        print(sections[choice][0])
                        print("="*80 + "\n")
                        print(sections[choice][1])
                    else:
                        print("Invalid choice. Please try again.")
            else:
                print(f"\nAnalysis failed: {result.get('message', 'Unknown error')}")
                
        except Exception as e:
            print(f"\nError analyzing video: {str(e)}")
    
    def main(self):
        """Main CLI entry point"""
        print("\n" + "="*80)
        print("ENHANCED YOUTUBE VIDEO ANALYZER")
        print("="*80)
        print("\nThis tool performs in-depth analysis of YouTube videos, including:")
        print("- Video quality assessment")
        print("- Audio quality analysis")
        print("- Content and transcript analysis")
        print("- SEO and metadata optimization")
        print("- Comprehensive performance improvement recommendations")
        
        self.setup_credentials()
        
        while True:
            print("\n" + "="*80)
            print("MAIN MENU")
            print("="*80)
            print("1. Analyze YouTube Video")
            print("0. Exit")
            
            choice = input("\nEnter your choice: ").strip()
            
            if choice == '1':
                self.run_analysis()
            elif choice == '0':
                print("\nThank you for using the YouTube Video Analyzer. Goodbye!\n")
                break
            else:
                print("Invalid choice. Please try again.")


if __name__ == "__main__":
    cli = VideoAnalyzerCLI()
    cli.main()