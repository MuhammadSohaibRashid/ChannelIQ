import os
import yt_dlp
import whisper
from urllib.parse import urlparse, parse_qs
from transformers import pipeline
from youtube_transcript_api import YouTubeTranscriptApi
import openai


def extract_video_id(video_url):
    """Extract Video ID from a YouTube URL."""
    parsed_url = urlparse(video_url)
    if "youtube.com" in parsed_url.netloc:
        return parse_qs(parsed_url.query).get("v", [None])[0]
    elif "youtu.be" in parsed_url.netloc:
        return parsed_url.path.strip("/")
    return None


def fetch_transcript(video_url, video_id, youtube_api_key):
    """Fetch transcript via YouTube API or fallback to Whisper."""
    try:
        # Attempt YouTube Transcript API
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["en"])
        return " ".join([seg["text"] for seg in transcript])
    except Exception:
        # Fallback to Whisper transcription
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_file = os.path.join(temp_dir, "audio.mp3")

            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': audio_file,
                'quiet': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])

            model = whisper.load_model("base")
            result = model.transcribe(audio_file)
            return result["text"]


def summarize_text_huggingface(text):
    """Summarize text using Hugging Face."""
    summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
    return summarizer(text, max_length=100, min_length=50, do_sample=False)[0]["summary_text"]


def generate_optimized_content(openai_api_key, summary):
    """Generate SEO content using OpenAI."""
    openai.api_key = openai_api_key
    prompt = f"""
    Generate SEO content based on this summary:
    {summary}
    Provide title, keywords, description, and tags in JSON format.
    """
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=300
    )
    return response.choices[0].text
