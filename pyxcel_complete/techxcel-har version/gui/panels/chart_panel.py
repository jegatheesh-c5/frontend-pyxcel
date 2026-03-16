"""
PyXcel — Chart & Graph Panel
Generate charts from Excel data with live preview.
"""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QLineEdit, QFrame,
    QScrollArea, QSizePolicy, QStackedWidget
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QPixmap


CHART_TYPES = [
    ("📊  Bar Chart",       "bar"),
    ("📈  Line Chart",      "line"),
    ("🥧  Pie Chart",       "pie"),
    ("⚡  Scatter Plot",    "scatter"),
    ("🏔️   Area Chart",     "area"),
    ("📉  Histogram",       "histogram"),
]


# ── Minimal chat bubble ───────────────────────────────────────────────────────
class _ChatBubble(QFrame):
    def __init__(self, text: str, is_user: bool, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)

        bubble = QLabel(text)
        bubble.setWordWrap(True)
        bubble.setTextInteractionFlags(Qt.TextSelectableByMouse)
        bubble.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        bubble.setMaximumWidth(320)

        if is_user:
            bubble.setStyleSheet(
                "QLabel{background-color:#1e2035;color:#c0c4ff;"
                "border-radius:10px;border-bottom-right-radius:3px;"
                "padding:8px 12px;font-size:12px;}"
            )
            av = QLabel("You")
            av.setFixedWidth(32)
            av.setAlignment(Qt.AlignTop | Qt.AlignCenter)
            av.setStyleSheet(
                "QLabel{background-color:#7c83ff;color:white;border-radius:8px;"
                "padding:3px;font-size:10px;font-weight:bold;margin-left:6px;}"
            )
            layout.addStretch()
            layout.addWidget(bubble)
            layout.addWidget(av)
        else:
            bubble.setStyleSheet(
                "QLabel{background-color:#162820;color:#a0d4b4;"
                "border-radius:10px;border-bottom-left-radius:3px;"
                "padding:8px 12px;font-size:12px;}"
            )
            av = QLabel("AI")
            av.setFixedWidth(32)
            av.setAlignment(Qt.AlignTop | Qt.AlignCenter)
            av.setStyleSheet(
                "QLabel{background-color:#4caf81;color:white;border-radius:8px;"
                "padding:3px;font-size:10px;font-weight:bold;margin-right:6px;}"
            )
            layout.addWidget(av)
            layout.addWidget(bubble)
            layout.addStretch()


# ── Typing indicator ─────────────────────────────────────────────────────────
class _TypingIndicator(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        av = QLabel("AI")
        av.setFixedWidth(32)
        av.setAlignment(Qt.AlignCenter)
        av.setStyleSheet(
            "QLabel{background-color:#4caf81;color:white;border-radius:8px;"
            "padding:3px;font-size:10px;font-weight:bold;margin-right:6px;}"
        )
        self.dots = QLabel("Thinking .")
        self.dots.setStyleSheet(
            "QLabel{background-color:#162820;color:#4caf81;"
            "border-radius:10px;padding:8px 12px;font-size:12px;}"
        )
        layout.addWidget(av)
        layout.addWidget(self.dots)
        layout.addStretch()
        self._state = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def start(self):  self._timer.start(400)
    def stop(self):   self._timer.stop()

    def _tick(self):
        self.dots.setText(["Thinking .", "Thinking ..", "Thinking ..."][self._state % 3])
        self._state += 1


class ChartPanel(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window  = main_window
        self.current_file = None
        self.sheet_names  = []
        self.columns      = []
        self.preview_data = None
        self._chat_history  = []
        self._chat_bubbles  = []
        self._build_ui()

    # ── Build UI ────────────────────────────────────────────
    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Left side — scrollable chart content
        root.addWidget(self._build_left_panel(), stretch=1)

        # Right side — collapsible chat button
        self.chat_toggle_btn = QPushButton("💬")
        self.chat_toggle_btn.setFixedSize(50, 50)
        self.chat_toggle_btn.setCursor(Qt.PointingHandCursor)
        self.chat_toggle_btn.clicked.connect(self._toggle_chat)
        self.chat_toggle_btn.setStyleSheet(
            "QPushButton{background-color:#7c83ff;color:white;border:none;"
            "border-radius:8px;font-size:20px;font-weight:bold;}"
            "QPushButton:hover{background-color:#6b72ff;}"
        )

        # Chat panel container (initially hidden)
        self.chat_panel = self._build_right_chat()
        self.chat_panel.hide()

        # Right side container with button and chat
        right_container = QWidget()
        right_layout = QHBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_layout.addWidget(self.chat_panel, stretch=1)
        right_layout.addWidget(self.chat_toggle_btn)

        root.addWidget(right_container)

    # ── LEFT: scrollable chart content ───────────────────────
    def _build_left_panel(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")

        inner = QWidget()
        inner.setStyleSheet("background:transparent;")
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(16)

        # ── Header ──
        badge = QLabel("CHART & GRAPH CREATOR")
        badge.setStyleSheet("background-color:#1e2035;color:#7c83ff;border-radius:12px;padding:3px 12px;font-size:10px;font-weight:bold;letter-spacing:1px;")
        badge.setFixedHeight(24)

        title = QLabel("Chart Generator")
        font  = QFont(); font.setPointSize(18); font.setBold(True)
        title.setFont(font)

        subtitle = QLabel(
            "Select columns and chart type to generate beautiful charts. "
            "Charts are embedded directly into your Excel file."
        )
        subtitle.setStyleSheet("color:#555;font-size:12px;")
        subtitle.setWordWrap(True)

        layout.addWidget(badge)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self._divider())

        # ── File Status ──
        self.file_status = QLabel("⚠️  No file loaded")
        self.file_status.setStyleSheet("color:#ff9800;font-size:12px;background:#1e1a0e;border-radius:6px;padding:8px 12px;")
        layout.addWidget(self.file_status)

        # ── Main Content ──
        content_row = QHBoxLayout()
        content_row.setSpacing(20)
        content_row.addWidget(self._build_controls(), stretch=2)
        content_row.addWidget(self._build_preview_panel(), stretch=3)
        layout.addLayout(content_row)

        layout.addStretch()
        scroll.setWidget(inner)
        return scroll

    # ── RIGHT: embedded chat panel ────────────────────────────
    def _build_right_chat(self):
        panel = QWidget()
        panel.setStyleSheet("background-color:#0f1117;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 30, 24, 20)
        layout.setSpacing(12)

        # Header
        chat_title = QLabel("💬  Chat with Data")
        font = QFont(); font.setPointSize(14); font.setBold(True)
        chat_title.setFont(font)

        chat_sub = QLabel("Ask questions about your spreadsheet")
        chat_sub.setStyleSheet("color:#555;font-size:11px;")

        clear_btn = QPushButton("Clear")
        clear_btn.setFixedWidth(60)
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.clicked.connect(self._clear_chat)
        clear_btn.setStyleSheet(
            "QPushButton{background:transparent;color:#555;border:1px solid #2a2d3e;"
            "border-radius:6px;padding:4px 8px;font-size:11px;}"
            "QPushButton:hover{color:#f44336;border-color:#5a2020;background:#3d1a1a;}"
        )

        title_row = QHBoxLayout()
        title_row.addWidget(chat_title)
        title_row.addStretch()
        title_row.addWidget(clear_btn)

        layout.addLayout(title_row)
        layout.addWidget(chat_sub)

        # File status bar
        self.chat_file_status = QLabel("⚠️  Load a file to start chatting")
        self.chat_file_status.setStyleSheet(
            "color:#ff9800;font-size:11px;background:#1e1a0e;"
            "border-radius:6px;padding:6px 10px;"
        )
        self.chat_file_status.setWordWrap(True)
        layout.addWidget(self.chat_file_status)

        # Divider
        div = QFrame(); div.setFrameShape(QFrame.HLine)
        div.setStyleSheet("background:#2a2d3e;max-height:1px;border:none;")
        layout.addWidget(div)

        # Chat scroll area
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setFrameShape(QFrame.NoFrame)
        self.chat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.chat_scroll.setStyleSheet(
            "QScrollArea{background-color:#13151f;border:1px solid #2a2d3e;"
            "border-radius:10px;}"
        )

        self.chat_container = QWidget()
        self.chat_container.setStyleSheet("background-color:#13151f;")
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(12, 12, 12, 12)
        self.chat_layout.setSpacing(6)
        self.chat_layout.addStretch()

        self.chat_scroll.setWidget(self.chat_container)
        layout.addWidget(self.chat_scroll, stretch=1)

        # Typing indicator
        self.typing_indicator = _TypingIndicator()
        self.typing_indicator.hide()
        layout.addWidget(self.typing_indicator)

        # Starter chips
        self.starters_widget = self._build_starter_chips()
        layout.addWidget(self.starters_widget)

        # Input bar
        input_frame = QFrame()
        input_frame.setStyleSheet(
            "QFrame{background-color:#1a1d2e;border:1px solid #2a2d3e;border-radius:10px;}"
        )
        input_frame.setFixedHeight(52)
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(12, 8, 8, 8)
        input_layout.setSpacing(8)

        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Ask about your data...")
        self.chat_input.setStyleSheet(
            "QLineEdit{background:transparent;border:none;color:#e0e0e0;font-size:12px;}"
        )
        self.chat_input.returnPressed.connect(self._send_chat)

        self.send_btn = QPushButton("➤")
        self.send_btn.setFixedSize(34, 34)
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.clicked.connect(self._send_chat)
        self.send_btn.setStyleSheet(
            "QPushButton{background-color:#7c83ff;color:white;border:none;"
            "border-radius:8px;font-size:14px;font-weight:bold;}"
            "QPushButton:hover{background-color:#6b72ff;}"
            "QPushButton:disabled{background-color:#2a2d3e;color:#555;}"
        )

        input_layout.addWidget(self.chat_input)
        input_layout.addWidget(self.send_btn)

        layout.addWidget(input_frame)

        return panel
    def _build_controls(self):
        frame = QFrame()
        frame.setStyleSheet("QFrame{background-color:#1a1d2e;border:1px solid #2a2d3e;border-radius:12px;}")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Sheet
        lbl_sheet = QLabel("Sheet:")
        lbl_sheet.setStyleSheet("color:#888;font-size:11px;")
        self.sheet_combo = QComboBox()
        self.sheet_combo.setStyleSheet(self._combo_style())
        self.sheet_combo.currentTextChanged.connect(self._on_sheet_changed)
        self.sheet_combo.addItem("Sheet1")

        # Chart type
        lbl_type = QLabel("Chart Type:")
        lbl_type.setStyleSheet("color:#888;font-size:11px;")
        self.type_combo = QComboBox()
        self.type_combo.setStyleSheet(self._combo_style())
        for label, value in CHART_TYPES:
            self.type_combo.addItem(label, value)
        self.type_combo.currentIndexChanged.connect(self._on_settings_changed)

        # X Column
        lbl_x = QLabel("X Axis (Category):")
        lbl_x.setStyleSheet("color:#888;font-size:11px;")
        self.x_combo = QComboBox()
        self.x_combo.setStyleSheet(self._combo_style())
        self.x_combo.currentIndexChanged.connect(self._on_settings_changed)

        # Y Column
        lbl_y = QLabel("Y Axis (Values):")
        lbl_y.setStyleSheet("color:#888;font-size:11px;")
        self.y_combo = QComboBox()
        self.y_combo.setStyleSheet(self._combo_style())
        self.y_combo.currentIndexChanged.connect(self._on_settings_changed)

        # Chart Title
        lbl_title = QLabel("Chart Title (optional):")
        lbl_title.setStyleSheet("color:#888;font-size:11px;")
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Auto-generated if left blank")
        self.title_input.setStyleSheet("""
            QLineEdit {
                background-color: #13151f;
                border: 1px solid #2a2d3e;
                border-radius: 8px;
                padding: 8px 12px;
                color: #e0e0e0;
                font-size: 12px;
            }
            QLineEdit:focus { border-color: #7c83ff; }
        """)

        # Status
        self.ctrl_status = QLabel("Ready")
        self.ctrl_status.setStyleSheet("color:#555;font-size:11px;")

        # Buttons
        self.preview_btn = QPushButton("👁  Preview")
        self.preview_btn.setFixedHeight(38)
        self.preview_btn.setCursor(Qt.PointingHandCursor)
        self.preview_btn.clicked.connect(self._generate_preview)
        self.preview_btn.setEnabled(False)
        self.preview_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e2035;
                color: #7c83ff;
                border: 1px solid #2a2d3e;
                border-radius: 8px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #252840; border-color: #7c83ff; }
            QPushButton:disabled { color: #333; border-color: #1e2035; }
        """)

        self.save_btn = QPushButton("💾  Save to Excel")
        self.save_btn.setFixedHeight(38)
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.clicked.connect(self._save_chart)
        self.save_btn.setEnabled(False)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #7c83ff;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #6b72ff; }
            QPushButton:disabled { background-color: #2a2d3e; color: #555; }
        """)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addWidget(self.preview_btn)
        btn_row.addWidget(self.save_btn)

        layout.addWidget(lbl_sheet)
        layout.addWidget(self.sheet_combo)
        layout.addWidget(self._mini_divider())
        layout.addWidget(lbl_type)
        layout.addWidget(self.type_combo)
        layout.addWidget(lbl_x)
        layout.addWidget(self.x_combo)
        layout.addWidget(lbl_y)
        layout.addWidget(self.y_combo)
        layout.addWidget(lbl_title)
        layout.addWidget(self.title_input)
        layout.addWidget(self._mini_divider())
        layout.addWidget(self.ctrl_status)
        layout.addLayout(btn_row)
        layout.addStretch()

        return frame

    # ── Preview Panel ────────────────────────────────────────
    def _build_preview_panel(self):
        frame = QFrame()
        frame.setStyleSheet("QFrame{background-color:#13151f;border:1px solid #2a2d3e;border-radius:12px;}")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        header_row = QHBoxLayout()
        preview_lbl = QLabel("Chart Preview")
        preview_lbl.setStyleSheet("color:#888;font-size:12px;font-weight:bold;background:transparent;")
        self.preview_status = QLabel("Configure settings and click Preview")
        self.preview_status.setStyleSheet("color:#3a3d5e;font-size:11px;background:transparent;")
        header_row.addWidget(preview_lbl)
        header_row.addStretch()
        header_row.addWidget(self.preview_status)
        layout.addLayout(header_row)

        # Preview image area
        self.preview_stack = QStackedWidget()

        # Empty state
        empty = QWidget()
        empty.setStyleSheet("background:transparent;")
        empty_layout = QVBoxLayout(empty)
        empty_layout.setAlignment(Qt.AlignCenter)
        empty_icon  = QLabel("📊")
        empty_icon.setAlignment(Qt.AlignCenter)
        empty_icon.setStyleSheet("font-size:48px;background:transparent;")
        empty_msg   = QLabel("Chart preview will appear here")
        empty_msg.setAlignment(Qt.AlignCenter)
        empty_msg.setStyleSheet("color:#3a3d5e;font-size:13px;background:transparent;")
        empty_layout.addWidget(empty_icon)
        empty_layout.addWidget(empty_msg)

        # Image display
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("background:transparent;")
        self.preview_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.preview_stack.addWidget(empty)
        self.preview_stack.addWidget(self.preview_label)
        layout.addWidget(self.preview_stack, stretch=1)

        return frame

    # ── Actions ──────────────────────────────────────────────
    def _generate_preview(self):
        if not self.current_file:
            return

        sheet      = self.sheet_combo.currentText()
        chart_type = self.type_combo.currentData()
        x_col      = self.x_combo.currentText()
        y_col      = self.y_combo.currentText()
        title      = self.title_input.text().strip()

        if not x_col or not y_col:
            self.preview_status.setText("Select X and Y columns first")
            return

        self.preview_btn.setEnabled(False)
        self.preview_btn.setText("⏳  Loading...")
        self.ctrl_status.setText("Generating preview...")
        self.preview_status.setText("Rendering chart...")

        from gui.workers.agent_worker import ChartPreviewWorker
        self.preview_worker = ChartPreviewWorker(
            self.current_file, sheet,
            chart_type, x_col, y_col, title
        )
        self.preview_worker.preview_ready.connect(self._on_preview_ready)
        self.preview_worker.result.connect(self._on_preview_result)
        self.preview_worker.error.connect(self._on_error)
        self.preview_worker.start()

    def _on_preview_ready(self, img_bytes: bytes):
        pixmap = QPixmap()
        pixmap.loadFromData(img_bytes)
        scaled = pixmap.scaled(
            680, 380,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.preview_label.setPixmap(scaled)
        self.preview_stack.setCurrentIndex(1)
        self.preview_data = img_bytes

    def _on_preview_result(self, data):
        self.preview_btn.setEnabled(True)
        self.preview_btn.setText("👁  Preview")
        if data["status"] == "success":
            self.ctrl_status.setText("Preview ready ✓")
            self.preview_status.setText("✓ Preview generated")
            self.save_btn.setEnabled(True)
        else:
            self.ctrl_status.setText("Preview failed ✗")
            self.preview_status.setText(
                f"❌  {data.get('message', 'Error')}"
            )

    def _save_chart(self):
        if not self.current_file:
            return

        sheet      = self.sheet_combo.currentText()
        chart_type = self.type_combo.currentData()
        x_col      = self.x_combo.currentText()
        y_col      = self.y_combo.currentText()
        title      = self.title_input.text().strip()

        self.save_btn.setEnabled(False)
        self.save_btn.setText("⏳  Saving...")
        self.ctrl_status.setText("Embedding chart in Excel...")

        from gui.workers.agent_worker import ChartWorker
        self.worker = ChartWorker(
            self.current_file, sheet,
            chart_type, x_col, y_col, title
        )
        self.worker.status.connect(
            lambda m: self.ctrl_status.setText(m)
        )
        self.worker.result.connect(self._on_save_result)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_save_result(self, data):
        self.save_btn.setEnabled(True)
        self.save_btn.setText("💾  Save to Excel")
        if data["status"] == "success":
            self.ctrl_status.setText("Chart saved ✓")
            self.main_window.set_status(
                f"Chart saved to '{data.get('output_sheet')}' sheet ✓"
            )
            if hasattr(self.main_window, "spreadsheet_panel"):
                self.main_window.spreadsheet_panel._reload()
        else:
            self.ctrl_status.setText("Save failed ✗")
            self.main_window.set_status(
                f"Chart save failed: {data.get('message')}"
            )

    def _on_settings_changed(self):
        """Auto-trigger preview after short delay when settings change."""
        if self.current_file and self.x_combo.currentText() and self.y_combo.currentText():
            self.preview_btn.setEnabled(True)

    def _on_sheet_changed(self, sheet):
        if self.current_file and sheet:
            self._load_columns(sheet)

    def _load_columns(self, sheet):
        try:
            import pandas as pd
            df = pd.read_excel(self.current_file, sheet_name=sheet)
            self.columns = list(df.columns)
            numeric = [
                c for c in self.columns
                if pd.api.types.is_numeric_dtype(df[c])
            ]

            self.x_combo.clear()
            self.y_combo.clear()

            for c in self.columns:
                self.x_combo.addItem(str(c))
            for c in numeric if numeric else self.columns:
                self.y_combo.addItem(str(c))

            self.preview_btn.setEnabled(True)
        except Exception as e:
            self.ctrl_status.setText(f"Error: {str(e)}")

    def _on_error(self, msg):
        self.preview_btn.setEnabled(True)
        self.preview_btn.setText("👁  Preview")
        self.save_btn.setEnabled(True)
        self.save_btn.setText("💾  Save to Excel")
        self.ctrl_status.setText(f"Error ✗")
        self.preview_status.setText(f"❌  {msg[:60]}")
        self.main_window.set_status(f"Error: {msg}")

    def on_file_loaded(self, path):
        self.current_file = path
        filename = os.path.basename(path)
        self.file_status.setText(f"✅  File loaded: {filename}")
        self.file_status.setStyleSheet(
            "color:#4caf81;font-size:12px;background:#0e1e14;border-radius:6px;padding:8px 12px;"
        )
        from core.workbook_inspector import get_sheet_names
        sheets = get_sheet_names(path)
        self.sheet_combo.clear()
        for s in sheets:
            self.sheet_combo.addItem(s)
        self.sheet_names = sheets
        if sheets:
            self._load_columns(sheets[0])
        self._update_file_status()

    # ── Chat Methods ──────────────────────────────────────────
    def _clear_chat(self):
        for bubble in self._chat_bubbles:
            bubble.hide()
            bubble.setParent(None)
        self._chat_bubbles.clear()
        self._chat_history.clear()
        self.chat_layout.addStretch()

    def _send_chat(self):
        text = self.chat_input.text().strip()
        if not text:
            return
        self.chat_input.clear()
        self._add_chat_bubble(text, True)
        self._show_typing()
        from gui.workers.agent_worker import ChatWorker
        self.chat_worker = ChatWorker(self.main_window.current_file, self._chat_history + [text])
        self.chat_worker.result.connect(self._on_chat_result)
        self.chat_worker.error.connect(self._on_chat_error)
        self.chat_worker.start()

    def _add_chat_bubble(self, text, is_user):
        bubble = _ChatBubble(text, is_user)
        self._chat_bubbles.append(bubble)
        self.chat_layout.addWidget(bubble)
        self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        )

    def _show_typing(self):
        self.typing_indicator.show()
        self.typing_indicator.start()
        self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        )

    def _hide_typing(self):
        self.typing_indicator.stop()
        self.typing_indicator.hide()

    def _update_file_status(self):
        if self.main_window.current_file:
            filename = os.path.basename(self.main_window.current_file)
            self.chat_file_status.setText(f"✅  Chatting with: {filename}")
            self.chat_file_status.setStyleSheet(
                "color:#4caf81;font-size:11px;background:#0e1e14;"
                "border-radius:6px;padding:6px 10px;"
            )
        else:
            self.chat_file_status.setText("⚠️  Load a file to start chatting")
            self.chat_file_status.setStyleSheet(
                "color:#ff9800;font-size:11px;background:#1e1a0e;"
                "border-radius:6px;padding:6px 10px;"
            )

    def _build_starter_chips(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        starters = [
            "What is the total of all numeric columns?",
            "Which row has the highest value?",
            "Are there any missing values in this data?",
            "What is the average of the numeric columns?",
        ]

        for q in starters:
            btn = QPushButton(q)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, text=q: self._send_starter(text))
            btn.setStyleSheet(
                "QPushButton{background-color:#1a1d2e;color:#7c83ff;border:1px solid #2a2d3e;"
                "border-radius:8px;padding:6px 10px;font-size:11px;text-align:left;}"
                "QPushButton:hover{background-color:#252840;border-color:#7c83ff;}"
            )
            layout.addWidget(btn)

        return widget

    def _send_starter(self, text):
        self.chat_input.setText(text)
        self._send_chat()

    def _on_chat_result(self, response):
        self._hide_typing()
        self._add_chat_bubble(response, False)
        self._chat_history.append(response)

    def _on_chat_error(self, error):
        self._hide_typing()
        self._add_chat_bubble(f"Error: {error}", False)

    def _toggle_chat(self):
        if self.chat_panel.isVisible():
            self.chat_panel.hide()
            self.chat_toggle_btn.setText("💬")
        else:
            self.chat_panel.show()
            self.chat_toggle_btn.setText("❌")
            self.chat_input.setFocus()

    # ── Helpers ──────────────────────────────────────────────
    def _combo_style(self):
        return (
            "QComboBox{background-color:#13151f;border:1px solid #2a2d3e;"
            "border-radius:8px;padding:7px 12px;color:#e0e0e0;font-size:12px;}"
            "QComboBox:focus{border-color:#7c83ff;}"
            "QComboBox QAbstractItemView{background-color:#1a1d2e;"
            "border:1px solid #2a2d3e;color:#e0e0e0;}"
        )

    def _divider(self):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color:#2a2d3e;max-height:1px;border:none;")
        return line

    def _mini_divider(self):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color:#1e2035;max-height:1px;border:none;")
        return line
