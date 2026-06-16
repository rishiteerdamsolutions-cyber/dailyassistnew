import sys
import os
import shutil
import datetime
import calendar
import zipfile
from pathlib import Path

try:
    from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                                 QLabel, QComboBox, QPushButton, QGridLayout, QDialog,
                                 QTextEdit, QFileDialog, QMessageBox)
    from PyQt6.QtGui import QDesktopServices
    from PyQt6.QtCore import Qt, QUrl
except ImportError:
    print("PyQt6 is required. Please install it using: pip install PyQt6")
    sys.exit(1)

PLATFORMS = ["LinkedIn", "Instagram", "Facebook", "X", "WhatsApp"]
PLAN_SUFFIX = "AI"

class ContentEngineApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AHA Content Engine - Manager Dashboard")
        self.setMinimumSize(800, 600)
        self.setStyleSheet("background-color: #0f172a; color: white; font-family: -apple-system, system-ui, sans-serif;")
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        self.main_layout = QVBoxLayout(main_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel("<h2>Content Engine</h2>")
        header_layout.addWidget(title)
        
        self.export_btn = QPushButton("Export as ZIP")
        self.export_btn.setFixedSize(140, 40)
        self.export_btn.setStyleSheet("background-color: #10b981; color: white; border: none; border-radius: 6px; font-weight: bold;")
        self.export_btn.clicked.connect(self.export_zip)
        header_layout.addWidget(self.export_btn)
        
        self.main_layout.addLayout(header_layout)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        self.platform_dropdown = QComboBox()
        self.platform_dropdown.addItems(PLATFORMS)
        self.platform_dropdown.setStyleSheet("padding: 8px; border-radius: 4px; background-color: #1e293b; border: 1px solid #334155;")
        self.platform_dropdown.currentTextChanged.connect(self.load_calendar)
        
        self.year_dropdown = QComboBox()
        current_year = datetime.date.today().year
        self.year_dropdown.addItems([str(y) for y in range(current_year - 1, current_year + 3)])
        self.year_dropdown.setCurrentText(str(current_year))
        self.year_dropdown.setStyleSheet("padding: 8px; border-radius: 4px; background-color: #1e293b; border: 1px solid #334155;")
        self.year_dropdown.currentTextChanged.connect(self.load_calendar)
        
        self.month_dropdown = QComboBox()
        self.month_dropdown.addItems([str(m) for m in range(1, 13)])
        self.month_dropdown.setCurrentText(str(datetime.date.today().month))
        self.month_dropdown.setStyleSheet("padding: 8px; border-radius: 4px; background-color: #1e293b; border: 1px solid #334155;")
        self.month_dropdown.currentTextChanged.connect(self.load_calendar)
        
        controls_layout.addWidget(QLabel("Platform:"))
        controls_layout.addWidget(self.platform_dropdown)
        controls_layout.addWidget(QLabel("Year:"))
        controls_layout.addWidget(self.year_dropdown)
        controls_layout.addWidget(QLabel("Month:"))
        controls_layout.addWidget(self.month_dropdown)
        controls_layout.addStretch()
        
        self.main_layout.addLayout(controls_layout)
        self.main_layout.addSpacing(20)
        
        # Calendar Grid
        self.main_layout.addWidget(QLabel("<h3>Select a day to upload content:</h3>"))
        
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
        
        self.load_calendar()

    def get_vault_dir(self):
        # The target structure: ~/Downloads/aha/AI Pro
        vault_dir = Path.home() / "Downloads" / "aha" / "AI Pro"
        vault_dir.mkdir(parents=True, exist_ok=True)
        return vault_dir
        
    def get_target_dir(self):
        platform = self.platform_dropdown.currentText()
        return self.get_vault_dir() / platform

    def load_calendar(self):
        target_dir = self.get_target_dir()
        
        try:
            year = int(self.year_dropdown.currentText())
            month = int(self.month_dropdown.currentText())
        except ValueError:
            year, month = datetime.date.today().year, datetime.date.today().month
            
        _, num_days = calendar.monthrange(year, month)
        
        for day in range(1, 32):
            btn = self.day_buttons[day]
            if day > num_days:
                btn.hide()
                continue
            else:
                btn.show()
                
            has_text, has_img, has_vid = False, False, False
            
            # Check Text
            txt_path = target_dir / "Texts" / f"{day}{PLAN_SUFFIX}.txt"
            if txt_path.exists() and txt_path.stat().st_size > 0: has_text = True
                
            # Check Image
            img_dir = target_dir / "Images"
            if img_dir.exists():
                for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif"]:
                    if (img_dir / f"{day}{PLAN_SUFFIX}{ext}").exists():
                        has_img = True
                        break
                        
            # Check Video
            vid_dir = target_dir / "Videos"
            if vid_dir.exists():
                for ext in [".mp4", ".mov", ".webm"]:
                    if (vid_dir / f"{day}{PLAN_SUFFIX}{ext}").exists():
                        has_vid = True
                        break
                        
            # Update button text
            base_text = str(day)
            indicators = []
            if has_text: indicators.append("📝")
            if has_img: indicators.append("🖼️")
            if has_vid: indicators.append("🎥")
            
            if indicators:
                btn.setText(f"{base_text}\n{' '.join(indicators)}")
                btn.setStyleSheet("background-color: #334155; color: white; border: 1px solid #3b82f6; border-radius: 8px;")
            else:
                btn.setText(base_text)
                btn.setStyleSheet("background-color: #1e293b; color: white; border: 1px solid rgba(255,255,255,0.2); border-radius: 8px;")

    def open_day_modal(self, day):
        platform = self.platform_dropdown.currentText()
        target_dir = self.get_target_dir()
            
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Upload Content for {platform} - Day {day}")
        dialog.setMinimumWidth(500)
        dialog.setStyleSheet("background-color: #1e293b; color: white;")
        
        layout = QVBoxLayout(dialog)
        
        layout.addWidget(QLabel("<b>Caption:</b>"))
        text_edit = QTextEdit()
        text_edit.setStyleSheet("background-color: #0f172a; border: 1px solid #334155; border-radius: 4px; padding: 4px;")
        
        # Load existing text
        txt_path = target_dir / "Texts" / f"{day}{PLAN_SUFFIX}.txt"
        if txt_path.exists():
            text_edit.setPlainText(txt_path.read_text(encoding="utf-8"))
        layout.addWidget(text_edit)
        
        # Image
        img_layout = QHBoxLayout()
        img_label = QLabel("Image: None")
        img_btn = QPushButton("Select Image")
        img_btn.setStyleSheet("background-color: #3b82f6; padding: 6px; border-radius: 4px;")
        img_preview_btn = QPushButton("👁️")
        img_preview_btn.setFixedSize(30, 30)
        img_preview_btn.hide()
        selected_img = [None]
        
        # Check existing image
        img_dir = target_dir / "Images"
        existing_img = None
        if img_dir.exists():
            for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif"]:
                p = img_dir / f"{day}{PLAN_SUFFIX}{ext}"
                if p.exists():
                    existing_img = p
                    break
        
        if existing_img:
            img_label.setText(f"Image: {existing_img.name}")
            img_preview_btn.show()
            
        def preview_img():
            target = selected_img[0] if selected_img[0] else str(existing_img)
            QDesktopServices.openUrl(QUrl.fromLocalFile(target))
        img_preview_btn.clicked.connect(preview_img)
        
        def pick_img():
            path, _ = QFileDialog.getOpenFileName(dialog, "Select Image", "", "Images (*.png *.jpg *.jpeg *.gif *.webp)")
            if path:
                selected_img[0] = path
                img_label.setText(f"Image: {os.path.basename(path)}")
                img_preview_btn.show()
        img_btn.clicked.connect(pick_img)
        img_layout.addWidget(img_label)
        img_layout.addWidget(img_btn)
        img_layout.addWidget(img_preview_btn)
        layout.addLayout(img_layout)
        
        # Video
        vid_layout = QHBoxLayout()
        vid_label = QLabel("Video: None")
        vid_btn = QPushButton("Select Video")
        vid_btn.setStyleSheet("background-color: #3b82f6; padding: 6px; border-radius: 4px;")
        vid_preview_btn = QPushButton("👁️")
        vid_preview_btn.setFixedSize(30, 30)
        vid_preview_btn.hide()
        selected_vid = [None]
        
        # Check existing video
        vid_dir = target_dir / "Videos"
        existing_vid = None
        if vid_dir.exists():
            for ext in [".mp4", ".mov", ".webm"]:
                p = vid_dir / f"{day}{PLAN_SUFFIX}{ext}"
                if p.exists():
                    existing_vid = p
                    break
                    
        if existing_vid:
            vid_label.setText(f"Video: {existing_vid.name}")
            vid_preview_btn.show()
            
        def preview_vid():
            target = selected_vid[0] if selected_vid[0] else str(existing_vid)
            QDesktopServices.openUrl(QUrl.fromLocalFile(target))
        vid_preview_btn.clicked.connect(preview_vid)
        
        def pick_vid():
            path, _ = QFileDialog.getOpenFileName(dialog, "Select Video", "", "Videos (*.mp4 *.mov *.webm)")
            if path:
                selected_vid[0] = path
                vid_label.setText(f"Video: {os.path.basename(path)}")
                vid_preview_btn.show()
        vid_btn.clicked.connect(pick_vid)
        vid_layout.addWidget(vid_label)
        vid_layout.addWidget(vid_btn)
        vid_layout.addWidget(vid_preview_btn)
        layout.addLayout(vid_layout)
        
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save Content")
        save_btn.setStyleSheet("background-color: #10b981; font-weight: bold; padding: 8px; border-radius: 4px;")
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("background-color: #ef4444; padding: 8px; border-radius: 4px;")
        
        cancel_btn.clicked.connect(dialog.reject)
        
        def save_content():
            txt = text_edit.toPlainText().strip()
            
            # Save Text
            if txt:
                txt_path.parent.mkdir(parents=True, exist_ok=True)
                txt_path.write_text(txt, encoding="utf-8")
            else:
                if txt_path.exists(): txt_path.unlink()
                
            # Save Image
            if selected_img[0]:
                img_dir.mkdir(parents=True, exist_ok=True)
                # Remove old
                for p in img_dir.glob(f"{day}{PLAN_SUFFIX}.*"): p.unlink()
                ext = os.path.splitext(selected_img[0])[1] or ".png"
                shutil.copy2(selected_img[0], img_dir / f"{day}{PLAN_SUFFIX}{ext}")
                
            # Save Video
            if selected_vid[0]:
                vid_dir.mkdir(parents=True, exist_ok=True)
                # Remove old
                for p in vid_dir.glob(f"{day}{PLAN_SUFFIX}.*"): p.unlink()
                ext = os.path.splitext(selected_vid[0])[1] or ".mp4"
                shutil.copy2(selected_vid[0], vid_dir / f"{day}{PLAN_SUFFIX}{ext}")
                
            dialog.accept()
            self.load_calendar()
            
        save_btn.clicked.connect(save_content)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        dialog.exec()

    def export_zip(self):
        root_dir = Path.home() / "Downloads" / "aha"
        if not root_dir.exists():
            QMessageBox.warning(self, "Error", "No content found. Please add content first.")
            return
            
        export_path = Path.home() / "Desktop" / "AHA_Export.zip"
        
        try:
            with zipfile.ZipFile(export_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Only walk AI Pro directory
                ai_pro_dir = root_dir / "AI Pro"
                if ai_pro_dir.exists():
                    for root, dirs, files in os.walk(ai_pro_dir):
                        for file in files:
                            if file == ".DS_Store": continue
                            file_path = os.path.join(root, file)
                            # Store it as 'aha/AI Pro/...'
                            arcname = os.path.relpath(file_path, root_dir.parent)
                            zipf.write(file_path, arcname)
                            
            QMessageBox.information(self, "Export Complete", f"Content exported to:\n{export_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export: {str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ContentEngineApp()
    window.show()
    sys.exit(app.exec())
