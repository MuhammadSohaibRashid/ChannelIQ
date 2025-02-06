import yt_dlp
import json


def fetch_video_metadata(url):
    ydl_opts = {
        'quiet': True,
        'forcejson': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Fetch the video metadata
            info_dict = ydl.extract_info(url, download=False)

            # Extract the title, description, and tags
            video_metadata = {
                'title': info_dict.get('title', 'N/A'),
                'description': info_dict.get('description', 'N/A').strip(),
                'tags': [
                    tag.replace('\r', '').replace('\n', '').strip()
                    for tag in info_dict.get('tags', [])
                    if tag.strip()
                ]
            }

            return video_metadata
    except Exception as e:
        print(f"Error fetching video metadata: {str(e)}")
        return None