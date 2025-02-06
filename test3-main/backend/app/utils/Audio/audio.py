# audio_utils/audio_processor.py

import os
import json
import torch
import torchaudio
import numpy as np
from moviepy.editor import VideoFileClip, AudioFileClip
from denoiser import pretrained
from denoiser.dsp import convert_audio
import soundfile as sf
import librosa
import pyloudnorm as pyln
from scipy import signal
from typing import Optional, Dict, Any, List
from django.core.exceptions import ValidationError
from pathlib import Path
class AudioEnhancer:
    def __init__(self, segment_duration: int = 10):
        """
        Initialize the Audio Enhancer with configuration parameters.
        
        Args:
            segment_duration (int): Duration of each audio segment in seconds
        """
        self.segment_duration = segment_duration
        self._validate_dependencies()

    def _validate_dependencies(self):
        """Validate that all required dependencies are available."""
        try:
            import torch
            import librosa
            import pyloudnorm
        except ImportError as e:
            raise ValidationError(f"Missing required dependency: {str(e)}")
    def _aggregate_analyses(self, segment_analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate analysis results from multiple segments."""
        if not segment_analyses:
            return {}
            
        aggregated = {
            "volume_levels": {},
            "noise_levels": {},
            "echo": {},
            "clarity": {},
            "music_detection": {}
        }
        
        for key in aggregated:
            values = [analysis[key] for analysis in segment_analyses if key in analysis]
            if not values:
                continue
                
            if isinstance(values[0], dict):
                # Aggregate dictionary values
                aggregated[key] = {
                    k: np.mean([v[k] for v in values if k in v])
                    for k in values[0]
                    if isinstance(values[0][k], (int, float))
                }
                
                # Handle boolean values separately
                bool_keys = [k for k in values[0] if isinstance(values[0][k], bool)]
                for k in bool_keys:
                    true_count = sum(1 for v in values if k in v and v[k])
                    aggregated[key][k] = true_count > len(values) / 2
            else:
                # Aggregate single values
                aggregated[key] = np.mean(values)
        
        return aggregated

    def analyze_audio(self, audio_path: str) -> Dict[str, Any]:
        """
        Analyze audio file and return detailed analysis.
        
        Args:
            audio_path (str): Path to the audio file
            
        Returns:
            Dict containing analysis results
        """
        try:
            # Convert to Path object and validate
            audio_path = Path(audio_path)
            if not audio_path.exists():
                raise ValidationError(f"Audio file not found: {audio_path}")

            # Load audio file
            try:
                audio_data, sr = librosa.load(str(audio_path), sr=None)
            except Exception as e:
                raise ValidationError(f"Failed to load audio file: {str(e)}")

            if len(audio_data) == 0:
                raise ValidationError("Audio file is empty")

            # Get segments
            segments = self._get_segments(audio_data, sr)
            
            # Analyze segments
            segment_analyses = []
            for i, segment in enumerate(segments):
                try:
                    analysis = self._analyze_segment(segment, sr)
                    segment_analyses.append(analysis)
                except Exception as e:
                    print(f"Warning: Failed to analyze segment {i}: {str(e)}")
                    continue

            if not segment_analyses:
                raise ValidationError("No segments could be analyzed")

            # Aggregate results
            final_results = self._aggregate_analyses(segment_analyses)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(final_results)
            final_results['recommended_enhancements'] = recommendations

            return self._ensure_json_serializable(final_results)
            
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Error analyzing audio: {str(e)}")
    def _generate_recommendations(self, analysis_results: Dict[str, Any]) -> List[str]:
        """Generate enhancement recommendations based on analysis results."""
        recommendations = []
        
        try:
            # Check noise levels
            if (analysis_results.get('noise_levels', {}).get('is_noisy', False) or
                analysis_results.get('noise_levels', {}).get('snr', 30) < 15):
                recommendations.append('noise_reduction')
            
            # Check volume levels
            if analysis_results.get('volume_levels', {}).get('needs_normalization', False):
                recommendations.append('volume_normalization')
            
            # Check clarity
            if analysis_results.get('clarity', {}).get('needs_clarity_enhancement', False):
                recommendations.append('clarity_enhancement')
            
            # Check echo
            if analysis_results.get('echo', {}).get('has_echo', False):
                recommendations.append('echo_reduction')
                
        except Exception as e:
            print(f"Warning: Error generating recommendations: {str(e)}")
            
        return recommendations

    def enhance_audio(self, input_path: str, output_path: str, analysis_results: Dict[str, Any]) -> None:
        """
        Enhance audio based on analysis results.
        
        Args:
            input_path (str): Path to input audio file
            output_path (str): Path to save enhanced audio
            analysis_results (Dict): Analysis results from analyze_audio
        """
        try:
            audio_data, sr = librosa.load(input_path, sr=None)
            duration = librosa.get_duration(y=audio_data, sr=sr)
            
            # Process audio in segments
            enhanced_segments = self._process_audio_segments(
                audio_data, sr, duration, analysis_results
            )
            
            # Combine segments with crossfade
            final_audio = self._combine_segments(enhanced_segments, sr)
            
            # Save enhanced audio
            sf.write(output_path, final_audio, sr)
            
        except Exception as e:
            raise ValidationError(f"Error enhancing audio: {str(e)}")

    def process_video(self, video_path: str, output_dir: str) -> Dict[str, Any]:
        """
        Process video file - extract audio, enhance it, and recombine.
        """
        try:
            # Convert paths to Path objects
            video_path = Path(video_path)
            output_dir = Path(output_dir)
            
            # Ensure output directory exists
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Get base name without extension
            base_name = video_path.stem
            
            # Generate temp paths
            temp_paths = self._generate_temp_paths(output_dir, base_name)
            
            # Extract and process audio
            with VideoFileClip(str(video_path)) as video:
                # Extract audio to temporary file
                video.audio.write_audiofile(str(temp_paths['temp_audio']))
                
                try:
                    # Analyze and enhance audio
                    analysis_results = self.analyze_audio(str(temp_paths['temp_audio']))
                    self.enhance_audio(
                        str(temp_paths['temp_audio']),
                        str(temp_paths['enhanced_audio']),
                        analysis_results
                    )
                except Exception as e:
                    print(f"Warning: Audio analysis/enhancement failed: {str(e)}")
                    # If analysis fails, just normalize the audio
                    self._apply_volume_normalization_file(
                        str(temp_paths['temp_audio']),
                        str(temp_paths['enhanced_audio'])
                    )
                
                # Combine enhanced audio with video
                self._combine_video_audio(
                    video, 
                    str(temp_paths['enhanced_audio']), 
                    str(temp_paths['enhanced_video'])
                )
            
            # Clean up temporary files
            self._cleanup_temp_files(temp_paths)
            
            return {
                'enhanced_video_path': str(temp_paths['enhanced_video']),
                'status': 'success'
            }
            
        except Exception as e:
            raise ValidationError(f"Error processing video: {str(e)}")

    def _get_segments(self, audio_data: np.ndarray, sr: int) -> List[np.ndarray]:
        """Split audio into segments for processing."""
        if not isinstance(sr, (int, np.integer)):
            raise ValidationError(f"Invalid sample rate: {sr}")
        
        segment_length = int(self.segment_duration * sr)
        if segment_length <= 0:
            raise ValidationError(f"Invalid segment length: {segment_length}")
            
        segments = []
        for i in range(0, len(audio_data), segment_length):
            segment = audio_data[i:i + segment_length]
            if len(segment) >= sr * 0.1:  # Only keep segments longer than 0.1 seconds
                segments.append(segment)
        
        return segments
    def _analyze_volume(self, segment: np.ndarray) -> Dict[str, Any]:
        """
        Analyze volume levels in audio segment.
        
        Args:
            segment (np.ndarray): Audio segment to analyze
            
        Returns:
            Dict containing volume analysis results
        """
        try:
            # Calculate RMS energy
            rms = np.sqrt(np.mean(segment**2))
            
            # Calculate peak amplitude
            peak = np.max(np.abs(segment))
            
            # Calculate dynamic range
            dynamic_range = 20 * np.log10(peak / (np.mean(np.abs(segment)) + 1e-10))
            
            # Calculate crest factor (peak to RMS ratio)
            crest_factor = peak / (rms + 1e-10)
            
            # Determine if normalization is needed
            needs_normalization = peak < 0.3 or peak > 0.9 or crest_factor > 20
            
            return {
                "rms_level": float(rms),
                "peak_level": float(peak),
                "dynamic_range": float(dynamic_range),
                "crest_factor": float(crest_factor),
                "needs_normalization": bool(needs_normalization)
            }
        except Exception as e:
            print(f"Warning: Error in volume analysis: {str(e)}")
            return {
                "rms_level": 0.0,
                "peak_level": 0.0,
                "dynamic_range": 0.0,
                "crest_factor": 0.0,
                "needs_normalization": True
            }
    def _analyze_segment(self, segment: np.ndarray, sr: int) -> Dict[str, Any]:
        """Analyze a single audio segment."""
        return {
            "volume_levels": self._analyze_volume(segment),
            "noise_levels": self._analyze_noise(segment, sr),
            "echo": self._detect_echo(segment, sr),
            "clarity": self._analyze_clarity(segment, sr),
            "music_detection": self._detect_music(segment, sr)
        }

    def _analyze_noise(self, segment: np.ndarray, sr: int) -> Dict[str, Any]:
        """Analyze noise levels in audio segment."""
        stft = librosa.stft(segment)
        mag_spec = np.abs(stft)
        
        # Calculate various noise metrics
        noise_floor = np.percentile(mag_spec, 15, axis=1)
        spectral_flatness = librosa.feature.spectral_flatness(S=mag_spec)[0]
        
        # Analyze frequency bands
        freqs = librosa.fft_frequencies(sr=sr)
        speech_band_mask = (freqs >= 300) & (freqs <= 3400)
        speech_band_energy = np.mean(mag_spec[speech_band_mask], axis=1)
        background_energy = np.mean(mag_spec[~speech_band_mask], axis=1)
        
        # Calculate SNR and other metrics
        signal_power = np.mean(speech_band_energy ** 2)
        noise_power = np.mean(background_energy ** 2)
        snr = 10 * np.log10(signal_power / (noise_power + 1e-10))
        
        return {
            "noise_level": float(np.mean(noise_floor)),
            "is_noisy": bool(snr < 15 or np.mean(spectral_flatness) > 0.4),
            "snr": float(snr),
            "spectral_flatness": float(np.mean(spectral_flatness))
        }

    def _detect_echo(self, segment: np.ndarray, sr: int) -> Dict[str, Any]:
        """Detect echo in audio segment."""
        correlation = signal.correlate(segment, segment, mode='full')
        correlation = correlation[len(correlation) // 2:]
        
        peaks, _ = signal.find_peaks(
            correlation,
            height=0.1,
            distance=int(0.05 * sr)
        )
        
        prominences = signal.peak_prominences(correlation, peaks)[0]
        has_echo = bool(len(peaks) > 2 and np.mean(prominences) > 0.15)
        
        return {
            "has_echo": has_echo,
            "echo_strength": float(np.mean(correlation[peaks]) if len(peaks) > 0 else 0)
        }

    def _analyze_clarity(self, segment: np.ndarray, sr: int) -> Dict[str, Any]:
        """Analyze speech clarity in audio segment."""
        try:
            centroid = librosa.feature.spectral_centroid(y=segment, sr=sr)[0]
            bandwidth = librosa.feature.spectral_bandwidth(y=segment, sr=sr)[0]
            
            return {
                "speech_clarity": float(np.mean(centroid)),
                "needs_clarity_enhancement": bool(np.mean(bandwidth) > 2000)
            }
        except Exception as e:
            return {
                "speech_clarity": 0.0,
                "needs_clarity_enhancement": False
            }

    def _detect_music(self, segment: np.ndarray, sr: int) -> Dict[str, Any]:
        """Detect presence of music in audio segment."""
        try:
            mel_spec = librosa.feature.melspectrogram(y=segment, sr=sr)
            onset_env = librosa.onset.onset_strength(y=segment, sr=sr)
            tempo, beats = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
            
            harmonic, _ = librosa.effects.hpss(segment)
            chroma = librosa.feature.chroma_stft(y=harmonic, sr=sr)
            
            has_music = bool(
                tempo > 50 and tempo < 200 and
                np.var(chroma) > 0.15
            )
            
            return {
                "has_music": has_music,
                "music_strength": float(np.mean(onset_env)),
                "tempo": float(tempo)
            }
        except Exception as e:
            return {
                "has_music": False,
                "music_strength": 0.0,
                "tempo": 0.0
            }

    def _process_audio_segments(
        self, 
        audio_data: np.ndarray, 
        sr: int, 
        duration: float,
        analysis_results: Dict[str, Any]
    ) -> List[np.ndarray]:
        """Process audio in segments with enhancements."""
        segments = self._get_segments(audio_data, sr)
        enhanced_segments = []
        
        for segment in segments:
            if len(segment) < sr * 0.1:  # Skip very short segments
                enhanced_segments.append(segment)
                continue
                
            enhanced = self._apply_enhancements(segment, sr, analysis_results)
            enhanced_segments.append(enhanced)
            
        return enhanced_segments

    def _apply_enhancements(
        self, 
        segment: np.ndarray, 
        sr: int, 
        analysis_results: Dict[str, Any]
    ) -> np.ndarray:
        """Apply audio enhancements based on analysis."""
        enhanced = segment.copy()
        
        if "noise_reduction" in analysis_results.get("recommended_enhancements", []):
            enhanced = self._apply_noise_reduction(enhanced, sr)
            
        if "volume_normalization" in analysis_results.get("recommended_enhancements", []):
            enhanced = self._apply_volume_normalization(enhanced, sr)
            
        return enhanced

    def _apply_noise_reduction(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """Apply noise reduction to audio segment."""
        try:
            denoiser = pretrained.dns64().cpu()
            wav = torch.FloatTensor(audio).unsqueeze(0)
            wav = convert_audio(wav, sr, denoiser.sample_rate, denoiser.chin)
            
            with torch.no_grad():
                denoised = denoiser(wav)[0].cpu().numpy().squeeze()
            
            return librosa.resample(
                denoised, 
                orig_sr=denoiser.sample_rate, 
                target_sr=sr
            )
        except Exception:
            return audio

    def _apply_volume_normalization_file(self, input_path: str, output_path: str) -> None:
        """Apply volume normalization directly to an audio file."""
        try:
            audio_data, sr = librosa.load(input_path, sr=None)
            normalized = self._apply_volume_normalization(audio_data, sr)
            sf.write(output_path, normalized, sr)
        except Exception as e:
            print(f"Warning: Volume normalization failed: {str(e)}")
            # If normalization fails, copy the input file to output
            import shutil
            shutil.copy2(input_path, output_path)
    def _combine_segments(
        self, 
        segments: List[np.ndarray], 
        sr: int, 
        crossfade_duration: float = 0.1
    ) -> np.ndarray:
        """Combine audio segments with crossfade."""
        if len(segments) == 1:
            return segments[0]
            
        crossfade_length = int(crossfade_duration * sr)
        result = segments[0][:-crossfade_length]
        
        for i in range(1, len(segments)):
            fade_out = np.linspace(1, 0, crossfade_length)
            fade_in = np.linspace(0, 1, crossfade_length)
            
            overlap_end = segments[i - 1][-crossfade_length:]
            overlap_start = segments[i][:crossfade_length]
            crossfaded = (overlap_end * fade_out) + (overlap_start * fade_in)
            
            result = np.concatenate([
                result, 
                crossfaded, 
                segments[i][crossfade_length:]
            ])
            
        return result

    def _combine_video_audio(
        self, 
        video: VideoFileClip, 
        audio_path: str, 
        output_path: str
    ) -> None:
        """Combine video with enhanced audio."""
        try:
            with AudioFileClip(audio_path) as audio:
                final_video = video.set_audio(audio)
                final_video.write_videofile(
                    output_path,
                    codec='libx264',
                    audio_codec='aac',
                    temp_audiofile=str(Path(output_path).parent / "temp-audio.m4a"),
                    remove_temp=True
                )
        except Exception as e:
            raise ValidationError(f"Error combining video and audio: {str(e)}")


    def _generate_temp_paths(self, output_dir: Path, base_name: str) -> Dict[str, Path]:
        """Generate paths for temporary and output files."""
        return {
            'temp_audio': output_dir / f"{base_name}_temp_audio.wav",
            'enhanced_audio': output_dir / f"{base_name}_enhanced_audio.wav",
            'enhanced_video': output_dir / f"{base_name}_enhanced_video.mp4"
        }

    def _cleanup_temp_files(self, temp_paths: Dict[str, Path]) -> None:
        """Clean up temporary files."""
        for key in ['temp_audio', 'enhanced_audio']:
            try:
                if temp_paths[key].exists():
                    temp_paths[key].unlink()
            except Exception as e:
                print(f"Warning: Could not delete temporary file {temp_paths[key]}: {str(e)}")

    def _ensure_json_serializable(self, obj: Any) -> Any:
        """Ensure all values are JSON serializable."""
        if isinstance(obj, dict):
            return {str(key): self._ensure_json_serializable(value) 
                    for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._ensure_json_serializable(value) for value in obj]
        elif isinstance(obj, (np.integer, np.floating)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        else:
            return str(obj)