import sys
import os
import shutil
import datetime
import calendar
import zipfile
import json
import base64
import threading
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

try:
    from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                                 QLabel, QComboBox, QPushButton, QGridLayout, QDialog,
                                 QTextEdit, QFileDialog, QMessageBox, QInputDialog)
    from PyQt6.QtGui import QDesktopServices, QPixmap
    from PyQt6.QtCore import Qt, QUrl
except ImportError:
    print("PyQt6 is required. Please install it using: pip install PyQt6")
    sys.exit(1)

PLAN_SUFFIX = "AI"
PORT = 8123

def get_vault_root():
    return Path.home() / "Downloads" / "aha" / "AI Pro"

class VaultHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != '/api/content':
            self.send_error(404)
            return
            
        qs = parse_qs(parsed.query)
        platform = qs.get('platform', [''])[0]
        day = qs.get('day', [''])[0]
        text_choice = qs.get('text', ['no'])[0].lower()
        media_choice = qs.get('media', ['none'])[0].lower()
        
        if not platform or not day:
            self.send_error(400, "Missing platform or day")
            return
            
        current_year = str(datetime.date.today().year)
        current_month = str(datetime.date.today().month).zfill(2)
        
        vault_dir = get_vault_root() / platform / current_year / current_month
        
        response_data = {
            "platform": platform,
            "day": day,
            "textContent": None,
            "mediaDataUrl": None,
            "mediaMimeType": None
        }
        
        # Read Text
        if text_choice == 'yes':
            txt_path = vault_dir / "Texts" / f"{day}{PLAN_SUFFIX}.txt"
            if txt_path.exists():
                response_data["textContent"] = txt_path.read_text(encoding="utf-8")
                
        # Read Media
        if media_choice in ['image', 'video']:
            subfolder = "Images" if media_choice == 'image' else "Videos"
            media_dir = vault_dir / subfolder
            if media_dir.exists():
                for p in media_dir.glob(f"{day}{PLAN_SUFFIX}.*"):
                    ext = p.suffix.lower()
                    mime_type = "application/octet-stream"
                    if ext in [".png", ".jpg", ".jpeg", ".webp", ".gif"]:
                        mime_type = f"image/{ext[1:]}"
                        if ext == ".jpg": mime_type = "image/jpeg"
                    elif ext in [".mp4", ".mov", ".webm"]:
                        mime_type = f"video/{ext[1:]}"
                        
                    with open(p, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode('utf-8')
                        response_data["mediaDataUrl"] = f"data:{mime_type};base64,{b64}"
                        response_data["mediaMimeType"] = mime_type
                    break
                    
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response_data).encode('utf-8'))

def run_server():
    server = HTTPServer(('127.0.0.1', PORT), VaultHandler)
    server.serve_forever()

class StorageEngineApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AHA Storage Engine")
        self.setMinimumSize(1000, 750)
        self.setStyleSheet("""
            QWidget { background-color: #0f172a; color: white; font-family: -apple-system, system-ui, sans-serif; font-size: 14px; }
            QComboBox { padding: 8px 12px; min-width: 140px; border-radius: 4px; background-color: #1e293b; border: 1px solid #334155; }
            QComboBox QAbstractItemView { background-color: #1e293b; color: white; selection-background-color: #3b82f6; }
            QLineEdit { background-color: #1e293b; color: white; padding: 8px; border: 1px solid #334155; border-radius: 4px; }
            QPushButton { font-weight: bold; font-size: 14px; }
            QInputDialog { background-color: #0f172a; }
        """)
        
        self.vault_root = get_vault_root()
        self.vault_root.mkdir(parents=True, exist_ok=True)
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        self.main_layout = QVBoxLayout(main_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Header with Import/Export
        header_layout = QHBoxLayout()
        title = QLabel("<h2>Storage Engine</h2>")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        self.import_btn = QPushButton("Import ZIP")
        self.import_btn.setFixedSize(120, 40)
        self.import_btn.setStyleSheet("background-color: #3b82f6; color: white; border: none; border-radius: 6px; font-weight: bold;")
        self.import_btn.clicked.connect(self.import_zip)
        header_layout.addWidget(self.import_btn)
        
        self.export_btn = QPushButton("Export ZIP")
        self.export_btn.setFixedSize(120, 40)
        self.export_btn.setStyleSheet("background-color: #10b981; color: white; border: none; border-radius: 6px; font-weight: bold;")
        self.export_btn.clicked.connect(self.export_zip)
        header_layout.addWidget(self.export_btn)
        
        self.main_layout.addLayout(header_layout)
        
        # Controls (Platform, Year, Month)
        controls_layout = QHBoxLayout()
        
        self.platform_dropdown = QComboBox()
        self.load_platforms()
        self.platform_dropdown.currentTextChanged.connect(self.load_calendar)
        
        add_platform_btn = QPushButton("+ New Platform")
        add_platform_btn.setFixedSize(140, 36)
        add_platform_btn.setStyleSheet("background-color: #475569; color: white; border-radius: 4px;")
        add_platform_btn.clicked.connect(self.add_new_platform)
        
        self.year_dropdown = QComboBox()
        current_year = datetime.date.today().year
        self.year_dropdown.addItems([str(y) for y in range(current_year - 1, current_year + 3)])
        self.year_dropdown.setCurrentText(str(current_year))
        self.year_dropdown.currentTextChanged.connect(self.load_calendar)
        
        self.month_dropdown = QComboBox()
        self.month_dropdown.addItems([str(m).zfill(2) for m in range(1, 13)])
        self.month_dropdown.setCurrentText(str(datetime.date.today().month).zfill(2))
        self.month_dropdown.currentTextChanged.connect(self.load_calendar)
        
        controls_layout.addWidget(QLabel("<b>Platform:</b>"))
        controls_layout.addWidget(self.platform_dropdown)
        controls_layout.addWidget(add_platform_btn)
        controls_layout.addSpacing(40)
        controls_layout.addWidget(QLabel("<b>Year:</b>"))
        controls_layout.addWidget(self.year_dropdown)
        controls_layout.addSpacing(40)
        controls_layout.addWidget(QLabel("<b>Month:</b>"))
        controls_layout.addWidget(self.month_dropdown)
        controls_layout.addStretch()
        
        self.main_layout.addLayout(controls_layout)
        self.main_layout.addSpacing(20)
        
        # Calendar Grid
        self.main_layout.addWidget(QLabel("<h3>Calendar (Click day to preview/edit content)</h3>"))
        
        self.calendar_grid = QGridLayout()
        self.calendar_grid.setSpacing(10)
        
        self.day_buttons = {}
        for day in range(1, 32):
            btn = QPushButton(str(day))
            btn.setFixedSize(80, 80)
            btn.setStyleSheet("background-color: #1e293b; color: white; border: 1px solid rgba(255,255,255,0.2); border-radius: 8px;")
            btn.clicked.connect(lambda checked, d=day: self.open_day_modal(d))
            row = (day - 1) // 7
            col = (day - 1) % 7
            self.calendar_grid.addWidget(btn, row, col)
            self.day_buttons[day] = btn
            
        self.main_layout.addLayout(self.calendar_grid)
        self.main_layout.addStretch()
        
        # Start server
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        
        self.load_calendar()
        
    def load_platforms(self):
        self.platform_dropdown.clear()
        if self.vault_root.exists():
            platforms = [d.name for d in self.vault_root.iterdir() if d.is_dir() and not d.name.startswith('.')]
            if platforms:
                self.platform_dropdown.addItems(sorted(platforms))
                
    def add_new_platform(self):
        name, ok = QInputDialog.getText(self, "New Platform", "Enter Platform Name:")
        if ok and name.strip():
            name = name.strip()
            (self.vault_root / name).mkdir(parents=True, exist_ok=True)
            self.load_platforms()
            self.platform_dropdown.setCurrentText(name)

    def load_calendar(self):
        year = int(self.year_dropdown.currentText())
        month = int(self.month_dropdown.currentText())
        _, days_in_month = calendar.monthrange(year, month)
        
        for day, btn in self.day_buttons.items():
            if day <= days_in_month:
                btn.show()
                has_content = self.check_day_content(day)
                if has_content:
                    btn.setStyleSheet("background-color: #3b82f6; color: white; border: 2px solid #60a5fa; border-radius: 8px; font-weight: bold;")
                else:
                    btn.setStyleSheet("background-color: #1e293b; color: white; border: 1px solid rgba(255,255,255,0.2); border-radius: 8px;")
            else:
                btn.hide()
                
    def get_day_dir(self):
        platform = self.platform_dropdown.currentText()
        year = self.year_dropdown.currentText()
        month = self.month_dropdown.currentText()
        if not platform: return None
        return self.vault_root / platform / year / month
        
    def check_day_content(self, day):
        day_dir = self.get_day_dir()
        if not day_dir: return False
        
        has_text = list((day_dir / "Texts").glob(f"{day}{PLAN_SUFFIX}.txt")) if (day_dir / "Texts").exists() else []
        has_img = list((day_dir / "Images").glob(f"{day}{PLAN_SUFFIX}.*")) if (day_dir / "Images").exists() else []
        has_vid = list((day_dir / "Videos").glob(f"{day}{PLAN_SUFFIX}.*")) if (day_dir / "Videos").exists() else []
        
        return bool(has_text or has_img or has_vid)

    def open_day_modal(self, day):
        modal = QDialog(self)
        modal.setWindowTitle(f"Content for Day {day}")
        modal.setMinimumSize(600, 500)
        modal.setStyleSheet("background-color: #1e293b; color: white;")
        layout = QVBoxLayout(modal)
        
        day_dir = self.get_day_dir()
        texts_dir = day_dir / "Texts"
        images_dir = day_dir / "Images"
        videos_dir = day_dir / "Videos"
        
        txt_path = texts_dir / f"{day}{PLAN_SUFFIX}.txt"
        
        # Text Preview / Edit
        layout.addWidget(QLabel("Text Caption:"))
        text_edit = QTextEdit()
        text_edit.setStyleSheet("background-color: #0f172a; color: white; border: 1px solid #334155; padding: 10px;")
        if txt_path.exists():
            text_edit.setPlainText(txt_path.read_text(encoding="utf-8"))
        layout.addWidget(text_edit)
        
        # Media Preview
        layout.addWidget(QLabel("Media Attachment:"))
        media_label = QLabel("No media attached")
        media_label.setStyleSheet("color: #94a3b8;")
        
        existing_media = None
        for d in [images_dir, videos_dir]:
            if d.exists():
                files = list(d.glob(f"{day}{PLAN_SUFFIX}.*"))
                if files:
                    existing_media = files[0]
                    media_label.setText(f"Attached: {existing_media.name}")
                    media_label.setStyleSheet("color: #10b981; font-weight: bold;")
                    break
                    
        layout.addWidget(media_label)
        
        btn_layout = QHBoxLayout()
        
        attach_img_btn = QPushButton("Attach Image")
        attach_img_btn.setStyleSheet("padding: 8px; background-color: #475569; color: white; border-radius: 4px;")
        def do_attach_img():
            nonlocal existing_media
            path, _ = QFileDialog.getOpenFileName(modal, "Select Image", "", "Image (*.png *.jpg *.jpeg *.webp *.gif)")
            if path:
                existing_media = Path(path)
                media_label.setText(f"Selected Image: {existing_media.name} (Will be saved on confirm)")
                media_label.setStyleSheet("color: #3b82f6; font-weight: bold;")
        attach_img_btn.clicked.connect(do_attach_img)

        attach_vid_btn = QPushButton("Attach Video")
        attach_vid_btn.setStyleSheet("padding: 8px; background-color: #475569; color: white; border-radius: 4px;")
        def do_attach_vid():
            nonlocal existing_media
            path, _ = QFileDialog.getOpenFileName(modal, "Select Video", "", "Video (*.mp4 *.mov *.webm)")
            if path:
                existing_media = Path(path)
                media_label.setText(f"Selected Video: {existing_media.name} (Will be saved on confirm)")
                media_label.setStyleSheet("color: #3b82f6; font-weight: bold;")
        attach_vid_btn.clicked.connect(do_attach_vid)
        
        clear_btn = QPushButton("Clear Content")
        clear_btn.setStyleSheet("padding: 8px; background-color: #ef4444; color: white; border-radius: 4px;")
        def do_clear():
            nonlocal existing_media
            text_edit.clear()
            existing_media = None
            media_label.setText("No media attached")
            media_label.setStyleSheet("color: #94a3b8;")
            if txt_path.exists(): txt_path.unlink()
            for d in [images_dir, videos_dir]:
                if d.exists():
                    for f in d.glob(f"{day}{PLAN_SUFFIX}.*"):
                        f.unlink()
            self.load_calendar()
        clear_btn.clicked.connect(do_clear)
        
        btn_layout.addWidget(attach_img_btn)
        btn_layout.addWidget(attach_vid_btn)
        btn_layout.addWidget(clear_btn)
        layout.addLayout(btn_layout)
        
        save_btn = QPushButton("Save Content")
        save_btn.setStyleSheet("padding: 12px; background-color: #10b981; color: white; font-weight: bold; border-radius: 6px;")
        def do_save():
            # Save Text
            texts_dir.mkdir(parents=True, exist_ok=True)
            txt = text_edit.toPlainText().strip()
            if txt:
                txt_path.write_text(txt, encoding="utf-8")
            elif txt_path.exists():
                txt_path.unlink()
                
            # Save Media
            if existing_media and existing_media.parent not in [images_dir, videos_dir]:
                ext = existing_media.suffix.lower()
                is_video = ext in ['.mp4', '.mov', '.webm']
                target_dir = videos_dir if is_video else images_dir
                target_dir.mkdir(parents=True, exist_ok=True)
                
                # remove old ones
                for d in [images_dir, videos_dir]:
                    if d.exists():
                        for f in d.glob(f"{day}{PLAN_SUFFIX}.*"):
                            f.unlink()
                            
                target_path = target_dir / f"{day}{PLAN_SUFFIX}{ext}"
                shutil.copy2(existing_media, target_path)
                
            self.load_calendar()
            modal.accept()
            
        save_btn.clicked.connect(do_save)
        layout.addSpacing(20)
        layout.addWidget(save_btn)
        
        modal.exec()

    def export_zip(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Vault ZIP", "AHA_Export.zip", "ZIP Files (*.zip)")
        if not path: return
        
        try:
            with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(self.vault_root):
                    for file in files:
                        if not file.startswith('.'):
                            file_path = Path(root) / file
                            arcname = file_path.relative_to(self.vault_root)
                            zf.write(file_path, arcname)
            QMessageBox.information(self, "Success", f"Successfully exported vault to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export ZIP:\n{str(e)}")

    def import_zip(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Vault ZIP", "", "ZIP Files (*.zip)")
        if not path: return
        
        try:
            with zipfile.ZipFile(path, 'r') as zf:
                zf.extractall(self.vault_root)
            self.load_platforms()
            self.load_calendar()
            QMessageBox.information(self, "Success", "Successfully imported ZIP to your vault!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to import ZIP:\n{str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = StorageEngineApp()
    window.show()
    sys.exit(app.exec())
