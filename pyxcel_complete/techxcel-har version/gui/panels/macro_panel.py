"""
PyXcel — Macro Replacement Panel
Replace VBA macros with natural language instructions via LLaMA.
"""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QPlainTextEdit,
    QFrame, QSizePolicy, QScrollArea, QLineEdit
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont


# ── Example prompts to help users get started ───────────────
EXAMPLE_PROMPTS = [
    "Highlight all rows where Profit is negative in red",
    "Bold the header row and set background to dark blue",
    "Add a SUM formula at the bottom of every numeric column",
    "Highlight duplicate values in column A in yellow",
    "Set column widths to auto-fit all content",
    "Add borders to all cells in the used range",
    "Color rows alternating light grey and white",
    "Delete all rows where the Status column is empty",
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


class MacroPanel(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window  = main_window
        self.current_file = None
        self._chat_history  = []
        self._chat_bubbles  = []
        self._build_ui()

    # ── Build UI ────────────────────────────────────────────
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # ── Header ──
        badge = QLabel("AI MACRO REPLACEMENT")
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

        title = QLabel("Macro Replacement")
        font  = QFont()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)

        subtitle = QLabel(
            "Describe what you want to do in plain English — "
            "LLaMA generates and executes the code automatically."
        )
        subtitle.setStyleSheet("color: #555; font-size: 12px;")
        subtitle.setWordWrap(True)

        layout.addWidget(badge)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self._divider())

        # ── File Status ──
        self.file_status = QLabel("⚠️  No file loaded — load an Excel file first")
        self.file_status.setStyleSheet(
            "color: #ff9800; font-size: 12px; "
            "background: #1e1a0e; border-radius: 6px; padding: 8px 12px;"
        )
        layout.addWidget(self.file_status)

        # ── Main Content — two columns ──
        content_row = QHBoxLayout()
        content_row.setSpacing(20)

        # Left — input area
        left = self._build_input_area()
        content_row.addWidget(left, stretch=3)

        # Right — examples
        right = self._build_examples_panel()
        content_row.addWidget(right, stretch=2)

        layout.addLayout(content_row)

        # ── Result Box ──
        layout.addWidget(self._section_label("RESULT"))
        self.result_box = QPlainTextEdit()
        self.result_box.setObjectName("result_box")
        self.result_box.setReadOnly(True)
        self.result_box.setPlaceholderText(
            "Generated code and execution result will appear here..."
        )
        self.result_box.setFixedHeight(200)
        self.result_box.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1a1d2e;
                border: 1px solid #2a2d3e;
                border-left: 3px solid #7c83ff;
                border-radius: 8px;
                padding: 12px;
                color: #c0c4ff;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.result_box)
        layout.addStretch()

    # ── Input Area ───────────────────────────────────────────
    def _build_input_area(self):
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #1a1d2e;
                border: 1px solid #2a2d3e;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        label = QLabel("Describe your operation:")
        label.setStyleSheet("color: #888; font-size: 12px; background: transparent;")

        self.instruction_input = QTextEdit()
        self.instruction_input.setPlaceholderText(
            'e.g. "Highlight all rows where Sales > 10000 in green '
            'and bold the values"'
        )
        self.instruction_input.setFixedHeight(120)
        self.instruction_input.setStyleSheet("""
            QTextEdit {
                background-color: #13151f;
                border: 1px solid #2a2d3e;
                border-radius: 8px;
                padding: 10px;
                color: #e0e0e0;
                font-size: 13px;
            }
            QTextEdit:focus { border-color: #7c83ff; }
        """)

        # Bottom row — status + run button
        bottom_row = QHBoxLayout()

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet(
            "color: #555; font-size: 11px; background: transparent;"
        )

        self.run_btn = QPushButton("▶  Execute")
        self.run_btn.setFixedWidth(130)
        self.run_btn.setCursor(Qt.PointingHandCursor)
        self.run_btn.clicked.connect(self._run_macro)
        self.run_btn.setStyleSheet("""
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

        bottom_row.addWidget(self.status_label)
        bottom_row.addStretch()
        bottom_row.addWidget(self.clear_btn)
        bottom_row.addWidget(self.run_btn)

        layout.addWidget(label)
        layout.addWidget(self.instruction_input)
        layout.addLayout(bottom_row)

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

        header = QLabel("💡  Example Prompts")
        header.setStyleSheet(
            "color: #888; font-size: 12px; "
            "font-weight: bold; background: transparent;"
        )
        layout.addWidget(header)

        hint = QLabel("Click any example to use it")
        hint.setStyleSheet(
            "color: #3a3d5e; font-size: 11px; background: transparent;"
        )
        layout.addWidget(hint)

        # Scrollable examples
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

        for prompt in EXAMPLE_PROMPTS:
            btn = QPushButton(prompt)
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
    def _run_macro(self):
        if not self.current_file:
            self.result_box.setPlainText(
                "❌  No file loaded.\n"
                "Please load an Excel file first."
            )
            return

        instruction = self.instruction_input.toPlainText().strip()
        if not instruction:
            self.result_box.setPlainText(
                "❌  Please enter an instruction first."
            )
            return

        # Disable button during processing
        self.run_btn.setEnabled(False)
        self.run_btn.setText("⏳  Processing...")
        self.result_box.setPlainText("🔄  Sending to LLaMA...\n")

        from gui.workers.agent_worker import MacroWorker

        self.worker = MacroWorker(self.current_file, instruction)
        self.worker.status.connect(self._on_status)
        self.worker.result.connect(self._on_result)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_status(self, msg: str):
        self.status_label.setText(msg)
        self.result_box.appendPlainText(f"  {msg}")
        self.main_window.set_status(msg)

    def _on_result(self, data: dict):
        self.run_btn.setEnabled(True)
        self.run_btn.setText("▶  Execute")
        self.status_label.setText("Done ✓")

        if data["status"] == "success":
            self.result_box.setPlainText(
                f"✅  Operation completed successfully!\n\n"
                f"── Generated Code ──────────────────\n"
                f"{data.get('code', '')}\n\n"
                f"── Message ─────────────────────────\n"
                f"{data.get('message', '')}"
            )
            self.main_window.set_status("Macro executed successfully ✓")

            # Refresh spreadsheet panel
            if hasattr(self.main_window, "spreadsheet_panel"):
                self.main_window.spreadsheet_panel._reload()
        else:
            self.result_box.setPlainText(
                f"❌  Execution failed.\n\n"
                f"Error: {data.get('message', 'Unknown error')}\n\n"
                f"── Generated Code ──────────────────\n"
                f"{data.get('code', '')}"
            )
            self.main_window.set_status("Macro execution failed ✗")

    def _on_error(self, msg: str):
        self.run_btn.setEnabled(True)
        self.run_btn.setText("▶  Execute")
        self.status_label.setText("Error ✗")
        self.result_box.setPlainText(
            f"❌  Error:\n{msg}\n\n"
            f"Make sure Ollama is running:\n"
            f"  ollama serve"
        )
        self.main_window.set_status(f"Error: {msg}")

    def _use_example(self, prompt: str):
        self.instruction_input.setPlainText(prompt)
        self.instruction_input.setFocus()

    def _clear(self):
        self.instruction_input.clear()
        self.result_box.clear()
        self.status_label.setText("Ready")

    def on_file_loaded(self, path: str):
        self.current_file = path
        filename = os.path.basename(path)
        self.file_status.setText(f"✅  File loaded: {filename}")
        self.file_status.setStyleSheet(
            "color: #4caf81; font-size: 12px; "
            "background: #0e1e14; border-radius: 6px; padding: 8px 12px;"
        )

    # ── Helpers ──────────────────────────────────────────────
    def _divider(self):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(
            "background-color: #2a2d3e; max-height: 1px; border: none;"
        )
        return line

    def _section_label(self, text: str):
        label = QLabel(text)
        label.setStyleSheet(
            "color: #444; font-size: 10px; letter-spacing: 1px;"
        )
        return label