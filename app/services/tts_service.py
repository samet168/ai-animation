import os
import asyncio
import logging
import edge_tts
from typing import Optional, Tuple, Dict
from app.core.settings import settings
from app.services.khmer_service import KhmerService

logger = logging.getLogger("AIAnimationStudio.TTSService")

class TTSService:
    """Voice generation service using Microsoft Edge-TTS (100% Free, No Key needed)."""

    VOICES = {
        "km-KH-PisethNeural": "សំឡេងប្រុស (Piseth - ខ្មែរ)",
        "km-KH-SreymomNeural": "សំឡេងស្រី (Sreymom - ខ្មែរ)",
        "en-US-AndrewMultilingualNeural": "English - Andrew (Multilingual)",
        "en-US-AvaMultilingualNeural": "English - Ava (Multilingual)",
        "zh-CN-YunxiNeural": "Chinese - Yunxi (Male)",
        "zh-CN-XiaoxiaoNeural": "Chinese - Xiaoxiao (Female)",
    }

    TONE_PRESETS = {
        "educational": {
            "name": "🧘 ទឹកដមបែបអប់រំ & ចិត្តវិទ្យា (Calm & Deep)",
            "rate": "-6%",
            "pitch": "-2Hz",
        },
        "story": {
            "name": "📖 ទឹកដមបែបនិទានរឿង (Storytelling)",
            "rate": "-4%",
            "pitch": "+0Hz",
        },
        "standard": {
            "name": "⚡ ទឹកដមធម្មតា/រហ័ស (Standard)",
            "rate": "+0%",
            "pitch": "+0Hz",
        },
    }

    @classmethod
    async def _generate_audio_async(cls, text: str, output_path: str, voice: str, rate: str = "-6%", pitch: str = "-2Hz"):
        communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
        await communicate.save(output_path)

    @classmethod
    def generate_speech(cls, 
                        text: str, 
                        output_path: str, 
                        voice: Optional[str] = None, 
                        rate: Optional[str] = None, 
                        pitch: Optional[str] = None) -> Tuple[bool, float]:
        """
        Generate audio from text with natural cadence, pause injection, and return (success, duration_seconds).
        """
        if not text or not text.strip():
            logger.warning("Empty text passed to TTS service.")
            return False, 0.0

        if not voice:
            voice = settings.get("default_voice", "km-KH-PisethNeural")
        if rate is None:
            rate = settings.get("voice_rate", "-6%")
        if pitch is None:
            pitch = settings.get("voice_pitch", "-2Hz")

        # Sanitize and inject natural breathing pauses
        enhanced_text = KhmerService.enhance_for_tts(text)

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        try:
            # Run edge-tts communicate
            asyncio.run(cls._generate_audio_async(enhanced_text, output_path, voice, rate, pitch))
            
            # Determine audio duration
            duration = cls.get_audio_duration(output_path)
            logger.info(f"Generated speech ({duration:.2f}s, rate={rate}, pitch={pitch}) -> {output_path}")
            return True, duration
        except Exception as e:
            logger.error(f"TTS generation error: {e}")
            return False, 0.0

    @classmethod
    def get_audio_duration(cls, audio_path: str) -> float:
        """Measure audio duration in seconds with fallbacks."""
        if not os.path.exists(audio_path) or os.path.getsize(audio_path) < 100:
            return 0.0

        # Try pydub
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(audio_path)
            return len(audio) / 1000.0
        except Exception:
            pass

        # Try soundfile
        try:
            import soundfile as sf # type: ignore
            f = sf.SoundFile(audio_path)
            return len(f) / float(f.samplerate)
        except Exception:
            pass

        # Default fallback
        return 3.0
