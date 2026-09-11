import os
import re
import yt_dlp
import unicodedata

def sanitize_filename(filename):
    """Remove invalid characters for filenames and strip emojis."""
    # Remove emojis and other non-printable characters
    filename = ''.join(c for c in filename if not unicodedata.category(c).startswith('So'))
    # Remove invalid characters for filenames
    return re.sub(r'[\\/*?:"<>|]', "_", filename)

def download_youtube_video(url, media_root="media"):
    try:
        video_folder = os.path.join(media_root, "videos")
        os.makedirs(video_folder, exist_ok=True)
        
        # Use yt-dlp to extract video and audio information
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info_dict = ydl.extract_info(url, download=False)  # Extract video info without downloading
        
        video_id = info_dict['id']
        output_file = os.path.join(video_folder, f"{video_id}.mp4")
        
        # Check if file already exists
        if os.path.exists(output_file):
            print(f"Video {video_id} already exists. Skipping download.")
            return os.path.abspath(output_file)
        
        # Define yt-dlp options
        ydl_opts = {
            'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]',
            'outtmpl': output_file,  # Save with video ID as filename
            'quiet': False,  # Enable verbose logging
        }

        # Download the video
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Return the absolute path of the video file
        return os.path.abspath(output_file)

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        print("Please ensure the latest versions of yt-dlp are installed.")
        print("Update it with:")
        print("pip install --upgrade yt-dlp")

if __name__ == "__main__":
    youtube_url = input("Enter YouTube video URL: ")
    downloaded_file_path = download_youtube_video(youtube_url)
    print(f"Downloaded video file: {downloaded_file_path}")