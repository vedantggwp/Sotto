"""
Sotto Transcriber
Speech-to-text using faster-whisper with Metal acceleration.
"""

import numpy as np
from typing import Optional, Tuple, Generator
from pathlib import Path
import time


class Transcriber:
    """
    Fast speech-to-text transcription using Whisper.
    Optimized for low latency on Apple Silicon.
    """
    
    # Available models (size -> approximate VRAM/RAM)
    MODELS = {
        "tiny.en": "~75MB - Fastest, English only",
        "base.en": "~150MB - Good balance, English only",
        "small.en": "~500MB - Better accuracy, English only",
        "medium.en": "~1.5GB - High accuracy, English only",
        "tiny": "~75MB - Fastest, multilingual",
        "base": "~150MB - Good balance, multilingual",
        "small": "~500MB - Better accuracy, multilingual",
        "medium": "~1.5GB - High accuracy, multilingual",
        "large-v3": "~3GB - Best accuracy, multilingual",
    }
    
    def __init__(
        self,
        model_name: str = "base.en",
        device: str = "auto",
        compute_type: str = "int8"
    ):
        """
        Initialize the transcriber.
        
        Args:
            model_name: Whisper model to use
            device: Device to run on (auto, cpu, cuda, mps)
            compute_type: Quantization type (int8, float16, float32)
        """
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self._model = None
        self._is_loaded = False
        
    def load_model(self) -> bool:
        """Load the Whisper model"""
        try:
            from faster_whisper import WhisperModel
            
            print(f"Loading Whisper model: {self.model_name}")
            start = time.time()
            
            # Determine device
            if self.device == "auto":
                # faster-whisper will automatically use CoreML/Metal on Mac
                device = "cpu"  # faster-whisper handles acceleration internally
                compute_type = self.compute_type
            else:
                device = self.device
                compute_type = self.compute_type
            
            self._model = WhisperModel(
                self.model_name,
                device=device,
                compute_type=compute_type,
                download_root=str(Path.home() / ".sotto" / "models")
            )
            
            self._is_loaded = True
            print(f"Model loaded in {time.time() - start:.2f}s")
            return True
            
        except Exception as e:
            print(f"Failed to load model: {e}")
            return False
    
    def transcribe(
        self,
        audio: np.ndarray,
        language: str = "en"
    ) -> Tuple[str, float]:
        """
        Transcribe audio to text.
        
        Args:
            audio: Audio data as numpy array (16kHz, float32)
            language: Language code
            
        Returns:
            Tuple of (transcribed text, confidence score)
        """
        if not self._is_loaded:
            if not self.load_model():
                return "", 0.0
        
        if len(audio) == 0:
            return "", 0.0
        
        try:
            start = time.time()
            
            # Transcribe with faster-whisper
            segments, info = self._model.transcribe(
                audio,
                language=language,
                beam_size=1,  # Faster with beam_size=1
                best_of=1,
                temperature=0.0,  # Deterministic
                condition_on_previous_text=False,
                vad_filter=True,  # Filter out non-speech
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    speech_pad_ms=200,
                )
            )
            
            # Combine all segments
            text_parts = []
            total_confidence = 0.0
            segment_count = 0
            
            for segment in segments:
                text_parts.append(segment.text)
                total_confidence += segment.avg_logprob
                segment_count += 1
            
            text = " ".join(text_parts).strip()
            
            # Convert log probability to confidence (rough approximation)
            if segment_count > 0:
                avg_logprob = total_confidence / segment_count
                confidence = min(1.0, max(0.0, 1.0 + avg_logprob))
            else:
                confidence = 0.0
            
            latency = time.time() - start
            # print(f"Transcription: '{text}' (confidence: {confidence:.2f}, latency: {latency*1000:.0f}ms)")
            
            return text, confidence
            
        except Exception as e:
            print(f"Transcription error: {e}")
            return "", 0.0
    
    def transcribe_stream(
        self,
        audio_generator: Generator[np.ndarray, None, None],
        language: str = "en",
        min_audio_length: float = 0.5  # Minimum seconds before transcribing
    ) -> Generator[str, None, None]:
        """
        Stream transcription - transcribe audio in real-time.
        
        Args:
            audio_generator: Generator yielding audio chunks
            language: Language code
            min_audio_length: Minimum audio length before attempting transcription
            
        Yields:
            Transcribed text as it becomes available
        """
        if not self._is_loaded:
            if not self.load_model():
                return
        
        audio_buffer = []
        sample_rate = 16000
        
        for chunk in audio_generator:
            audio_buffer.append(chunk)
            
            # Calculate buffered audio duration
            total_samples = sum(len(c) for c in audio_buffer)
            duration = total_samples / sample_rate
            
            # Only transcribe if we have enough audio
            if duration >= min_audio_length:
                audio = np.concatenate(audio_buffer)
                text, confidence = self.transcribe(audio, language)
                
                if text and confidence > 0.3:  # Only yield if confident enough
                    yield text
                    audio_buffer = []  # Clear buffer after successful transcription
    
    def is_loaded(self) -> bool:
        """Check if model is loaded"""
        return self._is_loaded
    
    def unload_model(self):
        """Unload the model to free memory"""
        self._model = None
        self._is_loaded = False
    
    @classmethod
    def list_models(cls) -> dict:
        """List available Whisper models"""
        return cls.MODELS
