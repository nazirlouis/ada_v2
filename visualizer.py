import math
import numpy as np
from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtCore import QTimer, Qt, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QRadialGradient, QBrush, QPainterPath, QFont

# Theme colors from the snippet
THEME = {
    'cyan': '#06b6d4',      # Cyan-500
    'cyan_dim': '#155e75',  # Cyan-900
    'red': '#ef4444',
}

class VisualizerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(16)
        
        self.time = 0.0
        self.is_speaking = False
        self.is_listening = False
        self.current_amplitude = 0.0
        
        self.waves = [
            {'color': QColor(6, 182, 212, 128), 'speed': 0.02, 'amp': 50, 'freq': 0.01},
            {'color': QColor(34, 211, 238, 80), 'speed': 0.03, 'amp': 30, 'freq': 0.02},
            {'color': QColor(103, 232, 249, 50), 'speed': 0.01, 'amp': 80, 'freq': 0.005},
        ]

    def update_audio_data(self, data):
        """
        Update the visualizer with new audio data.
        Calculates RMS amplitude to drive the wave animation.
        """
        try:
            audio_array = np.frombuffer(data, dtype=np.int16)
            if len(audio_array) > 0:
                # Sanitize data
                audio_array = np.nan_to_num(audio_array)
                
                # Calculate RMS amplitude
                rms = np.sqrt(np.mean(audio_array.astype(float)**2))
                
                # Check for NaN in RMS
                if np.isnan(rms):
                    rms = 0.0
                    
                # Normalize (assuming 16-bit audio)
                target_amp = min(rms / 1000.0, 5.0) # Scale factor
                
                # Smooth transition
                self.current_amplitude = self.current_amplitude * 0.7 + target_amp * 0.3
                
                # Final safety check
                if np.isnan(self.current_amplitude):
                    self.current_amplitude = 0.0
                
                # Threshold for "speaking" state
                if self.current_amplitude > 0.1:
                    self.is_speaking = True
                else:
                    self.is_speaking = False
        except Exception as e:
            print(f"Error updating visualizer: {e}")

    def update_animation(self):
        # Base speed
        increment = 0.05
        
        # Speed up if there's high amplitude
        if self.current_amplitude > 0.5:
            increment = 0.15
            
        self.time += increment
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        h = self.height()
        center_x = w / 2
        center_y = h / 2

        # Dynamic glow based on amplitude
        glow_size = 200 + (self.current_amplitude * 20)
        glow_opacity = 25 + min(int(self.current_amplitude * 50), 100)
        
        radial = QRadialGradient(center_x, center_y, glow_size)
        radial.setColorAt(0, QColor(6, 182, 212, glow_opacity))
        radial.setColorAt(1, QColor(0, 0, 0, 0))
        painter.fillRect(0, 0, w, h, radial)

        # Rings
        ring_color = QColor(THEME['cyan'])
        ring_color.setAlpha(50 + int(self.current_amplitude * 20))
        pen = QPen(ring_color)
        pen.setWidth(1 + int(self.current_amplitude))
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        radius_1 = 120 + math.sin(self.time * 2) * 5 + (self.current_amplitude * 10)
        painter.drawEllipse(QPointF(center_x, center_y), radius_1, radius_1)
        
        pen.setColor(QColor(6, 182, 212, 30))
        painter.setPen(pen)
        radius_2 = 180 - math.sin(self.time) * 10 - (self.current_amplitude * 5)
        painter.drawEllipse(QPointF(center_x, center_y), radius_2, radius_2)

        # Waves
        for i, wave in enumerate(self.waves):
            path = QPainterPath()
            wave_color = wave['color']
            painter.setPen(QPen(wave_color, 2))
            
            # Modulate amplitude with audio volume
            base_amp = wave['amp']
            active_amp = base_amp * (0.5 + self.current_amplitude)

            base_freq = wave['freq']
            if self.current_amplitude > 0.5:
                base_freq *= 1.5

            path.moveTo(0, center_y)
            
            for x in range(0, w + 5, 5):
                dist_from_center = x - center_x
                decay = math.exp(-0.0001 * dist_from_center**2)
                sine_val = math.sin(x * base_freq + self.time * (i + 1) + wave['speed'])
                y = center_y + sine_val * (active_amp * decay)
                path.lineTo(x, y)
            
            painter.drawPath(path)
            
        # Text
        painter.setPen(QColor(THEME['cyan']))
        font = QFont("Consolas", 10)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 3)
        painter.setFont(font)
        
        text = ""
        if self.is_listening:
            text = "LISTENING..."
            painter.setPen(QColor(THEME['red']))
        elif self.current_amplitude > 0.1:
            text = "VOICE ACTIVE"
            painter.setPen(QColor(THEME['cyan']))
        else:
            text = "SYSTEM READY"
            alpha = 100
            painter.setPen(QColor(6, 182, 212, alpha))
            
        if text:
            fm = painter.fontMetrics()
            tw = fm.horizontalAdvance(text)
            painter.drawText(int(center_x - tw/2), int(center_y + 10), text)
