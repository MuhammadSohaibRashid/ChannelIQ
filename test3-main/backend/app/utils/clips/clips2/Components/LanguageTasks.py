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


def extract_times(json_string, min_duration, max_duration):
    try:
        # Clean the JSON string
        json_string = re.sub(r'```json\s*|\s*```', '', json_string.strip())

        # Parse the JSON string
        data = json.loads(json_string)
        print("Time Given by Openai: ", data)
        
        # Extract highlights without validating duration
        highlights = []
        for clip in data:
            try:
                start_time = float(clip["start"])
                end_time = float(clip["end"])
                
                # Add all clips without duration validation
                highlights.append((int(start_time), int(end_time)))
                
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
            return extract_times(json.dumps(data), min_duration, max_duration)
        except:
            return []
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []


def GetHighlight(transcription, num_highlights, clip_length):
    # Define minimum duration (e.g., 15 seconds or 50% of max length)
    min_duration = max(15, clip_length * 0.5)

    system_prompt = f'''You are an expert video editor specializing in creating engaging short-form content. Analyze this transcription (which includes timestamps) and identify the {num_highlights} most compelling segments for short clips.

THE MOST IMPORTANT REQUIREMENT (CRITICAL): Each clip MUST be EXACTLY between {min_duration} and {clip_length} seconds long. This is a hard requirement - clips shorter than {min_duration} seconds or longer than {clip_length} seconds will be rejected.

SELECTING SEGMENTS:
- Look for moments that work well as standalone clips with clear beginnings and endings
- Find segments that are AS CLOSE AS POSSIBLE to {clip_length} seconds long
- Target complete thoughts or stories (don't cut mid-sentence)
- Prioritize:
  * Surprising revelations or "aha moments"
  * Concise explanations of interesting concepts
  * Emotional or humorous moments
  * High-energy or dramatic segments

TIMING INSTRUCTIONS (EXTREMELY IMPORTANT):
- Calculate your start and end times carefully to ensure clips are within the {min_duration}-{clip_length} second range
- DOUBLE-CHECK your start/end timestamps and verify each clip's duration before submitting
- If a segment seems too short, EXTEND it to include contextually relevant content but don't make it too long
- Choose natural break points at the beginning and end of segments
- Aim to make clips as close to {clip_length} seconds as possible - longer clips (within the limit) are preferred
- The ending time must be the last word spoken before the timestamp(00.00 - 10.45 i am aqib so it selects 10.45)

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
- Verify ALL clips are between {min_duration} and {clip_length} seconds
- If a clip is too short, extend it to include more context but dont make it too long that it exceeds {clip_length} seconds'''

    try:
        print(transcription)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.7,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": transcription}
            ]
        )

        json_string = response.choices[0].message.content
        highlights = extract_times(json_string, min_duration, clip_length)

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

if __name__ == "__main__":
    # Test the function
    test_transcription = """
    [Your test transcription here]
    """

    results = GetHighlight(test_transcription, 3, 30)

    if results:
        print("\nExtracted Highlights:")
        for idx, (start, end) in enumerate(results, 1):
            duration = end - start
            print(f"Highlight {idx}:")
            print(f"  Start: {start}s")
            print(f"  End: {end}s")
            print(f"  Duration: {duration}s")
    else:
        print("No valid highlights could be extracted")