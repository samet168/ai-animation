import os
import re
import math
import subprocess
import logging
from typing import Optional, List
import numpy as np
from PIL import Image
from app.core.settings import settings
from app.services.khmer_service import KhmerService

logger = logging.getLogger("AIAnimationStudio.WhiteboardEngine")

class WhiteboardEngine:
    """
    Whiteboard Animation Engine (តុក្កតាគូសដៃ).
    Renders realistic hand-drawn whiteboard animations:
    - Photorealistic animated hand holding a marker sketching the scene in real time.
    - Synchronized marker scratching sound effects + Khmer speech narration.
    - Burned Khmer Unicode subtitles.
    - 100% Free Forever, executed entirely on local PC via Python + FFmpeg.
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
        """Create ASS subtitle file with clean Khmer Unicode styling and sentence-by-sentence timing."""
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
    def render_scene_clip(cls,
                          image_path: str,
                          audio_path: str,
                          duration: float,
                          output_clip_path: str,
                          aspect_ratio: str = "9:16",
                          subtitle_text: Optional[str] = None) -> bool:
        """
        Render a whiteboard scene clip with hand drawing the image, marker audio, and subtitles.
        """
        ffmpeg = cls.get_ffmpeg_cmd()
        os.makedirs(os.path.dirname(os.path.abspath(output_clip_path)), exist_ok=True)

        width, height = cls.DIMENSIONS.get(aspect_ratio, (720, 1280))
        fps = 25
        duration = max(duration, 2.0)
        total_frames = int(duration * fps)

        # 1. Load image and resize to target dimension
        try:
            raw_img = Image.open(image_path).convert("RGB")
            # If aspect ratio does not match, fit and center on white canvas
            img_resized = raw_img.resize((width, height), Image.Resampling.LANCZOS)
            img_arr = np.array(img_resized, dtype=np.float32)
        except Exception as e:
            logger.error(f"Failed to load image {image_path}: {e}")
            return False

        # 2. Load hand graphic
        app_dir = settings.app_dir
        hand_path = os.path.join(app_dir, "assets", "draw_hand.png")
        if not os.path.exists(hand_path):
            hand_path = os.path.join(app_dir, "assets", "hand_drawing.png")

        try:
            hand_orig = Image.open(hand_path).convert("RGBA")
            # Hand scale: 78% of width for 9:16, 52% of width for 16:9
            scale_ratio = 0.78 if aspect_ratio == "9:16" else 0.52
            hand_w = int(width * scale_ratio)
            scale = hand_w / float(hand_orig.width)
            hand_h = int(hand_orig.height * scale)
            hand = hand_orig.resize((hand_w, hand_h), Image.Resampling.LANCZOS)
            # Calibrated marker nib tip coordinates
            tip_x = int(125 * scale) if "draw_hand" in hand_path else int(18 * scale)
            tip_y = int(70 * scale) if "draw_hand" in hand_path else int(18 * scale)
        except Exception as e:
            logger.error(f"Failed to load hand asset: {e}")
            return False

        # 3. Canvas and progressive reveal coordinates
        white_canvas = np.ones((height, width, 3), dtype=np.float32) * 255.0
        yy, xx = np.mgrid[0:height, 0:width]
        grid_progress = (0.22 * (xx / width) + 0.78 * (yy / height)).astype(np.float32)

        # Draw duration: up to 70% of scene duration, max 3.2s
        draw_dur = min(duration * 0.70, 3.2)
        draw_frames = int(draw_dur * fps)
        exit_frames = int(0.5 * fps)

        # 4. Marker SFX asset
        scribble_path = os.path.join(app_dir, "assets", "marker_scribble.wav")
        has_sfx = os.path.exists(scribble_path)

        # 5. Build Subtitle ASS
        ass_path = None
        has_sub = subtitle_text and settings.get("subtitle_enabled", True)
        if has_sub:
            ass_path = output_clip_path + ".ass"
            cls._create_ass_file(subtitle_text, duration, ass_path, aspect_ratio)

        # 6. Construct FFmpeg command
        cmd = [
            ffmpeg, "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{width}x{height}",
            "-pix_fmt", "rgb24",
            "-r", str(fps),
            "-i", "-",
            "-i", audio_path
        ]

        if has_sfx:
            cmd.extend(["-i", scribble_path])

        # Filters
        filter_parts = []
        # Video filter: subtitles if enabled
        if has_sub and ass_path:
            escaped_ass = ass_path.replace("\\", "/").replace(":", "\\:")
            filter_parts.append(f"[0:v]subtitles='{escaped_ass}'[vout]")
            v_map = "[vout]"
        else:
            v_map = "0:v"

        # Audio filter: mix speech with marker drawing SFX
        if has_sfx:
            fade_start = max(0.1, draw_dur - 0.35)
            sfx_filter = (
                f"[2:a]aloop=loop=-1:size=441000,atrim=0:{draw_dur:.2f},"
                f"afade=t=out:st={fade_start:.2f}:d=0.35,volume=0.20[sfx];"
                f"[1:a][sfx]amix=inputs=2:duration=first[aout]"
            )
            filter_parts.append(sfx_filter)
            a_map = "[aout]"
        else:
            a_map = "1:a"

        if filter_parts:
            cmd.extend(["-filter_complex", ";".join(filter_parts)])

        cmd.extend([
            "-map", v_map,
            "-map", a_map,
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "22",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-t", str(duration),
            output_clip_path
        ])

        logger.info(f"Rendering whiteboard scene clip: {output_clip_path} (dur={duration:.2f}s)")

        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            for f_idx in range(total_frames):
                t_cur = f_idx / fps
                if f_idx < draw_frames:
                    prog = f_idx / float(draw_frames)
                    feather = 0.08
                    mask = np.clip((prog - grid_progress + feather) / feather, 0.0, 1.0)
                    mask = np.expand_dims(mask, axis=2)
                    current_frame = (img_arr * mask + white_canvas * (1.0 - mask)).astype(np.uint8)

                    frontier_y = int(prog * height * 0.82 + height * 0.10)
                    sweep_x = int(width * 0.5 + width * 0.28 * math.sin(2.0 * math.pi * 3.5 * prog))
                    jitter_x = int(6 * math.sin(2.0 * math.pi * 16.0 * t_cur))
                    jitter_y = int(4 * math.cos(2.0 * math.pi * 16.0 * t_cur))

                    hx = sweep_x + jitter_x - tip_x
                    hy = frontier_y + jitter_y - tip_y

                    frame_pil = Image.fromarray(current_frame)
                    frame_pil.paste(hand, (hx, hy), hand)
                    final_frame_arr = np.array(frame_pil)
                elif f_idx < draw_frames + exit_frames:
                    # Hand exits smoothly off-screen towards bottom right
                    current_frame = img_arr.astype(np.uint8)
                    exit_prog = (f_idx - draw_frames) / float(exit_frames)
                    exit_ease = exit_prog * exit_prog
                    start_x = width * 0.55
                    start_y = height * 0.85
                    hx = int(start_x + (width - start_x + 100) * exit_ease) - tip_x
                    hy = int(start_y + (height - start_y + 100) * exit_ease) - tip_y

                    frame_pil = Image.fromarray(current_frame)
                    frame_pil.paste(hand, (hx, hy), hand)
                    final_frame_arr = np.array(frame_pil)
                else:
                    # Drawing complete, hand gone
                    final_frame_arr = img_arr.astype(np.uint8)

                proc.stdin.write(final_frame_arr.tobytes())

            proc.stdin.close()
            proc.wait()

            if os.path.exists(output_clip_path) and os.path.getsize(output_clip_path) > 1024:
                logger.info(f"Whiteboard clip rendered successfully: {output_clip_path}")
                return True
            else:
                logger.error(f"Whiteboard render failed or empty file: {output_clip_path}")
                return False

        except Exception as e:
            logger.error(f"Whiteboard render exception: {e}")
            return False
        finally:
            if ass_path and os.path.exists(ass_path):
                try:
                    os.remove(ass_path)
                except:
                    pass
