"""
PyXcel — Data Cleaner Panel
"""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QPlainTextEdit,
    QFrame, QScrollArea, QComboBox, QLineEdit
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont


CLEANER_EXAMPLES = [
    ("Duplicates",    "Remove all duplicate rows"),
    ("Missing values","Fill missing numeric values with 0 and missing text with 'Unknown'"),
    ("Whitespace",    "Strip leading and trailing whitespace from all text columns"),
    ("Date format",   "Convert all date columns to YYYY-MM-DD format"),
    ("Phone numbers", "Standardize all phone numbers to +XX-XXX-XXX-XXXX format"),
    ("Column names",  "Rename all column headers to lowercase with underscores"),
    ("Empty rows",    "Delete all rows where every cell is empty"),
    ("Text case",     "Convert all text in the Name column to Title Case"),
    ("Outliers",      "Remove rows where Sales value is more than 3 standard deviations from mean"),
    ("Sort",          "Sort the entire sheet by Date column ascending"),
    ("Currency",      "Remove currency symbols and commas from the Price column and convert to float"),
    ("Email validate","Remove rows where the Email column does not contain a valid email address"),
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


class CleanerPanel(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window  = main_window
        self.current_file = None
        self.sheet_names  = []
        self._chat_history  = []
        self._chat_bubbles  = []
        self._build_ui()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Left side — scrollable cleaner content
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

    # ── LEFT: scrollable cleaner content ─────────────────────
    def _build_left_panel(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        inner_widget = QWidget()
        inner_widget.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(inner_widget)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(14)

        badge = QLabel("AI DATA CLEANER")
        badge.setStyleSheet("background-color:#1e2035;color:#7c83ff;border-radius:12px;padding:3px 12px;font-size:10px;font-weight:bold;letter-spacing:1px;")
        badge.setFixedHeight(24)

        title = QLabel("Data Cleaner")
        font  = QFont(); font.setPointSize(18); font.setBold(True)
        title.setFont(font)

        subtitle = QLabel("Describe cleaning operations in plain English — LLaMA generates pandas code and applies it directly to your sheet.")
        subtitle.setStyleSheet("color:#555;font-size:12px;")
        subtitle.setWordWrap(True)

        layout.addWidget(badge)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self._divider())

        self.file_status = QLabel("⚠️  No file loaded — load an Excel file first")
        self.file_status.setStyleSheet("color:#ff9800;font-size:12px;background:#1e1a0e;border-radius:6px;padding:8px 12px;")
        layout.addWidget(self.file_status)

        # Sheet selector
        sheet_row = QHBoxLayout()
        sheet_label = QLabel("Target sheet:")
        sheet_label.setStyleSheet("color:#888;font-size:12px;")
        sheet_label.setFixedWidth(100)
        self.sheet_combo = QComboBox()
        self.sheet_combo.setFixedWidth(200)
        self.sheet_combo.setStyleSheet("QComboBox{background-color:#1a1d2e;border:1px solid #2a2d3e;border-radius:8px;padding:7px 12px;color:#e0e0e0;font-size:12px;}QComboBox:focus{border-color:#7c83ff;}")
        self.sheet_combo.addItem("Sheet1")
        sheet_row.addWidget(sheet_label)
        sheet_row.addWidget(self.sheet_combo)
        sheet_row.addStretch()
        layout.addLayout(sheet_row)

        # Main content row
        content_row = QHBoxLayout()
        content_row.setSpacing(16)
        content_row.addWidget(self._build_input_area(), stretch=3)
        content_row.addWidget(self._build_examples_panel(), stretch=2)
        layout.addLayout(content_row)

        # Stats bar
        self.stats_bar = self._build_stats_bar()
        layout.addWidget(self.stats_bar)

        # Result box
        layout.addWidget(self._section_label("GENERATED CODE & RESULT"))
        self.result_box = QPlainTextEdit()
        self.result_box.setReadOnly(True)
        self.result_box.setPlaceholderText("Generated pandas code and execution result will appear here...")
        self.result_box.setMinimumHeight(160)
        self.result_box.setStyleSheet("QPlainTextEdit{background-color:#1a1d2e;border:1px solid #2a2d3e;border-left:3px solid #4caf81;border-radius:8px;padding:12px;color:#a0c4a0;font-family:'Consolas','Courier New',monospace;font-size:12px;}")
        layout.addWidget(self.result_box)
        layout.addStretch()

        scroll.setWidget(inner_widget)
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

    def _build_input_area(self):
        frame = QFrame()
        frame.setStyleSheet("QFrame{background-color:#1a1d2e;border:1px solid #2a2d3e;border-radius:12px;}")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        label = QLabel("Describe the cleaning operations:")
        label.setStyleSheet("color:#888;font-size:12px;background:transparent;")

        self.instruction_input = QTextEdit()
        self.instruction_input.setPlaceholderText('e.g. "Remove duplicate rows, fill missing values with 0, trim whitespace"')
        self.instruction_input.setMinimumHeight(100)
        self.instruction_input.setStyleSheet("QTextEdit{background-color:#13151f;border:1px solid #2a2d3e;border-radius:8px;padding:10px;color:#e0e0e0;font-size:13px;}QTextEdit:focus{border-color:#7c83ff;}")

        hint = QLabel("💡  Tip: You can chain multiple operations in one instruction")
        hint.setStyleSheet("color:#3a3d5e;font-size:11px;background:transparent;")

        btn_row = QHBoxLayout()
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color:#555;font-size:11px;background:transparent;")

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setFixedWidth(80)
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.clicked.connect(self._clear)
        self.clear_btn.setStyleSheet("QPushButton{background-color:#1e2035;color:#7c83ff;border:1px solid #2a2d3e;border-radius:8px;padding:9px;font-size:12px;}QPushButton:hover{background-color:#252840;}")

        self.run_btn = QPushButton("🧹  Clean Data")
        self.run_btn.setFixedWidth(150)
        self.run_btn.setCursor(Qt.PointingHandCursor)
        self.run_btn.clicked.connect(self._run_cleaner)
        self.run_btn.setStyleSheet("QPushButton{background-color:#4caf81;color:white;border:none;border-radius:8px;padding:9px 20px;font-size:13px;font-weight:bold;}QPushButton:hover{background-color:#3d9e70;}QPushButton:disabled{background-color:#2a2d3e;color:#555;}")

        btn_row.addWidget(self.status_label)
        btn_row.addStretch()
        btn_row.addWidget(self.clear_btn)
        btn_row.addWidget(self.run_btn)

        layout.addWidget(label)
        layout.addWidget(self.instruction_input)
        layout.addWidget(hint)
        layout.addLayout(btn_row)
        return frame

    def _build_examples_panel(self):
        frame = QFrame()
        frame.setStyleSheet("QFrame{background-color:#13151f;border:1px solid #2a2d3e;border-radius:12px;}")
        frame.setMaximumWidth(320)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        header = QLabel("💡  Example Operations")
        header.setStyleSheet("color:#888;font-size:12px;font-weight:bold;background:transparent;")
        hint = QLabel("Click to append to instructions")
        hint.setStyleSheet("color:#3a3d5e;font-size:11px;background:transparent;")
        layout.addWidget(header)
        layout.addWidget(hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background:transparent;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        inner = QWidget()
        inner.setStyleSheet("background:transparent;")
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(0, 4, 0, 4)
        inner_layout.setSpacing(6)

        for category, prompt in CLEANER_EXAMPLES:
            btn = QPushButton(f"[{category}]\n{prompt}")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, p=prompt: self._append_example(p))
            btn.setStyleSheet("QPushButton{background-color:#1a1d2e;color:#888;border:1px solid #2a2d3e;border-radius:6px;padding:8px 10px;text-align:left;font-size:11px;}QPushButton:hover{background-color:#1e2035;color:#c0c4ff;border-color:#4caf81;}")
            inner_layout.addWidget(btn)

        inner_layout.addStretch()
        scroll.setWidget(inner)
        layout.addWidget(scroll)
        return frame

    def _build_stats_bar(self):
        bar = QFrame()
        bar.setStyleSheet("QFrame{background-color:#1a1d2e;border:1px solid #2a2d3e;border-radius:8px;}")
        bar.setFixedHeight(48)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(32)

        self.before_label = self._stat_chip("Before",  "—")
        self.after_label  = self._stat_chip("After",   "—")
        self.diff_label   = self._stat_chip("Removed", "—")
        self.time_label   = self._stat_chip("Status",  "Waiting")

        for chip in [self.before_label, self.after_label, self.diff_label, self.time_label]:
            layout.addWidget(chip)
        layout.addStretch()
        return bar

    def _stat_chip(self, label, value):
        w = QLabel(f"<span style='color:#444'>{label}: </span><span style='color:#4caf81;font-weight:bold'>{value}</span>")
        w.setStyleSheet("background:transparent;font-size:12px;")
        return w

    def _update_stat(self, chip, label, value, color="#4caf81"):
        chip.setText(f"<span style='color:#444'>{label}: </span><span style='color:{color};font-weight:bold'>{value}</span>")

    def _run_cleaner(self):
        if not self.current_file:
            self.result_box.setPlainText("❌  No file loaded.\nPlease load an Excel file first.")
            return
        instructions = self.instruction_input.toPlainText().strip()
        if not instructions:
            self.result_box.setPlainText("❌  Please enter cleaning instructions first.")
            return
        sheet = self.sheet_combo.currentText().strip() or "Sheet1"
        self.run_btn.setEnabled(False)
        self.run_btn.setText("⏳  Processing...")
        self.status_label.setText("Running...")
        self.result_box.setPlainText("🔄  Sending to LLaMA...\n")
        self._update_stat(self.time_label, "Status", "Processing...", "#ff9800")

        from gui.workers.agent_worker import CleanerWorker
        self.worker = CleanerWorker(self.current_file, sheet, instructions)
        self.worker.status.connect(self._on_status)
        self.worker.result.connect(self._on_result)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_status(self, msg):
        self.status_label.setText(msg)
        self.result_box.appendPlainText(f"  {msg}")
        self.main_window.set_status(msg)

    def _on_result(self, data):
        self.run_btn.setEnabled(True)
        self.run_btn.setText("🧹  Clean Data")
        if data["status"] == "success":
            before = data.get("original_shape", ("?","?"))
            after  = data.get("new_shape",      ("?","?"))
            diff   = before[0] - after[0] if isinstance(before[0], int) else "?"
            self._update_stat(self.before_label, "Before",  f"{before[0]} rows")
            self._update_stat(self.after_label,  "After",   f"{after[0]} rows")
            self._update_stat(self.diff_label,   "Removed", f"{diff} rows", "#f44336" if isinstance(diff,int) and diff>0 else "#4caf81")
            self._update_stat(self.time_label,   "Status",  "Done ✓", "#4caf81")
            self.status_label.setText("Done ✓")
            self.result_box.setPlainText(f"✅  Data cleaned successfully!\n\nBefore: {before[0]} rows × {before[1]} cols\nAfter:  {after[0]} rows × {after[1]} cols\nRemoved: {diff} rows\n\n── Generated Code ──\n{data.get('code','')}")
            self.main_window.set_status(f"Data cleaned: {before[0]} → {after[0]} rows ✓")
            if hasattr(self.main_window, "spreadsheet_panel"):
                self.main_window.spreadsheet_panel._reload()
        else:
            self._update_stat(self.time_label, "Status", "Failed ✗", "#f44336")
            self.status_label.setText("Error ✗")
            self.result_box.setPlainText(f"❌  Cleaning failed.\n\nError: {data.get('message','Unknown error')}\n\n── Generated Code ──\n{data.get('code','')}")

    def _on_error(self, msg):
        self.run_btn.setEnabled(True)
        self.run_btn.setText("🧹  Clean Data")
        self.status_label.setText("Error ✗")
        self._update_stat(self.time_label, "Status", "Error ✗", "#f44336")
        self.result_box.setPlainText(f"❌  Error:\n{msg}\n\nMake sure Ollama is running: ollama serve")
        self.main_window.set_status(f"Error: {msg}")

    def _append_example(self, prompt):
        existing = self.instruction_input.toPlainText().strip()
        self.instruction_input.setPlainText(f"{existing}\n{prompt}" if existing else prompt)
        self.instruction_input.setFocus()

    def _clear(self):
        self.instruction_input.clear()
        self.result_box.clear()
        self.status_label.setText("Ready")
        self._update_stat(self.before_label, "Before",  "—")
        self._update_stat(self.after_label,  "After",   "—")
        self._update_stat(self.diff_label,   "Removed", "—")
        self._update_stat(self.time_label,   "Status",  "Waiting", "#555")

    def on_file_loaded(self, path):
        self.current_file = path
        filename = os.path.basename(path)
        self.file_status.setText(f"✅  File loaded: {filename}")
        self.file_status.setStyleSheet("color:#4caf81;font-size:12px;background:#0e1e14;border-radius:6px;padding:8px 12px;")
        from core.workbook_inspector import get_sheet_names
        sheets = get_sheet_names(path)
        self.sheet_combo.clear()
        for s in sheets:
            self.sheet_combo.addItem(s)
        self.sheet_names = sheets
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

    def _divider(self):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color:#2a2d3e;max-height:1px;border:none;")
        return line

    def _section_label(self, text):
        label = QLabel(text)
        label.setStyleSheet("color:#444;font-size:10px;letter-spacing:1px;")
        return label
