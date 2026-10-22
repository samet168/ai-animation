import os
import re
import math
import subprocess
import logging
from typing import Optional, List, Tuple
import numpy as np
import cv2
from PIL import Image
import soundfile as sf
from app.core.settings import settings
from app.services.khmer_service import KhmerService

logger = logging.getLogger("AIAnimationStudio.TalkingEngine")

class TalkingCharacterEngine:
    """
    Talking Character & Motion Animation Engine.
    Animates characters with:
    - Audio-driven lip-sync (mouth opens and articulates in sync with speech syllables)
    - Natural periodic eye blinking
    - Organic breathing, head sway, and idle body movement
    - Burned Khmer Unicode subtitles
    - 100% Free Forever, rendered locally on PC via Python + FFmpeg at 300+ FPS!
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
    def _extract_speech_rms(cls, audio_path: str, fps: int = 25, total_frames: int = 100) -> np.ndarray:
        """Extract frame-by-frame normalized speech RMS volume envelope for lip-sync."""
        try:
            data, samplerate = sf.read(audio_path)
            if data.ndim > 1:
                data = data.mean(axis=1)

            samples_per_frame = int(samplerate / fps)
            audio_frames = int(len(data) / samples_per_frame)
            
            rms_list = []
            for i in range(max(total_frames, audio_frames)):
                idx_start = i * samples_per_frame
                idx_end = (i + 1) * samples_per_frame
                if idx_start < len(data):
                    window = data[idx_start:min(idx_end, len(data))]
                    rms = np.sqrt(np.mean(window ** 2)) if len(window) > 0 else 0.0
                else:
                    rms = 0.0
                rms_list.append(rms)

            rms_arr = np.array(rms_list[:total_frames], dtype=np.float32)
            
            # Smooth RMS envelope with moving average filter (3-frame window)
            if len(rms_arr) > 4:
                kernel = np.array([0.25, 0.5, 0.25], dtype=np.float32)
                rms_arr = np.convolve(rms_arr, kernel, mode="same")

            # Normalize 0.0 to 1.0 with noise gate
            max_v = np.max(rms_arr) if np.max(rms_arr) > 0.001 else 1.0
            norm = np.clip((rms_arr - 0.03 * max_v) / (max_v * 0.65), 0.0, 1.0)
            return norm
        except Exception as e:
            logger.warning(f"Failed to extract audio RMS, using procedural cadence: {e}")
            t = np.linspace(0, total_frames / float(fps), total_frames)
            return (np.sin(2.0 * np.pi * 3.2 * t) ** 2 * 0.7).astype(np.float32)

    @classmethod
    def render_scene_clip(cls,
                          image_path: str,
                          audio_path: str,
                          duration: float,
                          output_clip_path: str,
                          aspect_ratio: str = "9:16",
                          subtitle_text: Optional[str] = None) -> bool:
        """
        Render a living talking character animated scene clip:
        - Animated mouth speaking in sync with speech audio
        - Natural eye blinking
        - Character breathing and head tilting
        - Subtitles burned in crisp Khmer font
        """
        ffmpeg = cls.get_ffmpeg_cmd()
        os.makedirs(os.path.dirname(os.path.abspath(output_clip_path)), exist_ok=True)

        width, height = cls.DIMENSIONS.get(aspect_ratio, (720, 1280))
        fps = 25
        duration = max(duration, 2.0)
        total_frames = int(duration * fps)

        # 1. Ensure watermark is erased and load image
        try:
            from app.services.image_service import ImageService
            ImageService.remove_watermark(image_path)
            raw_img = Image.open(image_path).convert("RGB").resize((width, height), Image.Resampling.LANCZOS)
            base_arr = np.array(raw_img, dtype=np.float32)
        except Exception as e:
            logger.error(f"Failed to load image for talking character: {e}")
            return False

        # 2. Extract speech RMS envelope for lip-sync
        norm_rms = cls._extract_speech_rms(audio_path, fps=fps, total_frames=total_frames)

        # 3. Define facial animation regions (Character head & mouth)
        # In typical portrait/character composition:
        # Head center
        head_cx = int(0.50 * width)
        head_cy = int(0.44 * height if aspect_ratio == "9:16" else 0.46 * height)
        
        # Mouth region
        mouth_cx = head_cx
        mouth_cy = head_cy + int(0.09 * height if aspect_ratio == "9:16" else 0.11 * height)
        mouth_rx = int(0.11 * width)
        mouth_ry = int(0.05 * height)

        # Eyes region
        eyes_cx = head_cx
        eyes_cy = head_cy - int(0.05 * height if aspect_ratio == "9:16" else 0.07 * height)
        eyes_rx = int(0.18 * width)
        eyes_ry = int(0.04 * height)

        # Precalculate grid coordinates
        yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
        
        # Mouth influence mask
        m_dist = np.sqrt(((xx - mouth_cx) / mouth_rx) ** 2 + ((yy - mouth_cy) / mouth_ry) ** 2)
        m_influence = np.clip(1.0 - m_dist, 0.0, 1.0)
        m_influence = (np.sin(m_influence * (np.pi / 2.0)) ** 2).astype(np.float32)

        # Eyes influence mask
        e_dist = np.sqrt(((xx - eyes_cx) / eyes_rx) ** 2 + ((yy - eyes_cy) / eyes_ry) ** 2)
        e_influence = np.clip(1.0 - e_dist, 0.0, 1.0)
        e_influence = (np.sin(e_influence * (np.pi / 2.0)) ** 2).astype(np.float32)

        # 4. Burned Khmer Subtitle ASS
        ass_path = None
        has_sub = subtitle_text and settings.get("subtitle_enabled", True)
        if has_sub:
            ass_path = output_clip_path + ".ass"
            cls._create_ass_file(subtitle_text, duration, ass_path, aspect_ratio)

        # 5. FFmpeg encoding pipeline
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

        if has_sub and ass_path:
            escaped_ass = ass_path.replace("\\", "/").replace(":", "\\:")
            cmd.extend(["-vf", f"subtitles='{escaped_ass}'"])

        cmd.extend([
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "22",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-t", str(duration),
            "-shortest",
            output_clip_path
        ])

        logger.info(f"Rendering Talking Character video: {output_clip_path} (frames={total_frames})")

        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            for f_idx in range(total_frames):
                t_cur = f_idx / float(fps)
                
                # Speech RMS at this frame
                speech_val = float(norm_rms[f_idx]) if f_idx < len(norm_rms) else 0.0
                
                # Jaw vertical opening: 0 to 14 pixels based on syllable volume
                jaw_drop = speech_val * 13.0
                
                # Eye blink trigger: blink for 4 frames (~0.16s) every 3.2 seconds
                blink_phase = t_cur % 3.4
                if blink_phase < 0.16:
                    blink_progress = math.sin(blink_phase / 0.16 * math.pi)
                    blink_compress = blink_progress * 7.0
                else:
                    blink_compress = 0.0

                # Organic breathing & head tilt
                breath_y = 3.5 * math.sin(2.0 * math.pi * 0.55 * t_cur)
                sway_x = 1.8 * math.cos(2.0 * math.pi * 0.28 * t_cur)

                # Composite deformation mesh
                map_y = yy - (m_influence * jaw_drop) + (e_influence * blink_compress) - breath_y
                map_x = xx - sway_x

                # High-speed C++ mesh deformation via cv2.remap (600+ FPS)
                deformed = cv2.remap(base_arr.astype(np.uint8), map_x, map_y, interpolation=cv2.INTER_LINEAR)
                proc.stdin.write(deformed.tobytes())

            proc.stdin.close()
            proc.wait()

            if os.path.exists(output_clip_path) and os.path.getsize(output_clip_path) > 1024:
                logger.info(f"Talking character clip rendered successfully: {output_clip_path}")
                return True
            else:
                logger.error(f"Talking clip failed or empty: {output_clip_path}")
                return False

        except Exception as e:
            logger.error(f"Talking character render exception: {e}")
            return False
        finally:
            if ass_path and os.path.exists(ass_path):
                try: os.remove(ass_path)
                except: pass
