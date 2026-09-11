import googleapiclient.discovery
import re
import yt_dlp
import whisper
from pydub import AudioSegment
import tempfile
from transformers import pipeline
from youtube_transcript_api import YouTubeTranscriptApi
import torch
import openai
import json
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Initialize OpenAI API and Hugging Face summarizer once
openai.api_key = os.getenv("OPENAI_API_KEY")
summarizer = pipeline("summarization", model="facebook/bart-large-cnn", device=0 if torch.cuda.is_available() else -1)

# Helper function to extract video ID
def extract_video_id(url):
    """Extracts the video ID from a YouTube URL."""
    try:
        parsed_url = urlparse(url)
        if "youtube.com" in parsed_url.netloc:
            query_params = parse_qs(parsed_url.query)
            return query_params.get('v', [None])[0]
        elif "youtu.be" in parsed_url.netloc:
            return parsed_url.path.strip("/")
        else:
            print("Invalid YouTube URL.")
            return None
    except Exception as e:
        print(f"Error parsing URL: {e}")
        return None

# Function to get video duration
def get_video_duration(video_id, api_key):
    """Fetches the video duration in minutes."""
    try:
        youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=api_key)
        request = youtube.videos().list(part="contentDetails", id=video_id)
        response = request.execute()
        if response["items"]:
            duration = response["items"][0]["contentDetails"]["duration"]
            match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
            hours = int(match.group(1)) if match.group(1) else 0
            minutes = int(match.group(2)) if match.group(2) else 0
            seconds = int(match.group(3)) if match.group(3) else 0
            return hours * 60 + minutes + seconds / 60
        else:
            print("No video details found.")
            return None
    except Exception as e:
        print(f"Error fetching video duration: {e}")
        return None

# Download and transcribe audio with Whisper
def download_and_transcribe_with_whisper(youtube_url):
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_audio_file = os.path.join(temp_dir, "audio.mp3")

            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': temp_audio_file,
                'extractaudio': True,
                'audioquality': 1,
            }

            # Download audio using yt-dlp
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([youtube_url])

            # Convert to wav for Whisper
            audio = AudioSegment.from_file(temp_audio_file)
            wav_file = os.path.join(temp_dir, "audio.wav")
            audio.export(wav_file, format="wav")

            # Run Whisper transcription
            model = whisper.load_model("large")
            result = model.transcribe(wav_file)
            transcript = result['text']
            return transcript

    except Exception as e:
        print(f"Error during transcription: {e}")
        return None

# Fetch transcript from YouTube API
def get_transcript_from_youtube_api(video_id, video_length):
    """Fetches transcript using YouTube API if available."""
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        for transcript in transcript_list:
            if not transcript.is_generated:
                segments = transcript.fetch()
                return " ".join(segment['text'] for segment in segments)

        if video_length > 15:
            auto_transcript = transcript_list.find_generated_transcript(['en'])
            if auto_transcript:
                segments = auto_transcript.fetch()
                return " ".join(segment['text'] for segment in segments)

        print("Manual transcript not available, and video is too short for auto-transcript.")
        return None

    except Exception as e:
        print(f"Error fetching transcript: {e}")
        return None

# Get transcript based on availability
async def get_transcript(youtube_url, api_key):
    """Gets transcript from YouTube API or Whisper if unavailable."""
    video_id = extract_video_id(youtube_url)
    if not video_id:
        print("Invalid or unsupported YouTube URL.")
        return None

    video_length = get_video_duration(video_id, api_key)
    if video_length is not None:
        print(f"Video length: {video_length:.2f} minutes.")
        transcript = get_transcript_from_youtube_api(video_id, video_length)
        if transcript:
            return transcript
        print("Using Whisper for transcription.")
        return await asyncio.to_thread(download_and_transcribe_with_whisper, youtube_url)
    else:
        print("Error fetching video duration.")
        return None

# Summarize text using Hugging Face summarizer
def summarize_text_huggingface(text):
    """Summarizes text using a Hugging Face summarization model."""
    max_input_length = 1024
    chunk_overlap = 100
    text_chunks = [
        text[i:i + max_input_length]
        for i in range(0, len(text), max_input_length - chunk_overlap)
    ]
    summaries = [
        summarizer(chunk, max_length=100, min_length=50, do_sample=False)[0]['summary_text']
        for chunk in text_chunks
    ]
    return " ".join(summaries)

# Generate optimized content
async def generate_optimized_content(api_key, summarized_transcript):
    prompt = f"""
    Analyze the following summarized YouTube video transcript and:
    1. Extract the top 10 keywords.
    2. Generate an optimized title (less than 65 characters).
    3. Create an engaging description.
    4. Generate related tags for the video.

    Summarized Transcript:
    {summarized_transcript}

    Provide the results in the following JSON format:
    {{
        "keywords": ["keyword1", "keyword2", ..., "keyword10"],
        "title": "Generated Title",
        "description": "Generated Description",
        "tags": ["tag1", "tag2", ..., "tag10"]
    }}
    """

    try:
        # Use the updated OpenAI API format for chat completions
        response = await asyncio.to_thread(openai.ChatCompletion.create,
                                            model="gpt-3.5-turbo",
                                            messages=[{"role": "system", "content": "You are an SEO expert."},
                                                      {"role": "user", "content": prompt}])
        response_content = response['choices'][0]['message']['content']
        content = json.loads(response_content)
        return content

    except Exception as e:
        print(f"Error generating content: {e}")
        return None

# Main function to process the video
async def main():
    youtube_url = input("Enter a YouTube video URL: ").strip()
    youtube_api_key = "YOUR_YOUTUBE_API_KEY"
    
    if not youtube_api_key or not openai.api_key:
        print("Missing API keys. Please set your YOUTUBE_API_KEY and OPENAI_API_KEY environment variables.")
        return

    transcript = await get_transcript(youtube_url, youtube_api_key)
    if not transcript:
        print("Could not fetch the transcript. Please try another video.")
        return

    summary = summarize_text_huggingface(transcript)
    print("\nSummarized Transcript:\n", summary)

    optimized_content = await generate_optimized_content(openai.api_key, summary)
    if optimized_content:
        print("\nOptimized Content:")
        print(json.dumps(optimized_content, indent=4))
    else:
        print("Error generating optimized content.")

if __name__ == "__main__":
    asyncio.run(main())
