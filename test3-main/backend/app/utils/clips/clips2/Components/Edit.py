from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.editor import VideoFileClip, concatenate_videoclips
import subprocess

def extractAudio(video_path):
    try:
        video_clip = VideoFileClip(video_path)
        audio_path = "audio.wav"
        video_clip.audio.write_audiofile(audio_path)
        video_clip.close()
        return audio_path
    except Exception as e:
        print(f"An error occurred while extracting audio: {e}")
        return None


def crop_video(input_file, output_file, highlight, index=0):
    """
    Create a video clip from the input file based on the highlight information
    
    Args:
        input_file (str): Path to the input video file
        output_file (str): Path to save the output video file
        highlight (dict): Highlight information containing either a continuous segment or multiple segments
        index (int): Index of the highlight (used for naming output files)
    """
    try:
        with VideoFileClip(input_file) as video:
            if highlight["type"] == "continuous":
                start_time, end_time = highlight["segment"]
                print(f"Creating continuous clip from {start_time}s to {end_time}s (duration: {end_time-start_time}s)")
                cropped_video = video.subclip(start_time, end_time)
                cropped_video.write_videofile(output_file, codec='libx264')
                print(f"Created continuous clip: {output_file}")
            else:  # "cut" type
                # Create a list of subclips
                subclips = []
                total_duration = 0
                print(f"Creating clip with {len(highlight['segments'])} segments:")
                
                for start_time, end_time in highlight["segments"]:
                    segment_duration = end_time - start_time
                    total_duration += segment_duration
                    print(f"  - Segment from {start_time}s to {end_time}s (duration: {segment_duration}s)")
                    subclips.append(video.subclip(start_time, end_time))
                
                print(f"Total duration of cut clip: {total_duration}s")
                
                # Concatenate the subclips
                final_clip = concatenate_videoclips(subclips)
                final_clip.write_videofile(output_file, codec='libx264')
                print(f"Created clip with cuts: {output_file}")
    except Exception as e:
        print(f"An error occurred while cropping video: {e}")

# Example usage:
if __name__ == "__main__":
    input_file = r"Example.mp4" ## Test
    print(input_file)
    output_file = "Short.mp4"
    start_time = 31.92 
    end_time = 49.2   

    crop_video(input_file, output_file, start_time, end_time)

