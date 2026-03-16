"""
PyXcel — Formula Generator Panel
Generate Excel formulas from plain-English descriptions via LLaMA.
"""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QPlainTextEdit,
    QFrame, QScrollArea, QApplication
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont


# ── Example formula prompts ──────────────────────────────────
FORMULA_EXAMPLES = [
    ("SUM with condition",     "Sum column B only where column A equals 'Paid'"),
    ("XLOOKUP",                "Look up employee name from ID in column A, return salary from column D"),
    ("Dynamic filter",         "Filter all rows where Status is 'Active' and Age > 30"),
    ("Running total",          "Calculate running total of Sales column"),
    ("Unique values",          "Get unique list of values from column C"),
    ("Date difference",        "Calculate number of days between Start Date and End Date columns"),
    ("Conditional average",    "Average of Sales where Region equals 'North'"),
    ("Rank",                   "Rank each value in column B from highest to lowest"),
    ("Text combine",           "Combine First Name and Last Name columns with a space"),
    ("Percentage of total",    "Show each Sales value as percentage of total Sales"),
    ("Count non-empty",        "Count non-empty cells in column D"),
    ("Max per category",       "Find maximum Sales value for each unique Region"),
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


class FormulaPanel(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window  = main_window
        self.current_file = None
        self.last_formula = ""
        self._chat_history  = []
        self._chat_bubbles  = []
        self._build_ui()

    # ── Build UI ────────────────────────────────────────────
    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Left side — scrollable formula content
        root.addWidget(self._build_left_formula_panel(), stretch=1)

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

    # ── LEFT: scrollable formula content ─────────────────────
    def _build_left_formula_panel(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")

        inner = QWidget()
        inner.setStyleSheet("background:transparent;")
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # ── Header ──
        badge = QLabel("AI FORMULA GENERATOR")
        badge.setStyleSheet("""
            background-color: #1e2035;
            color: #7c83ff;
            border-radius: 12px;
            padding: 3px 12px;
            font-size: 10px;
            font-weight: bold;
            letter-spacing: 1px;
        """)
        badge.setFixedHeight(24)

        title = QLabel("Formula Generator")
        font  = QFont()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)

        subtitle = QLabel(
            "Describe the calculation in plain English — "
            "LLaMA generates the exact Excel formula including "
            "modern functions like XLOOKUP, FILTER, LET, and UNIQUE."
        )
        subtitle.setStyleSheet("color: #555; font-size: 12px;")
        subtitle.setWordWrap(True)

        layout.addWidget(badge)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self._divider())

        # ── Main Content ──
        content_row = QHBoxLayout()
        content_row.setSpacing(20)

        # Left — input + result
        left = self._build_input_panel()
        content_row.addWidget(left, stretch=3)

        # Right — examples
        right = self._build_examples_panel()
        content_row.addWidget(right, stretch=2)

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

    # ── Input Panel ──────────────────────────────────────────
    def _build_input_panel(self):
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #1a1d2e;
                border: 1px solid #2a2d3e;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Description input
        desc_label = QLabel("Describe the formula you need:")
        desc_label.setStyleSheet(
            "color: #888; font-size: 12px; background: transparent;"
        )

        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText(
            'e.g. "Sum column B only where column A equals Paid"'
        )
        self.desc_input.setFixedHeight(44)
        self.desc_input.setStyleSheet("""
            QLineEdit {
                background-color: #13151f;
                border: 1px solid #2a2d3e;
                border-radius: 8px;
                padding: 10px 14px;
                color: #e0e0e0;
                font-size: 13px;
            }
            QLineEdit:focus { border-color: #7c83ff; }
        """)
        # Allow Enter key to trigger generation
        self.desc_input.returnPressed.connect(self._generate_formula)

        # Context input (optional)
        ctx_label = QLabel(
            "Column context (optional — auto-filled if file is loaded):"
        )
        ctx_label.setStyleSheet(
            "color: #555; font-size: 11px; background: transparent;"
        )

        self.context_input = QPlainTextEdit()
        self.context_input.setPlaceholderText(
            "e.g. Column A = Region, Column B = Sales, Column C = Date\n"
            "(Leave blank to use loaded file structure)"
        )
        self.context_input.setFixedHeight(80)
        self.context_input.setStyleSheet("""
            QPlainTextEdit {
                background-color: #13151f;
                border: 1px solid #2a2d3e;
                border-radius: 8px;
                padding: 10px;
                color: #666;
                font-size: 12px;
            }
            QPlainTextEdit:focus { border-color: #3a3d5e; }
        """)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet(
            "color: #555; font-size: 11px; background: transparent;"
        )

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setFixedWidth(80)
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.clicked.connect(self._clear)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e2035;
                color: #7c83ff;
                border: 1px solid #2a2d3e;
                border-radius: 8px;
                padding: 9px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #252840; }
        """)

        self.gen_btn = QPushButton("🧮  Generate Formula")
        self.gen_btn.setFixedWidth(180)
        self.gen_btn.setCursor(Qt.PointingHandCursor)
        self.gen_btn.clicked.connect(self._generate_formula)
        self.gen_btn.setStyleSheet("""
            QPushButton {
                background-color: #7c83ff;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 9px 20px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #6b72ff; }
            QPushButton:disabled { background-color: #2a2d3e; color: #555; }
        """)

        btn_row.addWidget(self.status_label)
        btn_row.addStretch()
        btn_row.addWidget(self.clear_btn)
        btn_row.addWidget(self.gen_btn)

        layout.addWidget(desc_label)
        layout.addWidget(self.desc_input)
        layout.addWidget(ctx_label)
        layout.addWidget(self.context_input)
        layout.addLayout(btn_row)
        layout.addWidget(self._divider())

        # ── Formula Output ──
        output_label = QLabel("Generated Formula:")
        output_label.setStyleSheet(
            "color: #888; font-size: 12px; "
            "font-weight: bold; background: transparent;"
        )

        # Big formula display box
        self.formula_display = QLabel("—")
        self.formula_display.setAlignment(Qt.AlignCenter)
        self.formula_display.setWordWrap(True)
        self.formula_display.setFixedHeight(80)
        self.formula_display.setStyleSheet("""
            QLabel {
                background-color: #13151f;
                border: 1px solid #2a2d3e;
                border-left: 3px solid #7c83ff;
                border-radius: 8px;
                padding: 16px;
                color: #7c83ff;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 16px;
                font-weight: bold;
            }
        """)

        # Copy button row
        copy_row = QHBoxLayout()
        copy_row.setSpacing(10)

        self.copy_btn = QPushButton("📋  Copy Formula")
        self.copy_btn.setFixedWidth(160)
        self.copy_btn.setCursor(Qt.PointingHandCursor)
        self.copy_btn.clicked.connect(self._copy_formula)
        self.copy_btn.setEnabled(False)
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e2035;
                color: #7c83ff;
                border: 1px solid #2a2d3e;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #252840;
                border-color: #7c83ff;
            }
            QPushButton:disabled { color: #333; border-color: #1e2035; }
        """)

        self.copy_confirm = QLabel("")
        self.copy_confirm.setStyleSheet(
            "color: #4caf81; font-size: 11px; background: transparent;"
        )

        copy_row.addWidget(self.copy_btn)
        copy_row.addWidget(self.copy_confirm)
        copy_row.addStretch()

        # Explanation box
        explain_label = QLabel("How to use this formula:")
        explain_label.setStyleSheet(
            "color: #555; font-size: 11px; background: transparent;"
        )

        self.explain_box = QPlainTextEdit()
        self.explain_box.setReadOnly(True)
        self.explain_box.setPlaceholderText(
            "Formula explanation will appear here after generation..."
        )
        self.explain_box.setFixedHeight(100)
        self.explain_box.setStyleSheet("""
            QPlainTextEdit {
                background-color: #13151f;
                border: 1px solid #2a2d3e;
                border-radius: 8px;
                padding: 10px;
                color: #888;
                font-size: 12px;
            }
        """)

        layout.addWidget(output_label)
        layout.addWidget(self.formula_display)
        layout.addLayout(copy_row)
        layout.addWidget(explain_label)
        layout.addWidget(self.explain_box)

        return frame

    # ── Examples Panel ───────────────────────────────────────
    def _build_examples_panel(self):
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #13151f;
                border: 1px solid #2a2d3e;
                border-radius: 12px;
            }
        """)
        frame.setMaximumWidth(320)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        header = QLabel("💡  Example Requests")
        header.setStyleSheet(
            "color: #888; font-size: 12px; "
            "font-weight: bold; background: transparent;"
        )

        hint = QLabel("Click any example to use it")
        hint.setStyleSheet(
            "color: #3a3d5e; font-size: 11px; background: transparent;"
        )

        layout.addWidget(header)
        layout.addWidget(hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(0, 4, 0, 4)
        inner_layout.setSpacing(6)

        for category, prompt in FORMULA_EXAMPLES:
            btn = QPushButton(f"[{category}]\n{prompt}")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(
                lambda checked, p=prompt: self._use_example(p)
            )
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #1a1d2e;
                    color: #888;
                    border: 1px solid #2a2d3e;
                    border-radius: 6px;
                    padding: 8px 10px;
                    text-align: left;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #1e2035;
                    color: #c0c4ff;
                    border-color: #7c83ff;
                }
            """)
            inner_layout.addWidget(btn)

        inner_layout.addStretch()
        scroll.setWidget(inner)
        layout.addWidget(scroll)

        return frame

    # ── Actions ──────────────────────────────────────────────
    def _generate_formula(self):
        description = self.desc_input.text().strip()
        if not description:
            self.formula_display.setText("⚠️  Please enter a description first")
            return

        # Build context
        context = self.context_input.toPlainText().strip()
        if not context and self.current_file:
            from core.workbook_inspector import get_context_string
            context = get_context_string(self.current_file)

        self.gen_btn.setEnabled(False)
        self.gen_btn.setText("⏳  Generating...")
        self.copy_btn.setEnabled(False)
        self.status_label.setText("Generating...")
        self.formula_display.setText("🔄  Asking LLaMA...")
        self.explain_box.clear()
        self.copy_confirm.setText("")

        from gui.workers.agent_worker import FormulaWorker

        self.worker = FormulaWorker(description, context)
        self.worker.status.connect(self._on_status)
        self.worker.result.connect(self._on_result)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_status(self, msg: str):
        self.status_label.setText(msg)
        self.main_window.set_status(msg)

    def _on_result(self, data: dict):
        self.gen_btn.setEnabled(True)
        self.gen_btn.setText("🧮  Generate Formula")

        if data["status"] == "success":
            formula = data.get("formula", "").strip()
            self.last_formula = formula
            self.formula_display.setText(formula)
            self.copy_btn.setEnabled(True)
            self.status_label.setText("Done ✓")
            self.main_window.set_status("Formula generated ✓")

            # Generate explanation in background
            self._generate_explanation(formula)
        else:
            self.formula_display.setText("❌  Generation failed")
            self.status_label.setText("Error ✗")

    def _generate_explanation(self, formula: str):
        """Ask LLaMA to explain the generated formula briefly."""
        from gui.workers.agent_worker import FormulaWorker

        class ExplainWorker(FormulaWorker):
            def run(self_w):
                from core.ollama_client import ask_llama
                system = (
                    "Explain this Excel formula in 2-3 simple sentences. "
                    "Mention what it does, any key arguments, and when to use it. "
                    "No markdown, plain text only."
                )
                reply = ask_llama(system, f"Formula: {formula}")
                self_w.result.emit({"status": "success", "formula": reply})

        self.explain_worker = ExplainWorker("", "")
        self.explain_worker.result.connect(
            lambda d: self.explain_box.setPlainText(
                d.get("formula", "")
            )
        )
        self.explain_worker.start()

    def _on_error(self, msg: str):
        self.gen_btn.setEnabled(True)
        self.gen_btn.setText("🧮  Generate Formula")
        self.status_label.setText("Error ✗")
        self.formula_display.setText("❌  Error — is Ollama running?")
        self.explain_box.setPlainText(
            f"Error: {msg}\n\nMake sure Ollama is running:\n  ollama serve"
        )
        self.main_window.set_status(f"Error: {msg}")

    def _copy_formula(self):
        if self.last_formula:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.last_formula)
            self.copy_confirm.setText("✅  Copied!")
            # Clear confirm after 2 seconds
            from PySide6.QtCore import QTimer
            QTimer.singleShot(
                2000,
                lambda: self.copy_confirm.setText("")
            )

    def _use_example(self, prompt: str):
        self.desc_input.setText(prompt)
        self.desc_input.setFocus()

    def _clear(self):
        self.desc_input.clear()
        self.context_input.clear()
        self.formula_display.setText("—")
        self.explain_box.clear()
        self.copy_btn.setEnabled(False)
        self.copy_confirm.setText("")
        self.status_label.setText("Ready")
        self.last_formula = ""

    def on_file_loaded(self, path: str):
        self.current_file = path
        filename = os.path.basename(path)
        self.context_input.setPlaceholderText(
            f"Auto-context from {filename} will be used.\n"
            f"You can also add custom context here."
        )
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
    def _divider(self):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(
            "background-color: #2a2d3e; max-height: 1px; border: none;"
        )
        return line
