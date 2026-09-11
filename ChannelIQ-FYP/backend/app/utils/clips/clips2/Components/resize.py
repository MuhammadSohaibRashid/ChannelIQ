import os
from django.conf import settings
import clipsai
from datetime import datetime

def resize_video(input_video_path):
    """
    Resize a video file using clipsai and save it in Django media directory.
    
    Args:
        input_video_path (str): Path to the input video file
        
    Returns:
        str: Path to the processed video relative to MEDIA_ROOT, using forward slashes
    """
    # Create necessary directories if they don't exist
    processed_dir = os.path.join(settings.MEDIA_ROOT, 'processed')
    os.makedirs(processed_dir, exist_ok=True)
    
    # Generate unique filename for the output
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_filename = f'resized_video_{timestamp}.mp4'
    output_path = os.path.join(processed_dir, output_filename)
    
    try:
        # Get crops using clipsai
        crops = clipsai.resize(
            video_file_path=input_video_path,
            pyannote_auth_token="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",
            aspect_ratio=(9, 16)
        )
        
        # Initialize media editor
        media_editor = clipsai.MediaEditor()
        media_file = clipsai.AudioVideoFile(input_video_path)
        
        # Resize the video
        resized_video_file = media_editor.resize_video(
            original_video_file=media_file,
            resized_video_file_path=output_path,
            width=crops.crop_width,
            height=crops.crop_height,
            segments=crops.to_dict()["segments"],
        )
        
        # Return the path with forward slashes, formatted for frontend use
        relative_path = os.path.relpath(output_path, settings.MEDIA_ROOT)
        formatted_path = relative_path.replace(os.sep, '/')
        
        return formatted_path
        
    except Exception as e:
        print(f"Error processing video: {str(e)}")
        raise