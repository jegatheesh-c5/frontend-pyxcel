"""
PyXcel — Home Panel
Welcome screen with file upload, quick actions, system status,
and an embedded live chat panel on the right side.
"""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFileDialog, QFrame,
    QSizePolicy, QScrollArea, QLineEdit
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QFont, QDragEnterEvent, QDropEvent


# ── Background thread for Ollama checks ──────────────────────────────────────
class _StatusChecker(QThread):
    done = Signal(bool, bool)

    def run(self):
        from core.ollama_client import is_ollama_running, is_model_available
        running  = is_ollama_running()
        model_ok = is_model_available("llama3.1") if running else False
        self.done.emit(running, model_ok)


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


# ═════════════════════════════════════════════════════════════════════════════
class HomePanel(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window  = main_window
        self.current_file = None
        self._chat_history  = []
        self._chat_bubbles  = []
        self.setAcceptDrops(True)
        self._build_ui()
        self._start_status_check()

    # ── Master layout: left content + right chat ──────────────
    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Left side — scrollable home content
        root.addWidget(self._build_left_panel(), stretch=1)

        # Right side — collapsible chat container
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

    # ── LEFT: scrollable home content ────────────────────────
    def _build_left_panel(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")

        content = QWidget()
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 40, 30, 40)
        layout.setSpacing(22)

        # Header
        badge = QLabel("AI-POWERED SPREADSHEET SYSTEM")
        badge.setFixedHeight(24)
        badge.setAlignment(Qt.AlignLeft)
        badge.setStyleSheet(
            "background-color:#1e2035;color:#7c83ff;border-radius:12px;"
            "padding:3px 12px;font-size:10px;font-weight:bold;letter-spacing:1.5px;"
        )

        title = QLabel("Welcome to PyXcel")
        font = QFont(); font.setPointSize(22); font.setBold(True)
        title.setFont(font)

        subtitle = QLabel(
            "Replace macros with natural language  ·  "
            "Generate formulas  ·  Clean data  ·  Chat with your spreadsheet"
        )
        subtitle.setStyleSheet("color:#555;font-size:12px;letter-spacing:0.2px;")
        subtitle.setWordWrap(True)

        layout.addWidget(badge)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        # Drop zone
        self.drop_zone = self._build_drop_zone()
        layout.addWidget(self.drop_zone)

        # Quick actions
        layout.addWidget(self._section_label("QUICK ACTIONS"))
        layout.addWidget(self._build_quick_actions())

        # System status
        layout.addWidget(self._section_label("SYSTEM STATUS"))
        self.status_grid = self._build_status_cards()
        layout.addWidget(self.status_grid)

        layout.addSpacing(24)

        scroll.setWidget(content)
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

        # Message counter
        self.msg_counter = QLabel("0 messages")
        self.msg_counter.setAlignment(Qt.AlignCenter)
        self.msg_counter.setStyleSheet("color:#2a2d3e;font-size:10px;")
        layout.addWidget(self.msg_counter)

        return panel

    def _build_starter_chips(self):
        widget = QWidget()
        widget.setStyleSheet("background:transparent;")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        label = QLabel("💡  Try asking:")
        label.setStyleSheet("color:#444;font-size:10px;")
        layout.addWidget(label)

        starters = [
            "Summarise this spreadsheet",
            "What columns have missing values?",
            "Which row has the highest value?",
            "What trends do you see?",
        ]

        row1 = QHBoxLayout(); row1.setSpacing(6)
        row2 = QHBoxLayout(); row2.setSpacing(6)

        for i, q in enumerate(starters):
            btn = QPushButton(q)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, t=q: self._use_starter(t))
            btn.setStyleSheet(
                "QPushButton{background-color:#1a1d2e;color:#555;border:1px solid #2a2d3e;"
                "border-radius:14px;padding:4px 10px;font-size:10px;}"
                "QPushButton:hover{background-color:#1e2035;color:#c0c4ff;border-color:#7c83ff;}"
            )
            (row1 if i < 2 else row2).addWidget(btn)

        layout.addLayout(row1)
        layout.addLayout(row2)
        return widget

    # ── Drop Zone ─────────────────────────────────────────────
    def _build_drop_zone(self):
        zone = QFrame()
        zone.setObjectName("drop_zone")
        zone.setFixedHeight(175)
        zone.setCursor(Qt.PointingHandCursor)
        zone.setStyleSheet("""
            QFrame#drop_zone {
                background-color: #1a1d2e;
                border: 2px dashed #2a2d3e;
                border-radius: 12px;
            }
            QFrame#drop_zone:hover {
                border-color: #7c83ff;
                background-color: #1e2035;
            }
        """)

        layout = QVBoxLayout(zone)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(8)

        icon = QLabel("📂")
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("font-size: 32px; background: transparent;")

        self.drop_label = QLabel("Drop your Excel file here")
        self.drop_label.setAlignment(Qt.AlignCenter)
        self.drop_label.setStyleSheet("color:#555;font-size:14px;background:transparent;")

        hint = QLabel("or click to browse  ·  supports .xlsx  .xls")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("color:#3a3d5e;font-size:11px;background:transparent;")

        browse_btn = QPushButton("Browse Files")
        browse_btn.setFixedWidth(150)
        browse_btn.setFixedHeight(36)
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.clicked.connect(self._browse_file)

        layout.addWidget(icon)
        layout.addWidget(self.drop_label)
        layout.addWidget(hint)
        layout.addWidget(browse_btn, alignment=Qt.AlignCenter)

        zone.mousePressEvent = lambda e: self._browse_file()
        return zone

    # ── Quick Actions ─────────────────────────────────────────
    def _build_quick_actions(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        actions = [
            ("⚙️", "Macro\nReplacement", 2),
            ("🧮", "Formula\nGenerator",  3),
            ("🧹", "Data\nCleaner",       4),
            ("💬", "Chat\nwith Data",     5),
            ("📈", "KPI\nCards",          6),
        ]

        for icon, title, panel_index in actions:
            layout.addWidget(self._action_card(icon, title, panel_index), stretch=1)

        return widget

    def _action_card(self, icon, title, panel_index):
        card = QFrame()
        card.setObjectName("card")
        card.setCursor(Qt.PointingHandCursor)
        card.setMinimumHeight(90)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        card.setStyleSheet("""
            QFrame#card {
                background-color: #1a1d2e;
                border: 1px solid #2a2d3e;
                border-radius: 12px;
            }
            QFrame#card:hover {
                border-color: #7c83ff;
                background-color: #1e2035;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignCenter)

        icon_lbl = QLabel(icon)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("font-size:22px;background:transparent;border:none;")

        title_lbl = QLabel(title)
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setStyleSheet(
            "font-size:11px;font-weight:bold;color:#e0e0e0;"
            "background:transparent;border:none;"
        )
        title_lbl.setWordWrap(True)

        layout.addWidget(icon_lbl)
        layout.addWidget(title_lbl)

        card.mousePressEvent = lambda e, i=panel_index: self.main_window.switch_panel(i)
        return card

    # ── Status Cards ──────────────────────────────────────────
    def _build_status_cards(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self.ollama_card  = self._status_card("Ollama",       "Checking...", "⬤", "#555")
        self.model_card   = self._status_card("LLaMA Model",  "Checking...", "⬤", "#555")
        self.file_card    = self._status_card("File Loaded",  "None",        "📄", "#555")
        self.offline_card = self._status_card("Offline Mode", "Active ✓",   "🔒", "#4caf81")

        for card in [self.ollama_card, self.model_card,
                     self.file_card,   self.offline_card]:
            layout.addWidget(card["frame"], stretch=1)

        return widget

    def _status_card(self, title, value, icon, value_color):
        frame = QFrame()
        frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        frame.setMinimumWidth(100)
        frame.setStyleSheet(
            "QFrame{background-color:#1a1d2e;border:1px solid #2a2d3e;border-radius:12px;}"
        )

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        title_row = QHBoxLayout()
        title_row.setSpacing(5)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size:11px;color:#555;background:transparent;")
        icon_lbl.setFixedWidth(16)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            "font-size:10px;color:#888;background:transparent;"
            "letter-spacing:0.4px;font-weight:bold;"
        )

        title_row.addWidget(icon_lbl)
        title_row.addWidget(title_lbl)
        title_row.addStretch()

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("background-color:#2a2d3e;max-height:1px;border:none;")

        value_lbl = QLabel(value)
        value_lbl.setStyleSheet(
            f"font-size:14px;font-weight:bold;color:{value_color};"
            f"background:transparent;letter-spacing:0.3px;"
        )
        value_lbl.setWordWrap(True)

        layout.addLayout(title_row)
        layout.addWidget(divider)
        layout.addWidget(value_lbl)

        return {"frame": frame, "value": value_lbl}

    # ── Chat logic ────────────────────────────────────────────
    def _send_chat(self):
        if not self.current_file:
            self._add_system_msg("⚠️  Please load an Excel file first.")
            return
        msg = self.chat_input.text().strip()
        if not msg:
            return

        self.starters_widget.hide()
        self._add_bubble(msg, is_user=True)
        self.chat_input.clear()
        self.send_btn.setEnabled(False)
        self.chat_input.setEnabled(False)
        self.typing_indicator.show()
        self.typing_indicator.start()

        from gui.workers.agent_worker import ChatWorker
        self.worker = ChatWorker(self.current_file, msg, self._chat_history.copy())
        self.worker.result.connect(self._on_chat_result)
        self.worker.error.connect(self._on_chat_error)
        self.worker.start()

    def _on_chat_result(self, data):
        self.typing_indicator.stop()
        self.typing_indicator.hide()
        self.send_btn.setEnabled(True)
        self.chat_input.setEnabled(True)
        self.chat_input.setFocus()

        if data["status"] == "success":
            response = data.get("response", "")
            message  = data.get("message", "")
            self._add_bubble(response, is_user=False)
            self._chat_history.append({"role": "user",      "content": message})
            self._chat_history.append({"role": "assistant",  "content": response})
            if len(self._chat_history) > 20:
                self._chat_history = self._chat_history[-20:]
            self.msg_counter.setText(f"{len(self._chat_history)} messages")
        else:
            self._add_system_msg("❌  Error getting response from LLaMA.")

    def _on_chat_error(self, msg):
        self.typing_indicator.stop()
        self.typing_indicator.hide()
        self.send_btn.setEnabled(True)
        self.chat_input.setEnabled(True)
        self._add_system_msg(f"❌  {msg}")

    def _add_bubble(self, text: str, is_user: bool):
        bubble = _ChatBubble(text, is_user)
        idx = self.chat_layout.count() - 1
        self.chat_layout.insertWidget(idx, bubble)
        self._chat_bubbles.append(bubble)
        QTimer.singleShot(50, lambda: self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        ))

    def _add_system_msg(self, text: str):
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(
            "QLabel{color:#555;font-size:11px;background:#1a1d2e;"
            "border:1px solid #2a2d3e;border-radius:8px;padding:8px 12px;margin:2px 20px;}"
        )
        idx = self.chat_layout.count() - 1
        self.chat_layout.insertWidget(idx, lbl)

    def _use_starter(self, text: str):
        self.chat_input.setText(text)
        self.chat_input.setFocus()

    def _clear_chat(self):
        for b in self._chat_bubbles:
            self.chat_layout.removeWidget(b)
            b.deleteLater()
        self._chat_bubbles.clear()
        self._chat_history.clear()
        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.msg_counter.setText("0 messages")
        self.starters_widget.show()

    def _toggle_chat(self):
        if self.chat_panel.isVisible():
            self.chat_panel.hide()
            self.chat_toggle_btn.setText("💬")
        else:
            self.chat_panel.show()
            self.chat_toggle_btn.setText("❌")
            self.chat_input.setFocus()

    # ── Status checker ────────────────────────────────────────
    def _start_status_check(self):
        self._run_status_check()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._run_status_check)
        self.timer.start(20000)

    def _run_status_check(self):
        self._checker = _StatusChecker(self)
        self._checker.done.connect(self._on_status_result)
        self._checker.start()
        self._update_file_card()

    def _on_status_result(self, ollama_ok: bool, model_ok: bool):
        self._set_card(self.ollama_card, "Running ✓" if ollama_ok else "Offline ✗",
                       "#4caf81" if ollama_ok else "#f44336")
        self._set_card(self.model_card,  "Ready ✓"   if model_ok  else "Not Pulled ✗",
                       "#4caf81" if model_ok  else "#f44336")

    def _update_file_card(self):
        if self.main_window.current_file:
            name = os.path.basename(self.main_window.current_file)
            self._set_card(self.file_card, name[:20], "#7c83ff")
        else:
            self._set_card(self.file_card, "None", "#555")

    def _set_card(self, card, text, color):
        card["value"].setText(text)
        card["value"].setStyleSheet(
            f"font-size:14px;font-weight:bold;color:{color};"
            f"background:transparent;letter-spacing:0.3px;"
        )

    # ── File handling ─────────────────────────────────────────
    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Excel File", "", "Excel Files (*.xlsx *.xls)"
        )
        if path:
            self._load_file(path)

    def _load_file(self, path: str):
        self.main_window.current_file = path
        self.main_window._notify_panels_file_loaded(path)
        filename = os.path.basename(path)
        self.drop_label.setText(f"✅  {filename} loaded")
        self.drop_label.setStyleSheet("color:#4caf81;font-size:13px;background:transparent;")
        self.main_window.file_label.setText(f"📄 {filename}")
        self.main_window.status_bar.showMessage(f"Loaded: {filename}")
        self.main_window.switch_panel(1)

    # ── Drag & Drop ───────────────────────────────────────────
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and urls[0].toLocalFile().endswith((".xlsx", ".xls")):
                event.acceptProposedAction()
                self.drop_zone.setStyleSheet("""
                    QFrame#drop_zone {
                        background-color: #1e2035;
                        border: 2px dashed #7c83ff;
                        border-radius: 12px;
                    }
                """)

    def dragLeaveEvent(self, event):
        self.drop_zone.setStyleSheet("""
            QFrame#drop_zone {
                background-color: #1a1d2e;
                border: 2px dashed #2a2d3e;
                border-radius: 12px;
            }
        """)

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path.endswith((".xlsx", ".xls")):
                self._load_file(path)
        self.drop_zone.setStyleSheet("""
            QFrame#drop_zone {
                background-color: #1a1d2e;
                border: 2px dashed #2a2d3e;
                border-radius: 12px;
            }
        """)

    def on_file_loaded(self, path: str):
        """Called by main_window when file is loaded from sidebar."""
        self.current_file = path
        filename = os.path.basename(path)
        self.drop_label.setText(f"✅  {filename} loaded")
        self.drop_label.setStyleSheet("color:#4caf81;font-size:13px;background:transparent;")
        self.chat_file_status.setText(f"✅  Chatting about: {filename}")
        self.chat_file_status.setStyleSheet(
            "color:#4caf81;font-size:11px;background:#0e1e14;"
            "border-radius:6px;padding:6px 10px;"
        )
        self._update_file_card()
        self._clear_chat()
        self._add_system_msg(f"📄  {filename} loaded — ask me anything!")

    # ── Helper ────────────────────────────────────────────────
    def _section_label(self, text: str):
        label = QLabel(text)
        label.setStyleSheet(
            "color:#444;font-size:10px;letter-spacing:2px;padding-top:8px;"
        )
        return label
