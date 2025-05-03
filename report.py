import os
import tempfile
import re
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import yt_dlp
from openai import OpenAI
import math
from pydub import AudioSegment

def analyze_video(video_url, youtube_credentials=None, openai_api_key=None):
    """
    Complete video analysis pipeline:
    1. Get transcript (YouTube API or Whisper)
    2. Generate detailed analysis report
    3. Provide improvement suggestions
    """
    # Get transcript first
    transcript_result = get_video_transcript(
        video_url,
        youtube_credentials=youtube_credentials,
        openai_api_key=openai_api_key
    )
    
    if transcript_result['status'] != 'success':
        return transcript_result  # Return error if transcript failed
    
    # Now analyze the content
    return generate_analysis_report(
        transcript_result['transcript'],
        openai_api_key
    )

def get_video_transcript(video_url, youtube_credentials=None, openai_api_key=None):
    """
    Get transcript using best available method with large file handling:
    1. Try YouTube API captions first (if credentials provided)
    2. Fall back to Whisper with chunked processing for large files
    """
    # First try YouTube API if credentials available
    if youtube_credentials:
        youtube_result = get_youtube_captions(video_url, youtube_credentials)
        if youtube_result['status'] == 'success':
            return youtube_result
    
    # Fall back to Whisper if API key provided
    if openai_api_key:
        whisper_result = get_whisper_transcript(video_url, openai_api_key)
        if whisper_result['status'] == 'success':
            return whisper_result
    
    return {
        'status': 'error',
        'message': 'All methods failed: ' +
                  (youtube_result.get('message', '') if youtube_credentials else '') +
                  (whisper_result.get('message', '') if openai_api_key else '')
    }

def get_youtube_captions(video_url, credentials):
    """Get captions using YouTube API v3 with OAuth"""
    try:
        youtube = build('youtube', 'v3', credentials=credentials)
        video_id = extract_video_id(video_url)
        
        captions = youtube.captions().list(
            part="snippet",
            videoId=video_id
        ).execute()
        
        if not captions.get('items'):
            return {'status': 'error', 'message': 'No captions available'}
        
        # Find English captions
        caption_id = next(
            (item['id'] for item in captions['items'] 
             if item['snippet']['language'] == 'en'),
            None
        )
        
        if not caption_id:
            return {'status': 'error', 'message': 'No English captions found'}
        
        # Download captions
        caption = youtube.captions().download(
            id=caption_id,
            tfmt='srt'
        ).execute()
        
        return {
            'status': 'success',
            'source': 'youtube_api',
            'transcript': format_srt_to_text(caption),
            'message': ''
        }
        
    except Exception as e:
        return {'status': 'error', 'message': f'YouTube API error: {str(e)}'}

def get_whisper_transcript(video_url, api_key, max_size_mb=24):
    """Get transcript using Whisper with chunked processing for large files"""
    client = OpenAI(api_key=api_key)
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Download audio with yt-dlp
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(temp_dir, 'audio.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
            }],
            'quiet': True,
            'no_warnings': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            audio_path = ydl.prepare_filename(info)
            audio_path = audio_path.replace('.webm', '.wav').replace('.mp4', '.wav')
        
        if not os.path.exists(audio_path):
            return {'status': 'error', 'message': 'Audio file not found'}
        
        # Check file size and split if needed
        file_size = os.path.getsize(audio_path)
        max_size = max_size_mb * 1024 * 1024  # Convert MB to bytes
        
        if file_size <= max_size:
            # Process normally if under size limit
            with open(audio_path, "rb") as audio_file:
                result = client.audio.transcriptions.create(
                    file=audio_file,
                    model="whisper-1"
                )
            transcript = result.text
        else:
            # Split and process in chunks
            transcript = process_large_audio(client, audio_path, max_size)
        
        return {
            'status': 'success',
            'source': 'whisper',
            'transcript': transcript,
            'message': ''
        }
        
    except Exception as e:
        return {'status': 'error', 'message': f'Whisper error: {str(e)}'}
    finally:
        # Clean up temp files
        for file in os.listdir(temp_dir):
            os.remove(os.path.join(temp_dir, file))
        os.rmdir(temp_dir)

def process_large_audio(client, audio_path, max_size):
    """Split large audio file and process chunks with Whisper"""
    audio = AudioSegment.from_wav(audio_path)
    chunk_length_ms = calculate_chunk_length(audio_path, max_size)
    chunks = make_chunks(audio, chunk_length_ms)
    transcripts = []
    
    for i, chunk in enumerate(chunks):
        chunk_path = f"{audio_path}_chunk{i}.wav"
        chunk.export(chunk_path, format="wav")
        
        try:
            with open(chunk_path, "rb") as audio_file:
                result = client.audio.transcriptions.create(
                    file=audio_file,
                    model="whisper-1"
                )
            transcripts.append(result.text)
        finally:
            os.remove(chunk_path)
    
    return " ".join(transcripts)

def calculate_chunk_length(audio_path, max_size):
    """Calculate chunk length that will keep files under size limit"""
    audio = AudioSegment.from_wav(audio_path)
    duration_ms = len(audio)
    file_size = os.path.getsize(audio_path)
    
    # Calculate ratio of target size to current size
    size_ratio = max_size / file_size
    # Apply same ratio to duration
    return math.floor(duration_ms * size_ratio)

def make_chunks(audio, chunk_length_ms):
    """Split audio into chunks of specified length"""
    return [
        audio[i * chunk_length_ms:(i + 1) * chunk_length_ms]
        for i in range(math.ceil(len(audio) / chunk_length_ms))
    ]

def extract_video_id(url):
    """Extract video ID from URL"""
    regex = r'(?:v=|\/)([0-9A-Za-z_-]{11})'
    match = re.search(regex, url)
    return match.group(1) if match else None

def format_srt_to_text(srt_content):
    """Convert SRT captions to plain text"""
    lines = [
        line.strip() for line in srt_content.split('\n')
        if line.strip() and not ('-->' in line or line.strip().isdigit())
    ]
    return ' '.join(lines)

def generate_analysis_report(transcript, api_key):
    """Generate comprehensive analysis report from transcript"""
    client = OpenAI(api_key=api_key)
    
    try:
        # Detailed analysis prompt
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You're a professional video content analyst. Provide detailed feedback and suggestions."},
                {"role": "user", "content": f"""
Analyze this video transcript and provide a detailed report with these sections:
1. CONTENT SUMMARY (1 paragraph)
2. KEY STRENGTHS (3 bullet points)
3. WEAKNESSES/ISSUES (3 bullet points)
4. TECHNICAL IMPROVEMENTS (audio, video quality, pacing)
5. CONTENT IMPROVEMENTS (structure, engagement, storytelling)
6. SEO OPTIMIZATION (title suggestions, tags, description)
7. ACTIONABLE RECOMMENDATIONS (specific steps to improve)

Transcript:
{transcript[:15000]}  # Limit to 15k chars
"""}
            ],
            temperature=0.7
        )
        
        analysis = response.choices[0].message.content
        
        # Extract actionable suggestions
        suggestions = extract_action_items(analysis)
        
        return {
            'status': 'success',
            'transcript': transcript[:1000] + "..." if len(transcript) > 1000 else transcript,
            'full_analysis': analysis,
            'key_suggestions': suggestions
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f"Analysis failed: {str(e)}"
        }

def extract_action_items(analysis_text):
    """Parse the analysis to extract actionable items"""
    items = []
    lines = analysis_text.split('\n')
    current_section = None
    
    for line in lines:
        line = line.strip()
        # Detect sections
        if line.upper().startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.')):
            current_section = line.split('.')[1].strip().upper()
        # Capture bullet points
        elif line.startswith(('-', '•', '*')):
            items.append(f"{current_section}: {line[1:].strip()}" if current_section else line[1:].strip())
        # Capture numbered items
        elif re.match(r'^\d+\.', line):
            items.append(f"{current_section}: {line}" if current_section else line)
    
    return items[:15]  # Return top 15 suggestions

if __name__ == "__main__":
    # Configuration - replace with your actual credentials
    YOUTUBE_CREDENTIALS = None  # Set up OAuth if using YouTube API
    
    # Example video URL - replace with yours
    video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    print(f"Starting analysis for: {video_url}")
    result = analyze_video(
        video_url,
        youtube_credentials=YOUTUBE_CREDENTIALS,
        openai_api_key=OPENAI_API_KEY
    )
    
    if result['status'] == 'success':
        print("\n=== Transcript Preview ===")
        print(result['transcript'])
        
        print("\n=== Full Analysis Report ===")
        print(result['full_analysis'])
        
        print("\n=== Key Actionable Suggestions ===")
        for i, suggestion in enumerate(result['key_suggestions'], 1):
            print(f"{i}. {suggestion}")
    else:
        print(f"\nError: {result['message']}")