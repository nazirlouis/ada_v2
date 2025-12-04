import sys
import math
import random
import os
import threading
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# PySide6 Imports
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QFrame, QScrollArea, QPushButton,
                             QGraphicsDropShadowEffect, QSizePolicy, QProgressBar)
from PySide6.QtCore import Qt, QTimer, QPointF, Signal, QSize, QPropertyAnimation, QEasingCurve, QThread, Slot, QObject
from PySide6.QtGui import (QPainter, QColor, QPen, QRadialGradient, QBrush, 
                         QFont, QLinearGradient, QPainterPath, QGradient, QImage, QPixmap, QPolygonF)

from visualizer import VisualizerWidget
import ada

# Load environment variables
load_dotenv()

# --- CONFIGURATION ---
THEME = {
    'bg': '#000000',
    'cyan': '#06b6d4',      # Cyan-500
    'cyan_dim': '#155e75',  # Cyan-900
    'cyan_glow': '#22d3ee', # Cyan-400
    'text': '#cffafe',      # Cyan-100
    'red': '#ef4444',
    'green': '#22c55e'
}

STYLESHEET = f"""
QMainWindow {{
    background-color: {THEME['bg']};
}}
QLabel {{
    color: {THEME['text']};
    font-family: 'Consolas', 'Monospace';
}}
QScrollArea {{
    background: transparent;
    border: none;
}}
QScrollBar:vertical {{
    background: {THEME['bg']};
    width: 8px;
}}
QScrollBar::handle:vertical {{
    background: {THEME['cyan_dim']};
    border-radius: 4px;
}}
/* Progress Bar Styling */
QProgressBar {{
    border: 1px solid {THEME['cyan_dim']};
    background-color: #050505;
    text-align: center;
    color: {THEME['text']};
    font-family: 'Consolas';
    font-weight: bold;
}}
QProgressBar::chunk {{
    background-color: {THEME['cyan']};
    width: 10px; 
    margin: 1px;
}}
"""

# Signal helper for async updates
class Signaller(QObject):
    frame_signal = Signal(object)
    audio_signal = Signal(bytes)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("O.L.L.I.E Interface")
        self.resize(800, 600)
        self.setStyleSheet(STYLESHEET)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.setup_header()
        
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(20)
        self.main_layout.addLayout(content_layout)

        # --- VISUALIZER AREA ---
        self.visualizer = VisualizerWidget()
        content_layout.addWidget(self.visualizer)

        footer_line = QFrame()
        footer_line.setFixedHeight(2)
        footer_line.setStyleSheet(f"background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 black, stop:0.5 {THEME['cyan_dim']}, stop:1 black);")
        self.main_layout.addWidget(footer_line)

        # Signals
        self.signaller = Signaller()
        self.signaller.frame_signal.connect(self.update_frame)
        self.signaller.audio_signal.connect(self.update_audio)
        
        # Start Backend
        self.start_backend()

    def setup_header(self):
        header = QFrame()
        header.setStyleSheet(f"background-color: rgba(0, 0, 0, 100); border-bottom: 1px solid {THEME['cyan_dim']};")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 15, 20, 15)

        title_label = QLabel("O.L.L.I.E.")
        title_label.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {THEME['text']}; letter-spacing: 4px;")
        
        self.status_label = QLabel(" ONLINE // V.4.0.3")
        self.status_label.setStyleSheet(f"color: {THEME['green']}; font-size: 10px; letter-spacing: 2px;")

        header_layout.addWidget(title_label)
        header_layout.addWidget(self.status_label)
        header_layout.addStretch()

        stats = ["CPU: 12%", "NET: 45ms", "VOICE: ACTIVE"]
        self.stat_labels = {}
        
        for stat in stats:
            lbl = QLabel(stat)
            lbl.setStyleSheet(f"color: {THEME['cyan_dim']}; font-weight: bold; margin-left: 15px;")
            header_layout.addWidget(lbl)
            self.stat_labels[stat.split(':')[0]] = lbl

        self.main_layout.addWidget(header)

    # --- Backend Integration ---
    def start_backend(self):
        self.backend_thread = threading.Thread(target=self.run_async_loop, daemon=True)
        self.backend_thread.start()

    def run_async_loop(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            self.audio_loop = ada.AudioLoop(
                video_mode="none",
                on_audio_data=self.on_audio_data_callback,
                on_video_frame=self.on_video_frame_callback
            )
            
            loop.run_until_complete(self.audio_loop.run())
        except Exception as e:
            print(f"Backend error: {e}")

    def on_audio_data_callback(self, data):
        self.signaller.audio_signal.emit(data)

    def on_video_frame_callback(self, frame_rgb):
        self.signaller.frame_signal.emit(frame_rgb)

    @Slot(object)
    def update_frame(self, frame_rgb):
        pass # No video display

    @Slot(bytes)
    def update_audio(self, data):
        self.visualizer.update_audio_data(data)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
