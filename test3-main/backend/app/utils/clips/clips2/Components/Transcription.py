from faster_whisper import WhisperModel
import torch

def transcribeAudio(audio_path, language=None):
    """
    Transcribes audio using the FasterWhisper model.
    If `language` is None, the model will automatically detect the language.
    """
    try:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = WhisperModel("base", device=device)  # Use a multilingual model

        segments, info = model.transcribe(
            audio=audio_path,
            beam_size=5,
            language=language,  # Specify the language or leave it None for auto-detection
            max_new_tokens=128,
            condition_on_previous_text=False
        )
        extracted_texts = [[segment.text, segment.start, segment.end] for segment in segments]
        return extracted_texts
    except Exception as e:
        print("Transcription Error:", e)
        return []

