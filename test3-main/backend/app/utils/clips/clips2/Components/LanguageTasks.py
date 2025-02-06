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

        # Extract and validate highlights
        highlights = []
        for clip in data:
            try:
                start_time = float(clip["start"])
                end_time = float(clip["end"])

                # Validate duration
                if validate_clip_duration(start_time, end_time, min_duration, max_duration):
                    highlights.append((int(start_time), int(end_time)))
                else:
                    print(
                        f"Warning: Clip duration ({end_time - start_time}s) outside allowed range ({min_duration}-{max_duration}s)")

                    # Attempt to adjust clip length if too long
                    if end_time - start_time > max_duration:
                        new_end = start_time + max_duration
                        highlights.append((int(start_time), int(new_end)))
                        print(f"Adjusted clip to: {start_time}-{new_end}")

                    # Attempt to extend clip if too short
                    elif end_time - start_time < min_duration:
                        new_end = min(start_time + min_duration, end_time + (min_duration - (end_time - start_time)))
                        highlights.append((int(start_time), int(new_end)))
                        print(f"Adjusted clip to: {start_time}-{new_end}")

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

    system_prompt = f'''Based on the transcription provided with start and end times, highlight up to {num_highlights} main parts of the video, each between {min_duration} and {clip_length} seconds long. These highlights will be directly converted into short, engaging clips for platforms like TikTok.

Requirements:
1. Each clip MUST be between {min_duration} and {clip_length} seconds long.
2. Each clip should be a single continuous part of the video.
3. The highlights should be interesting and engaging.
4. Provide exactly {num_highlights} clips (or fewer only if not enough suitable content).
5. Format timestamps as decimal numbers (e.g., 12.5 not "12:30").

Format:
[
  {{
    "start": <start_time_in_seconds>,
    "content": "Brief description of clip content",
    "end": <end_time_in_seconds>
  }}
]
Ensure each clip duration is within the specified range. Invalid durations will be rejected.'''

    try:
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

        # Verify clip durations
        invalid_clips = [
            i for i, (start, end) in enumerate(highlights)
            if not validate_clip_duration(start, end, min_duration, clip_length)
        ]

        if invalid_clips:
            print(f"Found {len(invalid_clips)} invalid clip durations")

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