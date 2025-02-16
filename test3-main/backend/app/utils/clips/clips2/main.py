# backend/Clips-Generator/main.py

import sys
import os
import logging

from .Components.YoutubeDownloader import download_youtube_video
from .Components.Edit import extractAudio, crop_video
from .Components.Transcription import transcribeAudio
from .Components.LanguageTasks import GetHighlight
from .Components.FaceCrop import process_video_clip, combine_videos
from .Components.resize import resize_video
from django.conf import settings

# Suppress MoviePy logs
logging.getLogger("moviepy").setLevel(logging.WARNING)

def process_video(url, clip_length, clip_count, media_root):
    """
    Process YouTube video to create clips
    
    Args:
        url (str): YouTube video URL
        clip_length (int): Length of each clip in seconds
        clip_count (int): Number of clips to generate
        media_root (str): Path to media directory
    
    Returns:
        list: List of dictionaries containing paths to processed video clips
    """
    # Ensure media directory exists
    os.makedirs(media_root, exist_ok=True)

    # Download video
    Vid = download_youtube_video(url,media_root)

    if Vid:
        Vid = Vid.replace(".webm", ".mp4")

        # Extract audio
        Audio = extractAudio(Vid)
        if Audio:
            # Get transcription
            transcriptions = transcribeAudio(Audio)
            if len(transcriptions) > 0:
                TransText = ""

                # Combine transcription text for processing
                for text, start, end in transcriptions:
                    TransText += (f"{start} - {end}: {text}\n")

                # Get highlights
                highlights = GetHighlight(TransText, clip_count, clip_length)
                if highlights and len(highlights) >= clip_count:
                    final_videos = []

                    # Process each highlight
                    for idx, (start, stop) in enumerate(highlights):
                        # Generate output paths
                        processed = os.path.join(media_root, 'processed')
                        Temp = os.path.join(media_root, 'Temp')
                        os.makedirs(Temp, exist_ok=True)
                        os.makedirs(processed, exist_ok=True)
                        cropped_output = os.path.join(Temp, f"cropped_clip_{idx + 1}.mp4")
                        # Process video segments
                        crop_video(Vid, cropped_output, start, stop)
                        combined_output=resize_video(cropped_output)
                        final_videos.append({
                            "clip_path": combined_output
                        })

                    return final_videos
                else:
                    print("Error in getting sufficient highlights")
                    return None
            else:
                print("No transcriptions found")
                return None
        else:
            print("No audio file found")
            return None
    else:
        print("Unable to Download the video")
        return None
