"""
PyXcel — KPI Cards Panel
"""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QComboBox,
    QGridLayout, QSizePolicy, QLineEdit
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

TREND_ICON  = {"up": "↑", "down": "↓", "neutral": "→"}
TREND_COLOR = {"up": "#4caf81", "down": "#f44336", "neutral": "#ff9800"}


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


class KpiCard(QFrame):
    def __init__(self, title, value, description, trend="neutral", parent=None):
        super().__init__(parent)
        self.setMinimumWidth(200)
        self.setMinimumHeight(130)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        color = TREND_COLOR.get(trend, "#ff9800")
        icon  = TREND_ICON.get(trend,  "→")
        self.setStyleSheet(f"QFrame{{background-color:#1a1d2e;border:1px solid #2a2d3e;border-radius:12px;border-top:3px solid {color};}}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)

        title_row = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setStyleSheet("color:#888;font-size:11px;font-weight:bold;background:transparent;")
        title_label.setWordWrap(True)
        trend_label = QLabel(icon)
        trend_label.setStyleSheet(f"color:{color};font-size:16px;font-weight:bold;background:transparent;")
        trend_label.setFixedWidth(24)
        trend_label.setAlignment(Qt.AlignRight)
        title_row.addWidget(title_label)
        title_row.addStretch()
        title_row.addWidget(trend_label)

        value_label = QLabel(str(value))
        value_label.setStyleSheet(f"color:{color};font-size:26px;font-weight:bold;background:transparent;")
        value_label.setWordWrap(True)

        desc_label = QLabel(description)
        desc_label.setStyleSheet("color:#444;font-size:11px;background:transparent;")
        desc_label.setWordWrap(True)

        layout.addLayout(title_row)
        layout.addWidget(value_label)
        layout.addStretch()
        layout.addWidget(desc_label)


class KpiPanel(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window  = main_window
        self.current_file = None
        self.sheet_names  = []
        self.kpi_cards    = []
        self._chat_history  = []
        self._chat_bubbles  = []
        self._build_ui()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Left side — scrollable kpi content
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

    # ── LEFT: scrollable kpi content ──────────────────────────
    def _build_left_panel(self):
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

        header_row = QHBoxLayout()
        left = QVBoxLayout()
        left.setSpacing(4)

        badge = QLabel("AUTO KPI DETECTION")
        badge.setStyleSheet("background-color:#1e2035;color:#7c83ff;border-radius:12px;padding:3px 12px;font-size:10px;font-weight:bold;letter-spacing:1px;")
        badge.setFixedHeight(24)

        title = QLabel("KPI Cards")
        font  = QFont(); font.setPointSize(18); font.setBold(True)
        title.setFont(font)

        subtitle = QLabel("LLaMA automatically identifies business KPIs from any spreadsheet and computes their values.")
        subtitle.setStyleSheet("color:#555;font-size:12px;")
        subtitle.setWordWrap(True)

        left.addWidget(badge)
        left.addWidget(title)
        left.addWidget(subtitle)

        self.refresh_btn = QPushButton("🔄  Regenerate")
        self.refresh_btn.setFixedWidth(140)
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.clicked.connect(self._generate_kpis)
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setStyleSheet("QPushButton{background-color:#1e2035;color:#7c83ff;border:1px solid #2a2d3e;border-radius:8px;padding:9px 16px;font-size:12px;}QPushButton:hover{background-color:#252840;border-color:#7c83ff;}QPushButton:disabled{color:#333;border-color:#1e2035;}")

        header_row.addLayout(left)
        header_row.addStretch()
        header_row.addWidget(self.refresh_btn, alignment=Qt.AlignRight | Qt.AlignVCenter)
        layout.addLayout(header_row)
        layout.addWidget(self._divider())

        self.file_status = QLabel("⚠️  No file loaded — load an Excel file first")
        self.file_status.setStyleSheet("color:#ff9800;font-size:12px;background:#1e1a0e;border-radius:6px;padding:8px 12px;")
        layout.addWidget(self.file_status)

        controls_row = QHBoxLayout()
        controls_row.setSpacing(12)

        sheet_label = QLabel("Sheet:")
        sheet_label.setStyleSheet("color:#888;font-size:12px;")
        sheet_label.setFixedWidth(50)

        self.sheet_combo = QComboBox()
        self.sheet_combo.setFixedWidth(180)
        self.sheet_combo.setStyleSheet("QComboBox{background-color:#1a1d2e;border:1px solid #2a2d3e;border-radius:8px;padding:7px 12px;color:#e0e0e0;font-size:12px;}QComboBox:focus{border-color:#7c83ff;}")
        self.sheet_combo.addItem("Sheet1")

        self.generate_btn = QPushButton("📈  Generate KPI Cards")
        self.generate_btn.setFixedWidth(190)
        self.generate_btn.setCursor(Qt.PointingHandCursor)
        self.generate_btn.clicked.connect(self._generate_kpis)
        self.generate_btn.setEnabled(False)
        self.generate_btn.setStyleSheet("QPushButton{background-color:#7c83ff;color:white;border:none;border-radius:8px;padding:9px 20px;font-size:13px;font-weight:bold;}QPushButton:hover{background-color:#6b72ff;}QPushButton:disabled{background-color:#2a2d3e;color:#555;}")

        self.status_label = QLabel("Load a file to get started")
        self.status_label.setStyleSheet("color:#555;font-size:12px;")

        controls_row.addWidget(sheet_label)
        controls_row.addWidget(self.sheet_combo)
        controls_row.addWidget(self.generate_btn)
        controls_row.addStretch()
        controls_row.addWidget(self.status_label)
        layout.addLayout(controls_row)

        self.empty_state = self._build_empty_state()
        layout.addWidget(self.empty_state)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("background:transparent;")
        self.scroll_area.hide()

        self.grid_container = QWidget()
        self.grid_container.setStyleSheet("background:transparent;")
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(16)

        self.scroll_area.setWidget(self.grid_container)
        layout.addWidget(self.scroll_area, stretch=1)

        self.summary_frame = self._build_summary_box()
        self.summary_frame.hide()
        layout.addWidget(self.summary_frame)

        scroll.setWidget(inner)
        return scroll

    def _build_empty_state(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(12)
        icon = QLabel("📈"); icon.setAlignment(Qt.AlignCenter); icon.setStyleSheet("font-size:52px;")
        msg  = QLabel("No KPIs generated yet"); msg.setAlignment(Qt.AlignCenter); msg.setStyleSheet("color:#555;font-size:15px;")
        hint = QLabel("Load an Excel file and click 'Generate KPI Cards'\nLLaMA will automatically identify relevant business metrics")
        hint.setAlignment(Qt.AlignCenter); hint.setWordWrap(True); hint.setStyleSheet("color:#3a3d5e;font-size:12px;")
        layout.addWidget(icon); layout.addWidget(msg); layout.addWidget(hint)
        return widget

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
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(12)
        icon = QLabel("📈"); icon.setAlignment(Qt.AlignCenter); icon.setStyleSheet("font-size:52px;")
        msg  = QLabel("No KPIs generated yet"); msg.setAlignment(Qt.AlignCenter); msg.setStyleSheet("color:#555;font-size:15px;")
        hint = QLabel("Load an Excel file and click 'Generate KPI Cards'\nLLaMA will automatically identify relevant business metrics")
        hint.setAlignment(Qt.AlignCenter); hint.setStyleSheet("color:#3a3d5e;font-size:12px;"); hint.setWordWrap(True)
        layout.addWidget(icon); layout.addWidget(msg); layout.addWidget(hint)
        return widget

    def _build_summary_box(self):
        frame = QFrame()
        frame.setStyleSheet("QFrame{background-color:#1a1d2e;border:1px solid #2a2d3e;border-radius:10px;}")
        frame.setFixedHeight(48)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(24)
        self.total_kpi_label = self._info_chip("KPIs Found",     "—")
        self.up_kpi_label    = self._info_chip("Trending Up",    "—")
        self.down_kpi_label  = self._info_chip("Trending Down",  "—")
        self.sheet_kpi_label = self._info_chip("Sheet",          "—")
        for chip in [self.total_kpi_label, self.up_kpi_label, self.down_kpi_label, self.sheet_kpi_label]:
            layout.addWidget(chip)
        layout.addStretch()
        return frame

    def _info_chip(self, label, value):
        w = QLabel(f"<span style='color:#444'>{label}: </span><span style='color:#7c83ff;font-weight:bold'>{value}</span>")
        w.setStyleSheet("background:transparent;font-size:12px;")
        return w

    def _update_chip(self, chip, label, value, color="#7c83ff"):
        chip.setText(f"<span style='color:#444'>{label}: </span><span style='color:{color};font-weight:bold'>{value}</span>")

    def _generate_kpis(self):
        if not self.current_file:
            return
        sheet = self.sheet_combo.currentText().strip() or "Sheet1"
        self.generate_btn.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.generate_btn.setText("⏳  Analyzing...")
        self.status_label.setText("LLaMA is analyzing your data...")
        self._clear_cards()
        self.empty_state.hide()
        self.scroll_area.hide()
        self.summary_frame.hide()
        self.main_window.set_status("Generating KPIs with LLaMA...")

        from gui.workers.agent_worker import KpiWorker
        self.worker = KpiWorker(self.current_file, sheet)
        self.worker.status.connect(self._on_status)
        self.worker.result.connect(self._on_result)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_status(self, msg):
        self.status_label.setText(msg)
        self.main_window.set_status(msg)

    def _on_result(self, data):
        self.generate_btn.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        self.generate_btn.setText("📈  Generate KPI Cards")
        if data["status"] == "success":
            kpis = data.get("kpis", [])
            self._clear_cards()
            self._render_cards(kpis)
            self.status_label.setText(f"{len(kpis)} KPIs generated ✓")
            self.main_window.set_status(f"{len(kpis)} KPI cards generated ✓")
        else:
            self._clear_cards()
            self.empty_state.show()
            self.scroll_area.hide()
            self.status_label.setText("Generation failed ✗")

    def _on_error(self, msg):
        self.generate_btn.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        self.generate_btn.setText("📈  Generate KPI Cards")
        self._clear_cards()
        self.empty_state.show()
        self.scroll_area.hide()
        self.status_label.setText("Error — is Ollama running?")
        self.main_window.set_status(f"Error: {msg}")

    def _render_cards(self, kpis):
        if not kpis:
            self.empty_state.show()
            self.scroll_area.hide()
            return
        self.scroll_area.show()
        self.summary_frame.show()
        up_count   = sum(1 for k in kpis if k.get("trend") == "up")
        down_count = sum(1 for k in kpis if k.get("trend") == "down")
        sheet      = self.sheet_combo.currentText()
        self._update_chip(self.total_kpi_label, "KPIs Found",    str(len(kpis)))
        self._update_chip(self.up_kpi_label,    "Trending Up",   str(up_count),   "#4caf81")
        self._update_chip(self.down_kpi_label,  "Trending Down", str(down_count), "#f44336")
        self._update_chip(self.sheet_kpi_label, "Sheet",         sheet)
        cols = 3
        for i, kpi in enumerate(kpis):
            card = KpiCard(
                title       = kpi.get("title",       "KPI"),
                value       = kpi.get("value",       "—"),
                description = kpi.get("description", ""),
                trend       = kpi.get("trend",       "neutral")
            )
            self.grid_layout.addWidget(card, i // cols, i % cols)
            self.kpi_cards.append(card)

    def _clear_cards(self):
        for card in self.kpi_cards:
            self.grid_layout.removeWidget(card)
            card.deleteLater()
        self.kpi_cards.clear()
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

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
        self.generate_btn.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        self.status_label.setText("Ready — click Generate KPI Cards")
        self._clear_cards()
        self.empty_state.show()
        self.scroll_area.hide()
        self.summary_frame.hide()
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
