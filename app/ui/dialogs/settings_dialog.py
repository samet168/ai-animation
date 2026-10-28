import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QComboBox, QCheckBox, QFileDialog, QTabWidget, QWidget, QFrame, QMessageBox
)
from PySide6.QtCore import Qt, QUrl, QSize, QThread, Signal
from PySide6.QtGui import QDesktopServices
from app.core.settings import settings
from app.services.gemini_service import GeminiService
from app.services.tts_service import TTSService
from app.ui.icons import get_icon

class ApiTestWorker(QThread):
    """Background worker for testing API keys without freezing the UI."""
    result_ready = Signal(bool, str)

    def __init__(self, test_type: str, api_key: str):
        super().__init__()
        self.test_type = test_type  # "gemini" or "groq"
        self.api_key = api_key

    def run(self):
        if self.test_type == "gemini":
            ok, msg = GeminiService.test_api_key(self.api_key)
        else:
            ok, msg = GeminiService.test_groq_key(self.api_key)
        self.result_ready.emit(ok, msg)


class SettingsDialog(QDialog):
    """Settings dialog for configuring API keys, AI models, voices, and rendering options."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ការកំណត់ (Settings)")
        self.resize(750, 600)
        self.setMinimumSize(680, 520)
        self.setModal(True)
        self.gemini_test_worker = None
        self.groq_test_worker = None
        self._init_ui()
        self._load_values()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        # Header Title
        title_lay = QHBoxLayout()
        icon_lbl = QPushButton()
        icon_lbl.setIcon(get_icon("settings", "#D1D5DB", 22))
        icon_lbl.setIconSize(QSize(22, 22))
        icon_lbl.setStyleSheet("border: none; background: transparent; padding: 0;")
        title_lbl = QLabel("ការកំណត់កម្មវិធី (Application Settings)")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #F3F4F6;")
        title_lay.addWidget(icon_lbl)
        title_lay.addWidget(title_lbl)
        title_lay.addStretch()
        main_layout.addLayout(title_lay)

        # Tabs
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Tab 1: API Keys
        self.tab_api = QWidget()
        self._setup_api_tab()
        self.tabs.addTab(self.tab_api, "API Keys (Google & Groq)")
        self.tabs.setTabIcon(0, get_icon("key", "#9CA3AF", 16))

        # Tab 2: Audio & Voice
        self.tab_audio = QWidget()
        self._setup_audio_tab()
        self.tabs.addTab(self.tab_audio, "សំឡេង & រូបភាព (Voice & Image)")
        self.tabs.setTabIcon(1, get_icon("volume", "#9CA3AF", 16))

        # Tab 3: Video & Subtitle
        self.tab_video = QWidget()
        self._setup_video_tab()
        self.tabs.addTab(self.tab_video, "វីដេអូ & FFmpeg (Render)")
        self.tabs.setTabIcon(2, get_icon("video", "#9CA3AF", 16))

        # Bottom Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("បោះបង់ (Cancel)")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("  រក្សាទុក (Save)")
        self.btn_save.setIcon(get_icon("check", "#FFFFFF", 16))
        self.btn_save.setIconSize(QSize(16, 16))
        self.btn_save.setProperty("accent", "primary")
        self.btn_save.clicked.connect(self._save_and_close)
        btn_layout.addWidget(self.btn_save)

        main_layout.addLayout(btn_layout)

    def _setup_api_tab(self):
        layout = QVBoxLayout(self.tab_api)
        layout.setSpacing(14)
        layout.setContentsMargins(15, 15, 15, 15)

        # Notice Card
        notice_card = QFrame()
        notice_card.setProperty("card", "true")
        n_lay = QVBoxLayout(notice_card)
        n_lbl1 = QLabel("<b>ចំណាំសំខាន់៖</b> Google Gemini API និង Groq API គឺ <b>Free</b> សម្រាប់តែងសាច់រឿង & Prompts")
        n_lbl1.setStyleSheet("color: #6EE7B7; font-size: 13px;")
        n_lbl2 = QLabel("ចំណែក <b>រូបភាព (Pollinations)</b> និង <b>សំឡេងខ្មែរ (Edge-TTS)</b> ដំណើរការ Free ដោយស្វ័យប្រវត្តិ មិនបាច់ដាក់ Key ឡើយ។")
        n_lbl2.setStyleSheet("color: #9CA3AF; font-size: 12px;")
        n_lay.addWidget(n_lbl1)
        n_lay.addWidget(n_lbl2)
        layout.addWidget(notice_card)

        # Gemini API Key Field
        gem_card = QFrame()
        gem_card.setProperty("card", "true")
        g_lay = QVBoxLayout(gem_card)

        g_title_lay = QHBoxLayout()
        g_title = QLabel("Google Gemini API Key:")
        g_title.setStyleSheet("font-weight: 600; color: #E5E7EB;")
        
        g_link_btn = QPushButton("  យក Key Free (Google AI Studio)")
        g_link_btn.setIcon(get_icon("link", "#9CA3AF", 14))
        g_link_btn.setIconSize(QSize(14, 14))
        g_link_btn.setStyleSheet("color: #9CA3AF; background: transparent; border: none; text-decoration: underline;")
        g_link_btn.setCursor(Qt.PointingHandCursor)
        g_link_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://aistudio.google.com/app/apikey")))
        g_title_lay.addWidget(g_title)
        g_title_lay.addStretch()
        g_title_lay.addWidget(g_link_btn)
        g_lay.addLayout(g_title_lay)

        key_input_lay = QHBoxLayout()
        self.txt_gemini_key = QLineEdit()
        self.txt_gemini_key.setEchoMode(QLineEdit.Password)
        self.txt_gemini_key.setPlaceholderText("បញ្ចូល Gemini API Key នៅទីនេះ (ឧ. AIzaSy...)")
        key_input_lay.addWidget(self.txt_gemini_key)

        self.btn_toggle_gemini = QPushButton()
        self.btn_toggle_gemini.setIcon(get_icon("eye", "#9CA3AF", 16))
        self.btn_toggle_gemini.setFixedWidth(38)
        self.btn_toggle_gemini.clicked.connect(lambda: self._toggle_echo(self.txt_gemini_key, self.btn_toggle_gemini))
        key_input_lay.addWidget(self.btn_toggle_gemini)

        self.btn_test_gemini = QPushButton("តេស្ត Key (Test)")
        self.btn_test_gemini.clicked.connect(self._test_gemini)
        key_input_lay.addWidget(self.btn_test_gemini)
        g_lay.addLayout(key_input_lay)

        self.lbl_gemini_status = QLabel("")
        self.lbl_gemini_status.setWordWrap(True)
        self.lbl_gemini_status.setStyleSheet("font-size: 12px; margin-top: 4px;")
        g_lay.addWidget(self.lbl_gemini_status)
        layout.addWidget(gem_card)

        # Groq API Key Field (Alternative / Backup)
        groq_card = QFrame()
        groq_card.setProperty("card", "true")
        gr_lay = QVBoxLayout(groq_card)

        gr_title_lay = QHBoxLayout()
        gr_title = QLabel("Groq API Key (ជម្រើសជំនួស / Fallback):")
        gr_title.setStyleSheet("font-weight: 600; color: #E5E7EB;")

        gr_link_btn = QPushButton("  យក Key Free (console.groq.com)")
        gr_link_btn.setIcon(get_icon("link", "#9CA3AF", 14))
        gr_link_btn.setIconSize(QSize(14, 14))
        gr_link_btn.setStyleSheet("color: #9CA3AF; background: transparent; border: none; text-decoration: underline;")
        gr_link_btn.setCursor(Qt.PointingHandCursor)
        gr_link_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://console.groq.com/keys")))
        gr_title_lay.addWidget(gr_title)
        gr_title_lay.addStretch()
        gr_title_lay.addWidget(gr_link_btn)
        gr_lay.addLayout(gr_title_lay)

        groq_input_lay = QHBoxLayout()
        self.txt_groq_key = QLineEdit()
        self.txt_groq_key.setEchoMode(QLineEdit.Password)
        self.txt_groq_key.setPlaceholderText("បញ្ចូល Groq API Key នៅទីនេះ (ឧ. gsk_...)")
        groq_input_lay.addWidget(self.txt_groq_key)

        self.btn_toggle_groq = QPushButton()
        self.btn_toggle_groq.setIcon(get_icon("eye", "#9CA3AF", 16))
        self.btn_toggle_groq.setFixedWidth(38)
        self.btn_toggle_groq.clicked.connect(lambda: self._toggle_echo(self.txt_groq_key, self.btn_toggle_groq))
        groq_input_lay.addWidget(self.btn_toggle_groq)

        self.btn_test_groq = QPushButton("តេស្ត Groq (Test)")
        self.btn_test_groq.clicked.connect(self._test_groq)
        groq_input_lay.addWidget(self.btn_test_groq)
        gr_lay.addLayout(groq_input_lay)

        self.lbl_groq_status = QLabel("")
        self.lbl_groq_status.setWordWrap(True)
        self.lbl_groq_status.setStyleSheet("font-size: 12px; margin-top: 4px;")
        gr_lay.addWidget(self.lbl_groq_status)
        layout.addWidget(groq_card)

        # ElevenLabs API Key Field (Voice Cloning)
        el_card = QFrame()
        el_card.setProperty("card", "true")
        el_lay = QVBoxLayout(el_card)

        el_title_lay = QHBoxLayout()
        el_title = QLabel("ElevenLabs API Key (សម្រាប់ Voice Cloning):")
        el_title.setStyleSheet("font-weight: 600; color: #E5E7EB;")

        el_link_btn = QPushButton("  យក Key Free (elevenlabs.io)")
        el_link_btn.setIcon(get_icon("link", "#9CA3AF", 14))
        el_link_btn.setIconSize(QSize(14, 14))
        el_link_btn.setStyleSheet("color: #9CA3AF; background: transparent; border: none; text-decoration: underline;")
        el_link_btn.setCursor(Qt.PointingHandCursor)
        el_link_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://elevenlabs.io")))
        el_title_lay.addWidget(el_title)
        el_title_lay.addStretch()
        el_title_lay.addWidget(el_link_btn)
        el_lay.addLayout(el_title_lay)

        el_input_lay = QHBoxLayout()
        self.txt_elevenlabs_key = QLineEdit()
        self.txt_elevenlabs_key.setEchoMode(QLineEdit.Password)
        self.txt_elevenlabs_key.setPlaceholderText("បញ្ចូល ElevenLabs API Key សម្រាប់ Clone សំឡេងខ្មែរ (10,000 Free Chars/month)...")
        el_input_lay.addWidget(self.txt_elevenlabs_key)

        self.btn_toggle_el = QPushButton()
        self.btn_toggle_el.setIcon(get_icon("eye", "#9CA3AF", 16))
        self.btn_toggle_el.setFixedWidth(38)
        self.btn_toggle_el.clicked.connect(lambda: self._toggle_echo(self.txt_elevenlabs_key, self.btn_toggle_el))
        el_input_lay.addWidget(self.btn_toggle_el)
        el_lay.addLayout(el_input_lay)

        layout.addWidget(el_card)

        layout.addStretch()

    def _setup_audio_tab(self):
        layout = QVBoxLayout(self.tab_audio)
        layout.setSpacing(14)
        layout.setContentsMargins(15, 15, 15, 15)

        # Voice settings
        v_card = QFrame()
        v_card.setProperty("card", "true")
        v_lay = QVBoxLayout(v_card)

        v_lbl = QLabel("សំឡេងនិយាយចម្បង (Default Voice - Edge-TTS):")
        v_lbl.setStyleSheet("font-weight: 600; color: #E5E7EB;")
        v_lay.addWidget(v_lbl)

        self.cmb_voice = QComboBox()
        for v_id, v_label in TTSService.VOICES.items():
            self.cmb_voice.addItem(v_label, v_id)
        v_lay.addWidget(self.cmb_voice)

        # Voice Rate
        r_lay = QHBoxLayout()
        r_lbl = QLabel("ល្បឿននិយាយ (Speech Speed):")
        r_lbl.setStyleSheet("color: #9CA3AF;")
        self.cmb_rate = QComboBox()
        self.cmb_rate.addItem("-6% (ធម្មជាតិ អប់រំ - ណែនាំ)", "-6%")
        self.cmb_rate.addItem("-10% (យឺត ជ្រៅ)", "-10%")
        self.cmb_rate.addItem("-4% (និទានរឿង)", "-4%")
        self.cmb_rate.addItem("+0% (ធម្មតា)", "+0%")
        self.cmb_rate.addItem("+10% (លឿន)", "+10%")
        r_lay.addWidget(r_lbl)
        r_lay.addWidget(self.cmb_rate)
        v_lay.addLayout(r_lay)

        # Voice Pitch
        p_lay = QHBoxLayout()
        p_lbl = QLabel("កម្រិតសម្លេង (Voice Pitch / Depth):")
        p_lbl.setStyleSheet("color: #9CA3AF;")
        self.cmb_pitch = QComboBox()
        self.cmb_pitch.addItem("-2Hz (សំឡេងកក់ក្តៅ/ជ្រៅ - ណែនាំ)", "-2Hz")
        self.cmb_pitch.addItem("-4Hz (សំឡេងធ្ងន់ខ្លាំង)", "-4Hz")
        self.cmb_pitch.addItem("+0Hz (ធម្មតា)", "+0Hz")
        self.cmb_pitch.addItem("+2Hz (ស្រាល/ខ្ពស់)", "+2Hz")
        p_lay.addWidget(p_lbl)
        p_lay.addWidget(self.cmb_pitch)
        v_lay.addLayout(p_lay)
        layout.addWidget(v_card)

        # Image generator settings
        i_card = QFrame()
        i_card.setProperty("card", "true")
        i_lay = QVBoxLayout(i_card)

        i_lbl = QLabel("ម៉ូឌែលរូបភាព (Image Model - Pollinations):")
        i_lbl.setStyleSheet("font-weight: 600; color: #E5E7EB;")
        i_lay.addWidget(i_lbl)

        self.cmb_img_model = QComboBox()
        self.cmb_img_model.addItem("FLUX (គុណភាពល្អបំផុត - ណែនាំ)", "flux")
        self.cmb_img_model.addItem("Turbo (លឿន)", "turbo")
        i_lay.addWidget(self.cmb_img_model)

        self.chk_enhance_prompts = QCheckBox("បន្ថែម Style Keywords ដោយស្វ័យប្រវត្តិ (Auto-Enhance Prompts)")
        self.chk_enhance_prompts.setChecked(True)
        i_lay.addWidget(self.chk_enhance_prompts)
        layout.addWidget(i_card)

        layout.addStretch()

    def _setup_video_tab(self):
        layout = QVBoxLayout(self.tab_video)
        layout.setSpacing(14)
        layout.setContentsMargins(15, 15, 15, 15)

        # FFmpeg status card
        f_card = QFrame()
        f_card.setProperty("card", "true")
        f_lay = QVBoxLayout(f_card)

        f_lbl = QLabel("FFmpeg Engine Status:")
        f_lbl.setStyleSheet("font-weight: 600; color: #E5E7EB;")
        f_lay.addWidget(f_lbl)

        ffmpeg_path = settings.get_ffmpeg_path()
        if os.path.exists(ffmpeg_path):
            self.lbl_ffmpeg_status = QLabel(f"រកឃើញ FFmpeg រួចរាល់:\n{ffmpeg_path}")
            self.lbl_ffmpeg_status.setStyleSheet("color: #6EE7B7; font-size: 12px;")
        else:
            self.lbl_ffmpeg_status = QLabel("មិនទាន់រកឃើញ FFmpeg ទេ")
            self.lbl_ffmpeg_status.setStyleSheet("color: #F87171; font-size: 12px;")
        f_lay.addWidget(self.lbl_ffmpeg_status)
        layout.addWidget(f_card)

        # Subtitles Settings
        s_card = QFrame()
        s_card.setProperty("card", "true")
        s_lay = QVBoxLayout(s_card)

        self.chk_subtitles = QCheckBox("ដាក់អក្សររត់ស្វ័យប្រវត្តិក្នងវីដេអូ (Auto Subtitles)")
        self.chk_subtitles.setChecked(True)
        s_lay.addWidget(self.chk_subtitles)

        f_name_lay = QHBoxLayout()
        fn_lbl = QLabel("ពុម្ពអក្សរ (Font Family):")
        self.txt_font_name = QLineEdit()
        self.txt_font_name.setText(settings.get("subtitle_font", "Kantumruy Pro"))
        f_name_lay.addWidget(fn_lbl)
        f_name_lay.addWidget(self.txt_font_name)
        s_lay.addLayout(f_name_lay)
        layout.addWidget(s_card)

        # Output Folder Card
        o_card = QFrame()
        o_card.setProperty("card", "true")
        o_lay = QVBoxLayout(o_card)

        o_lbl = QLabel("ថតរក្សាទុកវីដេអូសម្រេច (Output Directory):")
        o_lbl.setStyleSheet("font-weight: 600; color: #E5E7EB;")
        o_lay.addWidget(o_lbl)

        o_in_lay = QHBoxLayout()
        self.txt_output_dir = QLineEdit()
        self.txt_output_dir.setText(settings.get_output_dir())
        o_in_lay.addWidget(self.txt_output_dir)

        btn_browse_out = QPushButton("ជ្រើសរើស...")
        btn_browse_out.clicked.connect(self._browse_output_dir)
        o_in_lay.addWidget(btn_browse_out)
        o_lay.addLayout(o_in_lay)
        layout.addWidget(o_card)

        layout.addStretch()

    def _toggle_echo(self, line_edit: QLineEdit, btn: QPushButton):
        if line_edit.echoMode() == QLineEdit.Password:
            line_edit.setEchoMode(QLineEdit.Normal)
            btn.setIcon(get_icon("eye-off", "#9CA3AF", 16))
        else:
            line_edit.setEchoMode(QLineEdit.Password)
            btn.setIcon(get_icon("eye", "#9CA3AF", 16))

    def _browse_output_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "ជ្រើសរើស Folder សម្រាប់ Save វីដេអូ", self.txt_output_dir.text())
        if folder:
            self.txt_output_dir.setText(folder)

    def _test_gemini(self):
        key = self.txt_gemini_key.text().strip()
        if not key:
            self.lbl_gemini_status.setText("សូមបញ្ចូល Gemini API Key ជាមុនសិន!")
            self.lbl_gemini_status.setStyleSheet("color: #F87171;")
            return

        self.lbl_gemini_status.setText("កំពុងតេស្តភ្ជាប់ទៅកាន់ Google Gemini...")
        self.lbl_gemini_status.setStyleSheet("color: #FBBF24;")
        self.btn_test_gemini.setEnabled(False)

        # Run test asynchronously in background thread to avoid freezing UI
        self.gemini_test_worker = ApiTestWorker("gemini", key)
        self.gemini_test_worker.result_ready.connect(self._on_gemini_test_result)
        self.gemini_test_worker.start()

    def _on_gemini_test_result(self, ok: bool, msg: str):
        self.btn_test_gemini.setEnabled(True)
        if ok:
            self.lbl_gemini_status.setText(f"{msg}")
            self.lbl_gemini_status.setStyleSheet("color: #6EE7B7; font-weight: bold;")
        else:
            self.lbl_gemini_status.setText(f"{msg}")
            self.lbl_gemini_status.setStyleSheet("color: #F87171;")

    def _test_groq(self):
        key = self.txt_groq_key.text().strip()
        if not key:
            self.lbl_groq_status.setText("សូមបញ្ចូល Groq API Key ជាមុនសិន!")
            self.lbl_groq_status.setStyleSheet("color: #F87171;")
            return

        self.lbl_groq_status.setText("កំពុងតេស្តភ្ជាប់ទៅកាន់ Groq...")
        self.lbl_groq_status.setStyleSheet("color: #FBBF24;")
        self.btn_test_groq.setEnabled(False)

        # Run test asynchronously in background thread to avoid freezing UI
        self.groq_test_worker = ApiTestWorker("groq", key)
        self.groq_test_worker.result_ready.connect(self._on_groq_test_result)
        self.groq_test_worker.start()

    def _on_groq_test_result(self, ok: bool, msg: str):
        self.btn_test_groq.setEnabled(True)
        if ok:
            self.lbl_groq_status.setText(f"{msg}")
            self.lbl_groq_status.setStyleSheet("color: #6EE7B7; font-weight: bold;")
        else:
            self.lbl_groq_status.setText(f"{msg}")
            self.lbl_groq_status.setStyleSheet("color: #F87171;")

    def _load_values(self):
        self.txt_gemini_key.setText(settings.get("gemini_api_key", ""))
        self.txt_groq_key.setText(settings.get("groq_api_key", ""))
        self.txt_elevenlabs_key.setText(settings.get("elevenlabs_api_key", ""))

        cur_voice = settings.get("default_voice", "km-KH-PisethNeural")
        idx = self.cmb_voice.findData(cur_voice)
        if idx >= 0:
            self.cmb_voice.setCurrentIndex(idx)

        cur_model = settings.get("image_model", "flux")
        idx_m = self.cmb_img_model.findData(cur_model)
        if idx_m >= 0:
            self.cmb_img_model.setCurrentIndex(idx_m)

        cur_rate = settings.get("voice_rate", "-6%")
        idx_r = self.cmb_rate.findData(cur_rate)
        if idx_r >= 0:
            self.cmb_rate.setCurrentIndex(idx_r)

        cur_pitch = settings.get("voice_pitch", "-2Hz")
        idx_p = self.cmb_pitch.findData(cur_pitch)
        if idx_p >= 0:
            self.cmb_pitch.setCurrentIndex(idx_p)

        self.chk_subtitles.setChecked(settings.get("subtitle_enabled", True))
        self.chk_enhance_prompts.setChecked(settings.get("enhance_prompts", True))

    def _save_and_close(self):
        settings.set("gemini_api_key", self.txt_gemini_key.text().strip())
        settings.set("groq_api_key", self.txt_groq_key.text().strip())
        settings.set("elevenlabs_api_key", self.txt_elevenlabs_key.text().strip())
        settings.set("default_voice", self.cmb_voice.currentData())
        settings.set("image_model", self.cmb_img_model.currentData())
        settings.set("subtitle_enabled", self.chk_subtitles.isChecked())
        settings.set("subtitle_font", self.txt_font_name.text().strip())
        settings.set("output_dir", self.txt_output_dir.text().strip())
        settings.set("enhance_prompts", self.chk_enhance_prompts.isChecked())

        settings.set("voice_rate", self.cmb_rate.currentData() or "-6%")
        settings.set("voice_pitch", self.cmb_pitch.currentData() or "-2Hz")

        QMessageBox.information(self, "ជោគជ័យ", "ការកំណត់ត្រូវបានរក្សាទុកដោយជោគជ័យ!")
        self.accept()
