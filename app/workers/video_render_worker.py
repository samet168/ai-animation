import os
import logging
from typing import List, Dict, Any, Optional
from PySide6.QtCore import QThread, Signal
from app.services.video_engine import VideoEngine
from app.services.image_service import ImageService
from app.services.tts_service import TTSService
from app.services.khmer_service import KhmerService
from app.core.database import db
from app.core.settings import settings

logger = logging.getLogger("AIAnimationStudio.VideoRenderWorker")

class VideoRenderWorker(QThread):
    progress = Signal(int, str)
    scene_updated = Signal(int, str, str, float)  # (scene_id, image_path, audio_path, duration)
    finished = Signal(str)  # final_video_path
    error = Signal(str)

    def __init__(self, project_id: int, scenes: List[Dict[str, Any]], aspect_ratio: str = "9:16", 
                 art_style: str = "3d_pixar", voice: str = "km-KH-PisethNeural", bgm_path: Optional[str] = None):
        super().__init__()
        self.project_id = project_id
        self.scenes = scenes
        self.aspect_ratio = aspect_ratio
        self.art_style = art_style
        self.voice = voice
        self.bgm_path = bgm_path
        self.is_cancelled = False

    def cancel(self):
        self.is_cancelled = True

    def run(self):
        try:
            total = len(self.scenes)
            app_dir = settings.app_dir
            audio_dir = os.path.join(app_dir, "data", "audio")
            images_dir = os.path.join(app_dir, "data", "images")
            clips_dir = os.path.join(app_dir, "data", "clips")
            os.makedirs(audio_dir, exist_ok=True)
            os.makedirs(images_dir, exist_ok=True)
            os.makedirs(clips_dir, exist_ok=True)

            rate = settings.get("voice_rate", "-6%")
            pitch = settings.get("voice_pitch", "-2Hz")
            img_model = settings.get("image_model", "flux")

            # Phase 1: Auto-generate missing Audio for any scene
            for i, scene in enumerate(self.scenes):
                if self.is_cancelled: return

                scene_id = scene["id"]
                scene_num = scene.get("scene_number", i + 1)
                aud = scene.get("audio_path")

                if not aud or not os.path.exists(aud) or os.path.getsize(aud) < 100:
                    self.progress.emit(
                        int((i / total) * 20),
                        f"កំពុងបញ្ចេញសំឡេង Scene #{scene_num}/{total}..."
                    )
                    out_aud = os.path.join(audio_dir, f"scene_{scene_id}_{scene_num}.mp3")
                    narration = KhmerService.clean_text(scene.get("narration_km", ""))
                    scene["narration_km"] = narration
                    db.update_scene(scene_id, narration_km=narration)
                    ok, dur = TTSService.generate_speech(narration, out_aud, self.voice, rate, pitch)
                    if ok:
                        scene["audio_path"] = out_aud
                        scene["audio_duration"] = dur
                        db.update_scene(scene_id, audio_path=out_aud, audio_duration=dur)
                        self.scene_updated.emit(scene_id, scene.get("image_path", ""), out_aud, dur)
                    else:
                        self.error.emit(f"មិនអាចបង្កើតសំឡេងសម្រាប់ Scene #{scene_num} បានទេ។")
                        return

            # Phase 2: Auto-generate missing or invalid images (including placeholder cards)
            for i, scene in enumerate(self.scenes):
                if self.is_cancelled: return

                scene_id = scene["id"]
                scene_num = scene.get("scene_number", i + 1)
                img = scene.get("image_path")

                # If image is missing or is an emergency placeholder card (<15KB)
                if not ImageService.is_valid_image(img):
                    cur_pct = 20 + int((i / total) * 30)
                    out_img = os.path.join(images_dir, f"scene_{scene_id}_{scene_num}.png")
                    prompt = scene.get("image_prompt", "")

                    def on_status(msg: str):
                        self.progress.emit(cur_pct, f"Scene #{scene_num}/{total}: {msg}")

                    on_status("កំពុងរៀបចំទាញយករូបភាព...")
                    ok = ImageService.generate_image(
                        prompt=prompt,
                        output_path=out_img,
                        style=self.art_style,
                        aspect_ratio=self.aspect_ratio,
                        model=img_model,
                        progress_callback=on_status
                    )
                    if ok and ImageService.is_valid_image(out_img):
                        scene["image_path"] = out_img
                        db.update_scene(scene_id, image_path=out_img)
                        self.scene_updated.emit(scene_id, out_img, scene.get("audio_path", ""), scene.get("audio_duration", 0.0))
                    else:
                        logger.warning(f"Could not generate real image for Scene #{scene_num}. Generating stylized fallback.")
                        ImageService.create_placeholder_image(out_img, prompt, self.aspect_ratio, self.art_style)
                        scene["image_path"] = out_img
                        db.update_scene(scene_id, image_path=out_img)
                        self.scene_updated.emit(scene_id, out_img, scene.get("audio_path", ""), scene.get("audio_duration", 0.0))

            # Phase 3: Render individual animated clips
            clip_paths = []
            for i, scene in enumerate(self.scenes):
                if self.is_cancelled: return

                scene_id = scene["id"]
                scene_num = scene.get("scene_number", i + 1)
                img = scene.get("image_path")
                aud = scene.get("audio_path")
                dur = scene.get("audio_duration", 3.0)
                motion = scene.get("camera_motion", "zoom_in")
                subtitle = scene.get("narration_km", "")

                pct = 50 + int((i / total) * 40)
                self.progress.emit(pct, f"កំពុង Render វីដេអូចលនា Scene #{scene_num}/{total}...")

                if (self.art_style and self.art_style.startswith("whiteboard")) or motion == "whiteboard":
                    chosen_motion = "whiteboard"
                elif motion in ("talking", "character_motion", "lip_sync"):
                    chosen_motion = "talking"
                elif motion in ("zoom_in", "zoom_out", "pan_left", "pan_right"):
                    chosen_motion = motion
                else:
                    chosen_motion = "talking"

                out_clip = os.path.join(clips_dir, f"clip_{scene_id}_{scene_num}.mp4")
                ok = VideoEngine.create_scene_clip(
                    image_path=img,
                    audio_path=aud,
                    duration=dur,
                    motion=chosen_motion,
                    output_clip_path=out_clip,
                    aspect_ratio=self.aspect_ratio,
                    subtitle_text=subtitle
                )

                if ok:
                    clip_paths.append(out_clip)
                    db.update_scene(scene_id, video_clip_path=out_clip)
                else:
                    self.error.emit(f"បរាជ័យក្នុងការ Render clip សម្រាប់ Scene #{scene_num}។")
                    return

            if self.is_cancelled: return

            # Phase 4: Concatenate all clips into final video
            self.progress.emit(92, "កំពុងផ្គុំវីដេអូពេញលេញ (Concatenating)...")
            output_dir = settings.get_output_dir()
            os.makedirs(output_dir, exist_ok=True)
            final_video_name = f"Animation_{self.project_id}_{self.aspect_ratio.replace(':', '_')}.mp4"
            final_video_path = os.path.join(output_dir, final_video_name)

            bgm_vol = settings.get("bgm_volume", 0.15) if settings.get("bgm_enabled", False) else 0.0
            bgm = self.bgm_path if settings.get("bgm_enabled", False) else None

            ok = VideoEngine.concatenate_scene_clips(
                clip_paths=clip_paths,
                output_path=final_video_path,
                bgm_path=bgm,
                bgm_volume=bgm_vol
            )

            if ok:
                db.update_project(self.project_id, final_video_path=final_video_path)
                self.progress.emit(100, "Render វីដេអូរួចរាល់!")
                self.finished.emit(final_video_path)
            else:
                self.error.emit("បរាជ័យក្នុងការផ្គុំវីដេអូចុងក្រោយ។")

        except Exception as e:
            logger.error(f"Render worker error: {e}")
            self.error.emit(str(e))
