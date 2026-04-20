import sys
import json
import random
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QSizePolicy, QDialog,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QFont

WORDS = {
    "00": "Zeus",  "01": "Sid",    "02": "sun",    "03": "Sam",    "04": "Sarah",
    "05": "soil",  "06": "sash",   "07": "sock",   "08": "safe",   "09": "sap",
    "10": "dice",  "11": "Toad",   "12": "dune",   "13": "dam",    "14": "tire",
    "15": "tail",  "16": "dish",   "17": "tick",   "18": "dove",   "19": "tape",
    "20": "nose",  "21": "net",    "22": "naan",   "23": "gnome",  "24": "Nero",
    "25": "nail",  "26": "Notch",  "27": "neck",   "28": "knife",  "29": "knob",
    "30": "moose", "31": "moat",   "32": "moon",   "33": "mummy",  "34": "Mario",
    "35": "mole",  "36": "Mochi",  "37": "Mike",   "38": "muff",   "39": "mop",
    "40": "rose",  "41": "rod",    "42": "Ron",    "43": "Remy",   "44": "Rory",
    "45": "rail",  "46": "Raj",    "47": "rake",   "48": "roof",   "49": "rope",
    "50": "Lisa",  "51": "loot",   "52": "lion",   "53": "lime",   "54": "Larry",
    "55": "Lalo",  "56": "leech",  "57": "lake",   "58": "leaf",   "59": "Lip",
    "60": "chess", "61": "jet",    "62": "chain",  "63": "Jim",    "64": "jar",
    "65": "cello", "66": "JJ",     "67": "Jackie", "68": "chef",   "69": "sheep",
    "70": "gas",   "71": "Kade",   "72": "Ken",    "73": "Kim",    "74": "Gary",
    "75": "kale",  "76": "cage",   "77": "Keke",   "78": "cave",   "79": "cap",
    "80": "vase",  "81": "foot",   "82": "van",    "83": "foam",   "84": "fire",
    "85": "Voli",  "86": "fudge",  "87": "fog",    "88": "fufu",   "89": "fob",
    "90": "bus",   "91": "Pat",    "92": "bun",    "93": "bomb",   "94": "bear",
    "95": "Pele",  "96": "Peach",  "97": "book",   "98": "beef",   "99": "poop",
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
IMAGES_DIR = Path("images")
IMAGE_HEIGHT = 280

MODE_ORDER  = "order"
MODE_RANDOM = "random"
MODE_WRONG  = "wrong"


def load_stats():
    base = {num: {"correct": 0, "wrong": 0} for num in WORDS}
    if STATS_FILE.exists():
        with open(STATS_FILE) as f:
            saved = json.load(f)
        for num in WORDS:
            if num in saved:
                base[num] = saved[num]
    return base


def save_stats(stats):
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, indent=2)


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
        self._major_dialog: MajorSystemDialog | None = None

        self._build_ui()
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

        self.btn_order  = self._mode_btn("In Order",    MODE_ORDER,  checked=True)
        self.btn_random = self._mode_btn("Random",      MODE_RANDOM)
        self.btn_wrong  = self._mode_btn("Most Wrong",  MODE_WRONG)

        self.btn_major = QPushButton("Major System")
        self.btn_major.setFixedHeight(36)
        self.btn_major.setStyleSheet(
            "QPushButton { border: 1px solid #888; border-radius: 6px;"
            " padding: 0 14px; background: #f0f0f0; }"
            "QPushButton:hover { background: #e0e0e0; }"
        )
        self.btn_major.clicked.connect(self._show_major)

        top.addWidget(self.btn_order)
        top.addWidget(self.btn_random)
        top.addWidget(self.btn_wrong)
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

        # Status row
        status = QHBoxLayout()
        self.progress_label = QLabel()
        self.progress_label.setFont(QFont("Arial", 12))
        self.session_label = QLabel()
        self.session_label.setFont(QFont("Arial", 12))
        status.addWidget(self.progress_label)
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
        self.btn_random.setChecked(mode == MODE_RANDOM)
        self.btn_wrong.setChecked(mode == MODE_WRONG)
        self.session_correct = 0
        self.session_wrong = 0
        self._build_deck()
        self._show_card()

    def _build_deck(self):
        keys = list(WORDS.keys())
        if self.mode == MODE_ORDER:
            self.deck = keys
        elif self.mode == MODE_RANDOM:
            self.deck = keys[:]
            random.shuffle(self.deck)
        elif self.mode == MODE_WRONG:
            self.deck = sorted(keys, key=lambda k: self.stats[k]["wrong"], reverse=True)
        self.current_index = 0
        self.is_flipped = False

    # ── Card display ─────────────────────────────────────────────────────────

    def _show_card(self):
        if self.current_index >= len(self.deck):
            self._show_complete()
            return

        num = self.deck[self.current_index]
        self.is_flipped = False

        self.card_frame.setStyleSheet(
            "QFrame { background: white; border: 2px solid #ccc; border-radius: 16px; }"
        )
        self.number_label.setText(num)
        self.number_label.show()
        self.word_label.hide()
        self.image_label.hide()

        self.progress_label.setText(f"Card {self.current_index + 1} / {len(self.deck)}")
        self._update_session_label()
        self.hint_label.setText("Space = flip     |     Enter = Got it ✓     |     Delete = Wrong ✗")

    def _flip_card(self):
        num = self.deck[self.current_index]
        if self.is_flipped:
            self.is_flipped = False
            self.word_label.hide()
            self.image_label.hide()
            self.number_label.show()
        else:
            self.is_flipped = True
            self.number_label.hide()
            self.word_label.setText(WORDS[num])
            self.word_label.show()

            img_path = self._find_image(num)
            if img_path:
                px = QPixmap(str(img_path)).scaledToHeight(
                    IMAGE_HEIGHT, Qt.SmoothTransformation
                )
                self.image_label.setPixmap(px)
                self.image_label.show()
            else:
                self.image_label.hide()

    def _mark_correct(self):
        num = self.deck[self.current_index]
        self.stats[num]["correct"] += 1
        self.session_correct += 1
        save_stats(self.stats)
        self.card_frame.setStyleSheet(
            "QFrame { background: #d4edda; border: 2px solid #28a745; border-radius: 16px; }"
        )
        self.current_index += 1
        self._show_card()

    def _mark_wrong(self):
        num = self.deck[self.current_index]
        self.stats[num]["wrong"] += 1
        self.session_wrong += 1
        save_stats(self.stats)
        self.card_frame.setStyleSheet(
            "QFrame { background: #f8d7da; border: 2px solid #dc3545; border-radius: 16px; }"
        )
        self.current_index += 1
        self._show_card()

    def _show_complete(self):
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
        for ext in ("png", "jpg", "jpeg", "webp"):
            p = IMAGES_DIR / f"{num}.{ext}"
            if p.exists():
                return p
        return None

    def _show_major(self):
        if self._major_dialog is None:
            self._major_dialog = MajorSystemDialog(self)
        self._major_dialog.show()
        self._major_dialog.raise_()
        self._major_dialog.activateWindow()

    # ── Keyboard ─────────────────────────────────────────────────────────────

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Space:
            if self.current_index < len(self.deck):
                self._flip_card()
        elif key in (Qt.Key_Return, Qt.Key_Enter):
            if self.current_index < len(self.deck):
                self._mark_correct()
        elif key in (Qt.Key_Delete, Qt.Key_Backspace):
            if self.current_index < len(self.deck):
                self._mark_wrong()
        else:
            super().keyPressEvent(event)


def main():
    IMAGES_DIR.mkdir(exist_ok=True)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = FlashcardApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
