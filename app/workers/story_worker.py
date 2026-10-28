import logging
from PySide6.QtCore import QThread, Signal
from app.services.gemini_service import GeminiService

logger = logging.getLogger("AIAnimationStudio.StoryWorker")

class StoryWorker(QThread):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, topic: str, num_scenes: int = 5, style: str = "aitest_style", genre: str = "general"):
        super().__init__()
        self.topic = topic
        self.num_scenes = num_scenes
        self.style = style
        self.genre = genre

    def run(self):
        try:
            logger.info(f"Generating story for topic: '{self.topic}' ({self.genre}) with {self.num_scenes} scenes...")
            result = GeminiService.generate_storyboard(self.topic, self.num_scenes, self.style, self.genre)
            self.finished.emit(result)
        except Exception as e:
            logger.error(f"Story generation failed: {e}")
            self.error.emit(str(e))
