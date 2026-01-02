"""
Sotto Audio Engine
Handles microphone capture with low latency.
"""

import numpy as np
import sounddevice as sd
from typing import Optional, Callable
from threading import Thread, Event
from queue import Queue
import time
import os

def _debug_print(*args, **kwargs):
    """Print only if debug mode is enabled (checks env var dynamically)"""
    if os.environ.get('SOTTO_DEBUG', '').lower() in ('1', 'true', 'yes'):
        print(*args, **kwargs)


class AudioEngine:
    """
    Low-latency audio capture engine.
    Captures audio from microphone and provides it for transcription.
    """
    
    # Audio settings optimized for speech recognition
    SAMPLE_RATE = 16000  # Whisper expects 16kHz
    CHANNELS = 1         # Mono audio
    DTYPE = np.float32   # Float32 for Whisper
    BLOCK_SIZE = 512     # ~32ms blocks for low latency
    
    def __init__(self):
        self._is_recording = False
        self._audio_queue: Queue = Queue()
        self._stop_event = Event()
        self._record_thread: Optional[Thread] = None
        self._on_audio_callback: Optional[Callable] = None
        self._audio_buffer: list = []
        
    def _audio_callback(self, indata, frames, time_info, status):
        """Callback for sounddevice stream"""
        if status:
            _debug_print(f"Audio status: {status}")
        
        # Copy audio data to avoid issues with buffer reuse
        audio_chunk = indata.copy().flatten()
        self._audio_queue.put(audio_chunk)
        self._audio_buffer.append(audio_chunk)
        
        # Call user callback if set
        if self._on_audio_callback:
            self._on_audio_callback(audio_chunk)
    
    def start_recording(self, on_audio: Optional[Callable] = None):
        """Start recording from microphone"""
        if self._is_recording:
            return
        
        self._is_recording = True
        self._stop_event.clear()
        self._audio_buffer = []
        self._on_audio_callback = on_audio
        
        # Clear queue
        while not self._audio_queue.empty():
            self._audio_queue.get()
        
        # Start recording in a thread
        self._record_thread = Thread(target=self._record_loop, daemon=True)
        self._record_thread.start()
    
    def _record_loop(self):
        """Main recording loop"""
        try:
            with sd.InputStream(
                samplerate=self.SAMPLE_RATE,
                channels=self.CHANNELS,
                dtype=self.DTYPE,
                blocksize=self.BLOCK_SIZE,
                callback=self._audio_callback
            ):
                while not self._stop_event.is_set():
                    time.sleep(0.01)  # Small sleep to prevent busy waiting
        except Exception as e:
            _debug_print(f"Audio recording error: {e}")
        finally:
            self._is_recording = False
    
    def stop_recording(self) -> np.ndarray:
        """Stop recording and return captured audio"""
        self._stop_event.set()
        
        if self._record_thread:
            self._record_thread.join(timeout=1.0)
            self._record_thread = None
        
        self._is_recording = False
        
        # Combine all audio chunks
        if self._audio_buffer:
            audio = np.concatenate(self._audio_buffer)
            self._audio_buffer = []
            return audio
        
        return np.array([], dtype=np.float32)
    
    def get_audio_chunk(self, timeout: float = 0.1) -> Optional[np.ndarray]:
        """Get the next audio chunk from the queue"""
        try:
            return self._audio_queue.get(timeout=timeout)
        except:
            return None
    
    def is_recording(self) -> bool:
        """Check if currently recording"""
        return self._is_recording
    
    def get_input_devices(self) -> list:
        """List available input devices"""
        devices = sd.query_devices()
        input_devices = []
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                input_devices.append({
                    'index': i,
                    'name': device['name'],
                    'channels': device['max_input_channels'],
                    'sample_rate': device['default_samplerate']
                })
        return input_devices
    
    def set_input_device(self, device_index: int):
        """Set the input device to use"""
        sd.default.device[0] = device_index


class VoiceActivityDetector:
    """
    Simple Voice Activity Detection (VAD)
    Detects when someone is speaking vs silence.
    """
    
    def __init__(self, 
                 energy_threshold: float = 0.01,
                 silence_duration: float = 0.5):
        self.energy_threshold = energy_threshold
        self.silence_duration = silence_duration
        self._silence_start: Optional[float] = None
    
    def is_speech(self, audio_chunk: np.ndarray) -> bool:
        """Check if audio chunk contains speech"""
        energy = np.sqrt(np.mean(audio_chunk ** 2))
        return energy > self.energy_threshold
    
    def check_silence_timeout(self, audio_chunk: np.ndarray) -> bool:
        """
        Check if silence has lasted longer than threshold.
        Returns True if we should stop recording due to silence.
        """
        if self.is_speech(audio_chunk):
            self._silence_start = None
            return False
        
        if self._silence_start is None:
            self._silence_start = time.time()
        
        return (time.time() - self._silence_start) > self.silence_duration
    
    def reset(self):
        """Reset the silence timer"""
        self._silence_start = None
