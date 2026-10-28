import os
import logging
from typing import List, Dict, Any
from PySide6.QtCore import QThread, Signal
from app.services.image_service import ImageService
from app.core.database import db
from app.core.settings import settings

logger = logging.getLogger("AIAnimationStudio.ImageWorker")

class ImageWorker(QThread):
    progress = Signal(int, str)
    scene_image_ready = Signal(int, str)  # (scene_id, image_path)
    finished = Signal()
    error = Signal(str)

    def __init__(self, scenes: List[Dict[str, Any]], style: str = "aitest_style", aspect_ratio: str = "16:9"):
        super().__init__()
        self.scenes = scenes
        self.style = style
        self.aspect_ratio = aspect_ratio
        self.is_cancelled = False

    def cancel(self):
        self.is_cancelled = True

    def run(self):
        try:
            total = len(self.scenes)
            app_dir = settings.app_dir
            images_dir = os.path.join(app_dir, "data", "images")
            os.makedirs(images_dir, exist_ok=True)

            model = settings.get("image_model", "flux")

            for i, scene in enumerate(self.scenes):
                if self.is_cancelled:
                    break

                scene_id = scene["id"]
                scene_num = scene.get("scene_number", i + 1)
                prompt = scene.get("image_prompt", "")
                existing_path = scene.get("image_path", "")

                pct = int((i / total) * 100)
                out_path = os.path.join(images_dir, f"scene_{scene_id}_{scene_num}.png")

                # If current image is already a real valid image (>15KB), reuse it
                if existing_path and ImageService.is_valid_image(existing_path):
                    self.progress.emit(pct, f"Scene {scene_num}/{total} មានរូបភាពរួចរាល់ហើយ")
                    self.scene_image_ready.emit(scene_id, existing_path)
                    continue

                def on_status(msg: str):
                    self.progress.emit(pct, f"Scene {scene_num}/{total}: {msg}")

                on_status("កំពុងរៀបចំ...")

                success = ImageService.generate_image(
                    prompt=prompt,
                    output_path=out_path,
                    style=self.style,
                    aspect_ratio=self.aspect_ratio,
                    model=model,
                    progress_callback=on_status
                )

                if success and ImageService.is_valid_image(out_path):
                    db.update_scene(scene_id, image_path=out_path)
                    self.scene_image_ready.emit(scene_id, out_path)
                else:
                    logger.warning(f"Failed to generate real image for scene {scene_num}")

            self.progress.emit(100, "បង្កើតរូបភាពរួចរាល់!")
            self.finished.emit()
        except Exception as e:
            logger.error(f"Image generation error: {e}")
            self.error.emit(str(e))
