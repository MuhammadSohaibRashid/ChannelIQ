from openai import OpenAI
from dotenv import load_dotenv
import os
import json
import re

load_dotenv()

client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY'),
)


def validate_clip_duration(start, end, min_duration, max_duration):
    """Validate if a clip meets the duration requirements"""
    duration = end - start
    return min_duration <= duration <= max_duration


def extract_times(json_string, min_duration, max_duration, transcript_lines):
    try:
        # Clean the JSON string
        json_string = re.sub(r'```json\s*|\s*```', '', json_string.strip())

        # Parse the JSON string
        data = json.loads(json_string)
        print("Time Given by Openai: ", data)
        
        # Extract highlights and adjust end times
        highlights = []
        for clip in data:
            try:
                start_time = float(clip["start"])
                end_time = float(clip["end"])
                
                # Find the proper ending timestamp in the transcript
                adjusted_end_time = find_proper_ending_timestamp(end_time, transcript_lines)
                
                # Add clip with adjusted end time
                highlights.append((int(start_time), int(adjusted_end_time)))
                
            except (ValueError, TypeError) as e:
                print(f"Error processing clip: {e}")
                continue

        return highlights
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        # Attempt to fix common JSON formatting issues
        try:
            cleaned_json = re.sub(r'[\n\r\t]', '', json_string)
            cleaned_json = re.sub(r',\s*}', '}', cleaned_json)
            data = json.loads(cleaned_json)
            return extract_times(json.dumps(data), min_duration, max_duration, transcript_lines)
        except:
            return []
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []

def find_proper_ending_timestamp(suggested_end, transcript_lines):
    """
    Find the proper ending timestamp from the transcript lines
    based on the suggested ending time from OpenAI
    """
    # Parse transcript lines to get timestamp pairs
    timestamps = []
    for line in transcript_lines:
        parts = line.strip().split(":", 1)
        if len(parts) == 2:
            try:
                time_range = parts[0].strip()
                start_end = time_range.split("-")
                if len(start_end) == 2:
                    start = float(start_end[0].strip())
                    end = float(start_end[1].strip())
                    timestamps.append((start, end))
            except (ValueError, TypeError):
                continue
    
    # Find the closest ending timestamp after the suggested end
    closest_end = None
    min_diff = float('inf')
    
    for start, end in timestamps:
        # Look for end timestamps that are at or after the suggested end
        if end >= suggested_end:
            diff = end - suggested_end
            if diff < min_diff:
                min_diff = diff
                closest_end = end
    
    # If we found a better ending timestamp, use it
    if closest_end is not None:
        print(f"Adjusted end time from {suggested_end} to {closest_end}")
        return closest_end
    
    # If no better ending found, return the original
    return suggested_end


def GetHighlight(transcription, num_highlights, clip_length):
    """
    Get highlights from transcription
    
    Args:
        transcription (str): Transcription text with timestamps
        num_highlights (int): Number of highlights to extract
        clip_length (int, str): Length of each clip in seconds or "auto"
    
    Returns:
        list: List of tuples containing start and end times for highlights
    """
    # Handle various input types for clip_length
    is_auto_mode = False
    
    # Convert clip_length to proper type
    try:
        if clip_length == "auto" or clip_length == "Auto" or clip_length == "AUTO":
            is_auto_mode = True
            max_duration = 120  # 2 minutes cap for auto mode
        else:
            # Try to convert to int first
            clip_length = int(float(clip_length))
            max_duration = clip_length
    except (ValueError, TypeError):
        # If conversion fails, default to auto mode
        print(f"Invalid clip_length value: {clip_length}, defaulting to auto mode")
        is_auto_mode = True
        max_duration = 120
    
    transcript_lines = transcription.strip().split('\n')
    
    # Set maximum duration cap for auto mode (2 minutes = 120 seconds)
    MAX_AUTO_DURATION = 120
    
    # If using specific clip length, calculate min_duration as 50% of max length
    # If using auto mode, set minimum duration to 15 seconds
    min_duration = 15 if is_auto_mode else max(15, max_duration * 0.5)

    # Create the appropriate system prompt based on whether we're in auto mode
    if is_auto_mode:
        system_prompt = f'''You are an expert video editor specializing in creating engaging short-form content. Analyze this transcription (which includes timestamps) and identify the {num_highlights} most compelling segments for short clips.

THE MOST IMPORTANT REQUIREMENT (CRITICAL): Each clip MUST be EXACTLY between {min_duration} and {MAX_AUTO_DURATION} seconds long. This is a hard requirement - clips shorter than {min_duration} seconds or longer than {MAX_AUTO_DURATION} seconds will be rejected.

SELECTING SEGMENTS:
- Look for moments that work well as standalone clips with clear beginnings and endings
- For each clip, YOU decide the OPTIMAL duration (between {min_duration}-{MAX_AUTO_DURATION} seconds)
- Choose the length that best fits the specific content of each highlight
- Target complete thoughts or stories (don't cut mid-sentence)
- Prioritize:
  * Surprising revelations or "aha moments"
  * Concise explanations of interesting concepts
  * Emotional or humorous moments
  * High-energy or dramatic segments

TIMING INSTRUCTIONS (EXTREMELY IMPORTANT):
- Calculate your start and end times carefully to ensure clips are within the {min_duration}-{MAX_AUTO_DURATION} second range
- DOUBLE-CHECK your start/end timestamps and verify each clip's duration before submitting
- Choose natural break points at the beginning and end of segments
- The ending time must correspond to the completion of a full thought or sentence
- Always include complete sentences; never cut off mid-sentence
- The timestamp should be the one that appears after the last word of the complete thought

PROVIDE EXACTLY THIS FORMAT:
[
  {{
    "start": <start_time_in_seconds>,
    "end": <end_time_in_seconds>,
    "content": "Brief description of clip content and why it's engaging"
  }}
]

FINAL VERIFICATION (MANDATORY):
- Start/end times must be decimal numbers (e.g., 12.5, not "12:30")
- Calculate the duration of each clip by subtracting start from end
- Verify ALL clips are between {min_duration} and {MAX_AUTO_DURATION} seconds
- Each clip should be as long as needed to capture the complete thought or narrative, but not exceeding the maximum limit'''
    else:
        system_prompt = f'''You are an expert video editor specializing in creating engaging short-form content. Analyze this transcription (which includes timestamps) and identify the {num_highlights} most compelling segments for short clips.

THE MOST IMPORTANT REQUIREMENT (CRITICAL): Each clip MUST be EXACTLY between {min_duration} and {max_duration} seconds long. This is a hard requirement - clips shorter than {min_duration} seconds or longer than {max_duration} seconds will be rejected.

SELECTING SEGMENTS:
- Look for moments that work well as standalone clips with clear beginnings and endings
- Find segments that are AS CLOSE AS POSSIBLE to {max_duration} seconds long
- Target complete thoughts or stories (don't cut mid-sentence)
- Prioritize:
  * Surprising revelations or "aha moments"
  * Concise explanations of interesting concepts
  * Emotional or humorous moments
  * High-energy or dramatic segments

TIMING INSTRUCTIONS (EXTREMELY IMPORTANT):
- Calculate your start and end times carefully to ensure clips are within the {min_duration}-{max_duration} second range
- DOUBLE-CHECK your start/end timestamps and verify each clip's duration before submitting
- If a segment seems too short, EXTEND it to include contextually relevant content but don't make it too long
- Choose natural break points at the beginning and end of segments
- Aim to make clips as close to {max_duration} seconds as possible - longer clips (within the limit) are preferred
- The ending time must correspond to the completion of a full thought or sentence
- Always include complete sentences; never cut off mid-sentence
- The timestamp should be the one that appears after the last word of the complete thought

PROVIDE EXACTLY THIS FORMAT:
[
  {{
    "start": <start_time_in_seconds>,
    "end": <end_time_in_seconds>,
    "content": "Brief description of clip content and why it's engaging"
  }}
]

FINAL VERIFICATION (MANDATORY):
- Start/end times must be decimal numbers (e.g., 12.5, not "12:30")
- Calculate the duration of each clip by subtracting start from end
- Verify ALL clips are between {min_duration} and {max_duration} seconds
- If a clip is too short, extend it to include more context but dont make it too long that it exceeds {max_duration} seconds'''

    try:
        print(transcription)
        print(f"Running in {'AUTO mode with max duration of 120s' if is_auto_mode else f'FIXED mode with {max_duration}s clips'}")
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.7,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": transcription}
            ]
        )

        json_string = response.choices[0].message.content
        highlights = extract_times(json_string, min_duration, max_duration, transcript_lines)

        # Verify we got the requested number of clips
        if len(highlights) == 0:
            print("No valid highlights extracted")
            return []
        elif len(highlights) < num_highlights:
            print(f"Warning: Only found {len(highlights)} valid highlights")

        return highlights

    except Exception as e:
        print(f"Error: {e}")
        return []