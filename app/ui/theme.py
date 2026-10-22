"""
Charcoal & Slate Dark Theme (ខ្មៅប្រផេះ) for AI Animation Studio.
Uses clean typography (Kantumruy Pro, Leelawadee UI) and a modern graphite color palette.
"""

CHARCOAL_THEME = """
QWidget {
    background-color: #121316;
    color: #E5E7EB;
    font-family: 'Kantumruy Pro', 'Leelawadee UI', 'Khmer OS Siemreap', 'Segoe UI', sans-serif;
    font-size: 13px;
}

/* Window & Dialogs */
QDialog, QMainWindow {
    background-color: #121316;
}

/* Cards & Frames (Graphite/Charcoal) */
QFrame[card="true"], QGroupBox {
    background-color: #1A1C20;
    border: 1px solid #2B2E36;
    border-radius: 8px;
    padding: 14px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    color: #D1D5DB;
    font-weight: 600;
    font-size: 13px;
}

/* Standard Buttons (Sleek Charcoal) */
QPushButton {
    background-color: #22252B;
    color: #E5E7EB;
    border: 1px solid #323640;
    border-radius: 7px;
    padding: 7px 15px;
    font-weight: 600;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #2C3038;
    border-color: #444A57;
    color: #FFFFFF;
}

QPushButton:pressed {
    background-color: #17191E;
}

QPushButton:disabled {
    background-color: #17181C;
    color: #555A66;
    border-color: #222429;
}

/* Primary Accent Button (Steel Slate) */
QPushButton[accent="primary"] {
    background-color: #374151;
    color: #F9FAFB;
    border: 1px solid #4B5563;
}

QPushButton[accent="primary"]:hover {
    background-color: #4B5563;
    border-color: #6B7280;
}

QPushButton[accent="primary"]:pressed {
    background-color: #1F2937;
}

/* Success Button */
QPushButton[accent="success"] {
    background-color: #1E3A34;
    color: #6EE7B7;
    border: 1px solid #2D5A50;
}

QPushButton[accent="success"]:hover {
    background-color: #264B43;
    color: #A7F3D0;
}

/* Inputs & LineEdit */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #17191D;
    color: #F3F4F6;
    border: 1px solid #2B2E36;
    border-radius: 6px;
    padding: 8px 10px;
    selection-background-color: #4B5563;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #5A6273;
    background-color: #1A1C22;
}

/* ComboBox */
QComboBox {
    background-color: #17191D;
    color: #E5E7EB;
    border: 1px solid #2B2E36;
    border-radius: 6px;
    padding: 7px 12px;
}

QComboBox:hover {
    border-color: #3E434F;
}

QComboBox:focus {
    border-color: #5A6273;
}

QComboBox::drop-down {
    border: none;
    padding-right: 10px;
}

QComboBox QAbstractItemView {
    background-color: #1A1C20;
    border: 1px solid #2B2E36;
    selection-background-color: #323640;
    selection-color: #FFFFFF;
    color: #E5E7EB;
    padding: 4px;
}

/* SpinBox */
QSpinBox {
    background-color: #17191D;
    color: #E5E7EB;
    border: 1px solid #2B2E36;
    border-radius: 6px;
    padding: 6px 10px;
}

/* Sliders */
QSlider::groove:horizontal {
    height: 5px;
    background: #252830;
    border-radius: 2px;
}

QSlider::sub-page:horizontal {
    background: #525B6C;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    background: #9CA3AF;
    width: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 7px;
}

QSlider::handle:horizontal:hover {
    background: #D1D5DB;
}

/* Progress Bar */
QProgressBar {
    background-color: #17191D;
    border: 1px solid #2B2E36;
    border-radius: 6px;
    text-align: center;
    color: #E5E7EB;
    font-weight: 600;
    height: 20px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #475163, stop:1 #6B768B);
    border-radius: 5px;
}

/* CheckBox */
QCheckBox {
    spacing: 8px;
    color: #D1D5DB;
    font-size: 13px;
}

QCheckBox::indicator {
    width: 17px;
    height: 17px;
    border-radius: 4px;
    border: 1px solid #3B404D;
    background-color: #17191D;
}

QCheckBox::indicator:checked {
    background-color: #4B5563;
    border-color: #6B7280;
}

/* ScrollBars */
QScrollBar:vertical {
    background: #121316;
    width: 8px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #282B33;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #3B404C;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Tab Widget */
QTabWidget::pane {
    border: 1px solid #2B2E36;
    background-color: #16181C;
    border-radius: 7px;
}

QTabBar::tab {
    background-color: #1A1C20;
    color: #9CA3AF;
    padding: 9px 18px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 3px;
    font-weight: 600;
}

QTabBar::tab:selected {
    background-color: #23262C;
    color: #F3F4F6;
    border-bottom: 2px solid #6B768B;
}

QTabBar::tab:hover {
    color: #E5E7EB;
}
"""
