import os
import logging
from PySide6.QtCore import QThread, Signal
from app.services.gemini_service import GeminiService
from app.services.image_service import ImageService
from app.services.tts_service import TTSService
from app.services.video_engine import VideoEngine
from app.services.khmer_service import KhmerService
from app.core.database import db
from app.core.settings import settings

logger = logging.getLogger("AIAnimationStudio.FullAutoWorker")

class FullAutoWorker(QThread):
    """
    1-Click Automated AI Video Generator Pipeline.
    Story -> TTS Voice -> Images -> Animated Clips -> Final MP4 Video.
    """
    progress = Signal(int, str)
    story_generated = Signal(int, list)  # (project_id, scenes)
    finished = Signal(int, str)           # (project_id, final_video_path)
    error = Signal(str)

    def __init__(self, topic: str, num_scenes: int = 5, style: str = "3d_pixar", 
                 aspect_ratio: str = "9:16", voice: str = "km-KH-PisethNeural",
                 motion_mode: str = "talking", genre: str = "general"):
        super().__init__()
        self.topic = topic
        self.num_scenes = num_scenes
        self.style = style
        self.aspect_ratio = aspect_ratio
        self.voice = voice
        self.motion_mode = motion_mode
        self.genre = genre
        self.is_cancelled = False

    def cancel(self):
        self.is_cancelled = True

    def run(self):
        try:
            # Step 1: AI Story Generation
            self.progress.emit(5, "AI កំពុងតែងសាច់រឿង និងរៀបចំប្លង់ Scene...")
            story_data = GeminiService.generate_storyboard(self.topic, self.num_scenes, self.style, self.genre)
            
            if self.is_cancelled: return

            title = story_data.get("title", self.topic)
            raw_scenes = story_data.get("scenes", [])
            if not raw_scenes:
                self.error.emit("AI មិនបានបញ្ជូន Scene ណាមួយមកទេ។")
                return

            # Save project to DB
            project_id = db.create_project(
                title=title,
                topic=self.topic,
                art_style=self.style,
                aspect_ratio=self.aspect_ratio,
                voice=self.voice
            )

            # Insert scenes into DB
            db_scenes = []
            for s in raw_scenes:
                scene_num = s.get("scene_number", 1)
                narration = s.get("narration_km", "")
                prompt = s.get("image_prompt_en", "")
                motion = s.get("camera_motion", "zoom_in")
                scene_id = db.add_scene(project_id, scene_num, narration, prompt, motion)
                db_scenes.append({
                    "id": scene_id,
                    "scene_number": scene_num,
                    "narration_km": narration,
                    "image_prompt": prompt,
                    "camera_motion": motion,
                    "audio_path": "",
                    "audio_duration": 0.0,
                    "image_path": ""
                })

            self.story_generated.emit(project_id, db_scenes)
            self.progress.emit(20, "សាច់រឿងត្រូវបានរៀបចំរួចរាល់!")

            # Step 2: Audio TTS Generation
            app_dir = settings.app_dir
            audio_dir = os.path.join(app_dir, "data", "audio")
            os.makedirs(audio_dir, exist_ok=True)
            rate = settings.get("voice_rate", "-6%")
            pitch = settings.get("voice_pitch", "-2Hz")

            for i, sc in enumerate(db_scenes):
                if self.is_cancelled: return
                cur_pct = 20 + int((i / len(db_scenes)) * 25)
                self.progress.emit(cur_pct, f"កំពុងបញ្ចេញសំឡេងខ្មែរ Scene {sc['scene_number']}/{len(db_scenes)}...")

                clean_narr = KhmerService.clean_text(sc["narration_km"])
                sc["narration_km"] = clean_narr
                db.update_scene(sc["id"], narration_km=clean_narr)

                audio_file = os.path.join(audio_dir, f"p{project_id}_s{sc['id']}.mp3")
                ok, dur = TTSService.generate_speech(clean_narr, audio_file, self.voice, rate, pitch)
                if ok:
                    sc["audio_path"] = audio_file
                    sc["audio_duration"] = dur
                    db.update_scene(sc["id"], audio_path=audio_file, audio_duration=dur)
                else:
                    sc["audio_path"] = audio_file
                    sc["audio_duration"] = 3.0

            # Step 3: AI Image Generation
            images_dir = os.path.join(app_dir, "data", "images")
            os.makedirs(images_dir, exist_ok=True)
            img_model = settings.get("image_model", "flux")

            for i, sc in enumerate(db_scenes):
                if self.is_cancelled: return
                cur_pct = 45 + int((i / len(db_scenes)) * 30)
                
                img_file = os.path.join(images_dir, f"p{project_id}_s{sc['id']}.png")

                # If already exists and is a valid real image (>15KB), skip regenerating
                if ImageService.is_valid_image(img_file):
                    sc["image_path"] = img_file
                    db.update_scene(sc["id"], image_path=img_file)
                    continue

                def on_status(msg: str):
                    self.progress.emit(cur_pct, f"Scene {sc['scene_number']}/{len(db_scenes)}: {msg}")

                on_status("កំពុងរៀបចំ...")
                ok = ImageService.generate_image(
                    prompt=sc["image_prompt"],
                    output_path=img_file,
                    style=self.style,
                    aspect_ratio=self.aspect_ratio,
                    model=img_model,
                    progress_callback=on_status
                )
                if ok and ImageService.is_valid_image(img_file):
                    sc["image_path"] = img_file
                    db.update_scene(sc["id"], image_path=img_file)
                else:
                    logger.warning(f"Scene {sc['scene_number']} real image generation unsuccessful.")
                    # Only fallback to styled backdrop if completely unavailable
                    ImageService.create_placeholder_image(img_file, sc.get("narration_km", ""), self.aspect_ratio, self.style)
                    sc["image_path"] = img_file
                    db.update_scene(sc["id"], image_path=img_file)

            # Step 4: Video Clips Animation & Subtitles
            clips_dir = os.path.join(app_dir, "data", "clips")
            os.makedirs(clips_dir, exist_ok=True)
            clip_paths = []

            for i, sc in enumerate(db_scenes):
                if self.is_cancelled: return
                cur_pct = 75 + int((i / len(db_scenes)) * 18)
                self.progress.emit(cur_pct, f"កំពុង Render ចលនា & អក្សររត់ Scene {sc['scene_number']}/{len(db_scenes)}...")

                # Resolve animation motion type
                if self.style.startswith("whiteboard") or self.motion_mode == "whiteboard" or sc.get("camera_motion") == "whiteboard":
                    chosen_motion = "whiteboard"
                elif self.motion_mode in ("talking", "character_motion", "lip_sync") or sc.get("camera_motion") == "talking":
                    chosen_motion = "talking"
                elif self.motion_mode == "cinematic":
                    chosen_motion = sc.get("camera_motion", "zoom_in")
                else:
                    # Default: talking character animation for characters, whiteboard for doodle styles
                    chosen_motion = "talking"

                clip_file = os.path.join(clips_dir, f"p{project_id}_s{sc['id']}.mp4")
                ok = VideoEngine.create_scene_clip(
                    image_path=sc["image_path"],
                    audio_path=sc.get("audio_path", ""),
                    duration=sc.get("audio_duration", 3.0),
                    motion=chosen_motion,
                    output_clip_path=clip_file,
                    aspect_ratio=self.aspect_ratio,
                    subtitle_text=sc["narration_km"]
                )
                if ok:
                    clip_paths.append(clip_file)
                    db.update_scene(sc["id"], video_clip_path=clip_file)

            if self.is_cancelled: return

            # Step 5: Final Concatenation
            self.progress.emit(94, "កំពុងផ្គុំវីដេអូចុងក្រោយ (Final Assembly)...")
            output_dir = settings.get_output_dir()
            os.makedirs(output_dir, exist_ok=True)
            final_mp4 = os.path.join(output_dir, f"Animation_{project_id}_{self.aspect_ratio.replace(':', '_')}.mp4")

            ok = VideoEngine.concatenate_scene_clips(clip_paths, final_mp4)
            if ok:
                db.update_project(project_id, final_video_path=final_mp4)
                self.progress.emit(100, "វីដេអូ Animation ត្រូវបានបង្កើតរួចរាល់ ១០០%!")
                self.finished.emit(project_id, final_mp4)
            else:
                self.error.emit("បរាជ័យក្នុងការផ្គុំវីដេអូចុងក្រោយ។")

        except Exception as e:
            logger.error(f"Full auto error: {e}")
            self.error.emit(str(e))
