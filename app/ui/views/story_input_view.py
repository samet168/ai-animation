import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, 
    QPushButton, QComboBox, QSpinBox, QProgressBar, QFrame, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QSize
from app.core.settings import settings
from app.services.image_service import ImageService
from app.services.tts_service import TTSService
from app.workers.full_auto_worker import FullAutoWorker
from app.workers.story_worker import StoryWorker
from app.ui.icons import get_icon

logger = logging.getLogger("AIAnimationStudio.StoryInputView")

class StoryInputView(QWidget):
    """View for initiating AI story generation (Full Auto or Script first)."""

    # Signals to parent window
    open_studio = Signal(int)       # (project_id)
    video_ready = Signal(int, str)  # (project_id, final_video_path)

    STYLES = [
        ("3d_pixar", "3D Disney Pixar Animation"),
        ("whiteboard_doodle", "តុក្កតាគូសដៃ Whiteboard Doodle (ពេញនិយម Free រហូត)"),
        ("whiteboard_color", "គូសដៃចម្រុះពណ៌ Whiteboard Color Sketch"),
        ("anime_manga", "2D Anime / Manga Style"),
        ("comic_book", "Comic Book / Graphic Novel"),
        ("cinematic_realistic", "Cinematic Realistic Movie"),
        ("chibi_3d", "Cute Chibi 3D Miniature"),
        ("watercolor", "Watercolor Fairy Tale Storybook"),
    ]

    GENRES = [
        ("psychology", "🧠 ចិត្តវិទ្យា & អារម្មណ៍ផ្លូវចិត្ត (Psychology & Emotions)"),
        ("story", "📖 រឿងនិទាន & ដំណើរផ្សងព្រេង (Storytelling & Tales)"),
        ("philosophy", "💡 ទស្សនវិជ្ជាជីវិត & គំនិតជោគជ័យ (Philosophy & Motivation)"),
        ("education", "🎓 ចំណេះដឹងទូទៅ & ការពិតប្លែកៗ (Education & Facts)"),
    ]

    GENRE_SUGGESTIONS = {
        "psychology": [
            ("មនុស្សស្ងៀមស្ងាត់ (Introvert)", "ចូលអ្នកនិយាយពីមនុស្សដែលស្ងៀមស្ងាត់ តើពួកគេមានលក្ខណៈពិសេសអ្វីខ្លះ ហេតុអ្វីពួកគេស្ងប់ស្ងាត់ និងពិភពផ្លូវចិត្តខាងក្នុងរបស់ពួកគេ"),
            ("ចិត្តវិទ្យានៃភាពឯកោ", "ចូលអ្នកវិភាគចិត្តវិទ្យានៃអារម្មណ៍ឯកោ ហេតុអ្វីមនុស្សមានអារម្មណ៍ឯកោទោះនៅកណ្តាលចំណោមមនុស្ស និងវិធីព្យាបាលចិត្ត"),
            ("មនុស្សគិតច្រើន (Overthinking)", "ចូលអ្នកនិយាយពីចិត្តសាស្ត្ររបស់មនុស្សដែលចូលចិត្តគិតច្រើន ផលប៉ះពាល់ផ្លូវចិត្ត និងវិធីរំដោះខួរក្បាលឱ្យមានសន្តិភាព"),
            ("ហេតុអ្វីមនុស្សឆ្លាតចូលចិត្តនៅស្ងៀម?", "ចូលអ្នកបកស្រាយទស្សនវិជ្ជា និងចិត្តវិទ្យា៖ ហេតុអ្វីបានជាមនុស្សឆ្លាតវៃចូលចិត្តភាពស្ងប់ស្ងាត់ និងនៅម្នាក់ឯង?")
        ],
        "story": [
            ("រឿងកូនទន្សាយ និងអណ្ដើក", "រឿងនិទានកូនទន្សាយឈ្លាសវៃ និងអណ្ដើកប្រណាំងគ្នា ក្នុងព្រៃបុរាណដែលពោរពេញដោយផ្កាចម្រុះពណ៌"),
            ("ដំណើរផ្សងព្រេងអង្គរវត្ត", "ដំណើរផ្សងព្រេងដ៏អស្ចារ្យរបស់កុមារាក្លាហាន ក្នុងការស្វែងរកកំណប់អាថ៌កំបាំងនៅប្រាសាទអង្គរវត្ត"),
            ("រឿងបក្សីមាស និងដើមឈើវេទមន្ត", "រឿងនិទានបក្សីមាស និងដើមឈើវេទមន្តដែលផ្ដល់សេចក្តីសុខដល់មនុស្សគ្រប់គ្នា"),
            ("កុមារក្លាហានជួយសង្គ្រោះភូមិ", "រឿងកុមារាក្លាហានដែលហ៊ានតស៊ូជួយសង្គ្រោះភូមិពីគ្រោះធម្មជាតិដោយក្ដីមេត្តា")
        ],
        "philosophy": [
            ("ទម្លាប់មនុស្សជោគជ័យ", "ច្បាប់នៃការអភិវឌ្ឍខ្លួន និងទម្លាប់សំខាន់ៗទាំង ៥ ដែលជួយឱ្យមនុស្សសម្រេចគោលដៅធំៗក្នុងជីវិត"),
            ("តម្លៃនៃពេលវេលា", "ទស្សនវិជ្ជាស៊ីជម្រៅស្តីពីតម្លៃនៃពេលវេលា និងការមិនខ្ជះខ្ជាយជីវិតជាមួយរឿងឥតប្រយោជន៍"),
            ("សិល្បៈនៃការអត់ធ្មត់", "អំណាចនៃការអត់ធ្មត់ និងភាពស្ងប់ស្ងាត់ក្នុងការដោះស្រាយបញ្ហាធំៗក្នុងជីវិត"),
            ("ការយកឈ្នះភាពភ័យខ្លាច", "វិធីសាស្ត្រផ្លូវចិត្តក្នុងការយកឈ្នះភាពភ័យខ្លាច និងការកសាងទំនុកចិត្តលើខ្លួនឯង")
        ],
        "education": [
            ("អាថ៌កំបាំងចក្រវាល", "ការពិតដ៏អស្ចារ្យទាំង ៥ អំពីចក្រវាល និងផ្កាយដែលមនុស្សភាគច្រើនមិនធ្លាប់បានដឹង"),
            ("ប្រវត្តិបុរាណវិទ្យាខ្មែរ", "ចំណេះដឹងទូទៅអំពីប្រវត្តិសាស្ត្រ និងភាពរុងរឿងនៃអារ្យធម៌អង្គរដ៏អស្ចារ្យ"),
            ("បច្ចេកវិទ្យា AI អនាគត", "របៀបដែលបច្ចេកវិទ្យាបញ្ញាសិប្បនិម្មិត AI កំពុងផ្លាស់ប្តូរពិភពលោក និងការងារមនុស្ស"),
            ("សុខភាពខួរក្បាល & ការចងចាំ", "គន្លឹះវិទ្យាសាស្ត្រក្នុងការថែរក្សាសុខភាពខួរក្បាល និងបង្កើនការចងចាំឱ្យកាន់តែមុតស្រួច")
        ]
    }

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
        title = QLabel("បង្កើតវីដេអូ Animation & សំឡេងដោយ AI ស្វ័យប្រវត្តិ")
        title.setStyleSheet("font-size: 17px; font-weight: bold; color: #F3F4F6;")
        t_row.addWidget(ic)
        t_row.addWidget(title)
        t_row.addStretch()
        h_lay.addLayout(t_row)

        subtitle = QLabel("បញ្ចូលប្រធានបទ ឬសាច់រឿងសង្ខេប AI នឹងតែងរឿង បញ្ចេញសំឡេងខ្មែរ បង្កើតរូបភាព និង Render វីដេអូមានចលនាពេញលេញ។")
        subtitle.setStyleSheet("color: #9CA3AF; font-size: 13px; margin-top: 4px;")
        h_lay.addWidget(subtitle)
        main_layout.addWidget(header_card)

        # Topic Input Card
        topic_card = QFrame()
        topic_card.setProperty("card", "true")
        t_lay = QVBoxLayout(topic_card)

        genre_row = QHBoxLayout()
        t_lbl = QLabel("ប្រធានបទ ឬគំនិតសាច់រឿង (Story Topic / Idea):")
        t_lbl.setStyleSheet("font-weight: 600; font-size: 13px; color: #E5E7EB;")
        genre_row.addWidget(t_lbl)
        genre_row.addStretch()

        g_lbl = QLabel("ប្រភេទមាតិកា:")
        g_lbl.setStyleSheet("color: #9CA3AF; font-size: 12px; font-weight: 600;")
        genre_row.addWidget(g_lbl)

        self.cmb_genre = QComboBox()
        for g_k, g_name in self.GENRES:
            self.cmb_genre.addItem(g_name, g_k)
        self.cmb_genre.currentIndexChanged.connect(self._on_genre_changed)
        genre_row.addWidget(self.cmb_genre)
        t_lay.addLayout(genre_row)

        self.txt_topic = QTextEdit()
        self.txt_topic.setMinimumHeight(90)
        t_lay.addWidget(self.txt_topic)

        # Dynamic Suggestions Lay
        self.sug_container = QWidget()
        self.sug_lay = QHBoxLayout(self.sug_container)
        self.sug_lay.setContentsMargins(0, 0, 0, 0)
        t_lay.addWidget(self.sug_container)
        self._update_suggestions()

        main_layout.addWidget(topic_card)

        # Parameters Grid Card
        param_card = QFrame()
        param_card.setProperty("card", "true")
        p_lay = QHBoxLayout(param_card)
        p_lay.setSpacing(18)

        # 1. Art Style
        st_box = QVBoxLayout()
        st_lbl = QLabel("រចនាប័ទ្មរូបភាព (Art Style):")
        st_lbl.setStyleSheet("font-weight: 600; color: #D1D5DB; font-size: 12px;")
        self.cmb_style = QComboBox()
        for k, name in self.STYLES:
            self.cmb_style.addItem(name, k)
        self.cmb_style.currentIndexChanged.connect(self._on_style_changed)
        st_box.addWidget(st_lbl)
        st_box.addWidget(self.cmb_style)
        p_lay.addLayout(st_box)

        # 2. Animation Motion Mode
        mot_box = QVBoxLayout()
        mot_lbl = QLabel("ចលនា Animation (Motion):")
        mot_lbl.setStyleSheet("font-weight: 600; color: #D1D5DB; font-size: 12px;")
        self.cmb_motion = QComboBox()
        self.cmb_motion.addItem("Talking Character (តួអង្គនិយាយ & ព្រិចភ្នែក)", "talking")
        self.cmb_motion.addItem("Whiteboard Hand-Drawn (តុក្កតាគូសដៃ)", "whiteboard")
        self.cmb_motion.addItem("Cinematic Camera Motion (Zoom/Pan)", "cinematic")
        mot_box.addWidget(mot_lbl)
        mot_box.addWidget(self.cmb_motion)
        p_lay.addLayout(mot_box)

        # 3. Aspect Ratio
        ar_box = QVBoxLayout()
        ar_lbl = QLabel("ទំហំវីដេអូ (Aspect Ratio):")
        ar_lbl.setStyleSheet("font-weight: 600; color: #D1D5DB; font-size: 12px;")
        self.cmb_ratio = QComboBox()
        self.cmb_ratio.addItem("បញ្ឈរ 9:16 (TikTok, Reels, Shorts)", "9:16")
        self.cmb_ratio.addItem("ផ្ដេក 16:9 (YouTube Video)", "16:9")
        ar_box.addWidget(ar_lbl)
        ar_box.addWidget(self.cmb_ratio)
        p_lay.addLayout(ar_box)

        # 4. Voice & Tone
        v_box = QVBoxLayout()
        v_lbl = QLabel("សំឡេង AI (Edge-TTS):")
        v_lbl.setStyleSheet("font-weight: 600; color: #D1D5DB; font-size: 12px;")
        self.cmb_voice = QComboBox()
        for v_id, v_name in TTSService.VOICES.items():
            self.cmb_voice.addItem(v_name, v_id)
        v_box.addWidget(v_lbl)
        v_box.addWidget(self.cmb_voice)

        # Voice Tone / Mood
        t_lbl = QLabel("ទឹកដមសម្លេង (Voice Mood):")
        t_lbl.setStyleSheet("font-weight: 600; color: #9CA3AF; font-size: 11px; margin-top: 4px;")
        self.cmb_tone = QComboBox()
        self.cmb_tone.addItem("🧘 ទឹកដមអប់រំ & ចិត្តវិទ្យា (Calm & Deep - ណែនាំ)", "educational")
        self.cmb_tone.addItem("📖 ទឹកដមបែបនិទានរឿង (Storyteller)", "story")
        self.cmb_tone.addItem("⚡ ទឹកដមធម្មតា/រហ័ស (Standard)", "standard")
        v_box.addWidget(t_lbl)
        v_box.addWidget(self.cmb_tone)
        p_lay.addLayout(v_box)

        # 5. Scene Count & Duration
        sc_box = QVBoxLayout()
        sc_lbl = QLabel("ចំនួន Scene (ប្រវែងវីដេអូ):")
        sc_lbl.setStyleSheet("font-weight: 600; color: #D1D5DB; font-size: 12px;")
        self.spn_scenes = QSpinBox()
        self.spn_scenes.setRange(2, 35)
        self.spn_scenes.setValue(6)
        sc_box.addWidget(sc_lbl)
        sc_box.addWidget(self.spn_scenes)

        # Quick Duration Presets row
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

        key = settings.get("gemini_api_key", "").strip()
        groq = settings.get("groq_api_key", "").strip()
        if not key and not groq:
            QMessageBox.information(
                self, 
                "ត្រូវការ Gemini API Key", 
                "សូមចូលទៅកាន់ 'ការកំណត់ (Settings)' ដើម្បីបញ្ចូល Google Gemini API Key (Free) ជាមុនសិន!"
            )
            return False
        return True

    def _on_genre_changed(self):
        self._update_suggestions()

    def _update_suggestions(self):
        # Clear existing items
        while self.sug_lay.count() > 0:
            item = self.sug_lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        genre = self.cmb_genre.currentData() if hasattr(self, "cmb_genre") else "psychology"
        
        # Update placeholder
        if genre == "psychology":
            self.txt_topic.setPlaceholderText("ឧទាហរណ៍៖ ចូលអ្នកនិយាយពីមនុស្សដែលស្ងៀមស្ងាត់ តើពួកគេមានលក្ខណៈអ្វីខ្លះ និងហេតុអ្វីពួកគេស្ងប់ស្ងាត់បែបនេះ?...")
        elif genre == "philosophy":
            self.txt_topic.setPlaceholderText("ឧទាហរណ៍៖ ច្បាប់នៃការអភិវឌ្ឍខ្លួន និងទម្លាប់សំខាន់ៗទាំង ៥ ដែលជួយឱ្យមនុស្សជោគជ័យ...")
        elif genre == "education":
            self.txt_topic.setPlaceholderText("ឧទាហរណ៍៖ ការពិតដ៏អស្ចារ្យទាំង ៥ អំពីចក្រវាល និងបច្ចេកវិទ្យា AI អនាគត...")
        else:
            self.txt_topic.setPlaceholderText("ឧទាហរណ៍៖ រឿងនិទានកូនទន្សាយឈ្លាសវៃ និងអណ្ដើកប្រណាំងគ្នា ក្នុងព្រៃបុរាណ...")

        # Add label
        sug_lbl = QLabel("គំនិតរហ័ស:")
        sug_lbl.setStyleSheet("color: #6B7280; font-size: 12px;")
        self.sug_lay.addWidget(sug_lbl)

        sug_list = self.GENRE_SUGGESTIONS.get(genre, self.GENRE_SUGGESTIONS["psychology"])
        for title, full_prompt in sug_list:
            btn_s = QPushButton(title)
            btn_s.setStyleSheet("background-color: #22252B; border: 1px solid #323640; color: #D1D5DB; font-size: 11px; padding: 4px 8px; border-radius: 4px;")
            btn_s.clicked.connect(lambda _, txt=full_prompt: self.txt_topic.setPlainText(txt))
            self.sug_lay.addWidget(btn_s)
        self.sug_lay.addStretch()

    def _on_style_changed(self):
        style = self.cmb_style.currentData()
        if style and style.startswith("whiteboard"):
            idx = self.cmb_motion.findData("whiteboard")
            if idx >= 0:
                self.cmb_motion.setCurrentIndex(idx)
        else:
            idx = self.cmb_motion.findData("talking")
            if idx >= 0:
                self.cmb_motion.setCurrentIndex(idx)

    def _apply_tone_settings(self):
        tone = self.cmb_tone.currentData() if hasattr(self, "cmb_tone") else "educational"
        preset = TTSService.TONE_PRESETS.get(tone, TTSService.TONE_PRESETS["educational"])
        settings.set("voice_rate", preset["rate"])
        settings.set("voice_pitch", preset["pitch"])

    def _start_full_auto(self):
        if not self._validate_inputs():
            return

        self._apply_tone_settings()

        topic = self.txt_topic.toPlainText().strip()
        num_scenes = self.spn_scenes.value()
        style = self.cmb_style.currentData()
        ratio = self.cmb_ratio.currentData()
        voice = self.cmb_voice.currentData()
        motion = self.cmb_motion.currentData()
        genre = self.cmb_genre.currentData()

        self._set_ui_busy(True)
        self.progress_bar.setValue(0)
        self.lbl_status.setText("កំពុងចាប់ផ្តើម...")

        self.worker = FullAutoWorker(topic, num_scenes, style, ratio, voice, motion_mode=motion, genre=genre)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_full_auto_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _start_script_only(self):
        if not self._validate_inputs():
            return

        self._apply_tone_settings()

        topic = self.txt_topic.toPlainText().strip()
        num_scenes = self.spn_scenes.value()
        style = self.cmb_style.currentData()
        ratio = self.cmb_ratio.currentData()
        voice = self.cmb_voice.currentData()
        genre = self.cmb_genre.currentData()

        self._set_ui_busy(True)
        self.progress_bar.setValue(20)
        self.lbl_status.setText("AI កំពុងតែងសាច់រឿង និងប្លង់ Scene...")

        from app.core.database import db

        motion = self.cmb_motion.currentData()

        def on_story_ready(story_data):
            title = story_data.get("title", topic)
            raw_scenes = story_data.get("scenes", [])
            proj_id = db.create_project(title, topic, style, ratio, voice)
            for s in raw_scenes:
                db.add_scene(
                    proj_id, 
                    s.get("scene_number", 1), 
                    s.get("narration_km", ""), 
                    s.get("image_prompt_en", ""),
                    s.get("camera_motion") or motion or "talking"
                )
            self._set_ui_busy(False)
            self.open_studio.emit(proj_id)

        self.worker = StoryWorker(topic, num_scenes, style, genre=genre)
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
