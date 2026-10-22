import os
import logging
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QStackedWidget, QFrame
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from app.ui.theme import CHARCOAL_THEME
from app.ui.icons import get_icon
from app.ui.dialogs.settings_dialog import SettingsDialog
from app.ui.views.story_input_view import StoryInputView
from app.ui.views.scene_editor_view import SceneEditorView
from app.ui.views.player_view import PlayerView
from app.core.settings import settings

logger = logging.getLogger("AIAnimationStudio.MainWindow")

class MainWindow(QMainWindow):
    """Main Application Window for AI Animation Studio."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Animation Studio - បង្កើតវីដេអូ Animation & សំឡេងដោយ AI")
        self.resize(1150, 780)
        self.setMinimumSize(950, 650)
        self.setStyleSheet(CHARCOAL_THEME)

        self._init_ui()
        self._check_api_key_status()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Top Navigation Bar (Charcoal / Graphite)
        nav_bar = QFrame()
        nav_bar.setStyleSheet("background-color: #16181C; border-bottom: 1px solid #2B2E36; padding: 6px 16px;")
        nav_lay = QHBoxLayout(nav_bar)
        nav_lay.setContentsMargins(0, 0, 0, 0)
        nav_lay.setSpacing(10)

        # App Brand
        brand_lay = QHBoxLayout()
        logo_btn = QPushButton()
        logo_btn.setIcon(get_icon("sparkles", "#D1D5DB", 22))
        logo_btn.setIconSize(QSize(22, 22))
        logo_btn.setStyleSheet("border: none; background: transparent; padding: 0;")
        
        brand_lbl = QLabel("AI Animation Studio")
        brand_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #F3F4F6;")
        brand_lay.addWidget(logo_btn)
        brand_lay.addWidget(brand_lbl)
        nav_lay.addLayout(brand_lay)

        nav_lay.addSpacing(25)

        # Nav Buttons with Vector Icons
        self.btn_nav_create = QPushButton("  បង្កើតថ្មី (Generator)")
        self.btn_nav_create.setIcon(get_icon("sparkles", "#9CA3AF", 18))
        self.btn_nav_create.setIconSize(QSize(18, 18))
        self.btn_nav_create.clicked.connect(lambda: self.switch_view(0))
        nav_lay.addWidget(self.btn_nav_create)

        self.btn_nav_studio = QPushButton("  ស្ទូឌីយោ Scene (Studio)")
        self.btn_nav_studio.setIcon(get_icon("film", "#9CA3AF", 18))
        self.btn_nav_studio.setIconSize(QSize(18, 18))
        self.btn_nav_studio.clicked.connect(lambda: self.switch_view(1))
        nav_lay.addWidget(self.btn_nav_studio)

        self.btn_nav_player = QPushButton("  Preview & Export")
        self.btn_nav_player.setIcon(get_icon("video", "#9CA3AF", 18))
        self.btn_nav_player.setIconSize(QSize(18, 18))
        self.btn_nav_player.clicked.connect(lambda: self.switch_view(2))
        nav_lay.addWidget(self.btn_nav_player)

        nav_lay.addStretch()

        # API Key Status Badge
        self.lbl_key_badge = QLabel()
        self.lbl_key_badge.setStyleSheet("font-size: 12px; padding: 4px 10px; border-radius: 5px;")
        nav_lay.addWidget(self.lbl_key_badge)

        # Settings Button with Gear Vector Icon
        self.btn_settings = QPushButton("  ការកំណត់")
        self.btn_settings.setIcon(get_icon("settings", "#F3F4F6", 18))
        self.btn_settings.setIconSize(QSize(18, 18))
        self.btn_settings.setProperty("accent", "primary")
        self.btn_settings.clicked.connect(self.open_settings)
        nav_lay.addWidget(self.btn_settings)

        main_layout.addWidget(nav_bar)

        # Stacked Views Container
        self.stack = QStackedWidget()

        # View 0: Story Input
        self.story_view = StoryInputView()
        self.story_view.open_studio.connect(self._on_open_studio)
        self.story_view.video_ready.connect(self._on_video_ready)
        self.stack.addWidget(self.story_view)

        # View 1: Scene Editor / Studio
        self.studio_view = SceneEditorView()
        self.studio_view.video_ready.connect(self._on_video_ready)
        self.stack.addWidget(self.studio_view)

        # View 2: Video Player
        self.player_view = PlayerView()
        self.player_view.back_to_editor.connect(self._on_open_studio)
        self.stack.addWidget(self.player_view)

        main_layout.addWidget(self.stack)

        self.switch_view(0)

    def switch_view(self, index: int):
        self.stack.setCurrentIndex(index)
        
        btns = [
            (self.btn_nav_create, "sparkles"),
            (self.btn_nav_studio, "film"),
            (self.btn_nav_player, "video")
        ]
        for i, (b, icon_name) in enumerate(btns):
            if i == index:
                b.setIcon(get_icon(icon_name, "#F3F4F6", 18))
                b.setStyleSheet("background-color: #2F333D; color: #FFFFFF; border: 1px solid #4B5263; font-weight: bold;")
            else:
                b.setIcon(get_icon(icon_name, "#9CA3AF", 18))
                b.setStyleSheet("background-color: #22252B; color: #D1D5DB; border: 1px solid #323640; font-weight: normal;")

    def _on_open_studio(self, project_id: int):
        self.studio_view.load_project(project_id)
        self.switch_view(1)

    def _on_video_ready(self, project_id: int, final_video_path: str):
        self.player_view.load_video(project_id, final_video_path)
        self.switch_view(2)

    def open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec():
            self._check_api_key_status()

    def _check_api_key_status(self):
        gemini_key = settings.get("gemini_api_key", "").strip()
        groq_key = settings.get("groq_api_key", "").strip()

        if gemini_key:
            self.lbl_key_badge.setText("Gemini Key: Active")
            self.lbl_key_badge.setStyleSheet("background-color: #16332C; color: #6EE7B7; border: 1px solid #234E43; font-weight: bold;")
        elif groq_key:
            self.lbl_key_badge.setText("Groq Key: Active")
            self.lbl_key_badge.setStyleSheet("background-color: #16332C; color: #6EE7B7; border: 1px solid #234E43; font-weight: bold;")
        else:
            self.lbl_key_badge.setText("មិនទាន់មាន Key (Settings)")
            self.lbl_key_badge.setStyleSheet("background-color: #361E22; color: #FCA5A5; border: 1px solid #572A30; font-weight: bold;")
