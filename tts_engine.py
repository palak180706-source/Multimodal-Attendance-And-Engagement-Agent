import os
import time
import hashlib
from pathlib import Path
from config import AUDIO_DIR

class TTSEngine:
    def __init__(self):
        self.audio_dir = Path(AUDIO_DIR)
        self.audio_dir.mkdir(parents=True, exist_ok=True)

    def synthesize(self, text: str) -> str:
        """
        Synthesizes text to an audio file (.mp3 / .wav) and returns its relative filename.
        Uses gTTS or pyttsx3, and caches generated audio files.
        """
        clean_text = text.strip()
        if not clean_text:
            return ""

        text_hash = hashlib.md5(clean_text.encode('utf-8')).hexdigest()
        filename = f"tts_{text_hash}.mp3"
        filepath = self.audio_dir / filename

        if filepath.exists():
            return filename

        # Try gTTS first
        try:
            from gtts import gTTS
            tts = gTTS(text=clean_text, lang='en', slow=False)
            tts.save(str(filepath))
            return filename
        except Exception as e:
            # Fallback to pyttsx3
            try:
                import pyttsx3
                engine = pyttsx3.init()
                wav_file = self.audio_dir / f"tts_{text_hash}.wav"
                engine.save_to_file(clean_text, str(wav_file))
                engine.runAndWait()
                return f"tts_{text_hash}.wav"
            except Exception as e2:
                print(f"[TTSEngine] Synthesis fallback error: {e2}")
                return ""
