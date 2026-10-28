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
        "cloned_voice": "Clone សំឡេងផ្ទាល់ខ្លួន (Custom Voice Clone)",
        "en-US-AndrewMultilingualNeural": "English - Andrew (Multilingual)",
        "en-US-AvaMultilingualNeural": "English - Ava (Multilingual)",
        "zh-CN-YunxiNeural": "Chinese - Yunxi (Male)",
        "zh-CN-XiaoxiaoNeural": "Chinese - Xiaoxiao (Female)",
    }

    TONE_PRESETS = {
        "educational": {
            "name": "ទឹកដមបែបអប់រំ & ចិត្តវិទ្យា (Calm & Deep)",
            "rate": "-6%",
            "pitch": "-2Hz",
        },
        "story": {
            "name": "ទឹកដមបែបនិទានរឿង (Storytelling)",
            "rate": "-4%",
            "pitch": "+0Hz",
        },
        "standard": {
            "name": "ទឹកដមធម្មតា/រហ័ស (Standard)",
            "rate": "+0%",
            "pitch": "+0Hz",
        },
    }

    @classmethod
    async def _generate_audio_async(cls, text: str, output_path: str, voice: str, rate: str = "-6%", pitch: str = "-2Hz"):
        communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
        await communicate.save(output_path)

    @classmethod
    def clone_voice_sample(cls, sample_path: str, voice_name: str = "MyClonedVoice") -> Tuple[bool, str]:
        """
        Register a custom voice sample for cloning.
        If ElevenLabs API key is configured, uploads to ElevenLabs Voice Lab.
        Otherwise, registers as local custom reference voice.
        """
        if not sample_path or not os.path.exists(sample_path):
            return False, "File សំឡេងមិនមាន ឬរកមិនឃើញឡើយ។"

        settings.set("custom_voice_sample_path", sample_path)
        
        el_key = settings.get("elevenlabs_api_key", "").strip()
        if el_key:
            try:
                import requests
                url = "https://api.elevenlabs.io/v1/voices/add"
                headers = {"xi-api-key": el_key}
                with open(sample_path, "rb") as f:
                    files = {"files": (os.path.basename(sample_path), f, "audio/mpeg")}
                    data = {"name": voice_name, "description": "Custom voice clone from AI Animation Studio"}
                    resp = requests.post(url, headers=headers, files=files, data=data, timeout=35)
                    if resp.status_code == 200:
                        v_id = resp.json().get("voice_id")
                        settings.set("cloned_voice_id", v_id)
                        logger.info(f"ElevenLabs voice cloned successfully: {v_id}")
                        return True, f"Clone សំឡេងជោគជ័យតាម ElevenLabs! (Voice ID: {v_id[:8]}...)"
                    else:
                        err = resp.json().get("detail", {}).get("message", resp.text)
                        return False, f"ElevenLabs Error: {err}"
            except Exception as e:
                logger.warning(f"ElevenLabs upload failed: {e}")
                return False, f"Connection error: {e}"

        return True, "រក្សាទុក File សំឡេងគំរូរួចរាល់! (កំពុងប្រើប្រាស់ក្នុង Studio)"

    @classmethod
    def generate_elevenlabs_speech(cls, text: str, output_path: str, voice_id: Optional[str] = None) -> Tuple[bool, float]:
        """Generate speech using ElevenLabs Multilingual v2 with the cloned voice."""
        el_key = settings.get("elevenlabs_api_key", "").strip()
        v_id = voice_id or settings.get("cloned_voice_id", "").strip()
        if not el_key or not v_id:
            return False, 0.0

        try:
            import requests
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{v_id}"
            headers = {"xi-api-key": el_key, "Content-Type": "application/json"}
            payload = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.8}
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=45)
            if resp.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                dur = cls.get_audio_duration(output_path)
                logger.info(f"ElevenLabs speech generated ({dur:.2f}s) -> {output_path}")
                return True, dur
            else:
                logger.warning(f"ElevenLabs TTS failed ({resp.status_code}): {resp.text}")
        except Exception as e:
            logger.error(f"ElevenLabs speech generation error: {e}")
        return False, 0.0

    @classmethod
    def generate_speech(cls, 
                        text: str, 
                        output_path: str, 
                        voice: Optional[str] = None, 
                        rate: Optional[str] = None, 
                        pitch: Optional[str] = None) -> Tuple[bool, float]:
        """
        Generate audio from text with natural cadence, pause injection, and return (success, duration_seconds).
        Supports Cloned Voice (ElevenLabs) with automatic fallback to Edge-TTS.
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

        # 1. Try Cloned Voice via ElevenLabs if requested
        if voice == "cloned_voice" or voice.startswith("elevenlabs:"):
            el_voice_id = voice.replace("elevenlabs:", "") if voice.startswith("elevenlabs:") else None
            ok, dur = cls.generate_elevenlabs_speech(enhanced_text, output_path, voice_id=el_voice_id)
            if ok:
                return True, dur
            logger.info("Cloned voice generation fallback to Edge-TTS Piseth...")
            voice = "km-KH-PisethNeural"

        # 2. Standard Free Edge-TTS Voice Generation
        try:
            # Run edge-tts communicate
            asyncio.run(cls._generate_audio_async(enhanced_text, output_path, voice, rate, pitch))
            
            # Determine audio duration
            duration = cls.get_audio_duration(output_path)
            logger.info(f"Generated speech ({duration:.2f}s, voice={voice}, rate={rate}, pitch={pitch}) -> {output_path}")
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
