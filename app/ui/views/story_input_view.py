import os
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, 
    QPushButton, QComboBox, QSpinBox, QProgressBar, QFrame, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt, Signal, QSize
from app.core.settings import settings
from app.services.tts_service import TTSService
from app.workers.full_auto_worker import FullAutoWorker
from app.workers.story_worker import StoryWorker
from app.ui.icons import get_icon

logger = logging.getLogger("AIAnimationStudio.StoryInputView")

class StoryInputView(QWidget):
    """View for initiating AI story generation matching aitest.mp4 style."""

    # Signals to parent window
    open_studio = Signal(int)       # (project_id)
    video_ready = Signal(int, str)  # (project_id, final_video_path)

    DEFAULT_STYLE = "aitest_style"

    TOPIC_SUGGESTIONS = [
        ("រឿងបើកហាងកាហ្វេខាត", "ចូលអ្នកនិយាយពីរឿងបរាជ័យនៃការបើកហាងកាហ្វេខាតបង់លុយ និងមេរៀនសំខាន់ៗដែលគួរដឹងមុនរកស៊ី"),
        ("មនុស្សស្ងៀមស្ងាត់ (Introvert)", "ចូលអ្នកនិយាយពីមនុស្សដែលស្ងៀមស្ងាត់ តើពួកគេមានលក្ខណៈពិសេសអ្វីខ្លះ ហេតុអ្វីពួកគេស្ងប់ស្ងាត់ និងពិភពផ្លូវចិត្តខាងក្នុងរបស់ពួកគេ"),
        ("របៀបសន្សំលុយ", "ចូលអ្នកចែករំលែកគន្លឹះចាត់ចែងលុយកាក់ និងទម្លាប់សន្សំលុយរបស់មនុស្សជោគជ័យ"),
        ("៥ កំហុសក្នុងការរកស៊ី", "ចូលអ្នកបកស្រាយពីកំហុសធ្ងន់ធ្ងរទាំង ៥ ដែលអ្នកចាប់ផ្ដើមរកស៊ីថ្មីថ្មោងតែងតែជួបប្រទះ"),
        ("ចិត្តវិទ្យានៃភាពឯកោ", "ចូលអ្នកវិភាគចិត្តវិទ្យានៃអារម្មណ៍ឯកោ ហេតុអ្វីមនុស្សមានអារម្មណ៍ឯកោទោះនៅកណ្តាលចំណោមមនុស្ស និងវិធីព្យាបាលចិត្ត"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 20, 25, 20)
        main_layout.setSpacing(16)

        # Welcome Card
        header_card = QFrame()
        header_card.setProperty("card", "true")
        h_lay = QVBoxLayout(header_card)
        
        t_row = QHBoxLayout()
        ic = QPushButton()
        ic.setIcon(get_icon("sparkles", "#D1D5DB", 20))
        ic.setIconSize(QSize(20, 20))
        ic.setStyleSheet("border: none; background: transparent; padding: 0;")
        title = QLabel("បង្កើតវីដេអូ aitest.mp4 (TalkMoney Style) ដោយ AI ស្វ័យប្រវត្តិ")
        title.setStyleSheet("font-size: 17px; font-weight: bold; color: #F3F4F6;")
        t_row.addWidget(ic)
        t_row.addWidget(title)
        t_row.addStretch()
        h_lay.addLayout(t_row)

        subtitle = QLabel("បញ្ចូលប្រធានបទ ឬសាច់រឿងដែលចង់បកស្រាយ AI នឹងតែងសាច់រឿង បញ្ចេញសំឡេងខ្មែរ បង្កើតរូបភាព និង Render វីដេអូ Ken Burns Motion ពេញលេញ។")
        subtitle.setStyleSheet("color: #9CA3AF; font-size: 13px; margin-top: 4px;")
        h_lay.addWidget(subtitle)
        main_layout.addWidget(header_card)

        # Topic Input Card
        topic_card = QFrame()
        topic_card.setProperty("card", "true")
        t_lay = QVBoxLayout(topic_card)

        t_lbl = QLabel("ប្រធានបទ ឬសាច់រឿងដែលចង់និយាយ (Topic / Story Script):")
        t_lbl.setStyleSheet("font-weight: 600; font-size: 13px; color: #E5E7EB;")
        t_lay.addWidget(t_lbl)

        self.txt_topic = QTextEdit()
        self.txt_topic.setMinimumHeight(95)
        self.txt_topic.setPlaceholderText("ឧទាហរណ៍៖ រឿងបើកហាងកាហ្វេខាតបង់លុយ និងមេរៀនសំខាន់ៗដែលគួរដឹងមុនរកស៊ី...")
        t_lay.addWidget(self.txt_topic)

        # Dynamic Quick Suggestions Row
        sug_row = QHBoxLayout()
        sug_row.setSpacing(8)
        sug_lbl = QLabel("គំនិតរហ័ស:")
        sug_lbl.setStyleSheet("color: #6B7280; font-size: 12px; font-weight: 600;")
        sug_row.addWidget(sug_lbl)

        for title, full_prompt in self.TOPIC_SUGGESTIONS:
            btn_s = QPushButton(title)
            btn_s.setStyleSheet("background-color: #22252B; border: 1px solid #323640; color: #D1D5DB; font-size: 11px; padding: 4px 8px; border-radius: 4px;")
            btn_s.clicked.connect(lambda _, txt=full_prompt: self.txt_topic.setPlainText(txt))
            sug_row.addWidget(btn_s)
        sug_row.addStretch()
        t_lay.addLayout(sug_row)

        main_layout.addWidget(topic_card)

        # Parameters Grid Card (4 Columns, No Clutter)
        param_card = QFrame()
        param_card.setProperty("card", "true")
        p_lay = QHBoxLayout(param_card)
        p_lay.setSpacing(18)

        # 1. Animation Motion Mode
        mot_box = QVBoxLayout()
        mot_lbl = QLabel("ចលនា Camera (Motion):")
        mot_lbl.setStyleSheet("font-weight: 600; color: #D1D5DB; font-size: 12px;")
        self.cmb_motion = QComboBox()
        self.cmb_motion.addItem(get_icon("sparkles", "#F59E0B", 16), "Auto (ឆ្លាតវៃស្វ័យប្រវត្តិតាមសាច់រឿង)", "auto")
        self.cmb_motion.addItem(get_icon("zoom-in", "#60A5FA", 16), "Zoom In (ពង្រីកចូលសន្សឹមៗ)", "zoom_in")
        self.cmb_motion.addItem(get_icon("zoom-out", "#60A5FA", 16), "Zoom Out (បង្រួមចេញសន្សឹមៗ)", "zoom_out")
        self.cmb_motion.addItem(get_icon("arrow-left", "#A78BFA", 16), "Pan Left (កាមេរ៉ារំកិលឆ្វេង)", "pan_left")
        self.cmb_motion.addItem(get_icon("arrow-right", "#A78BFA", 16), "Pan Right (កាមេរ៉ារំកិលស្តាំ)", "pan_right")
        self.cmb_motion.addItem(get_icon("square", "#9CA3AF", 16), "Steady / Cut (ប្តូរប្លង់កាត់តធម្មតា)", "steady")
        mot_box.addWidget(mot_lbl)
        mot_box.addWidget(self.cmb_motion)
        p_lay.addLayout(mot_box)

        # 2. Aspect Ratio (16:9 Widescreen default for aitest.mp4)
        ar_box = QVBoxLayout()
        ar_lbl = QLabel("ទំហំវីដេអូ (Aspect Ratio):")
        ar_lbl.setStyleSheet("font-weight: 600; color: #D1D5DB; font-size: 12px;")
        self.cmb_ratio = QComboBox()
        self.cmb_ratio.addItem(get_icon("monitor", "#60A5FA", 16), "ផ្ដេក 16:9 (YouTube Widescreen - ដូច aitest.mp4)", "16:9")
        self.cmb_ratio.addItem(get_icon("smartphone", "#A78BFA", 16), "បញ្ឈរ 9:16 (TikTok, Reels, Shorts)", "9:16")
        ar_box.addWidget(ar_lbl)
        ar_box.addWidget(self.cmb_ratio)
        p_lay.addLayout(ar_box)

        # 3. Voice & Voice Cloning
        v_box = QVBoxLayout()
        v_lbl = QLabel("សំឡេង & Clone (Voice):")
        v_lbl.setStyleSheet("font-weight: 600; color: #D1D5DB; font-size: 12px;")
        self.cmb_voice = QComboBox()
        self.cmb_voice.addItem(get_icon("volume", "#60A5FA", 16), "ពិសិដ្ឋ Piseth (ប្រុស - Edge-TTS Free)", "km-KH-PisethNeural")
        self.cmb_voice.addItem(get_icon("volume", "#F472B6", 16), "ស្រីមុំ Sreymom (ស្រី - Edge-TTS Free)", "km-KH-SreymomNeural")
        self.cmb_voice.addItem(get_icon("mic", "#34D399", 16), "Voice Clone (ក្លូនសំឡេង / ElevenLabs)", "cloned_voice")
        self.cmb_voice.currentIndexChanged.connect(self._on_voice_changed)
        v_box.addWidget(v_lbl)
        v_box.addWidget(self.cmb_voice)

        # Clone sample selector row
        self.clone_row = QWidget()
        cl_lay = QHBoxLayout(self.clone_row)
        cl_lay.setContentsMargins(0, 0, 0, 0)
        self.btn_pick_sample = QPushButton("  ជ្រើសសំឡេងគំរូ (.mp3/.wav)")
        self.btn_pick_sample.setIcon(get_icon("folder", "#60A5FA", 14))
        self.btn_pick_sample.setStyleSheet("font-size: 10px; padding: 2px 6px; background-color: #22252B; border: 1px solid #363B45; color: #60A5FA; border-radius: 4px;")
        self.btn_pick_sample.clicked.connect(self._pick_voice_sample)
        cl_lay.addWidget(self.btn_pick_sample)

        self.lbl_sample_status = QLabel("")
        self.lbl_sample_status.setStyleSheet("color: #34D399; font-size: 10px;")
        sample = settings.get("custom_voice_sample_path", "")
        if sample and os.path.exists(sample):
            self.lbl_sample_status.setText(os.path.basename(sample))
        cl_lay.addWidget(self.lbl_sample_status)
        cl_lay.addStretch()
        v_box.addWidget(self.clone_row)
        p_lay.addLayout(v_box)

        # 4. Scene Count & Duration
        sc_box = QVBoxLayout()
        sc_lbl = QLabel("ចំនួន Scene (ប្រវែងវីដេអូ):")
        sc_lbl.setStyleSheet("font-weight: 600; color: #D1D5DB; font-size: 12px;")
        self.spn_scenes = QSpinBox()
        self.spn_scenes.setRange(2, 35)
        self.spn_scenes.setValue(6)
        sc_box.addWidget(sc_lbl)
        sc_box.addWidget(self.spn_scenes)

        dur_presets = QHBoxLayout()
        dur_presets.setSpacing(4)
        for label, count in [("1m (6)", 6), ("3m (15)", 15), ("5m (25)", 25), ("6m (30)", 30)]:
            btn_dur = QPushButton(label)
            btn_dur.setStyleSheet("font-size: 10px; padding: 2px 4px; background-color: #262930; border: 1px solid #363B45; color: #9CA3AF;")
            btn_dur.clicked.connect(lambda _, c=count: self.spn_scenes.setValue(c))
            dur_presets.addWidget(btn_dur)
        sc_box.addLayout(dur_presets)
        p_lay.addLayout(sc_box)

        main_layout.addWidget(param_card)

        # Progress Section
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #9CA3AF; font-weight: 600;")
        self.lbl_status.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.lbl_status)

        # Action Buttons Layout
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(14)

        self.btn_script_only = QPushButton("  បង្កើតតែសាច់រឿងសិន (Studio Mode)")
        self.btn_script_only.setIcon(get_icon("edit", "#9CA3AF", 16))
        self.btn_script_only.setIconSize(QSize(16, 16))
        self.btn_script_only.setMinimumHeight(44)
        self.btn_script_only.clicked.connect(self._start_script_only)
        btn_layout.addWidget(self.btn_script_only)

        self.btn_full_auto = QPushButton("  បង្កើតវីដេអូ Auto ភ្លាមៗ (1-Click Full Video)")
        self.btn_full_auto.setIcon(get_icon("bolt", "#F9FAFB", 18))
        self.btn_full_auto.setIconSize(QSize(18, 18))
        self.btn_full_auto.setProperty("accent", "primary")
        self.btn_full_auto.setMinimumHeight(44)
        self.btn_full_auto.clicked.connect(self._start_full_auto)
        btn_layout.addWidget(self.btn_full_auto)

        main_layout.addLayout(btn_layout)
        main_layout.addStretch()

    def _validate_inputs(self) -> bool:
        topic = self.txt_topic.toPlainText().strip()
        if not topic:
            QMessageBox.warning(self, "ខ្វះទិន្នន័យ", "សូមបញ្ចូលប្រធានបទ ឬសាច់រឿងជាមុនសិន!")
            return False
        return True

    def _pick_voice_sample(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "ជ្រើសរើស File សំឡេងគំរូសម្រាប់ Clone", "", "Audio Files (*.mp3 *.wav *.m4a *.aac)"
        )
        if file_path:
            ok, msg = TTSService.clone_voice_sample(file_path)
            fname = os.path.basename(file_path)
            self.lbl_sample_status.setText(fname)
            idx = self.cmb_voice.findData("cloned_voice")
            if idx >= 0:
                self.cmb_voice.setCurrentIndex(idx)
            QMessageBox.information(self, "Clone សំឡេង", msg)

    def _on_voice_changed(self):
        v = self.cmb_voice.currentData()
        if v == "cloned_voice":
            sample = settings.get("custom_voice_sample_path", "")
            if sample and os.path.exists(sample):
                self.lbl_sample_status.setText(os.path.basename(sample))
            else:
                self.lbl_sample_status.setText("មិនទាន់ជ្រើស File គំរូ")

    def _start_full_auto(self):
        if not self._validate_inputs():
            return

        topic = self.txt_topic.toPlainText().strip()
        num_scenes = self.spn_scenes.value()
        style = self.DEFAULT_STYLE
        ratio = self.cmb_ratio.currentData()
        voice = self.cmb_voice.currentData()
        motion = self.cmb_motion.currentData()

        self._set_ui_busy(True)
        self.progress_bar.setValue(0)
        self.lbl_status.setText("កំពុងចាប់ផ្តើមបង្កើតវីដេអូ...")

        self.worker = FullAutoWorker(topic, num_scenes, style, ratio, voice, motion_mode=motion)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_full_auto_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _start_script_only(self):
        if not self._validate_inputs():
            return

        topic = self.txt_topic.toPlainText().strip()
        num_scenes = self.spn_scenes.value()
        style = self.DEFAULT_STYLE
        ratio = self.cmb_ratio.currentData()
        voice = self.cmb_voice.currentData()
        motion = self.cmb_motion.currentData()

        self._set_ui_busy(True)
        self.progress_bar.setValue(20)
        self.lbl_status.setText("AI កំពុងតែងសាច់រឿង និងប្លង់ Scene...")

        from app.core.database import db

        def on_story_ready(story_data):
            title = story_data.get("title", topic)
            raw_scenes = story_data.get("scenes", [])
            proj_id = db.create_project(title, topic, style, ratio, voice)
            auto_motions = ["zoom_in", "pan_left", "zoom_out", "steady", "zoom_in", "pan_right"]
            for i, s in enumerate(raw_scenes):
                sc_motion = s.get("camera_motion")
                if not sc_motion or sc_motion == "auto":
                    sc_motion = auto_motions[i % len(auto_motions)] if motion == "auto" else (motion or "zoom_in")
                db.add_scene(
                    proj_id, 
                    s.get("scene_number", i + 1), 
                    s.get("narration_km", ""), 
                    s.get("image_prompt_en", ""),
                    sc_motion
                )
            self._set_ui_busy(False)
            self.open_studio.emit(proj_id)

        self.worker = StoryWorker(topic, num_scenes, style)
        self.worker.finished.connect(on_story_ready)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, pct: int, msg: str):
        self.progress_bar.setValue(pct)
        self.lbl_status.setText(msg)

    def _on_full_auto_finished(self, project_id: int, final_video_path: str):
        self._set_ui_busy(False)
        self.lbl_status.setText("វីដេអូបង្កើតជោគជ័យ!")
        self.video_ready.emit(project_id, final_video_path)

    def _on_error(self, err_msg: str):
        self._set_ui_busy(False)
        QMessageBox.critical(self, "បញ្ហា", f"មានបញ្ហាអំឡុងពេលដំណើរការ៖\n{err_msg}")

    def _set_ui_busy(self, busy: bool):
        self.btn_full_auto.setEnabled(not busy)
        self.btn_script_only.setEnabled(not busy)
        self.progress_bar.setVisible(busy)
        self.lbl_status.setVisible(busy)
