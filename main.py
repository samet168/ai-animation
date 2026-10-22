import sys
import os
import logging

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("AIAnimationStudio")

def main():
    logger.info("Starting AI Animation Studio...")

    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFontDatabase, QFont
    from app.ui.main_window import MainWindow

    # High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("AI Animation Studio")
    app.setOrganizationName("AITools")

    # Load and register Khmer Kantumruy Pro Font
    font_path = os.path.join(BASE_DIR, "assets", "fonts", "KantumruyPro-Regular.ttf")
    if os.path.exists(font_path):
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id != -1:
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families:
                khmer_font = QFont(families[0], 10)
                app.setFont(khmer_font)
                logger.info(f"Loaded primary Khmer font: {families[0]}")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
