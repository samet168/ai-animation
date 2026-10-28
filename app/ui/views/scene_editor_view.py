import os
import re
import shutil
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, 
    QPushButton, QComboBox, QScrollArea, QFrame, QMessageBox, QProgressBar,
    QFileDialog
)
from PySide6.QtCore import Qt, Signal, QSize, QThread
from PySide6.QtGui import QPixmap
from app.core.database import db
from app.core.settings import settings
from app.services.image_service import ImageService
from app.services.tts_service import TTSService
from app.services.khmer_service import KhmerService
from app.workers.image_worker import ImageWorker
from app.workers.tts_worker import TTSWorker
from app.workers.video_render_worker import VideoRenderWorker
from app.ui.icons import get_icon

logger = logging.getLogger("AIAnimationStudio.SceneEditorView")

class SingleImageWorker(QThread):
    progress = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, prompt: str, out_path: str, style: str, ratio: str, model: str):
        super().__init__()
        self.prompt = prompt
        self.out_path = out_path
        self.style = style
        self.ratio = ratio
        self.model = model

    def run(self):
        def cb(msg: str):
            self.progress.emit(msg)
        ok = ImageService.generate_image(
            prompt=self.prompt,
            output_path=self.out_path,
            style=self.style,
            aspect_ratio=self.ratio,
            model=self.model,
            progress_callback=cb
        )
        self.finished.emit(ok, self.out_path)

class SceneCard(QFrame):
    """Card widget representing a single storyboard scene."""

    def __init__(self, scene_data: dict, project_data: dict, parent_view, parent=None):
        super().__init__(parent)
        self.scene = scene_data
        self.project = project_data
        self.parent_view = parent_view
        self.setProperty("card", "true")
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(12, 12, 12, 12)

        # 1. Left Thumbnail Preview
        thumb_box = QVBoxLayout()
        thumb_box.setAlignment(Qt.AlignCenter)
        
        self.lbl_thumb = QLabel()
        self.lbl_thumb.setFixedSize(140, 180)
        self.lbl_thumb.setStyleSheet("background-color: #16181C; border: 1px solid #2B2E36; border-radius: 6px;")
        self.lbl_thumb.setAlignment(Qt.AlignCenter)
        self._update_thumbnail()
        thumb_box.addWidget(self.lbl_thumb)

        self.btn_regen_img = QPushButton("  បង្កើតរូបថ្មី")
        self.btn_regen_img.setIcon(get_icon("refresh", "#9CA3AF", 14))
        self.btn_regen_img.setIconSize(QSize(14, 14))
        self.btn_regen_img.setStyleSheet("font-size: 11px; padding: 4px 6px;")
        self.btn_regen_img.clicked.connect(self._regenerate_image)
        thumb_box.addWidget(self.btn_regen_img)

        layout.addLayout(thumb_box)

        # 2. Center Content (Narration + Image Prompt)
        content_box = QVBoxLayout()
        content_box.setSpacing(8)

        # Header: Scene # and Motion selector
        header_lay = QHBoxLayout()
        sc_badge = QLabel(f"Scene #{self.scene.get('scene_number', 1)}")
        sc_badge.setStyleSheet("font-weight: bold; color: #E5E7EB; font-size: 14px;")
        header_lay.addWidget(sc_badge)

        header_lay.addStretch()

        m_lbl = QLabel("ចលនា Camera:")
        m_lbl.setStyleSheet("color: #9CA3AF; font-size: 12px;")
        header_lay.addWidget(m_lbl)

        self.cmb_motion = QComboBox()
        self.cmb_motion.addItem(get_icon("zoom-in", "#60A5FA", 14), "Zoom In (ពង្រីកចូល)", "zoom_in")
        self.cmb_motion.addItem(get_icon("zoom-out", "#60A5FA", 14), "Zoom Out (បង្រួមចេញ)", "zoom_out")
        self.cmb_motion.addItem(get_icon("arrow-left", "#A78BFA", 14), "Pan Left (កាមេរ៉ារំកិលឆ្វេង)", "pan_left")
        self.cmb_motion.addItem(get_icon("arrow-right", "#A78BFA", 14), "Pan Right (កាមេរ៉ារំកិលស្តាំ)", "pan_right")
        self.cmb_motion.addItem(get_icon("square", "#9CA3AF", 14), "Steady / Cut (រូបភាពនឹង)", "steady")
        self.cmb_motion.addItem(get_icon("user", "#34D399", 14), "Talking Character (តួអង្គនិយាយ)", "talking")
        self.cmb_motion.addItem(get_icon("edit", "#F472B6", 14), "Whiteboard Hand-Drawn", "whiteboard")
        
        cur_motion = self.scene.get("camera_motion", "zoom_in")
        idx = self.cmb_motion.findData(cur_motion)
        if idx >= 0:
            self.cmb_motion.setCurrentIndex(idx)
        self.cmb_motion.currentIndexChanged.connect(self._save_motion)
        header_lay.addWidget(self.cmb_motion)

        content_box.addLayout(header_lay)

        # Narration (Khmer)
        narr_head_lay = QHBoxLayout()
        narr_lbl = QLabel("អត្ថបទសម្រាយខ្មែរ (Khmer Narration):")
        narr_lbl.setStyleSheet("color: #D1D5DB; font-size: 12px; font-weight: 600;")
        narr_head_lay.addWidget(narr_lbl)
        narr_head_lay.addStretch()

        self.btn_fix_card_spell = QPushButton("  កែអក្ខរាវិរុទ្ធ")
        self.btn_fix_card_spell.setIcon(get_icon("check", "#6EE7B7", 12))
        self.btn_fix_card_spell.setIconSize(QSize(12, 12))
        self.btn_fix_card_spell.setStyleSheet("font-size: 11px; padding: 2px 6px; background-color: #1F2228; border: 1px solid #363B45; color: #6EE7B7; border-radius: 4px;")
        self.btn_fix_card_spell.clicked.connect(self._auto_fix_spelling)
        narr_head_lay.addWidget(self.btn_fix_card_spell)
        content_box.addLayout(narr_head_lay)

        self.txt_narration = QTextEdit()
        self.txt_narration.setPlainText(self.scene.get("narration_km", ""))
        self.txt_narration.setMaximumHeight(65)
        self.txt_narration.textChanged.connect(self._save_narration)
        content_box.addWidget(self.txt_narration)

        # Image Prompt (English)
        p_lbl = QLabel("Image Prompt (AI Prompts):")
        p_lbl.setStyleSheet("color: #D1D5DB; font-size: 12px; font-weight: 600;")
        content_box.addWidget(p_lbl)

        self.txt_prompt = QTextEdit()
        self.txt_prompt.setPlainText(self.scene.get("image_prompt", ""))
        self.txt_prompt.setMaximumHeight(55)
        self.txt_prompt.textChanged.connect(self._save_prompt)
        content_box.addWidget(self.txt_prompt)

        # Bottom Audio row
        aud_row = QHBoxLayout()
        dur = self.scene.get("audio_duration", 0.0)
        self.lbl_audio_status = QLabel(f"រយៈពេលសំឡេង: {dur:.1f}s" if dur > 0 else "មិនទាន់មានសំឡេង")
        self.lbl_audio_status.setStyleSheet("color: #9CA3AF; font-size: 12px;")
        aud_row.addWidget(self.lbl_audio_status)

        aud_row.addStretch()

        self.btn_import_voice = QPushButton("  ដាក់សំឡេងផ្ទាល់")
        self.btn_import_voice.setIcon(get_icon("folder", "#9CA3AF", 13))
        self.btn_import_voice.setIconSize(QSize(13, 13))
        self.btn_import_voice.setStyleSheet("font-size: 11px; padding: 4px 8px;")
        self.btn_import_voice.setToolTip("ជ្រើសរើសឯកសារសំឡេង MP3/WAV ផ្ទាល់ខ្លួនសម្រាប់ Scene នេះ")
        self.btn_import_voice.clicked.connect(self._import_custom_audio)
        aud_row.addWidget(self.btn_import_voice)

        self.btn_gen_voice = QPushButton("  បញ្ចេញសំឡេងនេះ")
        self.btn_gen_voice.setIcon(get_icon("volume", "#9CA3AF", 14))
        self.btn_gen_voice.setIconSize(QSize(14, 14))
        self.btn_gen_voice.setStyleSheet("font-size: 11px; padding: 4px 8px;")
        self.btn_gen_voice.clicked.connect(self._generate_single_tts)
        aud_row.addWidget(self.btn_gen_voice)

        content_box.addLayout(aud_row)
        layout.addLayout(content_box)

    def _update_thumbnail(self):
        img_path = self.scene.get("image_path")
        if img_path and os.path.exists(img_path):
            if ImageService.is_valid_image(img_path):
                pix = QPixmap(img_path)
                self.lbl_thumb.setPixmap(pix.scaled(self.lbl_thumb.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
                self.lbl_thumb.setStyleSheet("background-color: #16181C; border: 1px solid #2B2E36; border-radius: 6px;")
            else:
                self.lbl_thumb.setText("រូបភាពបណ្តោះអាសន្ន\n(ចុច 'បង្កើតរូបថ្មី')")
                self.lbl_thumb.setStyleSheet("color: #F59E0B; font-size: 11px; font-weight: 600; background-color: #1F1914; border: 1px dashed #D97706; border-radius: 6px;")
        else:
            self.lbl_thumb.setText("គ្មានរូបភាព\n(No Image)")
            self.lbl_thumb.setStyleSheet("color: #6B7280; font-size: 11px; background-color: #16181C; border: 1px dashed #2B2E36; border-radius: 6px;")

    def _save_narration(self):
        text = self.txt_narration.toPlainText()
        self.scene["narration_km"] = text
        db.update_scene(self.scene["id"], narration_km=text)

    def _save_prompt(self):
        p = self.txt_prompt.toPlainText()
        self.scene["image_prompt"] = p
        db.update_scene(self.scene["id"], image_prompt=p)

    def _save_motion(self):
        m = self.cmb_motion.currentData()
        self.scene["camera_motion"] = m
        db.update_scene(self.scene["id"], camera_motion=m)

    def _regenerate_image(self):
        self.btn_regen_img.setEnabled(False)
        self.btn_regen_img.setText("  កំពុងរៀបចំ...")
        prompt = self.txt_prompt.toPlainText().strip()
        style = self.project.get("art_style", "3d_pixar")
        ratio = self.project.get("aspect_ratio", "9:16")
        model = settings.get("image_model", "flux")

        app_dir = settings.app_dir
        images_dir = os.path.join(app_dir, "data", "images")
        os.makedirs(images_dir, exist_ok=True)
        out_path = os.path.join(images_dir, f"scene_{self.scene['id']}_{self.scene.get('scene_number', 1)}.png")

        self.img_worker = SingleImageWorker(prompt, out_path, style, ratio, model)
        
        def on_prog(msg: str):
            # Show concise countdown or status
            if "Cooldown" in msg:
                m = re.search(r"\((\d+)s\)", msg)
                sec = m.group(1) if m else "..."
                self.btn_regen_img.setText(f"  រង់ចាំ {sec}s...")
            else:
                self.btn_regen_img.setText("  ទាញយក...")

        def on_done(ok: bool, path: str):
            self.btn_regen_img.setEnabled(True)
            self.btn_regen_img.setText("  បង្កើតរូបថ្មី")
            if ok and ImageService.is_valid_image(path):
                self.scene["image_path"] = path
                db.update_scene(self.scene["id"], image_path=path)
                self._update_thumbnail()
            else:
                QMessageBox.warning(self, "បរាជ័យ", "មិនអាចទាញយករូបភាពបានទេ។ សូមសាកល្បងម្ដងទៀត។")

        self.img_worker.progress.connect(on_prog)
        self.img_worker.finished.connect(on_done)
        self.img_worker.start()

    def _auto_fix_spelling(self):
        text = self.txt_narration.toPlainText()
        cleaned = KhmerService.clean_text(text)
        if cleaned != text:
            self.txt_narration.setPlainText(cleaned)
            self._save_narration()

    def _generate_single_tts(self):
        text = self.txt_narration.toPlainText().strip()
        if not text:
            return
        
        # Clean text automatically before speech synthesis
        text = KhmerService.clean_text(text)
        self.txt_narration.setPlainText(text)
        self._save_narration()

        self.btn_gen_voice.setEnabled(False)
        self.btn_gen_voice.setText("  កំពុងបង្កើត...")
        
        voice = self.project.get("voice", "km-KH-PisethNeural")
        rate = settings.get("voice_rate", "-6%")
        pitch = settings.get("voice_pitch", "-2Hz")

        app_dir = settings.app_dir
        audio_dir = os.path.join(app_dir, "data", "audio")
        os.makedirs(audio_dir, exist_ok=True)
        out_path = os.path.join(audio_dir, f"scene_{self.scene['id']}.mp3")

        ok, dur = TTSService.generate_speech(text, out_path, voice, rate, pitch)
        self.btn_gen_voice.setEnabled(True)
        self.btn_gen_voice.setText("  បញ្ចេញសំឡេងនេះ")

        if ok:
            self.scene["audio_path"] = out_path
            self.scene["audio_duration"] = dur
            db.update_scene(self.scene["id"], audio_path=out_path, audio_duration=dur)
            self.lbl_audio_status.setText(f"រយៈពេលសំឡេង: {dur:.1f}s")
        else:
            QMessageBox.warning(self, "បរាជ័យ", "មិនអាចបង្កើតសំឡេងបានទេ។")

    def _import_custom_audio(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "ជ្រើសរើសឯកសារសំឡេងសម្រាប់ Scene នេះ", 
            "", 
            "Audio Files (*.mp3 *.wav *.m4a *.aac *.ogg)"
        )
        if not file_path or not os.path.exists(file_path):
            return

        dur = TTSService.get_audio_duration(file_path)
        if dur <= 0:
            QMessageBox.warning(self, "ឯកសារមិនត្រឹមត្រូវ", "មិនអាចវាស់ប្រវែងសំឡេងនេះបានទេ។ សូមពិនិត្យមើលឯកសារឡើងវិញ។")
            return

        app_dir = settings.app_dir
        audio_dir = os.path.join(app_dir, "data", "audio")
        os.makedirs(audio_dir, exist_ok=True)
        ext = os.path.splitext(file_path)[1].lower() or ".mp3"
        dest_path = os.path.join(audio_dir, f"scene_{self.scene['id']}{ext}")
        try:
            shutil.copyfile(file_path, dest_path)
            self.scene["audio_path"] = dest_path
            self.scene["audio_duration"] = dur
            db.update_scene(self.scene["id"], audio_path=dest_path, audio_duration=dur)
            self.lbl_audio_status.setText(f"រយៈពេលសំឡេង: {dur:.1f}s")
            QMessageBox.information(self, "ជោគជ័យ", f"បានបញ្ចូលសំឡេងផ្ទាល់ខ្លួន (ប្រវែង {dur:.1f}s) ដោយជោគជ័យ!")
        except Exception as e:
            QMessageBox.critical(self, "បញ្ហា", f"មិនអាចចម្លងឯកសារបានឡើយ៖ {e}")


class SceneEditorView(QWidget):
    """Studio / Scene Editor View."""

    video_ready = Signal(int, str)  # (project_id, final_video_path)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project_id = None
        self.project_data = {}
        self.scenes = []
        self.cards = []
        self.worker = None
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 15, 20, 15)
        main_layout.setSpacing(12)

        # Top Bar
        top_bar = QFrame()
        top_bar.setProperty("card", "true")
        t_lay = QHBoxLayout(top_bar)

        self.lbl_proj_title = QLabel("ស្ទូឌីយោកែសម្រួល Scene (Scene Studio)")
        self.lbl_proj_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #F3F4F6;")
        t_lay.addWidget(self.lbl_proj_title)
        t_lay.addStretch()

        self.btn_fix_all_spelling = QPushButton("  កែអក្ខរាវិរុទ្ធ")
        self.btn_fix_all_spelling.setIcon(get_icon("check", "#6EE7B7", 16))
        self.btn_fix_all_spelling.setIconSize(QSize(16, 16))
        self.btn_fix_all_spelling.setToolTip("កែកំហុសអក្ខរាវិរុទ្ធ និងតម្រៀបតួអក្សរខ្មែរគ្រប់ Scene ឱ្យត្រឹមត្រូវ")
        self.btn_fix_all_spelling.clicked.connect(self._auto_fix_all_spelling)
        t_lay.addWidget(self.btn_fix_all_spelling)

        self.btn_gen_all_tts = QPushButton("  បង្កើតសំឡេងទាំងអស់")
        self.btn_gen_all_tts.setIcon(get_icon("volume", "#9CA3AF", 16))
        self.btn_gen_all_tts.setIconSize(QSize(16, 16))
        self.btn_gen_all_tts.clicked.connect(self._generate_all_tts)
        t_lay.addWidget(self.btn_gen_all_tts)

        self.btn_gen_all_img = QPushButton("  បង្កើតរូបភាពទាំងអស់")
        self.btn_gen_all_img.setIcon(get_icon("image", "#9CA3AF", 16))
        self.btn_gen_all_img.setIconSize(QSize(16, 16))
        self.btn_gen_all_img.clicked.connect(self._generate_all_images)
        t_lay.addWidget(self.btn_gen_all_img)

        self.btn_render_all = QPushButton("  Render វីដេអូពេញលេញ")
        self.btn_render_all.setIcon(get_icon("video", "#F9FAFB", 16))
        self.btn_render_all.setIconSize(QSize(16, 16))
        self.btn_render_all.setProperty("accent", "primary")
        self.btn_render_all.clicked.connect(self._render_final_video)
        t_lay.addWidget(self.btn_render_all)

        main_layout.addWidget(top_bar)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #9CA3AF; font-weight: 600;")
        self.lbl_status.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.lbl_status)

        # Scrollable Cards Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setSpacing(14)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll.setWidget(self.scroll_content)

        main_layout.addWidget(self.scroll)

    def load_project(self, project_id: int):
        self.project_id = project_id
        self.project_data = db.get_project(project_id) or {}
        self.scenes = db.get_scenes(project_id)

        title = self.project_data.get("title", f"Project #{project_id}")
        self.lbl_proj_title.setText(f"{title} ({len(self.scenes)} Scenes)")

        # Clear existing cards
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.cards.clear()

        # Add scene cards
        for sc in self.scenes:
            card = SceneCard(sc, self.project_data, self)
            self.cards.append(card)
            self.scroll_layout.addWidget(card)

        self.scroll_layout.addStretch()

    def _auto_fix_all_spelling(self):
        """Auto-correct spelling and normalize Khmer Unicode across all project scenes."""
        changed_count = 0
        for card in self.cards:
            old_txt = card.txt_narration.toPlainText()
            new_txt = KhmerService.clean_text(old_txt)
            if new_txt != old_txt:
                card.txt_narration.setPlainText(new_txt)
                card._save_narration()
                changed_count += 1
        
        if changed_count > 0:
            QMessageBox.information(self, "ជោគជ័យ", f"បានកែតម្រូវអក្ខរាវិរុទ្ធចំនួន {changed_count} Scenes រួចរាល់ដោយជោគជ័យ!")
        else:
            QMessageBox.information(self, "ត្រឹមត្រូវ", "អក្ខរាវិរុទ្ធគ្រប់ Scene ត្រឹមត្រូវល្អហើយ!")

    def _generate_all_tts(self):
        if not self.scenes:
            return
        voice = self.project_data.get("voice", "km-KH-PisethNeural")
        self._set_busy(True)
        self.progress_bar.setValue(0)
        self.lbl_status.setText("កំពុងបញ្ចេញសំឡេងគ្រប់ Scene...")

        self.worker = TTSWorker(self.scenes, voice)
        self.worker.progress.connect(self._on_progress)
        self.worker.scene_audio_ready.connect(self._on_audio_ready)
        self.worker.finished.connect(lambda: self._set_busy(False))
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _generate_all_images(self):
        if not self.scenes:
            return
        style = self.project_data.get("art_style", "3d_pixar")
        ratio = self.project_data.get("aspect_ratio", "9:16")
        self._set_busy(True)
        self.progress_bar.setValue(0)
        self.lbl_status.setText("កំពុងទាញយករូបភាព AI គ្រប់ Scene...")

        self.worker = ImageWorker(self.scenes, style, ratio)
        self.worker.progress.connect(self._on_progress)
        self.worker.scene_image_ready.connect(self._on_image_ready)
        self.worker.finished.connect(lambda: self._set_busy(False))
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _render_final_video(self):
        self.scenes = db.get_scenes(self.project_id)
        if not self.scenes:
            QMessageBox.warning(self, "គ្មាន Scene", "គម្រោងនេះមិនទាន់មាន Scene ណាមួយនៅឡើយទេ។")
            return

        self._set_busy(True)
        self.progress_bar.setValue(0)
        self.lbl_status.setText("កំពុងរៀបចំ និង Render វីដេអូចលនា...")

        ratio = self.project_data.get("aspect_ratio", "9:16")
        art_style = self.project_data.get("art_style", "3d_pixar")
        voice = self.project_data.get("voice", "km-KH-PisethNeural")

        # Automatically auto-completes missing audio/images without warning blocks!
        self.worker = VideoRenderWorker(self.project_id, self.scenes, ratio, art_style, voice)
        self.worker.progress.connect(self._on_progress)
        self.worker.scene_updated.connect(self._on_scene_updated_live)
        self.worker.finished.connect(self._on_render_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_scene_updated_live(self, scene_id: int, img_path: str, aud_path: str, dur: float):
        for c in self.cards:
            if c.scene["id"] == scene_id:
                if img_path:
                    c.scene["image_path"] = img_path
                    c._update_thumbnail()
                if aud_path:
                    c.scene["audio_path"] = aud_path
                    c.scene["audio_duration"] = dur
                    c.lbl_audio_status.setText(f"រយៈពេលសំឡេង: {dur:.1f}s")
                break

    def _on_image_ready(self, scene_id: int, image_path: str):
        for c in self.cards:
            if c.scene["id"] == scene_id:
                c.scene["image_path"] = image_path
                c._update_thumbnail()
                break

    def _on_audio_ready(self, scene_id: int, audio_path: str, duration: float):
        for c in self.cards:
            if c.scene["id"] == scene_id:
                c.scene["audio_path"] = audio_path
                c.scene["audio_duration"] = duration
                c.lbl_audio_status.setText(f"រយៈពេលសំឡេង: {duration:.1f}s")
                break

    def _on_render_finished(self, final_video_path: str):
        self._set_busy(False)
        self.video_ready.emit(self.project_id, final_video_path)

    def _on_progress(self, pct: int, msg: str):
        self.progress_bar.setValue(pct)
        self.lbl_status.setText(msg)

    def _on_error(self, err_msg: str):
        self._set_busy(False)
        QMessageBox.critical(self, "បញ្ហា", f"មានបញ្ហាអំឡុងពេលដំណើរការ៖\n{err_msg}")

    def _set_busy(self, busy: bool):
        self.btn_gen_all_tts.setEnabled(not busy)
        self.btn_gen_all_img.setEnabled(not busy)
        self.btn_render_all.setEnabled(not busy)
        self.progress_bar.setVisible(busy)
        self.lbl_status.setVisible(busy)
