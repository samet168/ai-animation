import os
import logging
from typing import List, Dict, Any
from PySide6.QtCore import QThread, Signal
from app.services.tts_service import TTSService
from app.services.khmer_service import KhmerService
from app.core.database import db
from app.core.settings import settings

logger = logging.getLogger("AIAnimationStudio.TTSWorker")

class TTSWorker(QThread):
    progress = Signal(int, str)
    scene_audio_ready = Signal(int, str, float)  # (scene_id, audio_path, duration)
    finished = Signal()
    error = Signal(str)

    def __init__(self, scenes: List[Dict[str, Any]], voice: str = "km-KH-PisethNeural"):
        super().__init__()
        self.scenes = scenes
        self.voice = voice
        self.is_cancelled = False

    def cancel(self):
        self.is_cancelled = True

    def run(self):
        try:
            total = len(self.scenes)
            app_dir = settings.app_dir
            audio_dir = os.path.join(app_dir, "data", "audio")
            os.makedirs(audio_dir, exist_ok=True)

            rate = settings.get("voice_rate", "-6%")
            pitch = settings.get("voice_pitch", "-2Hz")

            for i, scene in enumerate(self.scenes):
                if self.is_cancelled:
                    break

                scene_id = scene["id"]
                scene_num = scene.get("scene_number", i + 1)
                narration = KhmerService.clean_text(scene.get("narration_km", ""))

                pct = int((i / total) * 100)
                self.progress.emit(pct, f"កំពុងបញ្ចេញសំឡេង Scene {scene_num}/{total}...")

                out_path = os.path.join(audio_dir, f"scene_{scene_id}_{scene_num}.mp3")
                success, duration = TTSService.generate_speech(
                    text=narration,
                    output_path=out_path,
                    voice=self.voice,
                    rate=rate,
                    pitch=pitch
                )

                if success:
                    db.update_scene(scene_id, audio_path=out_path, audio_duration=duration)
                    self.scene_audio_ready.emit(scene_id, out_path, duration)
                else:
                    logger.warning(f"Failed to generate TTS for scene {scene_num}")

            self.progress.emit(100, "បញ្ចេញសំឡេងរួចរាល់!")
            self.finished.emit()
        except Exception as e:
            logger.error(f"TTS generation error: {e}")
            self.error.emit(str(e))
