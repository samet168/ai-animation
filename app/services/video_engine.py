import os
import re
import subprocess
import logging
from typing import List, Optional
from app.core.settings import settings
from app.services.khmer_service import KhmerService

logger = logging.getLogger("AIAnimationStudio.VideoEngine")

class VideoEngine:
    """
    FFmpeg-powered 2.5D animation and video assembly engine.
    Applies dynamic cinematic camera motions (Zoom In, Zoom Out, Pan Left, Pan Right),
    burned Khmer subtitles, and audio synchronization.
    """

    DIMENSIONS = {
        "9:16": (720, 1280),
        "16:9": (1280, 720),
    }

    @classmethod
    def get_ffmpeg_cmd(cls) -> str:
        return settings.get_ffmpeg_path()

    @classmethod
    def _create_ass_file(cls, text: str, duration: float, ass_path: str, aspect_ratio: str = "9:16"):
        """Create ASS subtitle file with sentence-by-sentence timed dialogue chunks."""
        width, height = cls.DIMENSIONS.get(aspect_ratio, (720, 1280))
        font_size = 24 if aspect_ratio == "9:16" else 22
        margin_v = 85 if aspect_ratio == "9:16" else 45

        chunks = KhmerService.split_subtitles(text, max_chars=55)
        total_len = sum(len(c) for c in chunks) or 1

        def format_time(sec: float) -> str:
            m, s = divmod(sec, 60)
            h, m = divmod(m, 60)
            return f"{int(h):01d}:{int(m):02d}:{s:05.2f}"

        dialogues = []
        elapsed = 0.0
        for i, c in enumerate(chunks):
            c_dur = (len(c) / total_len) * duration
            start_t = elapsed
            end_t = min(elapsed + c_dur, duration) if i < len(chunks) - 1 else duration
            elapsed = end_t
            s_str = format_time(start_t)
            e_str = format_time(end_t)
            clean_c = c.replace("\n", " ").strip()
            dialogues.append(f"Dialogue: 0,{s_str},{e_str},Default,,0,0,0,,{clean_c}")

        events_str = "\n".join(dialogues)

        ass_content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Leelawadee UI,{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0.5,0,1,2,1,2,40,40,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
{events_str}
"""
        with open(ass_path, "w", encoding="utf-8") as f:
            f.write(ass_content)

    @classmethod
    def create_scene_clip(cls,
                          image_path: str,
                          audio_path: str,
                          duration: float,
                          motion: str,
                          output_clip_path: str,
                          aspect_ratio: str = "9:16",
                          subtitle_text: Optional[str] = None) -> bool:
        """
        Render a single animated scene video clip with real, visible camera motion or whiteboard hand-drawing.
        """
        if motion == "whiteboard":
            from app.services.whiteboard_engine import WhiteboardEngine
            return WhiteboardEngine.render_scene_clip(
                image_path=image_path,
                audio_path=audio_path,
                duration=duration,
                output_clip_path=output_clip_path,
                aspect_ratio=aspect_ratio,
                subtitle_text=subtitle_text
            )
        elif motion in ("talking", "character_motion", "lip_sync"):
            from app.services.talking_engine import TalkingCharacterEngine
            return TalkingCharacterEngine.render_scene_clip(
                image_path=image_path,
                audio_path=audio_path,
                duration=duration,
                output_clip_path=output_clip_path,
                aspect_ratio=aspect_ratio,
                subtitle_text=subtitle_text
            )

        ffmpeg = cls.get_ffmpeg_cmd()
        os.makedirs(os.path.dirname(os.path.abspath(output_clip_path)), exist_ok=True)
        
        # Ensure watermark is erased from image before rendering
        try:
            from app.services.image_service import ImageService
            ImageService.remove_watermark(image_path)
        except Exception:
            pass

        width, height = cls.DIMENSIONS.get(aspect_ratio, (720, 1280))
        fps = 25
        duration = max(duration, 2.0)
        total_frames = int(duration * fps)

        # Dynamic zoom speed calculation based on exact duration
        zoom_speed = 0.35 / float(total_frames)

        # Build dynamic zoompan filter based on motion type
        if motion == "zoom_out":
            zoom_filter = f"zoompan=z='if(lte(on,1),1.35,max(1.001,zoom-{zoom_speed:.5f}))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s={width}x{height}:fps={fps}"
        elif motion == "pan_left":
            zoom_filter = f"zoompan=z='1.25':x='(iw-iw/zoom)*(1-on/{total_frames})':y='ih/2-(ih/zoom/2)':d={total_frames}:s={width}x{height}:fps={fps}"
        elif motion == "pan_right":
            zoom_filter = f"zoompan=z='1.25':x='(iw-iw/zoom)*(on/{total_frames})':y='ih/2-(ih/zoom/2)':d={total_frames}:s={width}x{height}:fps={fps}"
        else: # Default zoom_in
            zoom_filter = f"zoompan=z='min(zoom+{zoom_speed:.5f},1.35)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s={width}x{height}:fps={fps}"

        video_filter_chain = zoom_filter

        # Subtitle burning
        ass_path = None
        if subtitle_text and settings.get("subtitle_enabled", True):
            ass_path = output_clip_path + ".ass"
            cls._create_ass_file(subtitle_text, duration, ass_path, aspect_ratio)
            escaped_ass = ass_path.replace("\\", "/").replace(":", "\\:")
            video_filter_chain += f",subtitles='{escaped_ass}'"

        # Note: We do NOT use "-loop 1" because loop 1 resets zoompan on every frame.
        # Passing single image to zoompan with d={total_frames} generates smooth continuous motion!
        cmd = [
            ffmpeg, "-y",
            "-i", image_path,
            "-i", audio_path,
            "-vf", video_filter_chain,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-t", str(duration),
            "-shortest",
            output_clip_path
        ]

        logger.info(f"Rendering scene clip: motion={motion}, dur={duration:.2f}s -> {output_clip_path}")
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if res.returncode == 0 and os.path.exists(output_clip_path):
                if ass_path and os.path.exists(ass_path):
                    try: os.remove(ass_path)
                    except: pass
                return True
            else:
                logger.error(f"FFmpeg error: {res.stderr}")
                return False
        except Exception as e:
            logger.error(f"Failed to render scene clip: {e}")
            return False

    @classmethod
    def concatenate_scene_clips(cls,
                                clip_paths: List[str],
                                output_path: str,
                                bgm_path: Optional[str] = None,
                                bgm_volume: float = 0.15) -> bool:
        """
        Concatenate multiple scene clips into the final video file.
        """
        if not clip_paths:
            return False

        ffmpeg = cls.get_ffmpeg_cmd()
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        
        concat_txt = output_path + ".concat.txt"
        with open(concat_txt, "w", encoding="utf-8") as f:
            for p in clip_paths:
                clean_p = p.replace("\\", "/")
                f.write(f"file '{clean_p}'\n")

        try:
            if bgm_path and os.path.exists(bgm_path):
                cmd = [
                    ffmpeg, "-y",
                    "-f", "concat", "-safe", "0", "-i", concat_txt,
                    "-stream_loop", "-1", "-i", bgm_path,
                    "-filter_complex", f"[1:a]volume={bgm_volume}[bgm];[0:a][bgm]amix=inputs=2:duration=first[aout]",
                    "-map", "0:v", "-map", "[aout]",
                    "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k",
                    output_path
                ]
            else:
                cmd = [
                    ffmpeg, "-y",
                    "-f", "concat", "-safe", "0", "-i", concat_txt,
                    "-c", "copy",
                    output_path
                ]

            res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if res.returncode == 0 and os.path.exists(output_path):
                logger.info(f"Final video rendered successfully: {output_path}")
                return True
            else:
                logger.error(f"Concat failed: {res.stderr}")
                return False
        finally:
            if os.path.exists(concat_txt):
                try: os.remove(concat_txt)
                except: pass
