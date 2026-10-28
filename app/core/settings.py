import os
import sys
import json
import logging

logger = logging.getLogger("AIAnimationStudio.Settings")

class SettingsManager:
    """Manages application settings, API keys, and user preferences."""

    DEFAULT_SETTINGS = {
        # API Keys
        "gemini_api_key": "",
        "groq_api_key": "",
        "huggingface_token": "",
        "elevenlabs_api_key": "",

        # Voice Cloning Settings
        "cloned_voice_id": "",
        "custom_voice_sample_path": "",

        # Story & Generation Defaults
        "default_style": "talkmoney_2d",
        "default_scenes_count": 6,
        "aspect_ratio": "16:9",  # "16:9" or "9:16"

        # Image Settings
        "image_model": "flux",    # "flux", "turbo"
        "enhance_prompts": True,

        # Voice / TTS Settings
        "default_voice": "km-KH-PisethNeural",  # Piseth (Male) or Sreymom (Female)
        "voice_rate": "-6%",
        "voice_pitch": "-2Hz",

        # Video & Subtitles
        "subtitle_enabled": True,
        "subtitle_font": "Leelawadee UI",
        "subtitle_font_size": 22,
        "subtitle_color": "#FFFFFF",
        "subtitle_outline_color": "#000000",
        "subtitle_outline_width": 2,

        # Motion & Transition
        "default_motion": "auto",  # "auto", "zoom_in", "zoom_out", "pan_left", "pan_right"
        "scene_transition": "fade", # "fade", "none"
        "transition_duration": 0.5,

        # BGM
        "bgm_enabled": False,
        "bgm_volume": 0.15,

        # Paths
        "ffmpeg_path": "",
        "output_dir": "",
    }

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SettingsManager, cls).__new__(cls)
            cls._instance._init_settings()
        return cls._instance

    def _init_settings(self):
        self.app_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # User AppData dir for persistent settings
        appdata_base = os.getenv("LOCALAPPDATA") or os.path.expanduser("~")
        self.config_dir = os.path.join(appdata_base, "AIAnimationStudio")
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            self.config_file = os.path.join(self.config_dir, "settings.json")
        except (PermissionError, OSError):
            self.config_dir = os.path.join(self.app_dir, "data")
            os.makedirs(self.config_dir, exist_ok=True)
            self.config_file = os.path.join(self.config_dir, "settings.json")

        self.settings = dict(self.DEFAULT_SETTINGS)
        self.load()
        self._ensure_ffmpeg_path()
        self._ensure_output_dir()

    def _ensure_ffmpeg_path(self):
        # 1. Bundled in project ./ffmpeg/ffmpeg.exe
        bundled_ffmpeg = os.path.join(self.app_dir, "ffmpeg", "ffmpeg.exe")
        translat_ffmpeg = os.path.join(os.path.dirname(self.app_dir), "tools-ai-translat", "ffmpeg", "ffmpeg.exe")

        if os.path.exists(bundled_ffmpeg):
            self.settings["ffmpeg_path"] = bundled_ffmpeg
        elif os.path.exists(translat_ffmpeg):
            self.settings["ffmpeg_path"] = translat_ffmpeg
        else:
            import shutil
            sys_ffmpeg = shutil.which("ffmpeg")
            if sys_ffmpeg:
                self.settings["ffmpeg_path"] = sys_ffmpeg

        # Ensure ffmpeg dir is added to os.environ["PATH"] for all sub-libraries (pydub, etc.)
        ffmpeg_bin = self.settings.get("ffmpeg_path")
        if ffmpeg_bin and os.path.exists(ffmpeg_bin):
            bin_dir = os.path.dirname(os.path.abspath(ffmpeg_bin))
            if bin_dir not in os.environ.get("PATH", ""):
                os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")

    def _ensure_output_dir(self):
        if not self.settings.get("output_dir"):
            default_out = os.path.join(self.app_dir, "output")
            os.makedirs(default_out, exist_ok=True)
            self.settings["output_dir"] = default_out

    def load(self):
        """Load settings from JSON file."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self.settings.update(loaded)
            except Exception as e:
                logger.error(f"Failed to load settings from {self.config_file}: {e}")

    def save(self):
        """Save settings to JSON file."""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            logger.info(f"Settings saved successfully to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            return False

    def get(self, key, default=None):
        return self.settings.get(key, default if default is not None else self.DEFAULT_SETTINGS.get(key))

    def set(self, key, value):
        self.settings[key] = value
        self.save()

    def get_ffmpeg_path(self) -> str:
        return self.settings.get("ffmpeg_path", "ffmpeg")

    def get_output_dir(self) -> str:
        return self.settings.get("output_dir", os.path.join(self.app_dir, "output"))


# Global convenience accessor
settings = SettingsManager()
