import sys
import json
import random
import time
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QSizePolicy, QDialog, QToolTip,
    QScrollArea, QTextEdit,
)
from PySide6.QtCore import Qt, QTimer, QEvent
from PySide6.QtGui import QPixmap, QFont, QShortcut, QKeySequence, QPainter, QColor, QPen

WORDS = {
    "00": "seesaw","01": "Sid",    "02": "sun",    "03": "Sam",    "04": "Sarah",
    "05": "soil",  "06": "Sage",   "07": "sock",   "08": "safe",   "09": "soup",
    "10": "dice",  "11": "dodo",   "12": "Donna",   "13": "Dom",    "14": "door",
    "15": "doll",  "16": "Deji",   "17": "duck",   "18": "Doof",   "19": "dip",
    "20": "nose",  "21": "net",    "22": "Nunu",   "23": "Nemo",   "24": "nori",
    "25": "nail",  "26": "Nacho",  "27": "nuke",   "28": "knife",  "29": "Nepo",
    "30": "moose", "31": "mud",    "32": "moon",   "33": "mummy",  "34": "Mario",
    "35": "mail",  "36": "Mochi",  "37": "Mike",   "38": "muff",   "39": "mop",
    "40": "rose",  "41": "rod",    "42": "Ron",    "43": "ram",   "44": "Rory",
    "45": "rail",  "46": "Raj",    "47": "rake",   "48": "Rafa",   "49": "rope",
    "50": "Lisa",  "51": "lid",   "52": "lion",   "53": "lime",   "54": "Larry",
    "55": "Lulu",  "56": "leash",  "57": "Luke",   "58": "leaf",   "59": "Lip",
    "60": "Jessie","61": "jet",    "62": "Jennie",   "63": "jam",    "64": "jar",
    "65": "jello", "66": "JJ",     "67": "Jackie", "68": "Jeff",   "69": "Jeep",
    "70": "case",  "71": "cod",   "72": "can",    "73": "cam",    "74": "choir",
    "75": "kale",  "76": "cage",   "77": "Keke",   "78": "coffee",   "79": "cab",
    "80": "fez",   "81": "foot",   "82": "fan",    "83": "foam",   "84": "fire",
    "85": "file",  "86": "fudge",  "87": "fake",    "88": "fufu",   "89": "fob",
    "90": "bus",   "91": "bat",    "92": "bun",    "93": "bam",   "94": "bear",
    "95": "ball",  "96": "bush",   "97": "bike",   "98": "beef",   "99": "baby",
}

MAJOR_SYSTEM = [
    ("0", "s, z"),
    ("1", "t, d"),
    ("2", "n"),
    ("3", "m"),
    ("4", "r"),
    ("5", "L"),
    ("6", "j, sh, ch, soft g"),
    ("7", "k, hard g"),
    ("8", "f, v"),
    ("9", "p, b"),
]

STATS_FILE = Path("stats.json")
LOG_FILE   = Path("log.json")
IMAGES_DIR = Path("images")
IMAGE_HEIGHT = 280

MODE_ORDER  = "order"
MODE_REV    = "reverse"
MODE_RANDOM = "random"
MODE_WRONG  = "wrong"
MODE_SLOW   = "slow"
MODE_STATS  = "stats"
MODE_LOG    = "log"


def load_stats():
    base = {num: {"correct": 0, "wrong": 0, "total_time": 0.0, "time_count": 0} for num in WORDS}
    if STATS_FILE.exists():
        with open(STATS_FILE) as f:
            saved = json.load(f)
        for num in WORDS:
            if num in saved:
                e = saved[num]
                base[num] = {
                    "correct":    e.get("correct", 0),
                    "wrong":      e.get("wrong", 0),
                    "total_time": e.get("total_time", 0.0),
                    "time_count": e.get("time_count", 0),
                }
    return base


def save_stats(stats):
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, indent=2)


def load_log() -> list:
    if LOG_FILE.exists():
        with open(LOG_FILE) as f:
            return json.load(f)
    return []


def append_log(entry: dict):
    log = load_log()
    log.append(entry)
    with open(LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)


class MajorSystemDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Major System Reference")
        self.setModal(False)
        self.setFixedSize(320, 340)

        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(24, 20, 24, 20)

        title = QLabel("Major Memorization System")
        title.setFont(QFont("Arial", 13, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        layout.addSpacing(8)

        for digit, sounds in MAJOR_SYSTEM:
            row = QLabel(f"  {digit}  →  {sounds}")
            row.setFont(QFont("Arial", 13))
            layout.addWidget(row)


class LogView(QTextEdit):
    MODE_LABELS = {
        MODE_ORDER: "In Order", MODE_REV: "Reverse",
        MODE_RANDOM: "Random", MODE_WRONG: "Most Wrong", MODE_SLOW: "Slowest",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("Menlo", 12))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def refresh(self):
        log = load_log()
        if not log:
            self.setHtml("<p style='color:#888; margin:20px;'>No completed runs yet.</p>")
            return

        rows = []
        for e in reversed(log):
            dt = datetime.fromisoformat(e["timestamp"])
            date_str = dt.strftime("%b %d, %Y  %I:%M %p")
            mode = self.MODE_LABELS.get(e["mode"], e["mode"])
            if e.get("inverse"):
                mode += " (Inv)"
            total = e["correct"] + e["wrong"]
            pct = int(100 * e["correct"] / total) if total else 0
            m, s = divmod(e["elapsed"], 60)
            time_str = f"{m}:{s:02d}"
            color = "#28a745" if pct >= 80 else "#dc3545" if pct < 50 else "#e67e00"
            rows.append(
                f"<tr>"
                f"<td style='padding:6px 12px; color:#555;'>{date_str}</td>"
                f"<td style='padding:6px 12px;'>{mode}</td>"
                f"<td style='padding:6px 12px; color:#28a745;'>✓ {e['correct']}</td>"
                f"<td style='padding:6px 12px; color:#dc3545;'>✗ {e['wrong']}</td>"
                f"<td style='padding:6px 12px; color:{color}; font-weight:bold;'>{pct}%</td>"
                f"<td style='padding:6px 12px; color:#555;'>⏱ {time_str}</td>"
                f"</tr>"
            )

        html = (
            "<table style='border-collapse:collapse; width:100%;'>"
            "<tr style='background:#f5f5f5; font-weight:bold;'>"
            "<th style='padding:6px 12px; text-align:left;'>Date</th>"
            "<th style='padding:6px 12px; text-align:left;'>Mode</th>"
            "<th style='padding:6px 12px; text-align:left;'>Correct</th>"
            "<th style='padding:6px 12px; text-align:left;'>Wrong</th>"
            "<th style='padding:6px 12px; text-align:left;'>Score</th>"
            "<th style='padding:6px 12px; text-align:left;'>Time</th>"
            "</tr>"
            + "".join(rows)
            + "</table>"
        )
        self.setHtml(html)


class StatsChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._stats: dict = {}
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def refresh(self, stats: dict):
        self._stats = stats
        self.update()

    def _pct(self, num: str) -> float:
        s = self._stats.get(num, {"correct": 0, "wrong": 0})
        total = s["correct"] + s["wrong"]
        return s["wrong"] / total if total else 0.0

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        ml, mr, mt, mb = 48, 16, 24, 40
        cw, ch = w - ml - mr, h - mt - mb

        painter.fillRect(self.rect(), QColor("white"))

        # Title
        painter.setPen(QColor("#444"))
        painter.setFont(QFont("Arial", 9, QFont.Bold))
        painter.drawText(ml, 4, cw, 16, Qt.AlignLeft | Qt.AlignVCenter, "Wrong %")

        # Grid lines + Y labels
        painter.setFont(QFont("Arial", 9))
        for pct in (0, 25, 50, 75, 100):
            y = int(mt + ch - pct / 100 * ch)
            painter.setPen(QPen(QColor("#e0e0e0"), 1))
            painter.drawLine(ml, y, ml + cw, y)
            painter.setPen(QColor("#888"))
            painter.drawText(0, y - 8, ml - 6, 16,
                             Qt.AlignRight | Qt.AlignVCenter, f"{pct}%")

        # Bars
        bw = cw / 100
        for i in range(100):
            num = f"{i:02d}"
            pct = self._pct(num)
            bh = int(pct * ch)
            x = int(ml + i * bw)
            y = int(mt + ch - bh)
            r = int(220 * pct)
            g = int(160 * (1 - pct))
            painter.fillRect(x + 1, y, max(1, int(bw) - 1), bh, QColor(r, g, 60))

        # X labels every 10
        painter.setPen(QColor("#555"))
        painter.setFont(QFont("Arial", 8))
        for i in range(0, 100, 10):
            x = int(ml + (i + 0.5) * bw)
            painter.drawText(x - 12, h - mb + 4, 24, 16, Qt.AlignCenter, f"{i:02d}")

        # Axes
        painter.setPen(QPen(QColor("#333"), 1))
        painter.drawLine(ml, mt, ml, mt + ch)
        painter.drawLine(ml, mt + ch, ml + cw, mt + ch)

        painter.end()

    def mouseMoveEvent(self, event):
        w, h = self.width(), self.height()
        ml, mr, mt, mb = 48, 16, 24, 40
        cw = w - ml - mr
        x = event.position().x()
        if ml <= x <= ml + cw:
            i = max(0, min(99, int((x - ml) / (cw / 100))))
            num = f"{i:02d}"
            pct = self._pct(num)
            s = self._stats.get(num, {"correct": 0, "wrong": 0})
            total = s["correct"] + s["wrong"]
            word = WORDS.get(num, "")
            tip = f"{num} {word}: {pct*100:.0f}% wrong ({s['wrong']}/{total})"
            QToolTip.showText(event.globalPosition().toPoint(), tip, self)
        else:
            QToolTip.hideText()
        super().mouseMoveEvent(event)


class TimeChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._stats: dict = {}
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def refresh(self, stats: dict):
        self._stats = stats
        self.update()

    def _avg_time(self, num: str) -> float:
        s = self._stats.get(num, {})
        tc = s.get("time_count", 0)
        return s.get("total_time", 0.0) / tc if tc else 0.0

    def _ceiling(self) -> float:
        max_t = max((self._avg_time(f"{i:02d}") for i in range(100)), default=0.0)
        for nice in (3, 5, 8, 10, 15):
            if max_t <= nice:
                return float(nice)
        return max(float(int(max_t) + 1), 1.0)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        ml, mr, mt, mb = 48, 16, 24, 40
        cw, ch = w - ml - mr, h - mt - mb

        painter.fillRect(self.rect(), QColor("white"))

        ceiling = self._ceiling()

        # Title
        painter.setPen(QColor("#444"))
        painter.setFont(QFont("Arial", 9, QFont.Bold))
        painter.drawText(ml, 4, cw, 16, Qt.AlignLeft | Qt.AlignVCenter, "Avg response time (s)")

        # Grid lines + Y labels
        painter.setFont(QFont("Arial", 9))
        for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
            y = int(mt + ch - frac * ch)
            painter.setPen(QPen(QColor("#e0e0e0"), 1))
            painter.drawLine(ml, y, ml + cw, y)
            painter.setPen(QColor("#888"))
            label = f"{ceiling * frac:.0f}s"
            painter.drawText(0, y - 8, ml - 6, 16,
                             Qt.AlignRight | Qt.AlignVCenter, label)

        # Bars
        bw = cw / 100
        for i in range(100):
            num = f"{i:02d}"
            avg = self._avg_time(num)
            if avg == 0:
                continue
            bh = int((avg / ceiling) * ch)
            x = int(ml + i * bw)
            y = int(mt + ch - bh)
            intensity = min(avg / ceiling, 1.0)
            painter.fillRect(x + 1, y, max(1, int(bw) - 1), bh,
                             QColor(int(60 + 80 * (1 - intensity)),
                                    int(120 + 40 * (1 - intensity)),
                                    int(200 + 55 * intensity)))

        # X labels every 10
        painter.setPen(QColor("#555"))
        painter.setFont(QFont("Arial", 8))
        for i in range(0, 100, 10):
            x = int(ml + (i + 0.5) * bw)
            painter.drawText(x - 12, h - mb + 4, 24, 16, Qt.AlignCenter, f"{i:02d}")

        # Axes
        painter.setPen(QPen(QColor("#333"), 1))
        painter.drawLine(ml, mt, ml, mt + ch)
        painter.drawLine(ml, mt + ch, ml + cw, mt + ch)

        painter.end()

    def mouseMoveEvent(self, event):
        w, h = self.width(), self.height()
        ml, mr, mt, mb = 48, 16, 24, 40
        cw = w - ml - mr
        x = event.position().x()
        if ml <= x <= ml + cw:
            i = max(0, min(99, int((x - ml) / (cw / 100))))
            num = f"{i:02d}"
            avg = self._avg_time(num)
            s = self._stats.get(num, {})
            tc = s.get("time_count", 0)
            word = WORDS.get(num, "")
            tip = (f"{num} {word}: {avg:.1f}s avg ({tc} timed)"
                   if tc else f"{num} {word}: no data yet")
            QToolTip.showText(event.globalPosition().toPoint(), tip, self)
        else:
            QToolTip.hideText()
        super().mouseMoveEvent(event)


class FlashcardApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Major System Flashcards")
        self.setMinimumSize(620, 720)

        self.stats = load_stats()
        self.mode = MODE_ORDER
        self.deck: list[str] = []
        self.current_index = 0
        self.is_flipped = False
        self.session_correct = 0
        self.session_wrong = 0
        self.session_marks: dict[int, str] = {}
        self.is_inverse = False
        self._major_dialog: MajorSystemDialog | None = None

        self._elapsed = 0
        self._timer_running = False
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self._card_shown_at: dict[int, float] = {}
        self._focus_lost_at: float | None = None

        self._build_ui()
        self._setup_shortcuts()
        self._build_deck()
        self._show_card()

    # ── UI construction ──────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(12)
        root.setContentsMargins(24, 20, 24, 20)

        # Top bar
        top = QHBoxLayout()
        top.setSpacing(8)

        self.btn_order  = self._mode_btn("In Order",       MODE_ORDER,  checked=True)
        self.btn_rev    = self._mode_btn("Reverse",        MODE_REV)
        self.btn_random = self._mode_btn("Random",         MODE_RANDOM)
        self.btn_wrong  = self._mode_btn("Most Wrong",     MODE_WRONG)
        self.btn_slow   = self._mode_btn("Slowest",        MODE_SLOW)
        self.btn_stats  = self._mode_btn("Statistics",     MODE_STATS)
        self.btn_log    = self._mode_btn("Log",            MODE_LOG)

        self.btn_inverse = QPushButton("⇄")
        self.btn_inverse.setCheckable(True)
        self.btn_inverse.setFixedSize(36, 36)
        self.btn_inverse.setFont(QFont("Arial", 16))
        self.btn_inverse.setToolTip("Flip Cards (show word first)")
        self.btn_inverse.setStyleSheet(
            "QPushButton { border: 1px solid #888; border-radius: 6px;"
            " padding: 0; background: #f0f0f0; }"
            "QPushButton:checked { background: #1a6fb5; color: white; border-color: #1a6fb5; }"
            "QPushButton:hover:!checked { background: #e0e0e0; }"
        )
        self.btn_inverse.clicked.connect(self._toggle_inverse)

        self.btn_major = QPushButton("ⓘ")
        self.btn_major.setFixedSize(36, 36)
        self.btn_major.setFont(QFont("Arial", 16))
        self.btn_major.setToolTip("Major System reference")
        self.btn_major.setStyleSheet(
            "QPushButton { border: 1px solid #888; border-radius: 6px;"
            " padding: 0; background: #f0f0f0; }"
            "QPushButton:hover { background: #e0e0e0; }"
        )
        self.btn_major.clicked.connect(self._show_major)

        top.addWidget(self.btn_order)
        top.addWidget(self.btn_rev)
        top.addWidget(self.btn_random)
        top.addWidget(self.btn_wrong)
        top.addWidget(self.btn_slow)
        top.addWidget(self.btn_stats)
        top.addWidget(self.btn_log)
        top.addWidget(self.btn_inverse)
        top.addStretch()
        top.addWidget(self.btn_major)
        root.addLayout(top)

        # Card frame
        self.card_frame = QFrame()
        self.card_frame.setFrameShape(QFrame.Box)
        self.card_frame.setStyleSheet(
            "QFrame { background: white; border: 2px solid #ccc; border-radius: 16px; }"
        )
        self.card_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        card_layout = QVBoxLayout(self.card_frame)
        card_layout.setAlignment(Qt.AlignCenter)
        card_layout.setSpacing(16)

        self.number_label = QLabel()
        self.number_label.setAlignment(Qt.AlignCenter)
        self.number_label.setFont(QFont("Arial", 90, QFont.Bold))

        self.word_label = QLabel()
        self.word_label.setAlignment(Qt.AlignCenter)
        self.word_label.setFont(QFont("Arial", 52, QFont.Bold))
        self.word_label.hide()

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.hide()

        card_layout.addWidget(self.number_label)
        card_layout.addWidget(self.word_label)
        card_layout.addWidget(self.image_label)
        root.addWidget(self.card_frame, stretch=1)

        self.stats_chart = StatsChart()
        self.stats_chart.hide()
        root.addWidget(self.stats_chart, stretch=1)

        self.time_chart = TimeChart()
        self.time_chart.hide()
        root.addWidget(self.time_chart, stretch=1)

        self.log_view = LogView()
        self.log_view.hide()
        root.addWidget(self.log_view, stretch=1)

        # Status row
        status = QHBoxLayout()
        self.progress_label = QLabel()
        self.progress_label.setFont(QFont("Arial", 12))
        self.timer_label = QLabel()
        self.timer_label.setFont(QFont("Arial", 12))
        self.timer_label.setStyleSheet("color: #666;")
        self.session_label = QLabel()
        self.session_label.setFont(QFont("Arial", 12))
        status.addWidget(self.progress_label)
        status.addWidget(self.timer_label)
        status.addStretch()
        status.addWidget(self.session_label)
        root.addLayout(status)

        # Hint
        self.hint_label = QLabel("Press Enter to flip")
        self.hint_label.setAlignment(Qt.AlignCenter)
        self.hint_label.setFont(QFont("Arial", 11))
        self.hint_label.setStyleSheet("color: #666;")
        root.addWidget(self.hint_label)

    def _mode_btn(self, label: str, mode: str, *, checked=False) -> QPushButton:
        btn = QPushButton(label)
        btn.setCheckable(True)
        btn.setChecked(checked)
        btn.setFixedHeight(36)
        btn.setStyleSheet(
            "QPushButton { border: 1px solid #888; border-radius: 6px;"
            " padding: 0 14px; background: #f0f0f0; }"
            "QPushButton:checked { background: #333; color: white; border-color: #333; }"
            "QPushButton:hover:!checked { background: #e0e0e0; }"
        )
        btn.clicked.connect(lambda: self._set_mode(mode))
        return btn

    # ── Mode / deck ──────────────────────────────────────────────────────────

    def _set_mode(self, mode: str):
        self.mode = mode
        self.btn_order.setChecked(mode == MODE_ORDER)
        self.btn_rev.setChecked(mode == MODE_REV)
        self.btn_random.setChecked(mode == MODE_RANDOM)
        self.btn_wrong.setChecked(mode == MODE_WRONG)
        self.btn_slow.setChecked(mode == MODE_SLOW)
        self.btn_stats.setChecked(mode == MODE_STATS)
        self.btn_log.setChecked(mode == MODE_LOG)

        self.card_frame.hide()
        self.stats_chart.hide()
        self.time_chart.hide()
        self.log_view.hide()

        if mode == MODE_STATS:
            self.stats_chart.refresh(self.stats)
            self.time_chart.refresh(self.stats)
            self.stats_chart.show()
            self.time_chart.show()
            self.progress_label.setText("")
            self.timer_label.setText("")
            self.hint_label.setText("Hover a bar for details")
        elif mode == MODE_LOG:
            self.log_view.refresh()
            self.log_view.show()
            self.progress_label.setText("")
            self.timer_label.setText("")
            self.hint_label.setText("")
        else:
            self.card_frame.show()
            self.session_correct = 0
            self.session_wrong = 0
            self.session_marks = {}
            self._reset_timer()
            self._build_deck()
            self._show_card()

    def _build_deck(self):
        keys = list(WORDS.keys())
        if self.mode == MODE_ORDER:
            self.deck = keys
        elif self.mode == MODE_REV:
            self.deck = list(reversed(keys))
        elif self.mode == MODE_RANDOM:
            self.deck = keys[:]
            random.shuffle(self.deck)
        elif self.mode == MODE_WRONG:
            def wrong_pct(k):
                s = self.stats[k]
                total = s["correct"] + s["wrong"]
                return s["wrong"] / total if total else 0
            self.deck = sorted(keys, key=wrong_pct, reverse=True)
        elif self.mode == MODE_SLOW:
            def avg_time(k):
                s = self.stats[k]
                tc = s.get("time_count", 0)
                return s.get("total_time", 0.0) / tc if tc else 0.0
            self.deck = sorted(keys, key=avg_time, reverse=True)
        self.current_index = 0
        self.is_flipped = False
        self.session_marks = {}
        self._card_shown_at = {}

    # ── Card display ─────────────────────────────────────────────────────────

    def _show_number_side(self, num: str):
        self.number_label.setFont(QFont("Arial", 90, QFont.Bold))
        self.number_label.setText(num)
        self.number_label.show()
        self.word_label.hide()
        self.image_label.hide()

    def _show_word_side(self, num: str):
        self.number_label.hide()
        self.word_label.setText(WORDS[num])
        self.word_label.show()
        img_path = self._find_image(num)
        px = QPixmap(str(img_path)) if img_path else QPixmap()
        if not px.isNull():
            self.image_label.setPixmap(px.scaledToHeight(IMAGE_HEIGHT, Qt.SmoothTransformation))
            self.image_label.show()
        else:
            self.image_label.hide()

    def _show_card(self):
        if self.current_index >= len(self.deck):
            self._show_complete()
            return

        num = self.deck[self.current_index]
        self.is_flipped = False

        if self.current_index not in self._card_shown_at:
            self._card_shown_at[self.current_index] = time.time()

        mark = self.session_marks.get(self.current_index)
        if mark == "correct":
            style = "QFrame { background: #d4edda; border: 2px solid #28a745; border-radius: 16px; }"
        elif mark == "wrong":
            style = "QFrame { background: #f8d7da; border: 2px solid #dc3545; border-radius: 16px; }"
        else:
            style = "QFrame { background: white; border: 2px solid #ccc; border-radius: 16px; }"
        self.card_frame.setStyleSheet(style)

        if self.is_inverse:
            self._show_word_side(num)
        else:
            self._show_number_side(num)

        self.progress_label.setText(f"Card {self.current_index + 1} / {len(self.deck)}")
        self._update_session_label()
        self.hint_label.setText("← → navigate     Space = flip     Enter = ✓     Delete = ✗")

    def _flip_card(self):
        if self.current_index >= len(self.deck):
            return
        num = self.deck[self.current_index]
        if self.is_flipped:
            self.is_flipped = False
            if self.is_inverse:
                self._show_word_side(num)
            else:
                self._show_number_side(num)
        else:
            self.is_flipped = True
            if self.is_inverse:
                self._show_number_side(num)
            else:
                self._show_word_side(num)

    def _mark_correct(self):
        self._record_mark("correct")

    def _mark_wrong(self):
        self._record_mark("wrong")

    def _record_mark(self, result: str):
        if self.current_index >= len(self.deck):
            return
        idx = self.current_index
        num = self.deck[idx]
        prev = self.session_marks.get(idx)

        shown_at = self._card_shown_at.pop(idx, None)
        if shown_at is not None and prev is None:
            card_time = min(time.time() - shown_at, 15.0)
            self.stats[num]["total_time"] = self.stats[num].get("total_time", 0.0) + card_time
            self.stats[num]["time_count"] = self.stats[num].get("time_count", 0) + 1

        if prev != result:
            if prev == "correct":
                self.stats[num]["correct"] = max(0, self.stats[num]["correct"] - 1)
                self.session_correct -= 1
            elif prev == "wrong":
                self.stats[num]["wrong"] = max(0, self.stats[num]["wrong"] - 1)
                self.session_wrong -= 1
            self.stats[num][result] += 1
            if result == "correct":
                self.session_correct += 1
            else:
                self.session_wrong += 1
            self.session_marks[idx] = result
            save_stats(self.stats)
            self.stats_chart.refresh(self.stats)
            self.time_chart.refresh(self.stats)

        self._start_timer()
        self.current_index += 1
        self._show_card()

    def _show_complete(self):
        self._timer.stop()
        if self._timer_running:
            append_log({
                "timestamp": datetime.now().isoformat(),
                "mode":      self.mode,
                "inverse":   self.is_inverse,
                "correct":   self.session_correct,
                "wrong":     self.session_wrong,
                "elapsed":   self._elapsed,
            })
        self.card_frame.setStyleSheet(
            "QFrame { background: white; border: 2px solid #ccc; border-radius: 16px; }"
        )
        self.number_label.setFont(QFont("Arial", 48, QFont.Bold))
        self.number_label.setText("Done!")
        self.number_label.show()
        self.word_label.hide()
        self.image_label.hide()
        self.progress_label.setText("")
        self._update_session_label()
        total = self.session_correct + self.session_wrong
        pct = int(100 * self.session_correct / total) if total else 0
        self.hint_label.setText(f"{pct}% correct this session — pick a mode to restart")

    def _update_session_label(self):
        self.session_label.setText(
            f"Correct: {self.session_correct}   Wrong: {self.session_wrong}"
        )

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _find_image(num: str) -> Path | None:
        p = IMAGES_DIR / f"{num}.webp"
        return p if p.exists() else None

    def _toggle_inverse(self):
        self.is_inverse = self.btn_inverse.isChecked()
        if self.mode not in (MODE_STATS, MODE_LOG):
            self._reset_timer()
            self.session_correct = 0
            self.session_wrong = 0
            self.session_marks = {}
            self._build_deck()
            self._show_card()

    def _tick(self):
        self._elapsed += 1
        m, s = divmod(self._elapsed, 60)
        self.timer_label.setText(f"  {m}:{s:02d}")

    def _start_timer(self):
        if not self._timer_running:
            self._timer_running = True
            self._timer.start()

    def _reset_timer(self):
        self._timer.stop()
        self._timer_running = False
        self._elapsed = 0
        self.timer_label.setText("")

    def _show_major(self):
        if self._major_dialog is None:
            self._major_dialog = MajorSystemDialog(self)
        self._major_dialog.show()
        self._major_dialog.raise_()
        self._major_dialog.activateWindow()

    # ── Focus tracking ───────────────────────────────────────────────────────

    def changeEvent(self, event):
        if event.type() == QEvent.Type.WindowDeactivate:
            self._focus_lost_at = time.time()
        elif event.type() == QEvent.Type.WindowActivate and self._focus_lost_at is not None:
            pause_duration = time.time() - self._focus_lost_at
            for k in self._card_shown_at:
                self._card_shown_at[k] += pause_duration
            self._focus_lost_at = None
        super().changeEvent(event)

    # ── Keyboard ─────────────────────────────────────────────────────────────

    def _nav_prev(self):
        if self.current_index > 0:
            self.current_index -= 1
            self._show_card()

    def _nav_next(self):
        if self.current_index < len(self.deck):
            self.current_index += 1
            self._show_card()

    def _setup_shortcuts(self):
        for key, slot in [
            (Qt.Key_Space,     self._flip_card),
            (Qt.Key_Return,    self._mark_correct),
            (Qt.Key_Enter,     self._mark_correct),
            (Qt.Key_Delete,    self._mark_wrong),
            (Qt.Key_Backspace, self._mark_wrong),
            (Qt.Key_Left,      self._nav_prev),
            (Qt.Key_Right,     self._nav_next),
        ]:
            sc = QShortcut(QKeySequence(key), self)
            sc.setContext(Qt.ApplicationShortcut)
            sc.activated.connect(slot)



def main():
    IMAGES_DIR.mkdir(exist_ok=True)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = FlashcardApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
