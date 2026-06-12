import sys
import threading
import requests
import json
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QTextEdit, QLineEdit, QPushButton, QSplitter, QLabel,
    QTabWidget, QComboBox, QGridLayout, QDialog, QFileDialog, QMessageBox, QTextBrowser
)
from PyQt6.QtCore import Qt, QUrl, QTimer, pyqtSignal, QObject
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage, QWebEngineScript

SERVER_URL = "https://aha-cloud-brain.onrender.com"

class WorkerSignals(QObject):
    response_received = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

class AgentWorker:
    def __init__(self, endpoint, payload):
        self.endpoint = endpoint
        self.payload = payload
        self.signals = WorkerSignals()
        
    def run(self):
        try:
            res = requests.post(self.endpoint, json=self.payload)
            self.signals.response_received.emit(res.json())
        except Exception as e:
            self.signals.error_occurred.emit(str(e))

class WebEnginePage(QWebEnginePage):
    """Custom page that handles popup windows (e.g. Google OAuth sign-in)
    by loading them in the same view instead of trying to open a new window."""
    def createWindow(self, _type):
        # Return self so the popup URL loads in the same webview
        return self

class CompanionApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AHA - Artificial Human Assistant")
        self.resize(1300, 900)

        # Style the app
        self.setStyleSheet("""
            QMainWindow {
                background-color: #121212;
            }
            QWidget {
                color: #ececf1;
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', Roboto, Helvetica, sans-serif;
            }
            QTextEdit {
                background-color: #121212;
                border: 1px solid #27272a;
                border-radius: 6px;
                padding: 10px;
                font-size: 14px;
            }
            QLineEdit {
                background-color: #121212;
                border: 1px solid #27272a;
                border-radius: 6px;
                padding: 10px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #64748b;
            }
            QPushButton {
                background-color: #27272a;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #3f3f46;
            }
            QPushButton:disabled {
                background-color: transparent;
                color: #3f3f46;
            }
            QComboBox {
                background-color: #121212;
                color: white;
                border: 1px solid #27272a;
                border-radius: 4px;
                padding: 6px 10px;
                min-width: 120px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #121212;
                color: white;
                selection-background-color: #27272a;
            }
        """)

        # Main Layout (Splitter)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(self.splitter)

        # Left Panel (Chat)
        self.chat_panel = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_panel)
        self.chat_layout.setContentsMargins(20, 20, 20, 20)
        self.chat_layout.setSpacing(15)
        
        self.chat_history = QTextBrowser()
        self.chat_history.setOpenExternalLinks(False)
        self.chat_history.anchorClicked.connect(self.handle_link_click)
        self.chat_history.setReadOnly(True)
        self.chat_history.setStyleSheet("border: none; background-color: #121212;")
        self.chat_messages = []
        
        self.append_message("AHA initialized. Ready to execute intents.", sender="System")
        self.append_message("Hello! Where would you like to go today? Tell me a website and what you want to do.", sender="Agent")
        
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("e.g. Open MakeMyTrip and book a flight to Delhi...")
        self.chat_input.returnPressed.connect(self.send_message)
        
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)
        
        self.resume_button = QPushButton("Resume AHA Workflow")
        self.resume_button.setStyleSheet("background-color: #f59e0b; color: white;")
        self.resume_button.setVisible(False)
        self.resume_button.clicked.connect(self.resume_workflow)

        self.clear_button = QPushButton("Clear Chat")
        self.clear_button.setStyleSheet("background-color: #ef4444; color: white;")
        self.clear_button.clicked.connect(self.clear_chat)

        input_layout = QHBoxLayout()
        input_layout.addWidget(self.chat_input)
        input_layout.addWidget(self.send_button)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.resume_button)
        btn_layout.addWidget(self.clear_button)

        self.chat_layout.addWidget(self.chat_history)
        self.chat_layout.addLayout(btn_layout)
        self.chat_layout.addLayout(input_layout)

        # Right Panel (Tabs)
        self.right_panel = QTabWidget()
        self.right_panel.setStyleSheet("""
            QTabWidget::pane { border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; }
            QTabBar::tab { background: #1e293b; color: #94a3b8; padding: 10px 20px; margin-right: 2px; border-top-left-radius: 8px; border-top-right-radius: 8px; }
            QTabBar::tab:selected { background: #3b82f6; color: white; }
        """)

        # Tab 1: Live Web Browser
        self.browser_panel = QWidget()
        self.browser_layout = QVBoxLayout(self.browser_panel)
        self.browser_layout.setContentsMargins(0, 0, 0, 0)
        self.browser_layout.setSpacing(0)
        self.right_panel.addTab(self.browser_panel, "Live Vision Feed")

        # Browser toolbar
        browser_toolbar = QHBoxLayout()
        browser_toolbar.setContentsMargins(8, 8, 8, 8)
        
        btn_style = """
            QPushButton {
                background-color: transparent;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 4px;
                padding: 0px;
                color: white;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border-color: #3b82f6;
            }
        """
        
        self.back_btn = QPushButton("◀")
        self.back_btn.setFixedSize(30, 30)
        self.back_btn.setStyleSheet(btn_style)
        self.back_btn.clicked.connect(lambda: self.current_browser().back() if self.current_browser() else None)
        
        self.forward_btn = QPushButton("▶")
        self.forward_btn.setFixedSize(30, 30)
        self.forward_btn.setStyleSheet(btn_style)
        self.forward_btn.clicked.connect(lambda: self.current_browser().forward() if self.current_browser() else None)
        
        self.reload_btn = QPushButton("↻")
        self.reload_btn.setFixedSize(30, 30)
        self.reload_btn.setStyleSheet(btn_style)
        self.reload_btn.clicked.connect(lambda: self.current_browser().reload() if self.current_browser() else None)
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter URL or search...")
        self.url_input.returnPressed.connect(self.navigate_to_url)
        
        self.new_tab_btn = QPushButton("+")
        self.new_tab_btn.setFixedSize(30, 30)
        self.new_tab_btn.setStyleSheet(btn_style)
        self.new_tab_btn.clicked.connect(lambda: self.add_browser_tab("https://google.com"))

        browser_toolbar.addWidget(self.back_btn)
        browser_toolbar.addWidget(self.forward_btn)
        browser_toolbar.addWidget(self.reload_btn)
        browser_toolbar.addWidget(self.url_input)
        browser_toolbar.addWidget(self.new_tab_btn)

        self.browser_layout.addLayout(browser_toolbar)
        
        # Browser Tabs
        self.browser_tabs = QTabWidget()
        self.browser_tabs.setTabsClosable(True)
        self.browser_tabs.tabCloseRequested.connect(self.close_browser_tab)
        self.browser_tabs.currentChanged.connect(self.on_browser_tab_changed)
        self.browser_tabs.setStyleSheet("""
            QTabWidget::pane { border: none; }
            QTabBar::tab { background: #1e293b; color: #94a3b8; padding: 8px 15px; margin-right: 2px; border-top-left-radius: 6px; border-top-right-radius: 6px; }
            QTabBar::tab:selected { background: #0f172a; color: white; }
        """)
        self.browser_layout.addWidget(self.browser_tabs)

        # Base Profile
        self.browser_profile = QWebEngineProfile("AHA_Profile", self)
        
        # Set up the browser profile with a real Chrome user-agent so Google login works
        chrome_ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        self.browser_profile.setHttpUserAgent(chrome_ua)
        # Persist cookies so login sessions survive app restarts
        self.browser_profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        )

        # Inject Chrome-specific JS APIs that Google/X check to detect embedded browsers
        chrome_spoof_js = QWebEngineScript()
        chrome_spoof_js.setName("ChromeSpoof")
        chrome_spoof_js.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
        chrome_spoof_js.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        chrome_spoof_js.setRunsOnSubFrames(True)
        chrome_spoof_js.setSourceCode('''
            // Spoof navigator.userAgentData (Chrome Client Hints API)
            if (!navigator.userAgentData) {
                Object.defineProperty(navigator, "userAgentData", {
                    get: () => ({
                        brands: [
                            { brand: "Not/A)Brand", version: "8" },
                            { brand: "Chromium", version: "126" },
                            { brand: "Google Chrome", version: "126" }
                        ],
                        mobile: false,
                        platform: "macOS",
                        getHighEntropyValues: (hints) => Promise.resolve({
                            architecture: "arm",
                            bitness: "64",
                            brands: [
                                { brand: "Not/A)Brand", version: "8.0.0.0" },
                                { brand: "Chromium", version: "126.0.0.0" },
                                { brand: "Google Chrome", version: "126.0.0.0" }
                            ],
                            fullVersionList: [
                                { brand: "Not/A)Brand", version: "8.0.0.0" },
                                { brand: "Chromium", version: "126.0.0.0" },
                                { brand: "Google Chrome", version: "126.0.0.0" }
                            ],
                            mobile: false,
                            model: "",
                            platform: "macOS",
                            platformVersion: "14.5.0",
                            uaFullVersion: "126.0.0.0"
                        })
                    })
                });
            }
            // Ensure window.chrome exists (Google checks this)
            if (!window.chrome) {
                window.chrome = { runtime: {}, csi: function(){}, loadTimes: function(){} };
            }
            // Spoof plugins to look like a real browser
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
        ''')
        self.browser_profile.scripts().insert(chrome_spoof_js)

        self.add_browser_tab("https://google.com")

        self.setup_vault_tab()

        self.splitter.addWidget(self.chat_panel)
        self.splitter.addWidget(self.right_panel)
        self.splitter.setSizes([450, 850])

        self.is_paused = False

        # Poll Chrome window bounds every 3s and update the capture region
        self.chrome_region_timer = QTimer()
        self.chrome_region_timer.timeout.connect(self.update_chrome_browser_coordinates)
        self.chrome_region_timer.start(3000)

    def setup_vault_tab(self):
        from pathlib import Path
        
        self.vault_panel = QWidget()
        self.vault_layout = QVBoxLayout(self.vault_panel)
        self.vault_layout.setContentsMargins(15, 15, 15, 15)
        
        # Controls
        vault_controls = QHBoxLayout()
        
        self.slot_dropdown = QComboBox()
        self.slot_dropdown.setMinimumWidth(120)
        self.slot_dropdown.currentIndexChanged.connect(self.load_vault_calendar)
        
        self.year_dropdown = QComboBox()
        import datetime
        current_year = datetime.date.today().year
        self.year_dropdown.addItems([str(y) for y in range(current_year, current_year + 10)])
        self.year_dropdown.currentIndexChanged.connect(self.load_vault_calendar)
        
        self.month_dropdown = QComboBox()
        self.month_dropdown.addItems([str(m) for m in range(1, 13)])
        self.month_dropdown.setCurrentText(str(datetime.date.today().month))
        self.month_dropdown.currentIndexChanged.connect(self.load_vault_calendar)
        
        self.new_slot_input = QLineEdit()
        self.new_slot_input.setPlaceholderText("New slot name...")
        self.new_slot_input.setMaximumWidth(120)
        
        self.create_slot_btn = QPushButton("Create Slot")
        self.create_slot_btn.clicked.connect(self.create_vault_slot)
        
        vault_controls.addWidget(QLabel("<b>Slot:</b>"))
        vault_controls.addWidget(self.slot_dropdown)
        vault_controls.addWidget(QLabel("<b>Year:</b>"))
        vault_controls.addWidget(self.year_dropdown)
        vault_controls.addWidget(QLabel("<b>Month:</b>"))
        vault_controls.addWidget(self.month_dropdown)
        vault_controls.addStretch()
        vault_controls.addWidget(self.new_slot_input)
        vault_controls.addWidget(self.create_slot_btn)
        
        self.vault_layout.addLayout(vault_controls)
        self.vault_layout.addSpacing(20)
        
        # Calendar Grid
        self.vault_layout.addWidget(QLabel("<h3>Select a day to preload content:</h3>"))
        
        self.calendar_grid = QGridLayout()
        self.calendar_grid.setSpacing(10)
        
        self.day_buttons = {}
        for day in range(1, 32):
            btn = QPushButton(str(day))
            btn.setFixedSize(60, 60)
            btn.setStyleSheet("background-color: #1e293b; color: white; border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; padding: 0px;")
            btn.clicked.connect(lambda checked, d=day: self.open_vault_modal(d))
            row = (day - 1) // 7
            col = (day - 1) % 7
            self.calendar_grid.addWidget(btn, row, col)
            self.day_buttons[day] = btn
            
        self.vault_layout.addLayout(self.calendar_grid)
        self.vault_layout.addStretch()
        
        self.right_panel.addTab(self.vault_panel, "Content Vault")
        self.refresh_slots()

    def get_slots_dir(self):
        from pathlib import Path
        slots_dir = Path.home() / "Downloads" / "aha" / "Slots"
        slots_dir.mkdir(parents=True, exist_ok=True)
        return slots_dir
        
    def refresh_slots(self):
        slots_dir = self.get_slots_dir()
        current_slot = self.slot_dropdown.currentText()
        self.slot_dropdown.clear()
        
        slots = sorted([p.name for p in slots_dir.iterdir() if p.is_dir()])
        if not slots:
            self.slot_dropdown.addItem("No slots found")
            self.slot_dropdown.setEnabled(False)
        else:
            self.slot_dropdown.setEnabled(True)
            self.slot_dropdown.addItems(slots)
            if current_slot in slots:
                self.slot_dropdown.setCurrentText(current_slot)
                
        self.load_vault_calendar()
        
    def create_vault_slot(self):
        slot_name = self.new_slot_input.text().strip()
        safe_name = "".join([c for c in slot_name if c.isalnum() or c in (" ", "-", "_")]).strip()
        if safe_name:
            slot_dir = self.get_slots_dir() / safe_name
            slot_dir.mkdir(parents=True, exist_ok=True)
            self.new_slot_input.clear()
            self.refresh_slots()
            idx = self.slot_dropdown.findText(safe_name)
            if idx >= 0:
                self.slot_dropdown.setCurrentIndex(idx)

    def load_vault_calendar(self):
        slot = self.slot_dropdown.currentText()
        if not slot or slot == "No slots found":
            for btn in self.day_buttons.values():
                btn.setText(btn.text().split("\n")[0])
            return
            
        slot_dir = self.get_slots_dir() / slot
        
        import datetime, calendar
        try:
            year = int(self.year_dropdown.currentText())
            month = int(self.month_dropdown.currentText())
        except ValueError:
            year, month = datetime.date.today().year, datetime.date.today().month
            
        _, num_days = calendar.monthrange(year, month)
        target_dir = slot_dir / str(year) / str(month)
        
        for day in range(1, 32):
            btn = self.day_buttons[day]
            if day > num_days:
                btn.hide()
                continue
            else:
                btn.show()
                
            has_text, has_img, has_vid = False, False, False
            
            # Check Text
            txt_path = target_dir / "Texts" / f"{day}.txt"
            if txt_path.exists() and txt_path.stat().st_size > 0: has_text = True
                
            # Check Image
            img_dir = target_dir / "Images"
            if img_dir.exists():
                for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif"]:
                    if (img_dir / f"{day}{ext}").exists():
                        has_img = True
                        break
                        
            # Check Video
            vid_dir = target_dir / "Videos"
            if vid_dir.exists():
                for ext in [".mp4", ".mov", ".webm"]:
                    if (vid_dir / f"{day}{ext}").exists():
                        has_vid = True
                        break
                        
            # Update button text to show indicators
            base_text = str(day)
            indicators = []
            if has_text: indicators.append("📝")
            if has_img: indicators.append("🖼️")
            if has_vid: indicators.append("🎥")
            
            if indicators:
                btn.setText(f"{base_text}\n{' '.join(indicators)}")
                btn.setStyleSheet("background-color: #334155; color: white; border: 1px solid #3b82f6; border-radius: 8px; padding: 0px;")
            else:
                btn.setText(base_text)
                btn.setStyleSheet("background-color: #1e293b; color: white; border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; padding: 0px;")

    def open_vault_modal(self, day):
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        import os
        
        slot = self.slot_dropdown.currentText()
        if not slot or slot == "No slots found":
            QMessageBox.warning(self, "No Slot", "Please create or select a slot first.")
            return
            
        year = self.year_dropdown.currentText()
        month = self.month_dropdown.currentText()
            
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Upload Content for {slot} - {year}/{month}/{day}")
        dialog.setMinimumWidth(450)
        
        layout = QVBoxLayout(dialog)
        
        layout.addWidget(QLabel("<b>Caption:</b>"))
        text_edit = QTextEdit()
        
        # Load existing text
        target_dir = self.get_slots_dir() / slot / year / month
        txt_path = target_dir / "Texts" / f"{day}.txt"
        if txt_path.exists():
            text_edit.setPlainText(txt_path.read_text(encoding="utf-8"))
        layout.addWidget(text_edit)
        
        # Image
        img_layout = QHBoxLayout()
        img_label = QLabel("Image: None")
        img_btn = QPushButton("Select Image")
        img_preview_btn = QPushButton("👁️")
        img_preview_btn.setFixedSize(30, 30)
        img_preview_btn.setStyleSheet("padding: 0px;")
        img_preview_btn.hide()
        selected_img = [None]
        
        # Check existing image
        img_dir = target_dir / "Images"
        existing_img = None
        if img_dir.exists():
            for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif"]:
                p = img_dir / f"{day}{ext}"
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
        vid_preview_btn = QPushButton("👁️")
        vid_preview_btn.setFixedSize(30, 30)
        vid_preview_btn.setStyleSheet("padding: 0px;")
        vid_preview_btn.hide()
        selected_vid = [None]
        
        # Check existing video
        vid_dir = target_dir / "Videos"
        existing_vid = None
        if vid_dir.exists():
            for ext in [".mp4", ".mov", ".webm"]:
                p = vid_dir / f"{day}{ext}"
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
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("background-color: #ef4444;")
        
        cancel_btn.clicked.connect(dialog.reject)
        
        def save_content():
            import shutil
            import os
            txt = text_edit.toPlainText().strip()
            # Save Text
            if txt:
                txt_path = target_dir / "Texts" / f"{day}.txt"
                txt_path.parent.mkdir(parents=True, exist_ok=True)
                txt_path.write_text(txt, encoding="utf-8")
            else:
                txt_path = target_dir / "Texts" / f"{day}.txt"
                if txt_path.exists(): txt_path.unlink()
                
            # Save Image
            if selected_img[0]:
                img_dir = target_dir / "Images"
                img_dir.mkdir(parents=True, exist_ok=True)
                for p in img_dir.glob(f"{day}.*"): p.unlink()
                ext = os.path.splitext(selected_img[0])[1] or ".png"
                shutil.copy2(selected_img[0], img_dir / f"{day}{ext}")
                
            # Save Video
            if selected_vid[0]:
                vid_dir = target_dir / "Videos"
                vid_dir.mkdir(parents=True, exist_ok=True)
                for p in vid_dir.glob(f"{day}.*"): p.unlink()
                ext = os.path.splitext(selected_vid[0])[1] or ".mp4"
                shutil.copy2(selected_vid[0], vid_dir / f"{day}{ext}")
                
            dialog.accept()
            self.load_vault_calendar()
            
        save_btn.clicked.connect(save_content)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        dialog.exec()

    def append_message(self, text, sender="Agent"):
        import uuid
        import re
        msg = {
            "id": str(uuid.uuid4()),
            "sender": sender,
            "text": text,
            "collapses": {}
        }
        
        # Parse [COLLAPSE:Title:Content] tags
        def replacer(match):
            c_id = str(uuid.uuid4())
            title = match.group(1)
            content = match.group(2)
            msg["collapses"][c_id] = {"title": title, "content": content, "expanded": False}
            return f'<a href="collapse:{msg["id"]}:{c_id}" style="color: #fbbf24; text-decoration: none; font-weight: bold;">[ + {title} ]</a>'
            
        parsed_text = re.sub(r'\[COLLAPSE:(.*?):(.*?)]', replacer, text, flags=re.DOTALL)
        # Convert newlines to breaks for regular text
        parsed_text = parsed_text.replace('\n', '<br>')
        msg["parsed_text"] = parsed_text
        self.chat_messages.append(msg)
        self.render_chat()

    def render_chat(self):
        import re
        html = "<div style='font-family: Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, sans-serif; padding: 8px 16px;'>"
        for i, msg in enumerate(self.chat_messages):
            text = msg["parsed_text"]
            for cid, cdata in msg["collapses"].items():
                if cdata["expanded"]:
                    expanded_html = f'<div style="padding: 8px 0 8px 12px; margin-top: 6px; margin-bottom: 6px; font-size: 13px; border-left: 2px solid #3f3f46; color: #a1a1aa;">{cdata["content"]}</div><a href="collapse:{msg["id"]}:{cid}" style="color: #64748b; text-decoration: underline; font-size: 12px;">[ Collapse ]</a>'
                    text = re.sub(rf'<a href="collapse:{msg["id"]}:{cid}".*?</a>', expanded_html, text)
                    
            if msg["sender"] == "User":
                html += f'<div style="padding: 14px 0 14px 0; border-bottom: 1px solid #1e1e21;"><div style="font-size: 13px; font-weight: 600; color: #a1a1aa; margin-bottom: 6px;">You</div><div style="color: #ececf1; font-size: 15px; line-height: 1.7;">{text}</div></div>'
                
            elif msg["sender"] == "System":
                html += f'<div style="padding: 6px 0; text-align: center;"><span style="color: #52525b; font-size: 12px; font-style: italic;">{text}</span></div>'
                
            elif msg["sender"] == "Error":
                html += f'<div style="padding: 14px 0 14px 0; border-bottom: 1px solid #1e1e21;"><div style="font-size: 13px; font-weight: 600; color: #ef4444; margin-bottom: 6px;">Error</div><div style="color: #fca5a5; font-size: 15px; line-height: 1.7;">{text}</div></div>'
                
            else:
                # AHA
                html += f'<div style="padding: 14px 0 14px 0; border-bottom: 1px solid #1e1e21;"><div style="font-size: 13px; font-weight: 600; color: #64748b; margin-bottom: 6px;">AHA</div><div style="color: #d4d4d8; font-size: 15px; line-height: 1.7;">{text}</div></div>'
                
        html += "</div>"
        self.chat_history.setHtml(html)
        
        # Scroll to bottom after layout
        import threading
        def scroll_down():
            scrollbar = self.chat_history.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        QTimer.singleShot(10, scroll_down)

    def handle_link_click(self, url: QUrl):
        url_str = url.toString()
        if url_str.startswith("collapse:"):
            _, msg_id, c_id = url_str.split(":", 2)
            for msg in self.chat_messages:
                if msg["id"] == msg_id and c_id in msg["collapses"]:
                    msg["collapses"][c_id]["expanded"] = not msg["collapses"][c_id]["expanded"]
                    self.render_chat()
                    break

    def update_chrome_browser_coordinates(self):
        """Poll Chrome window bounds and tell the server where to capture."""
        import subprocess
        try:
            script = '''
            tell application "Google Chrome"
                if not (exists window 1) then return "none"
                set b to bounds of window 1
                return (item 1 of b) & "," & (item 2 of b) & "," & (item 3 of b) & "," & (item 4 of b)
            end tell
            '''
            result = subprocess.check_output(
                ['osascript', '-e', script], timeout=1
            ).decode().strip()
            if result == "none" or not result:
                return
            parts = [int(x.strip()) for x in result.split(',')]
            x1, y1, x2, y2 = parts
            payload = {"x": x1, "y": y1, "width": x2 - x1, "height": y2 - y1}
            requests.post(f"{SERVER_URL}/api/config/set_browser_region", json=payload, timeout=0.5)
        except Exception:
            pass  # Chrome not running or server not ready

    def send_message(self):
        text = self.chat_input.text().strip()
        if not text:
            return
            
        self.append_message(text, sender="User")
        self.chat_input.clear()
        self.send_button.setEnabled(False)
        self.chat_input.setEnabled(False)
        
        self.start_worker(f"{SERVER_URL}/api/agent/chat", {"text": text, "is_native_app": True})

    def resume_workflow(self):
        self.resume_button.setVisible(False)
        self.append_message("Resuming workflow...", sender="System")
        self.start_worker(f"{SERVER_URL}/api/agent/resume", {"text": "USER_RESUMED", "is_native_app": True})

    def clear_chat(self):
        self.chat_history.clear()
        self.chat_messages.clear()
        self.append_message("AHA chat and context cleared.", sender="System")
        
        # Clear backend state as well
        threading.Thread(target=lambda: requests.post(f"{SERVER_URL}/api/agent/clear", timeout=1), daemon=True).start()

    def add_browser_tab(self, url="https://google.com"):
        browser = QWebEngineView()
        page = WebEnginePage(self.browser_profile, browser)
        browser.setPage(page)
        
        idx = self.browser_tabs.addTab(browser, "Loading...")
        self.browser_tabs.setCurrentIndex(idx)
        
        browser.urlChanged.connect(lambda qurl, browser=browser: self.on_url_changed(qurl, browser))
        browser.titleChanged.connect(lambda title, browser=browser: self.on_title_changed(title, browser))
        
        browser.setUrl(QUrl(url))
        
    def close_browser_tab(self, index):
        if self.browser_tabs.count() > 1:
            self.browser_tabs.widget(index).deleteLater()
            self.browser_tabs.removeTab(index)
            
    def current_browser(self):
        return self.browser_tabs.currentWidget()
        
    def on_browser_tab_changed(self, index):
        browser = self.current_browser()
        if browser and browser.url().toString():
            self.url_input.setText(browser.url().toString())
            
    def on_title_changed(self, title, browser):
        idx = self.browser_tabs.indexOf(browser)
        if idx >= 0:
            short_title = title[:15] + "..." if len(title) > 15 else title
            self.browser_tabs.setTabText(idx, short_title)

    def navigate_to_url(self):
        browser = self.current_browser()
        if not browser:
            return
            
        url_text = self.url_input.text().strip()
        if not url_text.startswith("http"):
            url_text = f"https://{url_text}"
            
        browser.setUrl(QUrl(url_text))

    def on_url_changed(self, url, browser):
        """Update the URL input when the browser navigates."""
        if browser == self.current_browser():
            self.url_input.setText(url.toString())

    def start_worker(self, endpoint, payload):
        self.worker = AgentWorker(endpoint, payload)
        self.worker.signals.response_received.connect(self.handle_response)
        self.worker.signals.error_occurred.connect(self.handle_error)
        threading.Thread(target=self.worker.run, daemon=True).start()

    def handle_response(self, data):
        self.send_button.setEnabled(True)
        self.chat_input.setEnabled(True)
        self.chat_input.setFocus()
        
        if data.get("status") == "error":
            error_msg = data.get("message")
            if not error_msg and data.get("messages"):
                error_msg = data.get("messages")[-1] # Get the latest system error
            self.append_message(error_msg or "Unknown error", sender="Error")
            return
            
        # Handle navigation — agent now opens URLs in Chrome directly
        if "url_to_open" in data:
            # Legacy: agent used to send this to load in embedded browser.
            # Now the agent opens Chrome directly, just show info in chat.
            self.append_message(f"Opening in Chrome: {data['url_to_open']}", sender="System")
            
        for msg in data.get("messages", []):
            self.append_message(msg, sender="Agent")
            
        if data.get("is_paused"):
            self.append_message("AHA is paused. Complete manual steps, then click Resume.", sender="System")
            self.is_paused = True
            self.resume_button.setVisible(True)
        elif data.get("is_done"):
            self.append_message("AHA has completed the task!", sender="System")
        elif data.get("is_asking"):
            self.append_message("AHA is waiting for your response...", sender="System")
        else:
            self.append_message("AHA is waiting 5 seconds before the next step...", sender="System")
            QTimer.singleShot(5000, lambda: self.start_worker(f"{SERVER_URL}/api/agent/chat", {"text": "Please continue to the next step.", "is_native_app": True}))

    def handle_error(self, error):
        self.send_button.setEnabled(True)
        self.chat_input.setEnabled(True)
        self.append_message(f"Connection error: {error}. Is the server running?", sender="Error")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Run the window
    window = CompanionApp()
    window.show()
    sys.exit(app.exec())
