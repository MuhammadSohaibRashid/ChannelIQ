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
        system_prompt = f'''You are an expert video editor specializing in creating engaging short-form content. Analyze this transcription and identify EXACTLY {num_highlights} most compelling segments - no more, no less.

CRITICAL REQUIREMENTS (MUST FOLLOW):
1. Generate EXACTLY {num_highlights} highlights - not more, not less.
2. STRICT DURATION ENFORCEMENT: Each highlight MUST be between {min_duration} and {MAX_AUTO_DURATION} seconds total duration.
3. Always calculate durations precisely by subtracting start from end timestamps.
4. VERIFY EVERY TIMESTAMP before submitting - clips with incorrect durations will be REJECTED.

YOU CAN CHOOSE BETWEEN TWO TYPES OF HIGHLIGHTS:
1. CONTINUOUS CLIPS (PREFERRED): A single uninterrupted segment that captures a complete thought.
2. SEGMENTED CLIPS (USE SPARINGLY): Only use if absolutely necessary to remove irrelevant content.

RULES FOR SEGMENTED CLIPS:
- Only use when removing irrelevant/boring sections is essential
- Never use segments shorter than 15 seconds
- Do not cut during a continuous thought or mid-sentence
- Calculate the TOTAL duration of ALL segments (must be between {min_duration} and {MAX_AUTO_DURATION} seconds)

SELECTION CRITERIA:
- Target complete thoughts with natural beginning and endings
- Focus on content that works as a standalone clip
- Prioritize surprising revelations, concise explanations, emotional moments
- Do not cut mid-sentence or during important context

YOUR RESPONSE MUST BE VALID JSON WITH THIS STRUCTURE:
{{
  "highlights": [
    {{
      "start": <start_time_in_seconds>,
      "end": <end_time_in_seconds>,
      "content": "Brief description of clip content"
    }},
    {{
      "segments": [
        {{ "start": <start_time_in_seconds>, "end": <end_time_in_seconds> }},
        {{ "start": <start_time_in_seconds>, "end": <end_time_in_seconds> }}
      ],
      "content": "Brief description of segments"
    }}
  ]
}}

DURATION VALIDATION (MANDATORY):
Before finalizing each highlight:
1. Calculate duration = end_time - start_time
2. For segmented clips, sum all segment durations
3. VERIFY duration is between {min_duration} and {MAX_AUTO_DURATION} seconds
4. If duration is invalid, adjust your timestamps until it is valid

FINAL VERIFICATION CHECKLIST (MANDATORY):
- Count your highlights: MUST BE EXACTLY {num_highlights}
- Verify EVERY start/end time explicitly by calculating end - start = duration
- Double-check ALL durations are between {min_duration} and {MAX_AUTO_DURATION} seconds
- Use continuous clips whenever possible
- Do not include any text outside the JSON structure
- Do not include explanations - ONLY valid JSON'''
    else:
        system_prompt = f'''You are an expert video editor specializing in creating engaging short-form content. Analyze this transcription and identify EXACTLY {num_highlights} most compelling segments - no more, no less.

CRITICAL REQUIREMENTS (MUST FOLLOW):
1. Generate EXACTLY {num_highlights} highlights - not more, no less.
2. STRICT DURATION ENFORCEMENT: Each highlight MUST be between {min_duration} and {max_duration} seconds - NEVER OUTSIDE THIS RANGE.
3. TARGET DURATION: Aim for clips as close as possible to {max_duration} seconds.
4. VERIFY ALL TIMESTAMPS: Calculate each duration as (end - start) and confirm it's within range.

YOU CAN CHOOSE BETWEEN TWO TYPES OF HIGHLIGHTS:
1. CONTINUOUS CLIPS (PREFERRED): A single uninterrupted segment that captures a complete thought.
2. SEGMENTED CLIPS (USE SPARINGLY): Only use if absolutely necessary to remove irrelevant content.

RULES FOR SEGMENTED CLIPS:
- Only use when removing irrelevant/boring sections is essential
- Never use segments shorter than 15 seconds
- Do not cut during a continuous thought or mid-sentence
- Calculate the TOTAL duration of ALL segments (must be between {min_duration} and {max_duration} seconds)

SELECTION CRITERIA:
- Target complete thoughts with natural beginning and endings
- AIM FOR CLIPS AS CLOSE TO {max_duration} SECONDS AS POSSIBLE
- Prioritize surprising revelations, concise explanations, emotional moments
- Do not cut mid-sentence or during important context

YOUR RESPONSE MUST BE VALID JSON WITH THIS STRUCTURE:
{{
  "highlights": [
    {{
      "start": <start_time_in_seconds>,
      "end": <end_time_in_seconds>,
      "content": "Brief description of clip content"
    }},
    {{
      "segments": [
        {{ "start": <start_time_in_seconds>, "end": <end_time_in_seconds> }},
        {{ "start": <start_time_in_seconds>, "end": <end_time_in_seconds> }}
      ],
      "content": "Brief description of segments"
    }}
  ]
}}

DURATION VALIDATION (MANDATORY):
Before finalizing each highlight:
1. Calculate duration = end_time - start_time
2. For segmented clips, sum all segment durations
3. VERIFY duration is between {min_duration} and {max_duration} seconds
4. If duration is invalid, adjust your timestamps until it is valid

EXAMPLES OF INVALID CLIPS (DO NOT DO THESE):
- A clip with start=10, end=14 (duration: 4 seconds) - TOO SHORT
- A clip with start=50, end=180 (duration: 130 seconds) - TOO LONG

FINAL VERIFICATION CHECKLIST (MANDATORY):
- Count your highlights: MUST BE EXACTLY {num_highlights}
- MATHEMATICAL CHECK: Verify ALL durations by computing (end - start) for each clip
- ENSURE ALL durations are between {min_duration} and {max_duration} seconds
- Use continuous clips whenever possible
- Do not include any text outside the JSON structure
- Do not include explanations - ONLY valid JSON'''

    for attempt in range(max_retries):
        try:
            print(f"Running in {'AUTO mode with max duration of 120s' if is_auto_mode else f'FIXED mode with {max_duration}s clips'}")
            print(f"Attempt {attempt + 1} of {max_retries}")
            print(f"Requesting exactly {num_highlights} highlights")
            
            # Add a user message that explicitly asks for JSON format
            user_message = transcription + f"\n\nIMPORTANT: Generate EXACTLY {num_highlights} clips as valid JSON only. No explanations."
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.1,  # Lower temperature for more deterministic results
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