"""Major System Flashcards — pywebview desktop app.

The UI lives in ./web (HTML + Tailwind + JS). This module is the Python
backend: it owns the word list, persists stats/log to disk, and exposes a
small JS-callable API over the pywebview bridge.
"""

import base64
import json
from pathlib import Path

import webview

WORDS = {
    "00": "seesaw","01": "Sid",    "02": "sun",    "03": "Sam",    "04": "Sarah",
    "05": "soil",  "06": "Sage",   "07": "sock",   "08": "safe",   "09": "soup",
    "10": "dice",  "11": "dodo",   "12": "Donna",   "13": "Dom",    "14": "door",
    "15": "doll",  "16": "Deji",   "17": "duck",   "18": "Doof",   "19": "dip",
    "20": "nose",  "21": "net",    "22": "Nunu",   "23": "Nemo",   "24": "nori",
    "25": "nail",  "26": "Nacho",  "27": "nuke",   "28": "knife",  "29": "Nepo",
    "30": "moose", "31": "mud",    "32": "moon",   "33": "mummy",  "34": "Mario",
    "35": "mail",  "36": "Mochi",  "37": "Mike",   "38": "muff",   "39": "mop",
    "40": "rose",  "41": "rod",    "42": "Ron",    "43": "Remy",   "44": "Rory",
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
WEB_DIR    = Path(__file__).parent / "web"


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


class Api:
    """Methods here are callable from JS as `window.pywebview.api.<name>(...)`."""

    def __init__(self):
        self.stats = load_stats()
        self._image_cache: dict[str, str | None] = {}

    def bootstrap(self) -> dict:
        """Everything the frontend needs on startup."""
        return {
            "words": WORDS,
            "major": MAJOR_SYSTEM,
            "stats": self.stats,
            "log":   load_log(),
        }

    def image(self, num: str) -> str | None:
        """Return the card image as a base64 data URI (cached), or None."""
        if num in self._image_cache:
            return self._image_cache[num]
        path = IMAGES_DIR / f"{num}.webp"
        uri = None
        if path.exists():
            data = base64.b64encode(path.read_bytes()).decode("ascii")
            uri = f"data:image/webp;base64,{data}"
        self._image_cache[num] = uri
        return uri

    def record_mark(self, num: str, result: str, prev, card_time) -> dict:
        """Apply a correct/wrong mark to persistent stats and save.

        `prev` is the card's previous mark (None on first mark). `card_time`
        is seconds-to-first-answer; it is only recorded on the first mark.
        Returns the full updated stats dict.
        """
        s = self.stats[num]
        changed = False

        if card_time is not None and prev is None:
            s["total_time"] = s.get("total_time", 0.0) + min(card_time, 15.0)
            s["time_count"] = s.get("time_count", 0) + 1
            changed = True

        if prev != result:
            if prev == "correct":
                s["correct"] = max(0, s["correct"] - 1)
            elif prev == "wrong":
                s["wrong"] = max(0, s["wrong"] - 1)
            s[result] += 1
            changed = True

        if changed:
            save_stats(self.stats)
        return self.stats

    def finish_session(self, entry: dict) -> list:
        """Append a completed-run entry to the log and return the full log."""
        append_log(entry)
        return load_log()


def main():
    IMAGES_DIR.mkdir(exist_ok=True)
    api = Api()
    webview.create_window(
        "Major System Flashcards",
        url=str(WEB_DIR / "index.html"),
        js_api=api,
        width=900,
        height=900,
        min_size=(820, 720),
        background_color="#f1ede3",
    )
    webview.start()


if __name__ == "__main__":
    main()
