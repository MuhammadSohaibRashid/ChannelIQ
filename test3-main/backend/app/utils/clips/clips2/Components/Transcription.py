from faster_whisper import WhisperModel
import torch
import os

def transcribeAudio(audio_path, language=None):
    """
    Transcribes audio using the FasterWhisper model and deletes the audio file after processing.
    If `language` is None, the model will automatically detect the language.
    
    Args:
        audio_path (str): Path to the audio file
        language (str, optional): Language code for transcription. Defaults to None for auto-detection.
    
    Returns:
        list: List of lists containing [text, start_time, end_time] for each segment
    """
    extracted_texts = []
    try:
        # Check if file exists before processing
        if not os.path.exists(audio_path):
            print(f"Error: Audio file not found at {audio_path}")
            return []

        # Set up device
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = WhisperModel("base", device=device)

        # Perform transcription
        segments, info = model.transcribe(
            audio=audio_path,
            beam_size=5,
            language=language,
            max_new_tokens=128,
            condition_on_previous_text=False,
            vad_filter=True
        )
        
        # Extract text segments
        extracted_texts = [[segment.text, segment.start, segment.end] for segment in segments]

    except Exception as e:
        print(f"Transcription Error: {str(e)}")
        return []
        
    finally:
        # Clean up the audio file
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
                print(f"Successfully deleted audio file: {audio_path}")
        except Exception as e:
            print(f"Error deleting audio file {audio_path}: {str(e)}")
    
    return extracted_texts