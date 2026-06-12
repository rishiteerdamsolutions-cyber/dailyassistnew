"""
Ghost Overlay — Transparent AR layer for AHA Agent.

Listens on UDP 9999 for packets from the executor:
  {"type": "clear"}                              → wipe all visuals
  {"type": "laser", "x": N, "y": N, "color": "green"|"blue"} → draw crosshair
  {"type": "threat", "bbox": [x, y, w, h]}       → draw red shield over wrong button

Run:
  python ghost_overlay.py
"""

import sys
import json
import socket
import threading
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QPainter, QColor, QPen, QFont


class Signals(QObject):
    packet_received = pyqtSignal(dict)


class GhostOverlay(QWidget):
    def __init__(self):
        super().__init__()

        # Transparent, borderless, always on top, click-through
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowTransparentForInput
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)

        # Full screen geometry
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)

        self.lasers = []   # [{"x": int, "y": int, "color": str}]
        self.threats = []  # [{"bbox": [x, y, w, h]}]

        # Signal bridge for thread-safe UI updates
        self.signals = Signals()
        self.signals.packet_received.connect(self._handle_packet)

        # Start UDP listener in background thread
        self._start_udp_listener()

        # Auto-clear visuals after 2 seconds of no new packets
        self._clear_timer = QTimer()
        self._clear_timer.setSingleShot(True)
        self._clear_timer.timeout.connect(self._auto_clear)

        print("Ghost Overlay ready. Waiting for agent packets on UDP 9999...")

    def _start_udp_listener(self):
        def _listen():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('127.0.0.1', 9999))
            while True:
                data, _ = sock.recvfrom(4096)
                try:
                    payload = json.loads(data.decode('utf-8'))
                    self.signals.packet_received.emit(payload)
                except Exception as e:
                    print(f"UDP parse error: {e}")

        t = threading.Thread(target=_listen, daemon=True)
        t.start()

    def _handle_packet(self, payload):
        ptype = payload.get("type")
        if ptype == "clear":
            self.lasers.clear()
            self.threats.clear()
        elif ptype == "laser":
            self.lasers.append({
                "x": payload["x"],
                "y": payload["y"],
                "color": payload.get("color", "green"),
            })
        elif ptype == "threat":
            self.threats.append({"bbox": payload["bbox"]})

        # Reset the auto-clear timer
        self._clear_timer.start(2000)
        self.update()  # trigger paintEvent

    def _auto_clear(self):
        self.lasers.clear()
        self.threats.clear()
        self.update()

    def paintEvent(self, event):
        if not self.lasers and not self.threats:
            return  # Nothing to paint

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # ── Draw Threats (Red Shields with X) ──
        for t in self.threats:
            x, y, w, h = t["bbox"]
            # Outer glow
            pen = QPen(QColor(255, 50, 50, 100), 5)
            painter.setPen(pen)
            painter.setBrush(QColor(255, 0, 0, 30))
            painter.drawRoundedRect(x - 4, y - 4, w + 8, h + 8, 6, 6)

            # Inner shield
            pen = QPen(QColor(255, 0, 0, 200), 3)
            painter.setPen(pen)
            painter.setBrush(QColor(255, 0, 0, 50))
            painter.drawRoundedRect(x, y, w, h, 4, 4)

            # Draw an X across the threat
            pen = QPen(QColor(255, 0, 0, 220), 2)
            painter.setPen(pen)
            painter.drawLine(x + 3, y + 3, x + w - 3, y + h - 3)
            painter.drawLine(x + w - 3, y + 3, x + 3, y + h - 3)

            # Label
            painter.setFont(QFont("Menlo", 9, QFont.Weight.Bold))
            painter.setPen(QColor(255, 80, 80, 230))
            painter.drawText(x, y - 6, "WRONG")

        # ── Draw Lasers (Crosshairs) ──
        for laser in self.lasers:
            lx, ly = laser["x"], laser["y"]
            if laser["color"] == "green":
                color = QColor(0, 255, 100, 220)
                label = "TARGET"
            else:
                color = QColor(50, 150, 255, 220)
                label = "TARGET"

            # Outer glow ring
            pen = QPen(QColor(color.red(), color.green(), color.blue(), 60), 3)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(lx - 22, ly - 22, 44, 44)

            # Inner crosshair lines
            pen = QPen(color, 2)
            painter.setPen(pen)
            painter.drawLine(lx - 16, ly, lx - 4, ly)
            painter.drawLine(lx + 4, ly, lx + 16, ly)
            painter.drawLine(lx, ly - 16, lx, ly - 4)
            painter.drawLine(lx, ly + 4, lx, ly + 16)

            # Center dot
            painter.setBrush(color)
            painter.drawEllipse(lx - 3, ly - 3, 6, 6)

            # Label
            painter.setFont(QFont("Menlo", 9, QFont.Weight.Bold))
            painter.setPen(color)
            painter.drawText(lx + 20, ly - 8, label)

        painter.end()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    overlay = GhostOverlay()
    overlay.show()
    sys.exit(app.exec())
