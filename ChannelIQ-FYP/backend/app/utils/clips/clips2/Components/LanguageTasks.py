from openai import OpenAI
from dotenv import load_dotenv
import os
import json
import re
import time
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
        # Debug the raw response
        print("Raw response from OpenAI:")
        print(json_string)
        
        # Return early if the response is empty
        if not json_string or json_string.isspace():
            print("Error: Empty response from OpenAI")
            return []
        
        # Clean the JSON string
        json_string = re.sub(r'```json\s*|\s*```', '', json_string.strip())
        
        # Debug the cleaned JSON string
        print("Cleaned JSON string:")
        print(json_string)
        
        # Try to parse the JSON string
        try:
            data = json.loads(json_string)
            print("Time Given by OpenAI: ", data)
            
            # Check if the data has a 'highlights' key and extract the array
            if isinstance(data, dict) and "highlights" in data:
                data = data["highlights"]
                
        except json.JSONDecodeError as e:
            print(f"Initial JSON parsing error: {e}")
            
            # Try more aggressive cleaning
            json_string = re.sub(r'[^\x00-\x7F]+', '', json_string)  # Remove non-ASCII chars
            json_string = re.sub(r'[\n\r\t]', '', json_string)
            json_string = re.sub(r',\s*}', '}', json_string)
            json_string = re.sub(r',\s*\]', ']', json_string)
            
            # Try to find JSON-like structure within the text
            match = re.search(r'\[.*\]', json_string, re.DOTALL)
            if match:
                json_string = match.group(0)
                print("Extracted JSON array:")
                print(json_string)
            
            try:
                data = json.loads(json_string)
                print("Successfully parsed JSON after cleaning")
                
                # Check if the data has a 'highlights' key and extract the array
                if isinstance(data, dict) and "highlights" in data:
                    data = data["highlights"]
                    
            except json.JSONDecodeError:
                print("Still couldn't parse JSON, checking for single object")
                # Check if it's a single object instead of an array
                match = re.search(r'\{.*\}', json_string, re.DOTALL)
                if match:
                    try:
                        obj = json.loads(match.group(0))
                        
                        # Check if obj has a 'highlights' key
                        if "highlights" in obj and isinstance(obj["highlights"], list):
                            data = obj["highlights"]
                        else:
                            data = [obj]  # Convert to list
                            
                        print("Successfully parsed single JSON object")
                    except json.JSONDecodeError:
                        print("Failed to parse single object too")
                        return []
                else:
                    print("No valid JSON structure found")
                    return []
        
        # Extract highlights 
        highlights = []
        for clip in data:
            try:
                # Check if this is a continuous clip or a clip with cuts
                if "segments" in clip:
                    # This is a clip with cuts
                    segments = []
                    for segment in clip["segments"]:
                        start_time = float(segment["start"])
                        end_time = float(segment["end"])
                        
                        # Find the proper ending timestamp in the transcript
                        adjusted_end_time = find_proper_ending_timestamp(end_time, transcript_lines)
                        
                        segments.append((int(start_time), int(adjusted_end_time)))
                    
                    highlights.append({
                        "type": "cut",
                        "segments": segments,
                        "content": clip.get("content", "")
                    })
                else:
                    # This is a continuous clip
                    start_time = float(clip["start"])
                    end_time = float(clip["end"])
                    
                    # Find the proper ending timestamp in the transcript
                    adjusted_end_time = find_proper_ending_timestamp(end_time, transcript_lines)
                    
                    # Add clip with adjusted end time
                    highlights.append({
                        "type": "continuous",
                        "segment": (int(start_time), int(adjusted_end_time)),
                        "content": clip.get("content", "")
                    })
                
            except (ValueError, TypeError, KeyError) as e:
                print(f"Error processing clip: {e}")
                print(f"Problematic clip data: {clip}")
                continue

        print(f"Successfully extracted {len(highlights)} highlights")
        return highlights
        
    except Exception as e:
        print(f"Unexpected error in extract_times: {e}")
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


def GetHighlight(transcription, num_highlights, clip_length, max_retries=1):
    """
    Get highlights from transcription with option for continuous clips or clips with cuts
    
    Args:
        transcription (str): Transcription text with timestamps
        num_highlights (int): Number of highlights to extract
        clip_length (int, str): Length of each clip in seconds or "auto"
        max_retries (int): Maximum number of retries if the API call fails
    
    Returns:
        list: List of dictionaries containing highlight information
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
    
    # If using specific clip length, calculate min_duration as 75% of max length
    # This forces clips to be much closer to the requested length
    min_duration = 15 if is_auto_mode else max(15, max_duration * 0.75)

    # Create the appropriate system prompt based on whether we're in auto mode
    if is_auto_mode:
        system_prompt = f"""You are a professional video editor. Your task is to extract EXACTLY {num_highlights} high-quality highlights from this transcript.

STRICT TIMING RULES:
1. Each highlight MUST be BETWEEN {min_duration} and {MAX_AUTO_DURATION} seconds — no exceptions.
2. Calculate duration as: duration = end_timestamp - start_timestamp.
3. Every highlight MUST include its calculated duration for verification.

HIGHLIGHT TYPES:
1. CONTINUOUS: A single uninterrupted segment (preferred).
2. SEGMENTED: Multiple segments stitched together (use only if essential to remove irrelevant parts).

RULES FOR SEGMENTED CLIPS:
- Use ONLY when trimming is necessary.
- Each segment must be AT LEAST 15 seconds long.
- Never split mid-sentence or during continuous thoughts.
- Combined duration must still fall between {min_duration} and {MAX_AUTO_DURATION} seconds.

MANDATORY VERIFICATION:
1. Continuous: duration = end - start
2. Segmented: total_duration = sum of segment durations
3. If duration < {min_duration}, extend to add context
4. If duration > {MAX_AUTO_DURATION}, trim or use segmentation
5. Every highlight must display its duration explicitly

OUTPUT FORMAT (STRICT JSON ONLY):
{{
  "highlights": [
    {{
      "start": <start_time_in_seconds>,
      "end": <end_time_in_seconds>,
      "duration": <calculated_duration>,
      "content": "Brief description of clip content"
    }},
    {{
      "segments": [
        {{ "start": <start_time>, "end": <end_time>, "duration": <duration> }},
        {{ "start": <start_time>, "end": <end_time>, "duration": <duration> }},
        ... //Continue as needed
      ],
      "total_duration": <total_combined_duration>,
      "content": "Brief description of segments"
    }}
  ]
}}
This is the format for one continous clip and one segmented clip, if u see both clips need to be segmented then use segmented format for both and if u see both clips need to be continous then use continous format for both and if u see one clip is continous and one clip is segmented then use continous format for first clip and segmented format for second clip.
for segments dont do very short jumps, only do jumps when there is a long pause or when the speaker is not speaking(u know the speaker is not speaking if the transcription dont have anything from a certain time like transcription starts from 4 then the speaker isnt speaking in that time period), and if you see that the speaker is not speaking for a long time then only do the jump and if you see that the speaker is speaking continously then dont do any jumps.

If segments offer better clarity or quality, you may use segmented format consistently across all highlights.

FINAL CHECKLIST:
1. TOTAL: Exactly {num_highlights} highlights ✓
2. DURATION: Each is within {min_duration}–{MAX_AUTO_DURATION} seconds ✓
3. VERIFICATION: All durations shown and correct ✓
4. FORMAT: Valid JSON with NO extra text ✓

OUTPUT MUST BE STRICTLY VALID JSON — NO commentary, no additional text.
"""
    else:
        system_prompt = f"""You are a professional video editor. Your task is to extract EXACTLY {num_highlights} compelling highlights from this transcript.

STRICT TIMING RULES:
1. Each highlight MUST be BETWEEN {min_duration} and {max_duration} seconds — NO exceptions.
2. TARGET: Keep each clip as close as possible to {max_duration} seconds without exceeding it.
3. Calculate duration as: duration = end_timestamp - start_timestamp.

HIGHLIGHT TYPES:
1. CONTINUOUS: A single uninterrupted segment (preferred).
2. SEGMENTED: Multiple segments that form a coherent clip. Use only when needed to remove filler.

MANDATORY CHECKS:
1. For each highlight: duration = end - start
2. For segmented: total_duration = sum of segment durations
3. Verify: {min_duration} ≤ duration ≤ {max_duration}
4. Do NOT cut mid-sentence or remove key context

SELECTION CRITERIA:
- Complete thoughts with natural beginnings and ends
- Standalone, self-contained clips
- Prioritize powerful moments: emotional reactions, concise insights, pivotal points

OUTPUT FORMAT (STRICT JSON ONLY):
{{
  "highlights": [
    {{
      "start": <start_time_in_seconds>,
      "end": <end_time_in_seconds>,
      "duration": <calculated_duration>,
      "content": "Brief description of clip content"
    }},
    {{
      "segments": [
        {{ "start": <start_time>, "end": <end_time>, "duration": <duration> }},
        {{ "start": <start_time>, "end": <end_time>, "duration": <duration> }},
        ... //Continue as needed
      ],
      "total_duration": <sum_of_durations>,
      "content": "Brief description of segments"
    }}
  ]
}}
This is the format for one continous clip and one segmented clip, if u see both clips need to be segmented then use segmented format for both and if u see both clips need to be continous then use continous format for both and if u see one clip is continous and one clip is segmented then use continous format for first clip and segmented format for second clip.
for segments dont do very short jumps, only do jumps when there is a long pause or when the speaker is not speaking(u know the speaker is not speaking if the transcription dont have anything from a certain time like transcription starts from 4 then the speaker isnt speaking in that time period), and if you see that the speaker is not speaking for a long time then only do the jump and if you see that the speaker is speaking continously then dont do any jumps.
FINAL CHECKLIST:
1. TOTAL: Exactly {num_highlights} highlights ✓
2. TIMING: All durations within {min_duration}–{max_duration} ✓
3. VERIFICATION: All durations correctly calculated ✓
4. FORMAT: Valid JSON only — NO extra text ✓

RESPONSE MUST BE PURE JSON — DO NOT INCLUDE EXPLANATIONS OR NOTES.
"""

    for attempt in range(max_retries):
        try:
            print(f"Running in {'AUTO mode with max duration of 120s' if is_auto_mode else f'FIXED mode with {max_duration}s clips'}")
            print(f"Attempt {attempt + 1} of {max_retries}")
            print(f"Requesting exactly {num_highlights} highlights")
            
            # Add a user message that explicitly asks for JSON format
            user_message = transcription + f"\n\nIMPORTANT: Generate EXACTLY {num_highlights} clips as valid JSON only. No explanations."
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.3,  # Lower temperature for more deterministic results
                response_format={"type": "json_object"},  # Force JSON response format
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ]
            )

            json_string = response.choices[0].message.content
            highlights = extract_times(json_string, min_duration, max_duration, transcript_lines)

            # Verify we got the exact requested number of clips
            if len(highlights) == 0:
                print("No valid highlights extracted in this attempt")
                # Wait before retry
                time.sleep(2)
                continue
            elif len(highlights) != num_highlights:
                print(f"Warning: Found {len(highlights)} highlights instead of the requested {num_highlights}")
                # If this is the last retry attempt and we have at least some highlights, return them
                if attempt == max_retries - 1 and len(highlights) > 0:
                    print("Returning available highlights after all retry attempts")
                    # If we have more highlights than requested, trim the list
                    if len(highlights) > num_highlights:
                        highlights = highlights[:num_highlights]
                    return highlights
                # Otherwise retry
                time.sleep(2)
                continue
            else:
                # Success! We got exactly the requested number of highlights
                return highlights

        except Exception as e:
            print(f"Error in attempt {attempt + 1}: {e}")
            time.sleep(2)  # Wait before retry
    
    # If we reach here, all attempts failed or we couldn't get exactly num_highlights
    print("All attempts to extract the exact number of highlights failed")
    return []