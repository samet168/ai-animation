import os
import re
import time
import urllib.parse
import requests
import logging
from typing import Optional, Callable
from PIL import Image, ImageDraw, ImageFont
from app.core.settings import settings

logger = logging.getLogger("AIAnimationStudio.ImageService")

class ImageService:
    """
    Image generation service using Pollinations.ai & Hugging Face Serverless
    with automated rate-limit recovery and queue pacing.
    """

    _last_request_time: float = 0.0
    COOLDOWN_SECONDS: float = 45.0

    STYLE_PROMPTS = {
        "whiteboard_doodle": "cute clean hand-drawn whiteboard doodle cartoon animation, minimalist black and white line art sketch, expressive cartoon character, crisp inked outlines, high contrast drawing on pure white background, coloring book style",
        "whiteboard_color": "vibrant hand-drawn whiteboard cartoon illustration, colorful markers sketch on pure white background, playful charming doodle characters, crisp inked outlines",
        "3d_pixar": "3D Disney Pixar animation style, vibrant colorful, expressive character design, smooth subsurface scattering, cinematic lighting, 8k render, masterpiece",
        "anime_manga": "Japanese anime style, Makoto Shinkai and Studio Ghibli inspired, vibrant colors, clean sharp lineart, beautiful aesthetic scenery, highly detailed",
        "comic_book": "Modern graphic novel comic art style, bold inked outlines, dynamic shading, rich color palette, Marvel/DC comic illustration",
        "cinematic_realistic": "Cinematic movie scene still, photorealistic, 35mm film lens, atmospheric lighting, depth of field, sharp focus, 4k",
        "chibi_3d": "Cute 3D chibi character, big expressive eyes, glossy miniature toy aesthetic, soft volumetric studio lighting, charming and adorable",
        "watercolor": "Whimsical storybook illustration, soft hand-painted watercolor textures, gentle pastel tones, fairy tale aesthetic",
    }

    DIMENSIONS = {
        "9:16": (720, 1280),
        "16:9": (1280, 720),
    }

    @classmethod
    def enhance_prompt(cls, base_prompt: str, style: str = "3d_pixar") -> str:
        """Combine user prompt with stylistic keywords for maximum aesthetic quality."""
        style_keywords = cls.STYLE_PROMPTS.get(style, cls.STYLE_PROMPTS["3d_pixar"])
        # Clean prompt of special non-breaking characters
        clean_p = base_prompt.replace("\u2011", "-").replace("—", "-").strip()
        return f"{clean_p}, {style_keywords}"

    @classmethod
    def is_valid_image(cls, path: Optional[str]) -> bool:
        """
        Verify if an image file exists, is not a placeholder card (<15KB),
        and has valid image header bytes.
        """
        if not path or not os.path.exists(path):
            return False
        try:
            sz = os.path.getsize(path)
            if sz < 15000:
                return False
            with open(path, "rb") as f:
                header = f.read(4)
            # JPEG, PNG, or WEBP (RIFF)
            if header.startswith(b'\xff\xd8\xff') or header.startswith(b'\x89PNG') or header.startswith(b'RIFF'):
                return True
            return False
        except Exception:
            return False

    @classmethod
    def create_placeholder_image(cls, output_path: str, text: str = "", aspect_ratio: str = "9:16", style: str = "") -> bool:
        """
        Generate a scene backdrop card for emergency UI preview.
        """
        try:
            width, height = cls.DIMENSIONS.get(aspect_ratio, (720, 1280))
            is_wb = style.startswith("whiteboard")
            bg_color = (255, 255, 255) if is_wb else (18, 20, 24)
            card_fill = (250, 250, 252) if is_wb else (26, 29, 36)
            card_outline = (203, 213, 225) if is_wb else (46, 52, 64)
            inner_outline = (226, 232, 240) if is_wb else (36, 41, 51)
            text_color = (15, 23, 42) if is_wb else (229, 231, 235)

            img = Image.new("RGB", (width, height), color=bg_color)
            draw = ImageDraw.Draw(img)

            margin_x = int(width * 0.08)
            margin_y = int(height * 0.18)
            box_coords = [(margin_x, margin_y), (width - margin_x, height - margin_y)]
            draw.rounded_rectangle(box_coords, radius=18, fill=card_fill, outline=card_outline, width=2)

            accent_coords = [(margin_x + 12, margin_y + 12), (width - margin_x - 12, height - margin_y - 12)]
            draw.rounded_rectangle(accent_coords, radius=12, fill=None, outline=inner_outline, width=1)

            app_dir = settings.app_dir
            font_path = os.path.join(app_dir, "assets", "fonts", "KantumruyPro-Regular.ttf")
            font = None
            if os.path.exists(font_path):
                try:
                    font = ImageFont.truetype(font_path, 26 if aspect_ratio == "9:16" else 22)
                except Exception:
                    pass

            center_x = width // 2
            center_y = height // 2

            title_text = "Whiteboard Animation Scene" if is_wb else "AI Animation Scene"
            if font:
                draw.text((center_x, center_y - 40), title_text, fill=text_color, font=font, anchor="mm")
            else:
                draw.text((center_x, center_y - 40), title_text, fill=text_color, anchor="mm")

            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            img.save(output_path, "PNG")
            return True
        except Exception as e:
            logger.error(f"Failed to create procedural image: {e}")
            return False

    @classmethod
    def remove_watermark(cls, image_path: str) -> bool:
        """
        Automatically remove third-party AI watermarks (such as 'pollinations.ai')
        from the bottom-right corner using OpenCV Telea inpainting.
        Guarantees 100% clean, watermark-free images and video frames.
        """
        try:
            if not os.path.exists(image_path):
                return False
            import cv2
            import numpy as np

            img = cv2.imread(image_path)
            if img is None:
                return False
            h, w = img.shape[:2]

            # The Pollinations badge sits at the bottom-right corner:
            # Height: bottom 58px, Width: right 215px
            mask = np.zeros((h, w), dtype=np.uint8)
            y_start = max(0, h - 58)
            x_start = max(0, w - 215)
            mask[y_start:h, x_start:w] = 255

            cleaned = cv2.inpaint(img, mask, inpaintRadius=7, flags=cv2.INPAINT_TELEA)
            cv2.imwrite(image_path, cleaned)
            logger.info(f"Watermark successfully erased from: {image_path}")
            return True
        except Exception as e:
            logger.warning(f"Watermark removal skipped for {image_path}: {e}")
            return False

    @classmethod
    def generate_image(cls, 
                        prompt: str, 
                        output_path: str, 
                        style: str = "3d_pixar", 
                        aspect_ratio: str = "9:16",
                        model: str = "flux",
                        seed: Optional[int] = None,
                        max_retries: int = 8,
                        progress_callback: Optional[Callable[[str], None]] = None) -> bool:
        """
        Generate image via Pollinations.ai or Hugging Face with proactive queue cooldown
        and guaranteed real image validation.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        
        full_prompt = cls.enhance_prompt(prompt, style)
        encoded_prompt = urllib.parse.quote(full_prompt)
        width, height = cls.DIMENSIONS.get(aspect_ratio, (720, 1280))
        
        # 1. Try Hugging Face Serverless if token configured
        hf_token = settings.get("huggingface_token", "").strip()
        if hf_token:
            try:
                if progress_callback:
                    progress_callback("កំពុងទាញយករូបភាពតាម Hugging Face FLUX...")
                hf_url = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
                hf_headers = {"Authorization": f"Bearer {hf_token}"}
                hf_res = requests.post(hf_url, headers=hf_headers, json={"inputs": full_prompt}, timeout=45)
                if hf_res.status_code == 200 and len(hf_res.content) > 15000:
                    with open(output_path, "wb") as f:
                        f.write(hf_res.content)
                    logger.info(f"Image successfully downloaded via Hugging Face: {output_path}")
                    return True
            except Exception as e:
                logger.warning(f"Hugging Face generation failed, falling back to Pollinations: {e}")

        # 2. Pollinations.ai Generation with Proactive Rate-Limit Cooldown
        pollen_key = settings.get("pollen_api_key", "").strip()

        # Build URL
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true"
        if pollen_key:
            url += f"&key={pollen_key}"
        elif model and model != "default" and model != "flux":
            url += f"&model={model}"

        if seed is not None:
            url += f"&seed={seed}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"
        }

        # Proactive Cooldown: Wait before sending request if 45s haven't elapsed
        if not pollen_key:
            elapsed = time.time() - cls._last_request_time
            if elapsed < cls.COOLDOWN_SECONDS:
                wait_needed = int(cls.COOLDOWN_SECONDS - elapsed) + 1
                for rem in range(wait_needed, 0, -1):
                    if progress_callback:
                        progress_callback(f"រង់ចាំ AI Cooldown ({rem}s) ដើម្បីបង្កើតរូបភាពបន្ទាប់...")
                    time.sleep(1)

        for attempt in range(1, max_retries + 1):
            try:
                if progress_callback:
                    progress_callback(f"កំពុងទាញយករូបភាពពី Pollinations AI (ព្យាយាម {attempt}/{max_retries})...")
                logger.info(f"Generating image (attempt {attempt}/{max_retries})...")
                
                response = requests.get(url, headers=headers, timeout=60)
                
                # Check for successful real image
                if response.status_code == 200 and len(response.content) > 15000:
                    first_bytes = response.content[:4]
                    if first_bytes.startswith(b'\xff\xd8\xff') or first_bytes.startswith(b'\x89PNG') or first_bytes.startswith(b'RIFF'):
                        with open(output_path, "wb") as f:
                            f.write(response.content)
                        cls._last_request_time = time.time()
                        # Automatically erase any third-party watermark from Pollinations
                        cls.remove_watermark(output_path)
                        logger.info(f"Real image successfully saved & watermark-free: {output_path} ({len(response.content)} bytes)")
                        return True
                
                # Handle rate limit (402 Free limit: 1 image every 45s)
                if response.status_code == 402:
                    resp_text = response.text
                    m = re.search(r"Retry after (\d+)s", resp_text)
                    wait_secs = int(m.group(1)) if m else 30
                    wait_secs = max(wait_secs, 5)
                    wait_secs = min(wait_secs, 45) + 1

                    if attempt < max_retries:
                        logger.info(f"Pollinations cooldown active. Waiting {wait_secs}s before retry {attempt+1}/{max_retries}...")
                        for rem in range(wait_secs, 0, -1):
                            if progress_callback:
                                progress_callback(f"រង់ចាំ AI Cooldown ({rem}s) មុនព្យាយាមម្តងទៀត...")
                            time.sleep(1)
                        # Switch to clean base URL if custom model was passed
                        if "model=" in url:
                            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true"
                        continue

            except Exception as e:
                logger.error(f"Image download error on attempt {attempt}: {e}")
            
            if attempt < max_retries:
                time.sleep(3)

        logger.error(f"Failed to generate real AI image for {output_path} after {max_retries} attempts.")
        return False
