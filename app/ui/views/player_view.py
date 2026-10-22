import os
import subprocess
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QSlider, QFrame, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, QUrl, Signal, QSize
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from app.ui.icons import get_icon

logger = logging.getLogger("AIAnimationStudio.PlayerView")

class PlayerView(QWidget):
    """Video Preview Player and Export View."""

    back_to_editor = Signal(int)  # (project_id)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project_id = None
        self.video_path = None
        self._init_player()
        self._init_ui()

    def _init_player(self):
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.video_widget = QVideoWidget()
        self.player.setVideoOutput(self.video_widget)

        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 15, 20, 15)
        main_layout.setSpacing(12)

        # Top Bar
        top_bar = QFrame()
        top_bar.setProperty("card", "true")
        t_lay = QHBoxLayout(top_bar)

        self.lbl_title = QLabel("មើលវីដេអូ Animation (Video Preview & Export)")
        self.lbl_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #F3F4F6;")
        t_lay.addWidget(self.lbl_title)
        t_lay.addStretch()

        self.btn_back = QPushButton("  ត្រឡប់ទៅកែសម្រួល (Edit Scenes)")
        self.btn_back.setIcon(get_icon("edit", "#9CA3AF", 16))
        self.btn_back.setIconSize(QSize(16, 16))
        self.btn_back.clicked.connect(self._on_back_clicked)
        t_lay.addWidget(self.btn_back)

        self.btn_open_folder = QPushButton("  បើកទីតាំង Folder")
        self.btn_open_folder.setIcon(get_icon("folder", "#9CA3AF", 16))
        self.btn_open_folder.setIconSize(QSize(16, 16))
        self.btn_open_folder.clicked.connect(self._open_in_explorer)
        t_lay.addWidget(self.btn_open_folder)

        self.btn_export_as = QPushButton("  រក្សាទុកជា... (Export As)")
        self.btn_export_as.setIcon(get_icon("download", "#FFFFFF", 16))
        self.btn_export_as.setIconSize(QSize(16, 16))
        self.btn_export_as.setProperty("accent", "primary")
        self.btn_export_as.clicked.connect(self._export_as)
        t_lay.addWidget(self.btn_export_as)

        main_layout.addWidget(top_bar)

        # Video Player Frame
        player_frame = QFrame()
        player_frame.setProperty("card", "true")
        p_lay = QVBoxLayout(player_frame)
        p_lay.setContentsMargins(8, 8, 8, 8)

        # Center video widget
        self.video_widget.setMinimumHeight(450)
        self.video_widget.setStyleSheet("background-color: #0D0E11; border-radius: 6px;")
        p_lay.addWidget(self.video_widget)

        # Controls bar
        ctrl_bar = QHBoxLayout()
        ctrl_bar.setSpacing(10)

        self.btn_play = QPushButton("  Play")
        self.btn_play.setIcon(get_icon("play", "#E5E7EB", 14))
        self.btn_play.setIconSize(QSize(14, 14))
        self.btn_play.setFixedWidth(85)
        self.btn_play.clicked.connect(self._toggle_play)
        ctrl_bar.addWidget(self.btn_play)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.sliderMoved.connect(self._set_position)
        ctrl_bar.addWidget(self.slider)

        self.lbl_time = QLabel("00:00 / 00:00")
        self.lbl_time.setStyleSheet("color: #9CA3AF; font-size: 12px;")
        ctrl_bar.addWidget(self.lbl_time)

        p_lay.addLayout(ctrl_bar)
        main_layout.addWidget(player_frame)

    def load_video(self, project_id: int, video_path: str):
        self.project_id = project_id
        self.video_path = video_path
        self.lbl_title.setText(f"វីដេអូសម្រេច: {os.path.basename(video_path)}")

        if os.path.exists(video_path):
            self.player.setSource(QUrl.fromLocalFile(video_path))
            self.player.play()
            self.btn_play.setText("  Pause")
            self.btn_play.setIcon(get_icon("pause", "#E5E7EB", 14))

    def _toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
            self.btn_play.setText("  Play")
            self.btn_play.setIcon(get_icon("play", "#E5E7EB", 14))
        else:
            self.player.play()
            self.btn_play.setText("  Pause")
            self.btn_play.setIcon(get_icon("pause", "#E5E7EB", 14))

    def _on_position_changed(self, pos: int):
        if not self.slider.isSliderDown():
            self.slider.setValue(pos)
        self._update_time_label(pos, self.player.duration())

    def _on_duration_changed(self, dur: int):
        self.slider.setRange(0, dur)
        self._update_time_label(self.player.position(), dur)

    def _set_position(self, pos: int):
        self.player.setPosition(pos)

    def _update_time_label(self, pos: int, dur: int):
        cur_sec = pos // 1000
        tot_sec = dur // 1000
        cur_str = f"{cur_sec // 60:02d}:{cur_sec % 60:02d}"
        tot_str = f"{tot_sec // 60:02d}:{tot_sec % 60:02d}"
        self.lbl_time.setText(f"{cur_str} / {tot_str}")

    def _open_in_explorer(self):
        if self.video_path and os.path.exists(self.video_path):
            folder = os.path.dirname(os.path.abspath(self.video_path))
            os.startfile(folder)
        else:
            QMessageBox.information(self, "ជូនដំណឹង", "រកមិនឃើញទីតាំង File វីដេអូទេ។")

    def _export_as(self):
        if not self.video_path or not os.path.exists(self.video_path):
            QMessageBox.warning(self, "ខ្វះ File", "គ្មានវីដេអូសម្រាប់ Export ទេ។")
            return

        dest, _ = QFileDialog.getSaveFileName(
            self, "រក្សាទុកវីដេអូជា...", 
            os.path.basename(self.video_path), 
            "MP4 Video (*.mp4)"
        )
        if dest:
            import shutil
            shutil.copy2(self.video_path, dest)
            QMessageBox.information(self, "ជោគជ័យ", f"បានរក្សាទុកវីដេអូទៅកាន់:\n{dest}")

    def _on_back_clicked(self):
        self.player.pause()
        self.btn_play.setText("  Play")
        self.btn_play.setIcon(get_icon("play", "#E5E7EB", 14))
        if self.project_id:
            self.back_to_editor.emit(self.project_id)
