# -*- coding: utf-8 -*-
"""Yavir Tools - адмін-тулс для MTA (Windows). PySide6 + psutil + keyboard."""
import sys, os, re, json, time, threading, ctypes, datetime, collections, io, wave, math, struct, asyncio, traceback, sqlite3, random
import hashlib, hmac
import urllib.request, urllib.error
from ctypes import wintypes

from PySide6.QtCore import Qt, QObject, QThread, QTimer, Signal, QEvent, QRectF, QPointF, Property, QElapsedTimer
from PySide6.QtGui import QFont, QTextCursor, QBrush
from PySide6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QHBoxLayout, QVBoxLayout, QGridLayout,
    QLabel, QPushButton, QStackedWidget, QFrame, QListWidget, QListWidgetItem,
    QTextEdit, QPlainTextEdit, QLineEdit, QCheckBox, QComboBox, QSpinBox,
    QDoubleSpinBox, QProgressBar, QSlider, QScrollArea, QTableWidget, QTableWidgetItem, QTimeEdit,
    QTabWidget, QFileDialog, QHeaderView, QSplitter, QMessageBox, QSizePolicy, QDialog, QTextBrowser,
    QInputDialog)
from PySide6.QtCore import QTime

import psutil
try:
    import keyboard
except Exception:
    keyboard = None

try:
    from winsdk.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as MediaSessionManager
    from winsdk.windows.storage.streams import DataReader as WinDataReader
except Exception:
    MediaSessionManager = None
    WinDataReader = None

IS_WIN = os.name == "nt"
if IS_WIN:
    import winsound
    user32 = ctypes.windll.user32

APP = "Yavir Tools"
APP_VERSION = "1.0.0"          # змінюйте при кожному релізі
# Пряме посилання на текстовий файл з останньою версією (одним рядком, напр. "1.2.0").
# Порожньо = перевірка вимкнена.
UPDATE_VERSION_URL = ""
DATA = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "YavirTools")
CHATLOG_DIR = os.path.join(DATA, "chatlogs")
PLAYERS_DB_PATH = os.path.join(DATA, "players.sqlite3")
CHATLOG_RETENTION_SECONDS = 7 * 24 * 60 * 60
os.makedirs(CHATLOG_DIR, exist_ok=True)
CFG_PATH = os.path.join(DATA, "config.json")
AI_CHAT_PATH = os.path.join(DATA, "ai_chat.json")


def resource_path(relative_path):
    root = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, relative_path)


LEVELS = ["Ігровий помічник", "Модератор", "Молодший Адміністратор", "Адміністратор",
          "Старший Адміністратор", "Куратор Лідерів", "Куратор Адміністрації",
          "Головний Адміністратор"]
POSITIONS = ["Немає посади", "Слідкуючий за держ. орг", "Слідкуючий за неоф. орг",
             "Слідкуючий зльот", "ЗГС зльот", "ГС зльот", "ГС Держ", "ЗГС Держ", "M.D"]

FORM_COMMAND_PATTERN = (r"(?:pmute|pbanoffline|pban|offmute|jailoffline|jail|sethp|acuff|warn|offwarn|"
                        r"pfreeze|punfreeze|pkick|reviving|vehspawn|offunwarn|offunmute|punban|offunjail)")
FORM_RANK_PATTERN = (r"(?P<form_rank>\[[^\]]+\]\s*.+?\[\d+\]:\s*/?" + FORM_COMMAND_PATTERN + r"\b.+)")

DEFAULT = {
    "admin_name": "Admin_Name", "admin_level": LEVELS[0], "admin_position": "Немає посади", "avatar_path": "",
    "game_process": "gta_sa.exe", "log_path": "", "chat_open_delay": 25,
    "key_pm": "f3", "key_id": "f4", "key_form": "f2", "key_reject_form": "f1",
    "key_overlay_menu": "alt+z",
    "auto_id_pm": True, "id_open_chat": False, "report_reminder_enabled": False,
    "report_reminder_minutes": 5, "log_chat": True,
    "admin_chat_cmd": "/a",
    "reply_cmd": "pm {id} {text}",
    "mute_cmd": "/pmute {id} 30 Реклама у /vip",
    "form_accept_cmd": "/af",
    "form_accepted_msg": "[Yavir_Tools] Accepted form: {form}",
    "form_declined_msg": "[Yavir_Tools] Declined form",
    "report_sound": False, "do_not_disturb": False, "ui_scale": 1.0, "overlay_edit_mode": False, "overlay_scale": 100, "autosave_settings": False, "sound_volume": 80,
    "overlay_max_rows": 6, "report_expire_minutes": 60,
    "report_splitter_sizes": [370, 860],
    "report_regex": r"Репорт від гравця\s+(?P<name>.+?)\s*\[(?P<id>\d+)\]:\s*(?P<text>.+)",
    "colleague_regex": r"(?:\[PM\]\s*\[[^\]]+\]\s*(?P<admin>.+?)\[\d+\]\s*->\s*(?P<name>.+?)\[(?P<id>\d+)\]:\s*(?P<reply>.+)|(?P<admin_legacy>[^\s\[\]]+) відповів на репорт (?P<name_legacy>.+?)\s*\[(?P<id_legacy>\d+)\])",
    "form_regex": r"(?:\[Форма\]\s*(?P<form>.+)|" + FORM_RANK_PATTERN + r")",
    "form_reject_regex": r"Форму відхилено|форму було відхилено", "form_test_send": False,
    "vip_regex": r"\[VIP\]\s*(?P<name>.+?)\s*\[(?P<id>\d+)\]:\s*(?P<text>.+)",
    "ac_regex": r"(?:\[(?:AC|AntiCheat|Anticheat|Античіт|Античит)\]\s*(?P<text>.+)|\[A\]\s*Увага!\s*Гравець\s*(?P<alert>.+?підозрюється\s+в\s+.+))",
    "vip_ad_words": "продам, пр0дам, прoдам, пр.одам, пр..одам, пр-одам, продаю, пр0даю, пр.даю, куплю, куп.лю, ку.плю, ку..плю, кyплю, скуплю, обмін, обмен, discord, дискорд, t.me, telegram, youtube, http, www., .com, .ua, .ru, ip:",
    "banned_words": "",
    "vip_monitor_start": "11:00", "vip_monitor_end": "22:00",
    "quick_binds_count": 6,
    "commands": [],
    "users_bulk_delete_mode": False,
    "player_notes": {},
    "norm_hours": 4.0, "shift_active": False, "norm_overlay": True, "overlay_enabled": True, "overlay_compact": False,
    "overlay_test_mode": False,
    "spotify_overlay_enabled": True,
    "winter_garland": True, "winter_snowfall": True,
    "overlay_x": 20, "overlay_y": 200, "norm_date": "", "norm_seconds": 0,
    "game_overlay_x": -1, "game_overlay_y": 28,
    "notification_width": 540, "notification_height": 104, "dynamic_island": True,
    "snd_take": "", "snd_reject": "", "snd_accept": "", "snd_reply": "", "snd_warn": "",
    "snd_vip": "", "snd_ac": "", "snd_report": "", "snd_ui": "",
    "gemini_key": "", "gemini_model": "gemini-2.5-flash", "ai_auto": False,
    "ai_report_prompt": ("Ти помічник адміністратора ігрового сервера MTA. Склади коротку, ввічливу "
                         "відповідь українською на репорт гравця (1-2 речення). Не вигадуй фактів, "
                         "не обіцяй покарань. Поверни лише текст відповіді, не довший за 110 символів."),
    "ai_chat_prompt": ("Ти — ШІ-помічник адміністратора українського ігрового сервера MTA. Відповідай українською, "
                       "коротко й по суті. Допомагай формулювати відповіді гравцям, причини покарань, перевіряти "
                       "тексти та пояснювати правила. Не вигадуй правил сервера, яких не знаєш, і не називай "
                       "терміни покарань без підстав. Якщо просять відповідь для гри — давай готовий текст до "
                       "110 символів без форматування."),
    "liquid_glass": False, "liquid_glass_strength": 40, "liquid_glass_edge": 75, "liquid_glass_blur": 60,
    "complaint_template": ("Заголовок: [Нік адміністратора / нік порушника — суть скарги]\n"
                           "Ваш нік: \nДата й час події: \nОпис ситуації: \nДокази (посилання): "),
    "complaint_rules": ("ПРИКЛАД - замініть на реальні правила вашого сервера:\n"
                        "1. Заголовок: 'Нік адміністратора / Нік порушника - суть'.\n"
                        "2. Вказати свій нік, дату та час порушення.\n"
                        "3. Докази (відео/скріншоти) обов'язкові, посилання на хостинг.\n"
                        "4. Докази мають показувати момент порушення повністю, з /time.\n"
                        "5. Скарга подається не пізніше 48 годин після порушення.\n"
                        "6. Заборонено образи та капс у тексті скарги."),
    "binds": [
        {"keys": "alt+f6", "text": "Вітаю, чим можу допомогти?", "send": True, "open_chat": True},
        {"keys": "alt+f7", "text": "Перевіряю вашу ситуацію, зачекайте, будь ласка.", "send": True, "open_chat": True},
        {"keys": "alt+f3", "text": "Приємної гри!", "send": True, "open_chat": True},
        {"keys": "alt+f5", "text": "Звертайтеся, якщо виникнуть питання.", "send": True, "open_chat": True},
    ],
}


def load_cfg():
    cfg = json.loads(json.dumps(DEFAULT))
    try:
        with open(CFG_PATH, "r", encoding="utf-8") as f:
            saved_cfg = json.load(f)
            saved_cfg.pop("auto_forms", None)
            for legacy_key in ("key_record", "record_process", "record_fps", "record_resolution", "record_output_folder"):
                saved_cfg.pop(legacy_key, None)
            cfg.pop("key_record", None)
            for legacy_key in ("record_process", "record_fps", "record_resolution", "record_output_folder"):
                cfg.pop(legacy_key, None)
            cfg.update(saved_cfg)
            # Remove the expensive winter decorations from older saved configs.
            for winter_key in ("winter_effects", "winter_shooting_star", "winter_snow_base", "winter_ice_corners"):
                cfg.pop(winter_key, None)
            if cfg.get("form_accepted_msg") == "{admin}":
                cfg["form_accepted_msg"] = DEFAULT["form_accepted_msg"]
            # Migrate the old built-in pattern so saved configs also accept names without a space before [ID].
            if cfg.get("report_regex") == r"Репорт від гравця (?P<name>.+?) \[(?P<id>\d+)\]:\s*(?P<text>.+)":
                cfg["report_regex"] = DEFAULT["report_regex"]
            if cfg.get("ac_regex") == r"\[(?:AC|AntiCheat|Anticheat|Античіт|Античит)\]\s*(?P<text>.+)":
                cfg["ac_regex"] = DEFAULT["ac_regex"]
            old_ads = "продам, куплю, продаю, скуплю, обмін, discord, дискорд, t.me, youtube, http, www., .com, .ua, .ru, ip:"
            if cfg.get("vip_ad_words") == old_ads:
                cfg["vip_ad_words"] = DEFAULT["vip_ad_words"]
            for bind in cfg.get("binds", []):
                if bind.get("keys", "").lower() == "alt+f1" and bind.get("text") == "Вітаю, чим можу допомогти?":
                    bind["keys"] = "alt+f6"
                elif bind.get("keys", "").lower() == "alt+f2" and bind.get("text") == "Перевіряю вашу ситуацію, зачекайте, будь ласка.":
                    bind["keys"] = "alt+f7"
            if cfg.get("form_regex") in (r"\[Форма\]\s*(?P<form>.+)",
                                           r"(?:\[Форма\]\s*(?P<form>.+)|\[[^\]]+\]\s*(?P<form_rank>.+?\[\d+\]:\s*\S.+))",
                                           r"(?:\[Форма\]\s*(?P<form>.+)|(?P<form_rank>\[[^\]]+\]\s*.+?\[\d+\]:\s*/?(?:pmute|pbanoffline|pban|offmute|jailoffline|jail)\b.+))"):
                cfg["form_regex"] = DEFAULT["form_regex"]
            old_colleague = r"(?:\[PM\]\s*\[[^\]]+\]\s*(?P<admin>.+?)\[\d+\]\s*->\s*(?P<name>.+?)\[(?P<id>\d+)\]:|(?P<admin_legacy>[^\s\[\]]+) відповів на репорт (?P<name_legacy>.+?)\s*\[(?P<id_legacy>\d+)\])"
            if cfg.get("colleague_regex") == old_colleague:
                cfg["colleague_regex"] = DEFAULT["colleague_regex"]
    except Exception:
        pass
    return cfg


def save_cfg(cfg):
    try:
        with open(CFG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("cfg save error", e)


# ---------------------------------------------------------------- Права доступу (керує власник під паролем)
ACCESS_SECRET = b"YavirTools::access::v1::change-me-before-build"
# Корінний пароль власника. Однаковий на кожному ПК, його не можна замінити локальним.
ROOT_PASSWORD = "461243"
# Адреса, звідки всі копії програми беруть права (raw-посилання на gist). Заповнюється один раз після
# першої публікації з панелі «Права доступу» (програма покаже готовий рядок). Порожньо = без віддаленої синхронізації.
ACCESS_URL = ""

# (id, назва, група, небезпечна) — «небезпечні» вимикаються, якщо файл прав пошкоджено/підроблено
ACCESS_FEATURES = [
    ("page_dash", "Дашборд", "Сторінки", False),
    ("page_reports", "Репорти", "Сторінки", False),
    ("page_users", "Користувачі", "Сторінки", True),
    ("page_vip", "VIP чат", "Сторінки", False),
    ("page_binds", "Бінди", "Сторінки", False),
    ("page_po", "Адмін ПО", "Сторінки", False),
    ("page_punishments", "Відправка покарань", "Сторінки", True),
    ("page_complaint", "Розгляд скарги", "Сторінки", False),
    ("page_chat", "Чат з ШІ", "Сторінки", False),
    ("page_settings", "Налаштування", "Сторінки", True),
    ("rep_send", "Репорти: «Надіслати» відповідь", "Дії в репортах", False),
    ("rep_ai", "Репорти: «ШІ-відповідь»", "Дії в репортах", False),
    ("rep_take", "Репорти: «Вставити /pm ID»", "Дії в репортах", False),
    ("rep_spectate", "Репорти: «Слідкувати»", "Дії в репортах", True),
    ("rep_warp", "Репорти: «Телепортуватися»", "Дії в репортах", True),
    ("rep_admin", "Репорти: «В адмін-чат»", "Дії в репортах", False),
    ("rep_colleague", "Репорти: «Відповідь колеги»", "Дії в репортах", False),
    ("rep_copy", "Репорти: «Скопіювати репорт»", "Дії в репортах", False),
    ("rep_remove", "Репорти: «Прибрати» / очистити", "Дії в репортах", False),
    ("rep_quick", "Репорти: швидкі відповіді (бінди на картці)", "Дії в репортах", False),
    ("rep_commands", "Репорти: кнопки команд на картці", "Дії в репортах", True),
    ("hk_take", "Хоткей: авто ID (PM)", "Гарячі клавіші", False),
    ("hk_id", "Хоткей: вставка ID", "Гарячі клавіші", False),
    ("hk_form_accept", "Хоткей/кнопка: прийняти форму", "Гарячі клавіші", True),
    ("hk_form_reject", "Хоткей/кнопка: відхилити форму", "Гарячі клавіші", True),
    ("hk_binds", "Хоткеї: бінди та команди", "Гарячі клавіші", False),
    ("hk_overlay_menu", "Хоткей: ігрова панель (Alt+Z)", "Гарячі клавіші", False),
    ("notif_colleague", "Сповіщення про відповідь колеги", "Інше", False),
    ("overlay_view", "Екранний оверлей репортів/норми", "Інше", False),
    ("punish_send", "Відправка покарань/команд у гру", "Інше", True),
]
ACCESS_BY_ID = {f[0]: f for f in ACCESS_FEATURES}


def _hash_pw(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 200_000).hex()


_ROOT_PASS_CACHE = None


def _root_pass():
    # PBKDF2 на 200 000 ітерацій дорогий (~0.1 с) — рахуємо один раз за запуск.
    global _ROOT_PASS_CACHE
    if _ROOT_PASS_CACHE is None:
        salt = hashlib.sha256(b"YavirTools::root-password::v1").hexdigest()[:32]
        _ROOT_PASS_CACHE = {"salt": salt, "hash": _hash_pw(ROOT_PASSWORD, salt)}
    return dict(_ROOT_PASS_CACHE)


def _access_sig(acc):
    """Підпис старого формату (пароль + профілі). Лишається для читання вже збережених файлів."""
    body = json.dumps({"pass": acc.get("pass", {}), "profiles": acc.get("profiles", {})},
                      ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hmac.new(ACCESS_SECRET, body, hashlib.sha256).hexdigest()


def _profiles_sig(profiles):
    body = json.dumps({"v": 2, "profiles": profiles or {}},
                      ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hmac.new(ACCESS_SECRET, body, hashlib.sha256).hexdigest()


def _password_matches_root(password):
    given = hashlib.sha256(str(password or "").encode("utf-8")).digest()
    root = hashlib.sha256(ROOT_PASSWORD.encode("utf-8")).digest()
    return hmac.compare_digest(given, root)


POLICY_LOG_PATH = os.path.join(DATA, "policy_sync.log")
_POLICY_LOG_LAST = {}


def _policy_log(topic, msg):
    """Журнал синхронізації прав (%APPDATA%\\YavirTools\\policy_sync.log). Пише лише коли статус змінився."""
    try:
        if _POLICY_LOG_LAST.get(topic) == msg:
            return
        _POLICY_LOG_LAST[topic] = msg
        try:
            if os.path.getsize(POLICY_LOG_PATH) > 100_000:
                os.remove(POLICY_LOG_PATH)
        except OSError:
            pass
        with open(POLICY_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S") + "  [" + topic + "] " + msg + "\n")
    except Exception:
        pass


def _shipped_policy_paths():
    dirs = []
    if getattr(sys, "frozen", False):
        dirs.append(os.path.dirname(sys.executable))
    dirs.append(os.path.dirname(os.path.abspath(__file__)))
    meipass = getattr(sys, "_MEIPASS", "")
    if meipass:
        dirs.append(meipass)
    return [os.path.join(d, "access_policy.json") for d in dirs]


def _load_shipped_profiles():
    """access_policy.json поруч із програмою: права власника, підписані його ж ключем. Діє на кожному ПК."""
    found = False
    for path in _shipped_policy_paths():
        try:
            if not os.path.isfile(path):
                continue
            found = True
            with open(path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            profiles = data.get("profiles")
            if isinstance(profiles, dict) and hmac.compare_digest(str(data.get("sig", "")), _profiles_sig(profiles)):
                _policy_log("file", "OK, права з файлу " + path + " (профілів: " + str(len(profiles)) + ")")
                return profiles
            _policy_log("file", "файл " + path + " знайдено, але підпис не збігається "
                        "(інший ACCESS_SECRET у коді або файл змінено вручну) — ігнорую")
        except Exception as exc:
            _policy_log("file", "помилка читання " + path + ": " + repr(exc))
    if not found:
        _policy_log("file", "access_policy.json не знайдено в: " + " | ".join(_shipped_policy_paths()))
    return None


def fetch_policy_remote(url):
    """Завантажує підписані права. Повертає profiles або None, якщо файл недоступний/підроблений."""
    sep = "&" if "?" in url else "?"
    req = urllib.request.Request(url + sep + "t=" + str(int(time.time())),
                                 headers={"User-Agent": "YavirTools", "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read().decode("utf-8-sig"))
    profiles = data.get("profiles")
    if isinstance(profiles, dict) and hmac.compare_digest(str(data.get("sig", "")), _profiles_sig(profiles)):
        return profiles
    return None


def publish_policy_remote(token, gist_id, profiles):
    """Кладе підписані права у GitHub Gist (створює його, якщо id ще немає). Повертає (gist_id, raw_url)."""
    payload = {"v": 2, "profiles": profiles, "sig": _profiles_sig(profiles)}
    files = {"access_policy.json": {"content": json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)}}
    headers = {"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
               "Content-Type": "application/json", "User-Agent": "YavirTools"}
    if gist_id:
        req = urllib.request.Request("https://api.github.com/gists/" + gist_id,
                                     data=json.dumps({"files": files}).encode("utf-8"), method="PATCH", headers=headers)
    else:
        req = urllib.request.Request("https://api.github.com/gists", method="POST", headers=headers,
                                     data=json.dumps({"description": "Yavir Tools access", "public": False,
                                                      "files": files}).encode("utf-8"))
    with urllib.request.urlopen(req, timeout=15) as r:
        res = json.loads(r.read().decode("utf-8"))
    raw = res["files"]["access_policy.json"]["raw_url"]
    raw = re.sub(r"/raw/[0-9a-f]{40}/", "/raw/", raw)  # без ревізії: завжди остання версія
    return res["id"], raw


class PolicySync(QObject):
    """Фоново підтягує права: при запуску і далі раз на хвилину. Офлайн — лишаються останні збережені."""
    fetched = Signal(dict)

    def __init__(self, url, interval=60):
        super().__init__()
        self.url, self.interval = url, interval

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        _policy_log("net", "синхронізація запущена: " + self.url)
        while True:
            try:
                profiles = fetch_policy_remote(self.url)
                if profiles is not None:
                    _policy_log("net", "OK, отримано права з мережі (профілів: " + str(len(profiles)) + ")")
                    self.fetched.emit(profiles)
                else:
                    _policy_log("net", "файл завантажено, але підпис не збігається або формат не той — ігнорую")
            except Exception as exc:
                _policy_log("net", "не вдалося завантажити: " + repr(exc))
            time.sleep(self.interval)


class Signal_(QObject):
    """Мінімальний wrapper: дозволяє emit рядка зі стороннього потоку в GUI."""
    value = Signal(str)


class AccessPolicy:
    """Хто що може. Шари застосовуються по черзі: all -> level:<рівень> -> nick:<нік>.

    all — заборони для абсолютно всіх (список id).
    level:<рівень> та nick:<нік> — {"deny": [...], "allow": [...]}:
        deny  — додатково заборонити цьому рівню / цій людині;
        allow — явно дозволити, навіть якщо попередній шар забороняє;
        решта пунктів лишаються як у попередньому шарі.
    Зміна одного шару не чіпає інші.
    """

    def __init__(self, cfg):
        self.cfg = cfg
        self.tampered = False
        self.needs_save = False
        self._rev = 0
        self._cache_key = None
        self._cache_val = set()
        self.reload()

    def reload(self):
        self._rev += 1
        self.needs_save = False
        acc = self.cfg.get("access")
        if not isinstance(acc, dict):
            acc = {}
            self.cfg["access"] = acc
        profiles = acc.get("profiles")
        if not isinstance(profiles, dict):
            profiles = {}
            acc["profiles"] = profiles
        root = _root_pass()
        shipped = _load_shipped_profiles()
        if shipped is not None and (profiles != shipped or acc.get("sig") != _profiles_sig(shipped)):
            profiles.clear()
            profiles.update(json.loads(json.dumps(shipped)))
            acc["sig"] = _profiles_sig(profiles)
            self.needs_save = True
        old_pass = acc.get("pass") if isinstance(acc.get("pass"), dict) else {}
        sig = acc.get("sig")
        fresh = not profiles and not old_pass and not sig
        valid_v2 = sig == _profiles_sig(profiles)
        valid_v1 = sig == _access_sig({"pass": old_pass, "profiles": profiles})
        self.tampered = not (fresh or valid_v2 or valid_v1)
        if valid_v1 and not valid_v2:
            for key in list(profiles):
                if key.startswith("nick:") and not profiles.get(key):
                    profiles.pop(key, None)
            acc["sig"] = _profiles_sig(profiles)
            self.needs_save = True
        if fresh:
            acc["sig"] = _profiles_sig(profiles)
            self.needs_save = True
        if acc.get("pass") != root or acc.get("v") != 2:
            acc["pass"] = dict(root)
            acc["v"] = 2
            self.needs_save = True
        if not self.tampered and acc.get("sig") != _profiles_sig(profiles):
            acc["sig"] = _profiles_sig(profiles)
            self.needs_save = True

    @property
    def data(self):
        acc = self.cfg.get("access")
        if not isinstance(acc, dict):
            acc = self.cfg["access"] = {"profiles": {}, "pass": _root_pass(), "v": 2}
        return acc

    def has_password(self):
        return True

    def check_password(self, password):
        return _password_matches_root(password)

    def set_password(self, password=None):
        # Пароль власника один на всіх і зашитий у програму — змінити його локально не можна.
        self.data["pass"] = _root_pass()
        self.commit()

    def commit(self):
        self._rev += 1
        acc = self.data
        profiles = acc.get("profiles") if isinstance(acc.get("profiles"), dict) else {}
        acc["profiles"] = profiles
        acc["pass"] = _root_pass()
        acc["v"] = 2
        acc["sig"] = _profiles_sig(profiles)
        self.tampered = False

    def profile_keys(self):
        return list(self.data.get("profiles", {}).keys())

    def layer(self, profile):
        """(deny, allow) одного шару."""
        known = {f[0] for f in ACCESS_FEATURES}
        raw = self.data.get("profiles", {}).get(profile)
        if isinstance(raw, dict):
            d, a = raw.get("deny", []), raw.get("allow", [])
            deny = {str(i) for i in d if str(i) in known} if isinstance(d, (list, tuple, set)) else set()
            allow = {str(i) for i in a if str(i) in known} if isinstance(a, (list, tuple, set)) else set()
            return deny, allow - deny
        if isinstance(raw, (list, tuple, set)):
            deny = {str(i) for i in raw if str(i) in known}
            # Старий нік-профіль повністю замінював решту: усе, що не заборонено, було дозволено.
            allow = (known - deny) if str(profile).startswith("nick:") else set()
            return deny, allow
        return set(), set()

    def denied_set(self, profile):
        return self.layer(profile)[0]

    def set_layer(self, profile, deny, allow=()):
        known = {f[0] for f in ACCESS_FEATURES}
        deny = {str(i) for i in deny if str(i) in known}
        allow = {str(i) for i in allow if str(i) in known} - deny
        profiles = self.data.setdefault("profiles", {})
        if profile == "all":
            profiles["all"] = sorted(deny)
        elif str(profile).startswith("level:") and not deny and not allow:
            profiles.pop(profile, None)
        else:
            profiles[profile] = {"deny": sorted(deny), "allow": sorted(allow)}
        self.commit()

    def set_denied(self, profile, denied):
        self.set_layer(profile, denied, ())

    def delete_profile(self, profile):
        self.data.get("profiles", {}).pop(profile, None)
        self.commit()

    def clear_level_overrides(self):
        profiles = self.data.setdefault("profiles", {})
        for key in list(profiles):
            if key.startswith("level:"):
                profiles.pop(key, None)
        self.commit()

    @staticmethod
    def _nick_norm(name):
        # «Name_Surname», «name surname» і «NAME_SURNAME » — той самий нік
        return re.sub(r"[\s_]+", " ", str(name or "")).strip().casefold()

    def nick_profile_key(self, name):
        want = self._nick_norm(name)
        if not want:
            return None
        for key in self.data.get("profiles", {}):
            if str(key).startswith("nick:") and self._nick_norm(str(key).split(":", 1)[1]) == want:
                return key
        return None

    def compute(self, level, nick):
        """Підсумок заборон для пари (рівень, нік): all -> рівень -> нік."""
        out = set(self.layer("all")[0])
        d, a = self.layer("level:" + str(level))
        out = (out | d) - a
        nick_key = self.nick_profile_key(nick)
        if nick_key is not None:
            d, a = self.layer(nick_key)
            out = (out | d) - a
        return out

    def effective_denied(self):
        key = (self._rev, self.tampered, self.cfg.get("admin_level", ""), self.cfg.get("admin_name", ""))
        if key != self._cache_key:
            if self.tampered:
                self._cache_val = {f[0] for f in ACCESS_FEATURES if f[3]}
            else:
                self._cache_val = self.compute(key[2], key[3])
            self._cache_key = key
        return self._cache_val

    def layer_label(self):
        if self.tampered:
            return "аварійні обмеження"
        if self.nick_profile_key(self.cfg.get("admin_name", "")):
            return "загальні → рівень → нік-профіль"
        d, a = self.layer("level:" + str(self.cfg.get("admin_level", "")))
        if d or a:
            return "загальні → додатково рівень"
        return "загальні для всіх"

    def can(self, feature):
        return feature not in self.effective_denied()


POLICY = None


def can(feature):
    """Глобальна перевірка: чи дозволена функція поточному адміну."""
    return True if POLICY is None else POLICY.can(feature)


def ask_owner_password(parent, text="Введіть пароль власника."):
    if POLICY is None or not POLICY.has_password():
        return True
    pw, ok = QInputDialog.getText(parent, "Пароль власника", text, QLineEdit.Password)
    if not ok:
        return False
    if POLICY.check_password(pw):
        return True
    QMessageBox.warning(parent, "Невірний пароль", "Пароль власника невірний.")
    return False


class Safe(dict):
    def __missing__(self, k):
        return "{" + k + "}"


def fmt(sec):
    sec = max(0, int(sec))
    h, r = divmod(sec, 3600)
    m, s = divmod(r, 60)
    return f"{h:02}:{m:02}:{s:02}"


COLOR_RX = re.compile(r"#[0-9A-Fa-f]{6}")
ANSI_RX = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
TS_RX = re.compile(r"^\[\d{2}:\d{2}:\d{2}\]\s*")
PM_REPLY_RX = re.compile(
    r"\[PM\]\s*\[[^\]]+\]\s*(?P<admin>.+?)\[\d+\]\s*->\s*"
    r"(?P<name>.+?)\[(?P<id>\d+)\]:\s*(?P<reply>.+)", re.I)
PLAYER_MENTION_RX = re.compile(
    r"(?<![\w])(?P<name>[A-Za-zА-Яа-яІіЇїЄєҐґ][A-Za-zА-Яа-яІіЇїЄєҐґ0-9_. '\-]{0,39}?)\s*\[(?P<id>\d{5,10})\]"
)
# Some echoed admin commands are followed by a player's [ID] in console.log;
# do not let their command token become part of the stored nickname.
PLAYER_COMMAND_PREFIX_RX = re.compile(
    r"^\s*/?(?:" + FORM_COMMAND_PATTERN + r"|sp|pwarp|get|pm)\b\s+", re.I)
PLAYER_GENERIC_PREFIX_RX = re.compile(r"^\s*(?:гравець|игрок)\s+", re.I)
KILL_CHAT_RX = re.compile(r"\[[^\]]+\]\s*Вбив\s+", re.I)
LATIN_NAME_RX = re.compile(r"^[A-Za-z0-9_. '\-]+$")


def clean_player_name(value):
    name = re.sub(r"\s+", " ", str(value or "")).strip(" .:-")
    previous = None
    while name != previous:
        previous = name
        name = PLAYER_GENERIC_PREFIX_RX.sub("", name)
        name = PLAYER_COMMAND_PREFIX_RX.sub("", name)
    return name.strip(" .:-")


def is_cyrillic_player_name(value):
    """База користувачів зберігає лише кириличні імена гравців."""
    name = clean_player_name(value)
    return bool(name and re.search(r"[А-Яа-яІіЇїЄєҐґ]", name) and not LATIN_NAME_RX.fullmatch(name))


def clean(line):
    line = COLOR_RX.sub("", line)
    line = TS_RX.sub("", line.strip())
    return line.strip()


def notification_text(value, limit=200):
    value = ANSI_RX.sub("", clean(str(value or "")))
    value = "".join(ch for ch in value if ch.isprintable() or ch.isspace())
    value = re.sub(r"\s+", " ", value).strip()
    if limit is None:
        return value
    return value[:limit] + ("…" if len(value) > limit else "")


def split_words(s):
    return [w.strip().lower() for w in re.split(r"[,\n]", s or "") if w.strip()]


# ---------------------------------------------------------------- Windows / input
if IS_WIN:
    ULONG_PTR = ctypes.c_size_t

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                    ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]

    class _IU(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]

    class INPUT(ctypes.Structure):
        _anonymous_ = ("i",)
        _fields_ = [("type", wintypes.DWORD), ("i", _IU)]

    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    SC_T, SC_ENTER = 0x14, 0x1C  # скан-коди: працюють незалежно від розкладки


def _ki(scan, flags):
    i = INPUT()
    i.type = 1
    i.ki = KEYBDINPUT(0, scan, flags, 0, 0)
    return i


def _send(lst):
    if not lst:
        return
    arr = (INPUT * len(lst))(*lst)
    user32.SendInput(len(lst), arr, ctypes.sizeof(INPUT))


def game_pids(name):
    out = set()
    for p in psutil.process_iter(["name", "pid"]):
        try:
            if (p.info["name"] or "").lower() == name.lower():
                out.add(p.info["pid"])
        except Exception:
            pass
    return out


def game_hwnd(name):
    if not IS_WIN:
        return 0
    pids = game_pids(name)
    found = []

    def cb(h, l):
        if user32.IsWindowVisible(h) and user32.GetWindowTextLengthW(h) > 0:
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
            if pid.value in pids:
                found.append(h)
        return True
    if pids:
        user32.EnumWindows(WNDENUMPROC(cb), 0)
    return found[0] if found else 0


def game_foreground(name):
    if not IS_WIN:
        return False
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), ctypes.byref(pid))
    return pid.value in game_pids(name)


SEND_LOCK = threading.Lock()
SC_F8 = 0x42


def say(cfg, text, send=True, erase_open_key=False, open_chat=True):
    """Відкриває чат (T), вводить текст, за потреби тисне Enter."""
    if not IS_WIN:
        print("SAY:", text)
        return
    with SEND_LOCK:
        h = game_hwnd(cfg["game_process"])
        if h and user32.GetForegroundWindow() != h:
            if user32.IsIconic(h):
                user32.ShowWindow(h, 9)
            user32.keybd_event(0x12, 0, 0, 0)
            user32.keybd_event(0x12, 0, 2, 0)
            user32.SetForegroundWindow(h)
            time.sleep(0.05)
        for vk in (0x12, 0x11, 0x10, 0x5B):
            if user32.GetAsyncKeyState(vk) & 0x8000:
                user32.keybd_event(vk, 0, 2, 0)
        if open_chat:
            _send([_ki(SC_T, 8), _ki(SC_T, 8 | 2)])
        open_delay = max(80 if erase_open_key else 0, cfg["chat_open_delay"]) if open_chat else 0
        time.sleep(max(0, open_delay) / 1000.0)
        if erase_open_key:
            sc_backspace = 0x0E
            _send([_ki(sc_backspace, 8), _ki(sc_backspace, 8 | 2)])
            time.sleep(0.02)
        seq = []
        for ch in text:
            if ord(ch) > 0xFFFF or ch in "\r\n":
                continue
            seq += [_ki(ord(ch), 4), _ki(ord(ch), 4 | 2)]
        _send(seq)
        if send:
            time.sleep(0.005)
            _send([_ki(SC_ENTER, 8), _ki(SC_ENTER, 8 | 2)])


def say_f8(cfg, text):
    """Focus game, run a command through F8, then close the console with F8."""
    text = text.strip()
    if text.startswith("/"):
        text = text[1:]
    if not IS_WIN:
        print("F8:", text)
        return
    with SEND_LOCK:
        h = game_hwnd(cfg["game_process"])
        if h and user32.GetForegroundWindow() != h:
            if user32.IsIconic(h):
                user32.ShowWindow(h, 9)
            user32.keybd_event(0x12, 0, 0, 0)
            user32.keybd_event(0x12, 0, 2, 0)
            user32.SetForegroundWindow(h)
            time.sleep(0.08)
        for vk in (0x12, 0x11, 0x10, 0x5B):
            if user32.GetAsyncKeyState(vk) & 0x8000:
                user32.keybd_event(vk, 0, 2, 0)
        _send([_ki(SC_F8, 8), _ki(SC_F8, 8 | 2)])
        time.sleep(0.18)
        seq = []
        for ch in text:
            if ord(ch) > 0xFFFF or ch in "\r\n":
                continue
            seq += [_ki(ord(ch), 4), _ki(ord(ch), 4 | 2)]
        _send(seq)
        time.sleep(0.02)
        _send([_ki(SC_ENTER, 8), _ki(SC_ENTER, 8 | 2)])
        # F8 submits commands from the console; Enter executes the command,
        # then toggle F8 once more to return to gameplay/chat.
        time.sleep(0.08)
        _send([_ki(SC_F8, 8), _ki(SC_F8, 8 | 2)])


PATTERNS = {
    "take": [(740, 100), (1040, 120), (1480, 180)],
    "reject": [(620, 140), (420, 160), (260, 300)],
    "accept": [(980, 90), (1280, 90), (1680, 220)],
    "vip": [(1160, 110), (820, 130), (1160, 110), (1540, 200)],
    "ac": [(1180, 170), (720, 170), (1180, 170), (620, 240)],
    "report": [(880, 120), (1320, 140), (1760, 240)],
    "warn": [(520, 120), (760, 180)],
}


def _scaled_wave(path, volume):
    try:
        with wave.open(path, "rb") as src:
            params = src.getparams()
            if params.comptype != "NONE" or params.sampwidth not in (1, 2, 3, 4):
                return None
            raw = src.readframes(params.nframes)
        width = params.sampwidth
        if width == 1:
            scaled = bytes(max(0, min(255, round(128 + (v - 128) * volume))) for v in raw)
        else:
            top = (1 << (8 * width - 1)) - 1
            bottom = -(1 << (8 * width - 1))
            samples = []
            for i in range(0, len(raw), width):
                value = int.from_bytes(raw[i:i + width], "little", signed=True)
                value = max(bottom, min(top, round(value * volume)))
                samples.append(value.to_bytes(width, "little", signed=True))
            scaled = b"".join(samples)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as dst:
            dst.setparams(params)
            dst.writeframes(scaled)
        return buf.getvalue()
    except (OSError, wave.Error, EOFError):
        return None


def _tone_wave(notes, volume):
    rate = 44100
    raw = bytearray()
    for freq, duration_ms in notes:
        count = int(rate * duration_ms / 1000)
        fade = max(1, int(rate * 0.012))
        for i in range(count):
            env = max(0.0, min(1.0, i / fade, (count - 1 - i) / fade))
            t = i / rate
            sample = (math.sin(2 * math.pi * freq * t) + 0.18 * math.sin(4 * math.pi * freq * t)) / 1.18
            raw.extend(struct.pack("<h", int(32767 * 0.88 * volume * env * sample)))
        raw.extend(b"\0\0" * int(rate * 0.055))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as dst:
        dst.setnchannels(1)
        dst.setsampwidth(2)
        dst.setframerate(rate)
        dst.writeframes(bytes(raw))
    return buf.getvalue()


def _premium_ui_wave(volume):
    """Original, soft ascending glass chime used for a successful tool save."""
    rate = 44100
    duration = 0.62
    notes = ((698.46, 0.00, 0.34), (880.00, 0.075, 0.27),
             (1046.50, 0.15, 0.21), (1396.91, 0.24, 0.12))
    raw = bytearray()
    for i in range(int(rate * duration)):
        t = i / rate
        sample = 0.0
        for freq, start, level in notes:
            age = t - start
            if age < 0:
                continue
            env = (1.0 - math.exp(-age * 190.0)) * math.exp(-age * 7.2)
            shimmer = (math.sin(2 * math.pi * freq * age)
                       + 0.17 * math.sin(2 * math.pi * freq * 2.01 * age + 0.16)
                       + 0.055 * math.sin(2 * math.pi * freq * 3.98 * age + 0.42))
            sample += level * env * shimmer
        sample = max(-0.94, min(0.94, sample * volume * 0.55))
        raw.extend(struct.pack("<h", int(32767 * sample)))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as dst:
        dst.setnchannels(1)
        dst.setsampwidth(2)
        dst.setframerate(rate)
        dst.writeframes(bytes(raw))
    return buf.getvalue()


def play(cfg, kind):
    if not IS_WIN:
        return
    volume = max(0, min(100, int(cfg.get("sound_volume", 80)))) / 100.0
    if volume <= 0:
        return
    path = cfg.get("snd_" + kind, "")

    def run():
        try:
            if path and os.path.isfile(path):
                data = _scaled_wave(path, volume)
                if data is not None:
                    winsound.PlaySound(data, winsound.SND_MEMORY)
                else:
                    winsound.PlaySound(path, winsound.SND_FILENAME)
            elif kind == "ui":
                winsound.PlaySound(_premium_ui_wave(volume), winsound.SND_MEMORY)
            else:
                data = _tone_wave(PATTERNS.get(kind, [(800, 120), (1200, 180)]), volume)
                winsound.PlaySound(data, winsound.SND_MEMORY)
        except RuntimeError:
            if path and os.path.isfile(path):
                winsound.PlaySound(path, winsound.SND_FILENAME)
    threading.Thread(target=run, daemon=True).start()



def check_for_update(current_version, url):
    """Повертає рядок із новою версією або None. Викликається у фоновому потоці."""
    if not url:
        return None
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "YavirTools/" + current_version,
                          "Cache-Control": "no-cache"})
        with urllib.request.urlopen(req, timeout=8) as r:
            latest = r.read(64).decode("utf-8").strip()
        if not latest:
            return None
        def _ver(v):
            try:
                return tuple(int(x) for x in v.lstrip("v").split("."))
            except ValueError:
                return (0,)
        return latest if _ver(latest) > _ver(current_version) else None
    except Exception:
        return None


def gemini(cfg, prompt, system=""):
    key = cfg["gemini_key"].strip()
    if not key:
        raise RuntimeError("Не вказано Gemini API ключ (Налаштування → ШІ Gemini).")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{cfg['gemini_model']}:generateContent"
    body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    req = urllib.request.Request(url, json.dumps(body).encode("utf-8"),
                                 {"Content-Type": "application/json", "x-goog-api-key": key})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Gemini HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:300]}")
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


def gemini_chat(cfg, history, system=""):
    """Діалог із Gemini: history = [{"role": "user"|"model", "text": ...}, ...]. Ключ і модель — з налаштувань."""
    key = cfg["gemini_key"].strip()
    if not key:
        raise RuntimeError("Не вказано Gemini API ключ (Налаштування → ШІ Gemini).")
    model = (cfg.get("gemini_model") or "gemini-2.5-flash").strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {"contents": [{"role": m["role"], "parts": [{"text": m["text"]}]} for m in history]}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    req = urllib.request.Request(url, json.dumps(body).encode("utf-8"),
                                 {"Content-Type": "application/json", "x-goog-api-key": key})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        hints = {400: "Перевірте API ключ і назву моделі в налаштуваннях.",
                 403: "Ключ не має доступу до цієї моделі.",
                 429: "Перевищено ліміт запитів Gemini — зачекайте хвилину."}
        raise RuntimeError(f"Gemini HTTP {e.code}. {hints.get(e.code, e.read().decode('utf-8', 'replace')[:240])}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Немає зв'язку з Gemini: {e.reason}")
    cands = data.get("candidates") or []
    if not cands:
        reason = (data.get("promptFeedback") or {}).get("blockReason")
        raise RuntimeError("ШІ не повернув відповідь" + (f" (причина: {reason})." if reason else "."))
    parts = (cands[0].get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts).strip()
    if not text:
        raise RuntimeError("ШІ повернув порожню відповідь (можливо, спрацював фільтр безпеки).")
    return text


class Worker(QThread):
    done = Signal(str, bool)

    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def run(self):
        try:
            self.done.emit(self.fn(), True)
        except Exception as e:
            self.done.emit(str(e), False)


# ---------------------------------------------------------------- Локальна база гравців
class PlayerStore:
    """Профілі гравців і історія репортів у локальній SQLite-базі."""

    def __init__(self, path=PLAYERS_DB_PATH):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.lock = threading.RLock()
        self.conn = sqlite3.connect(path, timeout=5, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS players (
                id TEXT PRIMARY KEY, nickname TEXT NOT NULL,
                first_seen TEXT NOT NULL, last_seen TEXT NOT NULL,
                reports_total INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS player_reports (
                row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT NOT NULL, message TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_player_reports_player_date
                ON player_reports(player_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_player_reports_date_player
                ON player_reports(created_at, player_id);
            CREATE INDEX IF NOT EXISTS idx_players_nickname ON players(nickname COLLATE NOCASE);
        """)
        # Remove English-only names collected by older parser versions.
        stale_english = self.conn.execute("SELECT id,nickname FROM players").fetchall()
        for row in stale_english:
            if not is_cyrillic_player_name(row["nickname"]):
                self.conn.execute("DELETE FROM players WHERE id=?", (row["id"],))
        # Older parser versions could store echoed commands (e.g. `pwarp Nick`)
        # as part of a nickname. Normalize those existing profiles in place.
        stale_names = self.conn.execute("SELECT id,nickname FROM players").fetchall()
        for row in stale_names:
            cleaned_name = clean_player_name(row["nickname"])
            if cleaned_name != row["nickname"] and is_cyrillic_player_name(cleaned_name):
                self.conn.execute("UPDATE players SET nickname=? WHERE id=?", (cleaned_name, row["id"]))
            elif cleaned_name != row["nickname"]:
                self.conn.execute("DELETE FROM players WHERE id=?", (row["id"],))
        self.conn.commit()
        # Cache known IDs/nicknames: the chat parser sees the same users on many
        # log lines, so avoid a SELECT and COMMIT for every single mention.
        now_mono = time.monotonic()
        self._known_players = {str(row["id"]): row["nickname"]
                              for row in self.conn.execute("SELECT id,nickname FROM players")}
        self._last_seen_write = {player_id: now_mono for player_id in self._known_players}
        self._last_commit = now_mono

    def observe(self, nickname, player_id, seen_at=None):
        nickname, player_id = clean_player_name(nickname), str(player_id).strip()
        if not is_cyrillic_player_name(nickname) or not player_id:
            return False
        seen_at = seen_at or datetime.datetime.now().isoformat(timespec="seconds")
        now_mono = time.monotonic()
        with self.lock:
            cached_name = self._known_players.get(player_id)
            is_new = cached_name is None
            renamed = not is_new and cached_name != nickname
            last_write = self._last_seen_write.get(player_id, 0)
            if is_new:
                self.conn.execute("INSERT INTO players(id,nickname,first_seen,last_seen) VALUES(?,?,?,?)",
                                  (player_id, nickname, seen_at, seen_at))
                self._known_players[player_id] = nickname
                self._last_seen_write[player_id] = now_mono
            elif renamed or now_mono - last_write >= 30:
                self.conn.execute("UPDATE players SET nickname=?,last_seen=? WHERE id=?",
                                  (nickname, seen_at, player_id))
                self._known_players[player_id] = nickname
                self._last_seen_write[player_id] = now_mono
        return is_new or renamed

    def commit_if_due(self, force=False):
        now = time.monotonic()
        if not force and now - self._last_commit < 2.0:
            return
        with self.lock:
            if not force and now - self._last_commit < 2.0:
                return
            self.conn.commit()
            self._last_commit = now

    def record_report(self, nickname, player_id, message, created_at=None):
        nickname, player_id = clean_player_name(nickname), str(player_id).strip()
        if not is_cyrillic_player_name(nickname) or not player_id:
            return False
        stamp = created_at or datetime.datetime.now().isoformat(timespec="seconds")
        with self.lock:
            is_new = player_id not in self._known_players
            self.conn.execute("""INSERT INTO players(id,nickname,first_seen,last_seen,reports_total)
                VALUES(?,?,?,?,1) ON CONFLICT(id) DO UPDATE SET nickname=excluded.nickname,
                last_seen=excluded.last_seen,reports_total=players.reports_total+1""",
                (player_id, nickname, stamp, stamp))
            self.conn.execute("INSERT INTO player_reports(player_id,message,created_at) VALUES(?,?,?)",
                              (player_id, str(message), stamp))
            self.conn.commit()
            self._known_players[player_id] = nickname
            self._last_seen_write[player_id] = time.monotonic()
            self._last_commit = time.monotonic()
        return is_new

    def reports_today(self, player_id):
        day = datetime.date.today().isoformat()
        tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
        with self.lock:
            row = self.conn.execute("SELECT COUNT(*) FROM player_reports WHERE player_id=? AND created_at>=? AND created_at<?",
                                    (str(player_id), day, tomorrow)).fetchone()
        return int(row[0]) if row else 0

    def list_users(self, query="", limit=3000):
        query = (query or "").strip()
        pattern = f"%{query}%"
        day = datetime.date.today().isoformat()
        tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
        with self.lock:
            rows = self.conn.execute("""SELECT p.id,p.nickname,p.first_seen,p.last_seen,p.reports_total,
                COALESCE(today.amount,0) AS reports_today
                FROM players p LEFT JOIN (
                    SELECT player_id,COUNT(*) AS amount FROM player_reports
                    WHERE created_at>=? AND created_at<? GROUP BY player_id
                ) AS today ON today.player_id=p.id
                WHERE (?='' OR p.nickname LIKE ? COLLATE NOCASE OR p.id LIKE ?)
                ORDER BY p.last_seen DESC LIMIT ?""",
                (day, tomorrow, query, pattern, pattern, int(limit))).fetchall()
        return [dict(row) for row in rows]

    def get_user(self, player_id):
        with self.lock:
            row = self.conn.execute("SELECT * FROM players WHERE id=?", (str(player_id),)).fetchone()
        return dict(row) if row else None

    def delete_user(self, player_id):
        player_id = str(player_id or "").strip()
        if not player_id:
            return False
        with self.lock:
            self.conn.execute("DELETE FROM player_reports WHERE player_id=?", (player_id,))
            cursor = self.conn.execute("DELETE FROM players WHERE id=?", (player_id,))
            self.conn.commit()
            self._known_players.pop(player_id, None)
            self._last_seen_write.pop(player_id, None)
            self._last_commit = time.monotonic()
        return cursor.rowcount > 0

    def history(self, player_id, limit=30):
        with self.lock:
            rows = self.conn.execute("SELECT message,created_at FROM player_reports WHERE player_id=? ORDER BY row_id DESC LIMIT ?",
                                     (str(player_id), int(limit))).fetchall()
        return [dict(row) for row in rows]

    def report_counts_by_day(self, player_id, days=7):
        today = datetime.date.today()
        dates = [today - datetime.timedelta(days=offset) for offset in reversed(range(max(1, int(days))))]
        start = dates[0].isoformat()
        with self.lock:
            rows = self.conn.execute(
                "SELECT substr(created_at,1,10) AS day, COUNT(*) AS amount FROM player_reports "
                "WHERE player_id=? AND substr(created_at,1,10)>=? GROUP BY substr(created_at,1,10)",
                (str(player_id), start)).fetchall()
        counts = {row["day"]: int(row["amount"]) for row in rows}
        return [(day, counts.get(day.isoformat(), 0)) for day in dates]

    def count(self):
        with self.lock:
            row = self.conn.execute("SELECT COUNT(*) FROM players").fetchone()
        return int(row[0]) if row else 0

    def close(self):
        with self.lock:
            self.conn.commit()
            self.conn.close()


# ---------------------------------------------------------------- Core
class Core(QObject):
    reports_changed = Signal()
    users_changed = Signal()
    new_report = Signal()
    vip_ad = Signal(dict)
    vip_msg = Signal(str)
    chat_line = Signal(str)
    chatlog_created = Signal(str)
    pending_form_changed = Signal(str)
    event = Signal(str, str)      # kind: ac|bad|vipviol|repviol|form|info
    stats_changed = Signal()
    overlay_menu_toggle = Signal()

    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.players = PlayerStore()
        self.reports = []
        self.rid = 0
        self.selected = None
        self.stats = {"reports": 0, "forms": 0, "ads": 0, "ac": 0,
                      "replies": 0, "punishments": 0}
        self._rx = {}
        self._log_day = None
        self._log_f = None
        self._log_pending = 0
        self._log_buffer = []
        self._last_log_flush = time.monotonic()
        self._line_queue = collections.deque()
        self._defer_ui_signals = False
        self._pending_ui_signals = set()
        self._chat_ui_buffer = []
        self._line_drain_timer = QTimer(self)
        self._line_drain_timer.setSingleShot(True)
        self._line_drain_timer.timeout.connect(self._drain_log_lines)
        self._chat_flush_timer = QTimer(self)
        self._chat_flush_timer.setSingleShot(True)
        self._chat_flush_timer.setInterval(120)
        self._chat_flush_timer.timeout.connect(self._flush_chat_display)
        self._last_form = ("", 0)
        self.pending_form = ""
        self._form_accept_lock = threading.Lock()
        self._form_accepting = set()
        self._form_declining = set()
        self._reminded_reports = set()
        self._last_reminder_check = 0.0
        self._report_seen = collections.OrderedDict()
        self.refresh_word_filters()
        self.last_taken_report_id = None
        self._ignore_injected_f1_until = 0.0
        self.key_capture_active = False
        self.key_capture_cooldown = 0.0
        self.seconds_session = 0

    # --- helpers
    def rx(self, key):
        if key not in self._rx:
            try:
                self._rx[key] = re.compile(self.cfg[key], re.I)
            except re.error as e:
                self.event.emit("info", f"Помилка regex {key}: {e}")
                self._rx[key] = re.compile(r"(?!x)x")
        return self._rx[key]

    def bad_hits(self, text):
        t = text.lower()
        return [w for w in self._banned_words if w in t]

    def refresh_word_filters(self):
        self._banned_words = split_words(self.cfg.get("banned_words", ""))
        self._vip_ad_words = split_words(self.cfg.get("vip_ad_words", ""))
        self._vip_normalized_words = tuple(
            (re.sub(r"[^а-яіїєґ]", "", str(word).lower().translate(VIP_HOMOGLYPHS)),
             re.sub(r"[^a-z]", "", str(word).lower()))
            for word in self._vip_ad_words)
        transaction_terms = (
            "продам", "продаю", "продать", "продажа", "продается", "продається",
            "куплю", "купить", "купляю", "покупка", "покупаю", "обмен", "обмін",
            "торг", "віддам", "отдам", "міняю", "меняю", "реалізую", "реализую",
            "ціна", "ціною", "цена", "стоимость", "вартість", "buy", "sell", "trade",
        )
        self._vip_transaction_terms = tuple(
            re.sub(r"[^а-яіїєґ]", "", term.translate(VIP_HOMOGLYPHS))
            for term in transaction_terms)

    def is_ad(self, text):
        t = text.lower()
        return any(w in t for w in self._vip_ad_words) or \
            re.search(r"\d{1,3}(\.\d{1,3}){3}", t) is not None

    def by_rid(self, rid):
        return next((r for r in self.reports if r["rid"] == rid), None)

    def last_report(self):
        return next((r for r in self.reports if r["status"] == "Новий"), self.reports[0] if self.reports else None)

    def target(self):
        return self.by_rid(self.selected) or self.last_report()

    def _notify_ui(self, signal_name):
        if self._defer_ui_signals and QThread.currentThread() == self.thread():
            self._pending_ui_signals.add(signal_name)
        else:
            getattr(self, signal_name).emit()

    def _flush_chat_display(self):
        if self._chat_ui_buffer:
            text = "\n".join(self._chat_ui_buffer)
            self._chat_ui_buffer.clear()
            self.chat_line.emit(text)

    def render(self, text, r):
        values = {"id": r["id"] if r else "", "name": r["name"] if r else "",
                  "admin": self.cfg["admin_name"], "time": datetime.datetime.now().strftime("%H:%M:%S")}
        return re.sub(r"\{(id|name|admin|time)\}",
                      lambda m: str(values[m.group(1).lower()]), text, flags=re.I)

    def vip_monitor_active(self, now=None):
        now = now or datetime.datetime.now().time()
        def to_minutes(value, fallback):
            try:
                h, m = str(value).split(":", 1)
                return max(0, min(1439, int(h) * 60 + int(m)))
            except (TypeError, ValueError):
                return fallback
        start = to_minutes(self.cfg.get("vip_monitor_start", "11:00"), 11 * 60)
        end = to_minutes(self.cfg.get("vip_monitor_end", "22:00"), 22 * 60)
        current = now.hour * 60 + now.minute
        return start <= current < end if start <= end else current >= start or current < end

    def vip_candidate(self, text):
        # Пишемо можливу рекламу навіть коли гравець обходить словник крапками,
        # пробілами, цифрами або латинськими літерами, схожими на кириличні.
        raw_text = str(text or "").lower()
        text = raw_text.translate(VIP_HOMOGLYPHS)
        latin_compact = re.sub(r"[^a-z]", "", raw_text)
        compact = re.sub(r"[^а-яіїєґ]", "", text)
        if not compact and not latin_compact:
            return False

        # Підтримуємо також розділення букв: «пр.одам», «ку п лю» тощо.
        for normalized_word, latin_word in self._vip_normalized_words:
            if len(normalized_word) >= 4 and normalized_word in compact:
                return True
            if len(latin_word) >= 4 and latin_word in latin_compact:
                return True

        for normalized_term in self._vip_transaction_terms:
            if len(normalized_term) >= 4 and normalized_term in compact:
                return True
        if re.search(r"(?:prodam|prodaju|kuplyu|kupit|obmen|buy|sell|selling|trade)", latin_compact):
            return True

        # Ціна з валютою або оголошення про продаж предмета/транспорту.
        has_price = bool(re.search(r"(?:\d[\d .]{2,}\s*(?:грн|руб|дол|\$|€)|(?:грн|руб|дол|\$|€)\s*\d)", text))
        market_item = re.search(r"(?:авто|машин|транспорт|мото|фур|будинок|квартир|бізнес|бизнес|аккаунт|акаунт|предмет|товар)", compact)
        return has_price and bool(market_item)

    # --- швидка гілка (потік читання логу): розпізнавання форм
    def fast(self, line):
        c = self.cfg
        m = self.rx("form_regex").search(line)
        if m:
            gd = m.groupdict()
            form = (gd.get("form") or gd.get("form_rank") or m.group(0)).strip()
            now = time.monotonic()
            previous_form, previous_time = self._last_form
            if form != previous_form or now - previous_time > 600:
                self.pending_form = form
                self._last_form = (form, now)
                self.pending_form_changed.emit(form)
                self.event.emit("form", "Знайдена форма: " + form)
        if self.rx("form_reject_regex").search(line):
            self.pending_form = ""
            play(c, "reject")
            self.event.emit("form", "Форму відхилено: " + line)

    def _accept_form(self, form):
        if self.deny("hk_form_accept"):
            return
        c = self.cfg
        match = re.search(r":\s*(/?" + FORM_COMMAND_PATTERN + r"\b.+)$", form, re.I)
        if not match:
            self.event.emit("info", "Не вдалося витягнути команду з форми: " + form)
            return
        command = match.group(1).strip()
        if not command.startswith("/"):
            command = "/" + command
        # Захищаємо ручне прийняття від подвійного виклику гарячої клавіші.
        form_key = re.sub(r"\s+", " ", command).strip().casefold()
        with self._form_accept_lock:
            # A second hotkey/UI event may already have captured the same form.
            # Only the currently pending form can be submitted, once.
            if self.pending_form != form or form_key in self._form_accepting:
                return
            self._form_accepting.add(form_key)
        try:
            say(c, command, True)
            if re.match(r"/?" + FORM_COMMAND_PATTERN + r"\b", command, re.I):
                self.stats["punishments"] += 1
            admin_parts = re.sub(r"\s*\[\d+\]", "", c.get("admin_name", "")).split()
            admin_display = " ".join(admin_parts[:2]) or "Адміністратор"
            accepted_text = c.get("form_accepted_msg", DEFAULT["form_accepted_msg"]).format_map(
                Safe(form=form, id="", name="", admin=admin_display))
            threading.Thread(target=self._send_admin_form_notice, args=(accepted_text,), daemon=True).start()
            if self.pending_form == form:
                self.pending_form = ""
                self.pending_form_changed.emit("")
            play(c, "accept")
            self.stats["forms"] += 1
            self._notify_ui("stats_changed")
            self.event.emit("form", "Форму схвалив адміністратор: " + admin_display)
        finally:
            with self._form_accept_lock:
                self._form_accepting.discard(form_key)

    def check_report_reminders(self, now=None):
        if not self.cfg.get("report_reminder_enabled", False):
            return
        now = time.monotonic() if now is None else now
        if now - self._last_reminder_check < 5:
            return
        self._last_reminder_check = now
        delay = max(1, int(self.cfg.get("report_reminder_minutes", 5))) * 60
        active_ids = set()
        for report in self.reports:
            if report.get("status") != "Новий":
                continue
            rid = report.get("rid")
            active_ids.add(rid)
            if rid in self._reminded_reports or now - report.get("created_at", now) < delay:
                continue
            self._reminded_reports.add(rid)
            self.event.emit("report_reminder", f"{report['name']} [{report['id']}]: {report['text']}")
        self._reminded_reports.intersection_update(active_ids)

    def hk_form(self):
        if not game_foreground(self.cfg["game_process"]):
            return
        form = self.pending_form
        if form:
            self._accept_form(form)
        else:
            self.event.emit("info", "Ще не знайдено форму в логах чату")

    def accept_pending_form_from_ui(self):
        form = self.pending_form
        if form:
            threading.Thread(target=self._accept_form, args=(form,), daemon=True).start()

    def decline_pending_form_from_ui(self):
        form = self.pending_form
        if form:
            threading.Thread(target=self._decline_form, args=(form, True), daemon=True).start()

    def hk_reject_form(self):
        self._decline_form(self.pending_form, False)

    def _decline_form(self, form, from_ui=False):
        if self.deny("hk_form_reject"):
            return
        if time.monotonic() < self._ignore_injected_f1_until:
            return
        if keyboard and any(keyboard.is_pressed(k) for k in ("alt", "ctrl", "shift")):
            return
        form_key = re.sub(r"\s+", " ", form or "").strip().casefold()
        with self._form_accept_lock:
            if not form or self.pending_form != form:
                self.event.emit("info", "Немає форми для відхилення")
                return
            if form_key in self._form_declining:
                return
            self._form_declining.add(form_key)
        try:
            self._decline_form_once(form, from_ui)
        finally:
            with self._form_accept_lock:
                self._form_declining.discard(form_key)

    def _decline_form_once(self, form, from_ui=False):
        if time.monotonic() < self._ignore_injected_f1_until:
            return
        if keyboard and any(keyboard.is_pressed(k) for k in ("alt", "ctrl", "shift")):
            return
        if not form or self.pending_form != form:
            return
        if from_ui:
            hwnd = game_hwnd(self.cfg["game_process"])
            if not hwnd:
                self.event.emit("info", "Не знайдено вікно гри для відхилення форми")
                return
            if user32.IsIconic(hwnd):
                user32.ShowWindow(hwnd, 9)
            user32.keybd_event(0x12, 0, 0, 0)
            user32.keybd_event(0x12, 0, 2, 0)
            user32.SetForegroundWindow(hwnd)
            time.sleep(0.08)
        elif not game_foreground(self.cfg["game_process"]):
            return
        sc_f1 = 0x3B
        self._ignore_injected_f1_until = time.monotonic() + 0.35
        _send([_ki(sc_f1, 8), _ki(sc_f1, 8 | 2)])
        if self.pending_form == form:
            self.pending_form = ""
            self.pending_form_changed.emit("")
        play(self.cfg, "reject")
        declined_text = self.cfg.get("form_declined_msg", "[Yavir_Tools] Declined form")
        threading.Thread(target=self._send_admin_form_notice, args=(declined_text,), daemon=True).start()
        self.event.emit("form", "Форму відхилено через інтерфейс" if from_ui else "Натиснуто F1 для відхилення форми")

    def _send_admin_form_notice(self, message):
        time.sleep(0.2)
        # Повідомлення про форму має залишатися в адмін-чаті навіть якщо
        # поле команди випадково очищене в налаштуваннях.
        prefix = (self.cfg.get("admin_chat_cmd") or "/a").strip() or "/a"
        # У консолі F8 MTA команда вводиться без початкового слеша: `a текст`.
        prefix = prefix.lstrip("/").strip() or "a"
        say_f8(self.cfg, f"{prefix} {message}".strip())

    # --- основна обробка (GUI-потік)
    def on_line(self, line):
        c = self.cfg
        if c["log_chat"]:
            self._write_log(line)
        unanswered = bool(re.match(r"^\[БЕЗ ВІДПОВІДІ\]\s*", line, flags=re.I))
        report_line = re.sub(r"^\[БЕЗ ВІДПОВІДІ\]\s*", "", line, flags=re.I)
        m = self.rx("report_regex").search(report_line)
        if m:
            gd = m.groupdict()
            if self.players.observe(gd.get("name", ""), gd.get("id", "")):
                self._notify_ui("users_changed")
            self.add_report(gd, unanswered=unanswered)
            return
        # Збираємо ID та нікнейми, які з'являються в будь-яких рядках console.log.
        # Kill feed messages contain player mentions too, but are not chat/profile
        # records. Skip the whole line so neither killer nor victim enters the DB.
        if not KILL_CHAT_RX.search(line):
            for mention in PLAYER_MENTION_RX.finditer(line):
                gd = mention.groupdict()
                name = re.sub(r"\s+", " ", gd.get("name", "")).strip(" .:-")
                if name and self.players.observe(name, gd.get("id", "")):
                    self._notify_ui("users_changed")
        pm = PM_REPLY_RX.search(line)
        m = None if pm else self.rx("colleague_regex").search(line)
        if pm or m:
            gd = pm.groupdict() if pm else m.groupdict()
            admin_name = (gd.get("admin") or gd.get("admin_legacy") or "?").strip()
            report_id = gd.get("id") or gd.get("id_legacy")
            colleague_text = (gd.get("reply") or "").strip()
            for r in self.reports:
                if str(r["id"]) == str(report_id) and colleague_text:
                    r["colleague_reply"] = colleague_text
                    r["colleague_admin"] = admin_name
                    if r["status"] in ("Новий", "Взято", "Взяв я", "В адмін-чат"):
                        r["status"] = "Колега відповів"
                    r["unanswered"] = False
                    break
            self._notify_ui("reports_changed")
            if can("notif_colleague"):
                self.event.emit("colleague", f"{admin_name} відповів на репорт [{report_id}]: {colleague_text}")
            return
        m = self.rx("vip_regex").search(line)
        if m:
            gd = m.groupdict()
            self.vip_msg.emit(f"{gd['name']} [{gd['id']}]: {gd['text']}")
            vip_active = self.vip_monitor_active()
            if vip_active:
                hits = self.bad_hits(gd["text"])
                if hits:
                    self.event.emit("vipviol", f"{gd['name']} [{gd['id']}]: {gd['text']}  ({', '.join(hits)})")
                if self.is_ad(gd["text"]):
                    self.stats["ads"] += 1
                    self._notify_ui("stats_changed")
                    play(c, "vip")
                    self.vip_ad.emit(gd)
                    self.event.emit("vipad", f"{gd['name']} [{gd['id']}]: {gd['text']}")
                elif self.vip_candidate(gd["text"]):
                    self.event.emit("vip_possible", f"{gd['name']} [{gd['id']}]: {gd['text']}")
            return
        m = self.rx("ac_regex").search(line)
        if m:
            self.stats["ac"] += 1
            self._notify_ui("stats_changed")
            play(c, "ac")
            gd = m.groupdict()
            alert = gd.get("alert") or gd.get("text") or line
            self.event.emit("ac", notification_text(alert))
            return
        hits = self.bad_hits(line)
        if hits:
            self.event.emit("bad", f"{line}  ({', '.join(hits)})")

    def on_lines(self, lines):
        if not lines:
            return
        self._line_queue.extend(lines)
        if not self._line_drain_timer.isActive():
            self._line_drain_timer.start(0)

    def _drain_log_lines(self):
        # Keep each GUI-thread slice short so a bursty console.log cannot block paints/input.
        batch = []
        deadline = time.perf_counter() + 0.006
        while self._line_queue and len(batch) < 120:
            batch.append(self._line_queue.popleft())
            if len(batch) > 1 and time.perf_counter() >= deadline:
                break
        self._defer_ui_signals = True
        self._pending_ui_signals.clear()
        try:
            for line in batch:
                try:
                    self.on_line(line)
                except Exception:
                    traceback.print_exc()
        finally:
            self._defer_ui_signals = False
        # Refresh large views once per slice, not once for every matching chat line.
        for signal_name in ("users_changed", "reports_changed", "stats_changed"):
            if signal_name in self._pending_ui_signals:
                getattr(self, signal_name).emit()
        self._pending_ui_signals.clear()
        if self.cfg.get("log_chat", False):
            self._chat_ui_buffer.extend(batch)
            if not self._chat_flush_timer.isActive():
                self._chat_flush_timer.start()
        if self._line_queue:
            self._line_drain_timer.start(8)

    def add_report(self, gd, unanswered=False):
        key = (str(gd["id"]), gd["text"].strip().casefold())
        now = time.monotonic()
        previous = next((r for r in self.reports if (str(r["id"]), r["text"].strip().casefold()) == key), None)
        last_seen = self._report_seen.get(key)
        active_status = previous and previous["status"] in (
            "Новий", "Взято", "Взяв я", "В адмін-чат", "Колега відповів")
        if (last_seen is not None and now - last_seen < 5) or active_status:
            self._report_seen[key] = now
            self._report_seen.move_to_end(key)
            if previous and unanswered and not previous.get("unanswered"):
                previous["unanswered"] = True
                self._notify_ui("reports_changed")
            return
        self._report_seen[key] = now
        self._report_seen.move_to_end(key)
        while self._report_seen and now - next(iter(self._report_seen.values())) > 3600:
            self._report_seen.popitem(last=False)
        while len(self._report_seen) > 2000:
            self._report_seen.popitem(last=False)
        self.rid += 1
        hits = self.bad_hits(gd["text"])
        ad = self.is_ad(gd["text"])
        r = {"rid": self.rid, "name": gd["name"], "id": gd["id"], "text": gd["text"],
             "created_at": now, "time": datetime.datetime.now().strftime("%H:%M:%S"), "status": "Новий",
             "unanswered": bool(unanswered),
             "colleague_reply": "", "colleague_admin": "",
             "flags": hits + (["реклама/посилання"] if ad else [])}
        self.players.record_report(r["name"], r["id"], r["text"])
        self._notify_ui("users_changed")
        self.reports.insert(0, r)
        del self.reports[300:]
        self.stats["reports"] += 1
        self._notify_ui("stats_changed")
        self._notify_ui("reports_changed")
        self.new_report.emit()
        if self.cfg.get("report_sound", False):
            play(self.cfg, "report")
        if r["flags"]:
            self.event.emit("repviol", f"{r['name']} [{r['id']}]: {r['text']}  ({', '.join(r['flags'])})")
        elif unanswered:
            self.event.emit("unanswered", f"{r['name']} [{r['id']}]: {r['text']}")
        else:
            self.event.emit("report", f"{r['name']} [{r['id']}]: {r['text']}")

    def expire_reports(self):
        ttl = max(0, int(self.cfg.get("report_expire_minutes", 60))) * 60
        if ttl <= 0:
            return False
        now = time.monotonic()
        keep = [r for r in self.reports if now - r.get("created_at", now) < ttl]
        if len(keep) == len(self.reports):
            return False
        self.reports[:] = keep
        if self.selected and not self.by_rid(self.selected):
            self.selected = None
        self._notify_ui("reports_changed")
        return True

    def _write_log(self, line):
        day = datetime.date.today().isoformat()
        if day != self._log_day:
            if self._log_f:
                self.flush_log(force=True)
                self._log_f.close()
            path = os.path.join(CHATLOG_DIR, f"chat_{day}.txt")
            is_new = not os.path.exists(path)
            self._log_f = open(path, "a", encoding="utf-8")
            self._log_day = day
            if is_new:
                self.chatlog_created.emit(path)
        self._log_buffer.append(datetime.datetime.now().strftime("[%H:%M:%S] ") + line)
        self._log_pending += 1
        now = time.monotonic()
        if self._log_pending >= 64 or now - self._last_log_flush >= 1.0:
            self.flush_log(force=True)

    def prune_chatlogs(self, now=None):
        now = time.time() if now is None else now
        removed = []
        try:
            names = os.listdir(CHATLOG_DIR)
        except OSError:
            return removed
        for name in names:
            if not (name.startswith("chat_") and name.lower().endswith(".txt")):
                continue
            path = os.path.join(CHATLOG_DIR, name)
            try:
                created = os.path.getctime(path)
                if now - created < CHATLOG_RETENTION_SECONDS:
                    continue
                if self._log_f and os.path.abspath(self._log_f.name) == os.path.abspath(path):
                    self.flush_log(force=True)
                    self._log_f.close()
                    self._log_f = None
                    self._log_day = None
                os.remove(path)
                removed.append(path)
            except OSError:
                continue
        return removed

    def flush_log(self, force=False):
        if not self._log_f or not self._log_buffer:
            return
        if not force and time.monotonic() - self._last_log_flush < 1.0:
            return
        try:
            self._log_f.write("\n".join(self._log_buffer) + "\n")
            self._log_f.flush()
        except OSError:
            pass
        self._log_buffer.clear()
        self._log_pending = 0
        self._last_log_flush = time.monotonic()

    # --- дії
    def deny(self, feature):
        """True, якщо функцію заборонено власником (і показує повідомлення)."""
        if can(feature):
            return False
        self.event.emit("info", "Немає доступу: " + ACCESS_BY_ID[feature][1])
        return True

    def take(self, r):
        if not r or self.deny("rep_take"):
            return
        if r["status"] in ("Новий", "Взято", "Взяв я"):
            r["status"] = "Взяв я"
        r["unanswered"] = False
        self.last_taken_report_id = str(r["id"])
        self._notify_ui("reports_changed")
        play(self.cfg, "take")
        self.event.emit("take", f"Репорт {r['name']} [{r['id']}] взято в роботу")
        threading.Thread(target=say, args=(self.cfg, f"/pm {r['id']} ", False), daemon=True).start()

    def spectate_report(self, r):
        if r and not self.deny("rep_spectate"):
            self.event.emit("action", f"Спостереження за {r['name']} [{r['id']}]")
            threading.Thread(target=say_f8, args=(self.cfg, f"/sp {r['id']}"), daemon=True).start()

    def warp_report(self, r):
        if r and not self.deny("rep_warp"):
            self.event.emit("action", f"Телепортація до {r['name']} [{r['id']}]")
            threading.Thread(target=say_f8, args=(self.cfg, f"/pwarp {r['id']}"), daemon=True).start()

    def send_reply(self, text, r):
        text = text.strip()
        if not text or not r or self.deny("rep_send"):
            return
        cmd = text if text.startswith("/") else self.cfg["reply_cmd"].format_map(
            Safe(id=r["id"], name=r["name"], text=text))
        r["status"] = "Відповів"
        r["unanswered"] = False
        self.stats["replies"] += 1
        self._notify_ui("reports_changed")
        self._notify_ui("stats_changed")
        play(self.cfg, "reply")
        self.event.emit("reply", f"Відповідь на репорт {r['name']} [{r['id']}] відправляється")
        threading.Thread(target=say_f8, args=(self.cfg, cmd), daemon=True).start()

    def to_admin(self, r):
        if not r or self.deny("rep_admin"):
            return
        r["status"] = "В адмін-чат"
        self._notify_ui("reports_changed")
        txt = f"{self.cfg['admin_chat_cmd']} Репорт від гравця {r['name']} [{r['id']}]: {r['text']}"
        self.event.emit("action", f"Репорт {r['id']} надіслано в адмін-чат")
        threading.Thread(target=say, args=(self.cfg, txt, True), daemon=True).start()

    def send_raw(self, text, send=True):
        command = str(text or "").strip()
        if self.deny("punish_send"):
            return
        if send and re.match(r"/?" + FORM_COMMAND_PATTERN + r"\b", command, re.I):
            self.stats["punishments"] += 1
            self._notify_ui("stats_changed")
        threading.Thread(target=say, args=(self.cfg, text, send), daemon=True).start()

    # --- хоткеї
    def hk_pm(self):
        if not self.cfg["auto_id_pm"] or not game_foreground(self.cfg["game_process"]) or self.deny("hk_take"):
            return
        r = self.last_report()
        if r:
            self.take(r)

    def hk_id(self):
        if not game_foreground(self.cfg["game_process"]) or self.deny("hk_id"):
            return
        report_id = self.last_taken_report_id
        if not report_id:
            # After restarting the tool there may be no in-memory "taken" ID yet.
            # Let F4 still work with the selected report, or the newest one as fallback.
            report = self.by_rid(self.selected) or self.last_report()
            report_id = str(report["id"]) if report else ""
        if not report_id:
            self.event.emit("info", "Немає репорту, з якого можна вставити ID через F4")
            return
        open_chat = bool(self.cfg.get("id_open_chat", False))
        threading.Thread(target=say, args=(self.cfg, report_id, False, False, open_chat), daemon=True).start()

    def hk_bind(self, b):
        if not game_foreground(self.cfg["game_process"]) or self.deny("hk_binds"):
            return
        r = self.target()
        text = self.render(b["text"], r)
        say(self.cfg, text, b.get("send", True), open_chat=b.get("open_chat", True))

    def hk_command_insert(self, command):
        if not game_foreground(self.cfg["game_process"]) or self.deny("hk_binds"):
            return
        text = self.render(command.get("text", ""), self.target())
        if text:
            say(self.cfg, text, False, open_chat=command.get("open_chat", True))

    def register_hotkeys(self):
        if not keyboard:
            self.event.emit("info", "Модуль keyboard недоступний - хоткеї вимкнено")
            return
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass

        def reg(hk, fn, suppress=False):
            hk = (hk or "").strip().lower()
            if not hk:
                return
            def dispatch():
                if self.key_capture_active or time.monotonic() < self.key_capture_cooldown:
                    return
                threading.Thread(target=fn, daemon=True).start()
            try:
                keyboard.add_hotkey(hk, dispatch, suppress=suppress)
            except (KeyError, ValueError, TypeError):
                # Invalid/stale saved shortcuts are skipped quietly; do not flood
                # the dashboard with repeated parser errors on every rebind.
                return
            except Exception:
                return
        reg(self.cfg["key_pm"], self.hk_pm)
        reg(self.cfg["key_id"], self.hk_id, suppress=True)
        reg(self.cfg.get("key_form", "f2"), self.hk_form, suppress=True)
        reg(self.cfg.get("key_reject_form", "f1"), self.hk_reject_form, suppress=True)
        for command in self.cfg.get("commands", []):
            keys = (command.get("keys") or "").strip()
            if keys:
                reg(keys, lambda command=command: self.hk_command_insert(command), suppress=True)
        reg(self.cfg.get("key_overlay_menu", "alt+z"), self.hk_overlay_menu, suppress=True)
        for b in self.cfg["binds"]:
            reg(b["keys"], lambda b=b: self.hk_bind(b))

    def hk_overlay_menu(self):
        if self.deny("hk_overlay_menu"):
            return
        self.overlay_menu_toggle.emit()

    def test_line(self, line):
        out = []
        for key in ("report_regex", "colleague_regex", "form_regex", "form_reject_regex", "vip_regex", "ac_regex"):
            m = self.rx(key).search(clean(line))
            out.append(("✔ " if m else "✘ ") + key + (f"  {m.groupdict()}" if m else ""))
        return "\n".join(out)


class GameProcessWatcher(QThread):
    """Poll the game process off the UI thread to avoid periodic interface stalls."""
    running_changed = Signal(bool)

    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.run_flag = True

    def run(self):
        last_state = None
        while self.run_flag:
            target = str(self.cfg.get("game_process", "")).casefold()
            running = False
            if target:
                try:
                    for proc in psutil.process_iter(["name"]):
                        try:
                            if str(proc.info.get("name") or "").casefold() == target:
                                running = True
                                break
                        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                            continue
                except Exception:
                    pass
            if running != last_state:
                last_state = running
                self.running_changed.emit(running)
            self.msleep(1500)


def find_console_log(cfg):
    path = str(cfg.get("log_path", "")).strip()
    if path:
        return path
    for proc in psutil.process_iter(["name", "exe"]):
        try:
            if (proc.info.get("name") or "").casefold() == "multi theft auto.exe":
                candidate = os.path.join(os.path.dirname(proc.info.get("exe") or ""), "MTA", "logs", "console.log")
                if os.path.isfile(candidate):
                    return candidate
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, OSError):
            continue
    for base in (r"C:\Program Files (x86)\MTA San Andreas 1.6", r"C:\Program Files (x86)\MTA San Andreas 1.5",
                 r"C:\Program Files\MTA San Andreas 1.6", r"C:\Program Files\MTA San Andreas 1.5"):
        candidate = os.path.join(base, "MTA", "logs", "console.log")
        if os.path.isfile(candidate):
            return candidate
    return ""


class LogWatcher(QThread):
    batch = Signal(list)
    status = Signal(str)

    def __init__(self, core):
        super().__init__()
        self.core = core
        self.run_flag = True

    def find_path(self):
        return find_console_log(self.core.cfg)

    def run(self):
        path, f, pos, buf = "", None, 0, b""
        file_id = None
        next_path_scan = 0.0
        while self.run_flag:
            try:
                now = time.monotonic()
                if now >= next_path_scan:
                    p = self.find_path()
                    next_path_scan = now + 2.0
                    if p != path or f is None:
                        if f:
                            f.close()
                            f = None
                        path, pos, buf, file_id = p, 0, b"", None
                        if path and os.path.isfile(path):
                            f = open(path, "rb")
                            f.seek(0, 2)
                            pos = f.tell()
                            stat = os.fstat(f.fileno())
                            file_id = (stat.st_dev, stat.st_ino)
                            self.status.emit("Лог: " + path)
                        else:
                            path = ""
                            self.status.emit("Файл логу не знайдено (вкажіть у Налаштуваннях)")
                if f is None:
                    time.sleep(0.25)
                    continue

                stat = os.stat(path)
                current_id = (stat.st_dev, stat.st_ino)
                if current_id != file_id:
                    f.close()
                    f = open(path, "rb")
                    f.seek(0, 2)
                    pos = f.tell()
                    buf = b""
                    stat = os.fstat(f.fileno())
                    file_id = (stat.st_dev, stat.st_ino)
                size = stat.st_size
                if size < pos:
                    f.seek(0)
                    pos, buf = 0, b""
                if size > pos:
                    f.seek(pos)
                    data = f.read(min(size - pos, 65536))
                    pos += len(data)
                    buf += data
                    parts = buf.split(b"\n")
                    buf = parts.pop()
                    lines = []
                    for raw in parts:
                        ln = clean(raw.decode("utf-8", "replace"))
                        if ln:
                            self.core.fast(ln)
                            lines.append(ln)
                    if lines:
                        self.batch.emit(lines)
            except Exception as e:
                self.status.emit("Помилка читання логу: " + str(e))
                if f:
                    try:
                        f.close()
                    except OSError:
                        pass
                    f = None
            time.sleep(0.08)


# ---------------------------------------------------------------- UI
import math
from PySide6.QtCore import (QRectF, QPointF, QSize, QRect, QPropertyAnimation, QEasingCurve, Property,
                            QParallelAnimationGroup)
from PySide6.QtGui import (QPainter, QColor, QPen, QPixmap, QIcon, QImage, QPainterPath, QFontMetrics, QLinearGradient, QRadialGradient, QConicalGradient, QRegion,
                           QShortcut, QKeySequence, QCursor)
from PySide6.QtWidgets import QStyledItemDelegate, QStyle, QButtonGroup, QGraphicsOpacityEffect

# ---- палітра: графітово-синя «диспетчерська», один холодний акцент + семантичні статуси
BG, SIDE, SURF, SURF2, FIELD = "#0d1218", "#0a0e13", "#141b24", "#1a232f", "#0f151c"
LINE, TEXT, MUTED, DIM = "#222d3b", "#e7ebf0", "#8593a3", "#5b6878"
ACC, ACC_H, ACC_D = "#6ea8ff", "#8bbaff", "#1b2a40"
C_NEW, C_TAKEN, C_DONE, C_ADMIN, C_BAD = "#f5b84a", "#6ea8ff", "#7ed492", "#c3a1ff", "#ff6974"
C_COLLEAGUE, C_UNANSWERED = "#62d68f", "#ff626f"
VIP_HOMOGLYPHS = str.maketrans({
    "a": "а", "e": "е", "o": "о", "p": "р", "c": "с", "x": "х",
    "y": "у", "i": "і", "k": "к", "m": "м", "t": "т", "b": "в",
    "h": "н", "0": "о", "3": "з", "4": "ч", "6": "б", "8": "в",
})
HEAD_FONT, BODY_FONT, MONO_FONT = "Bahnschrift", "Segoe UI", "Consolas"

STATUS_COLOR = {"Новий": C_NEW, "Без відповіді": C_UNANSWERED, "Взято": C_TAKEN, "Взяв я": C_TAKEN,
                "Відповів": ACC, "В адмін-чат": C_ADMIN,
                "Колега відповів": C_COLLEAGUE, "Взяв колега": C_COLLEAGUE}
ROLE = Qt.UserRole + 1


def report_visual_status(report):
    if report.get("unanswered"):
        return "Без відповіді"
    return {"Взято": "Взяв я", "Колега відповів": "Взяв колега"}.get(report.get("status"), report.get("status", ""))


def report_color(report):
    return STATUS_COLOR.get(report_visual_status(report), MUTED)

UI_DIR = os.path.join(DATA, "ui")


def tint(hexcol, a=38):
    c = QColor(hexcol)
    return f"rgba({c.red()},{c.green()},{c.blue()},{a})"


def mix(c1, c2, t):
    a, b = QColor(c1), QColor(c2)
    return QColor(int(a.red() + (b.red() - a.red()) * t), int(a.green() + (b.green() - a.green()) * t),
                  int(a.blue() + (b.blue() - a.blue()) * t))


def head_font(px, weight=QFont.DemiBold):
    f = QFont()
    f.setFamilies([HEAD_FONT, BODY_FONT])
    f.setPixelSize(px)
    f.setWeight(weight)
    return f


# ---------------------------------------------------------------- іконки (малюємо самі, без емодзі)
def icon_pix(kind, color, size=20):
    dpr = 2
    pm = QPixmap(size * dpr, size * dpr)
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color), 1.6)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    if kind == "dash":
        for x, y, w, h in ((3, 3, 6, 8), (11, 3, 6, 4), (3, 13, 6, 4), (11, 9, 6, 8)):
            p.drawRoundedRect(QRectF(x, y, w, h), 1.6, 1.6)
    elif kind == "inbox":
        p.drawPolyline([QPointF(3, 11), QPointF(5.5, 4.5), QPointF(14.5, 4.5), QPointF(17, 11), QPointF(17, 15),
                        QPointF(3, 15), QPointF(3, 11)])
        p.drawPolyline([QPointF(3, 11), QPointF(7, 11), QPointF(8.2, 13), QPointF(11.8, 13), QPointF(13, 11),
                        QPointF(17, 11)])
    elif kind == "users":
        p.drawEllipse(QPointF(8, 7), 3, 3)
        p.drawEllipse(QPointF(14.2, 8), 2.2, 2.2)
        p.drawArc(QRectF(3, 10, 10, 8), 0, 180 * 16)
        p.drawArc(QRectF(11, 11, 7, 6), 0, 180 * 16)
    elif kind == "star":
        pts = []
        for i in range(10):
            r = 7.6 if i % 2 == 0 else 3.3
            a = -math.pi / 2 + i * math.pi / 5
            pts.append(QPointF(10 + r * math.cos(a), 10.5 + r * math.sin(a)))
        p.drawPolygon(pts)
    elif kind == "keys":
        p.drawRoundedRect(QRectF(2.5, 5, 15, 10), 2, 2)
        for x in (5.5, 8.5, 11.5, 14.5):
            p.drawPoint(QPointF(x, 8.2))
        p.drawLine(QPointF(6.5, 12), QPointF(13.5, 12))
    elif kind == "shield":
        path = QPainterPath()
        path.moveTo(10, 2.5)
        path.lineTo(16.5, 5)
        path.lineTo(16.5, 10)
        path.cubicTo(16.5, 14, 13.5, 16.5, 10, 17.8)
        path.cubicTo(6.5, 16.5, 3.5, 14, 3.5, 10)
        path.lineTo(3.5, 5)
        path.closeSubpath()
        p.drawPath(path)
        p.drawPolyline([QPointF(7, 10), QPointF(9.2, 12.2), QPointF(13, 8)])
    elif kind == "doc":
        p.drawRoundedRect(QRectF(4, 2.5, 12, 15), 2, 2)
        p.drawLine(QPointF(7, 7), QPointF(13, 7))
        p.drawLine(QPointF(7, 10), QPointF(13, 10))
        p.drawLine(QPointF(7, 13), QPointF(10.5, 13))
    elif kind == "ban":
        p.drawRoundedRect(QRectF(3, 3, 14, 14), 4, 4)
        p.drawLine(QPointF(6, 14), QPointF(14, 6))
    elif kind == "gear":
        p.drawEllipse(QPointF(10, 10), 2.8, 2.8)
        p.drawEllipse(QPointF(10, 10), 5.6, 5.6)
        for i in range(8):
            a = i * math.pi / 4
            p.drawLine(QPointF(10 + 5.6 * math.cos(a), 10 + 5.6 * math.sin(a)),
                       QPointF(10 + 7.6 * math.cos(a), 10 + 7.6 * math.sin(a)))
    elif kind == "chat":
        p.drawRoundedRect(QRectF(3, 3.5, 14, 10.5), 3.2, 3.2)
        p.drawPolyline([QPointF(7, 14), QPointF(7, 17.2), QPointF(10.4, 14)])
        for x in (7, 10, 13):
            p.drawPoint(QPointF(x, 8.7))
    elif kind in ("bell", "bell_on"):
        # дзвоник
        path = QPainterPath()
        path.moveTo(10, 2.5)
        path.cubicTo(6.5, 2.5, 4.5, 5.0, 4.5, 8.5)
        path.lineTo(4.5, 13.0)
        path.lineTo(3.0, 14.5)
        path.lineTo(17.0, 14.5)
        path.lineTo(15.5, 13.0)
        path.lineTo(15.5, 8.5)
        path.cubicTo(15.5, 5.0, 13.5, 2.5, 10, 2.5)
        p.drawPath(path)
        p.drawArc(int(7.5 * 16), int(14.5 * 16), int(5 * 16), int(3 * 16), 180 * 16, -180 * 16)
    elif kind == "bell_off":
        # дзвоник перекреслений
        path = QPainterPath()
        path.moveTo(10, 2.5)
        path.cubicTo(6.5, 2.5, 4.5, 5.0, 4.5, 8.5)
        path.lineTo(4.5, 13.0)
        path.lineTo(3.0, 14.5)
        path.lineTo(17.0, 14.5)
        path.lineTo(15.5, 13.0)
        path.lineTo(15.5, 8.5)
        path.cubicTo(15.5, 5.0, 13.5, 2.5, 10, 2.5)
        p.drawPath(path)
        p.drawArc(int(7.5 * 16), int(14.5 * 16), int(5 * 16), int(3 * 16), 180 * 16, -180 * 16)
        pen2 = QPen(col, 1.5)
        pen2.setCapStyle(Qt.RoundCap)
        p.setPen(pen2)
        p.drawLine(QPointF(3.5, 3.5), QPointF(16.5, 16.5))
    elif kind == "star_new":
        # зірка «новачок»
        import math as _m
        pts = []
        for i in range(5):
            a_out = _m.pi * (i * 2 - 0.5) / 5
            a_in  = _m.pi * (i * 2 + 0.5) / 5
            pts.append(QPointF(10 + 6.5 * _m.cos(a_out), 10 + 6.5 * _m.sin(a_out)))
            pts.append(QPointF(10 + 2.8 * _m.cos(a_in),  10 + 2.8 * _m.sin(a_in)))
        p.drawPolygon(pts)
    p.end()
    return pm


def nav_icon(kind):
    ic = QIcon()
    ic.addPixmap(icon_pix(kind, MUTED), QIcon.Normal, QIcon.Off)
    ic.addPixmap(icon_pix(kind, ACC), QIcon.Normal, QIcon.On)
    return ic


def logo_pix(size=36):
    asset = QPixmap(resource_path(os.path.join("assets", "yavir_icon.png")))
    if not asset.isNull():
        dpr = 2
        scaled = asset.scaled(size * dpr, size * dpr, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        scaled.setDevicePixelRatio(dpr)
        return scaled
    dpr = 2
    pm = QPixmap(size * dpr, size * dpr)
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    gradient = QLinearGradient(0, 0, size, size)
    gradient.setColorAt(0.0, QColor("#82B4FF"))
    gradient.setColorAt(0.52, QColor("#637EF1"))
    gradient.setColorAt(1.0, QColor("#42D8C1"))
    outer = QRectF(1, 1, size - 2, size - 2)
    p.setPen(QPen(QColor(255, 255, 255, 74), max(1, size * 0.025)))
    p.setBrush(gradient)
    p.drawRoundedRect(outer, size * 0.26, size * 0.26)

    shield = QPainterPath()
    shield.moveTo(size * 0.5, size * 0.16)
    shield.lineTo(size * 0.77, size * 0.27)
    shield.lineTo(size * 0.73, size * 0.59)
    shield.quadTo(size * 0.68, size * 0.75, size * 0.5, size * 0.84)
    shield.quadTo(size * 0.32, size * 0.75, size * 0.27, size * 0.59)
    shield.lineTo(size * 0.23, size * 0.27)
    shield.closeSubpath()
    p.setPen(QPen(QColor(255, 255, 255, 150), max(1, size * 0.025)))
    p.setBrush(QColor(9, 20, 34, 232))
    p.drawPath(shield)

    mark = QPainterPath()
    mark.moveTo(size * 0.35, size * 0.36)
    mark.lineTo(size * 0.5, size * 0.52)
    mark.lineTo(size * 0.65, size * 0.36)
    mark.moveTo(size * 0.5, size * 0.52)
    mark.lineTo(size * 0.5, size * 0.68)
    pen = QPen(QColor("#F4FBFF"), max(1.7, size * 0.085))
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawPath(mark)
    p.end()
    return pm


def brand_pix(width=330):
    asset = QPixmap(resource_path(os.path.join("assets", "yavir_wordmark.png")))
    if asset.isNull():
        return logo_pix(48)
    return asset.scaledToWidth(width, Qt.SmoothTransformation)


def make_assets():
    """Стрілки/галочка для QSS (малюються один раз у папку даних)."""
    os.makedirs(UI_DIR, exist_ok=True)
    out = {}
    for name, pts, col in (("down", [(4, 7.5), (10, 13), (16, 7.5)], MUTED),
                           ("up", [(4, 12.5), (10, 7), (16, 12.5)], MUTED),
                           ("check", [(4.5, 10.5), (8.5, 14.2), (15.5, 6)], "#07111f")):
        pm = QPixmap(20, 20)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(col), 2.2)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        p.drawPolyline([QPointF(x, y) for x, y in pts])
        p.end()
        path = os.path.join(UI_DIR, name + ".png")
        pm.save(path, "PNG")
        out[name.upper()] = path.replace("\\", "/")
    return out


# ---------------------------------------------------------------- QSS
QSS_T = """
* { font-family: "@BODY"; font-size: 13px; color: @TEXT; }
QMainWindow, QWidget#root { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #0c1118,stop:1 #111923); }
QLabel { background: transparent; }
QToolTip { background: @SURF2; color: @TEXT; border: 1px solid #2b3a4d; padding: 5px 8px; }

/* сайдбар */
QFrame#sidebar { background: @SIDE; border-right: 1px solid @LINE; }
QLabel#brand { font-family: "@HEAD"; font-size: 18px; font-weight: 600; color: #fff; }
QLabel#brandsub { color: @DIM; font-size: 11px; }
QPushButton#nav { background: transparent; border: 1px solid transparent; border-left: 3px solid transparent; border-radius: 8px;
  margin: 2px 9px; text-align: left; padding: 0 14px 0 12px; color: @MUTED; font-weight: 500; }
QPushButton#nav:hover { background: #111923; border-color: #1e2936; color: @TEXT; }
QPushButton#nav:checked { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #17263d,stop:1 #121c2b);
  border-color: #2b3c55; border-left: 3px solid @ACC; color: #fff; }
QLabel#badge { background: @NEW; color: #1a1204; font-weight: 700; font-size: 11px; border-radius: 9px;
  min-width: 18px; max-height: 18px; padding: 0 5px; }
QFrame#profile { background: @SURF; border: 1px solid #202b38; border-radius: 10px; }
QLabel#dashBrandTitle { color: #f7faff; font-family: "@HEAD"; font-size: 25px; font-weight: 700; }
QLabel#dashBrandSub { color: #9eacbf; font-size: 12px; }
QLabel#avatar { background: @SURF2; color: @ACC; border-radius: 19px; font-family: "@HEAD"; font-size: 16px; font-weight: 600; }
QLabel#pname { font-weight: 600; color: #fff; }
QLabel#psub { color: @MUTED; font-size: 11px; }

/* типографіка */
QLabel#h1 { font-family: "@HEAD"; font-size: 27px; font-weight: 650; color: #fff; }
QLabel#h2 { font-size: 14px; font-weight: 650; color: @TEXT; }
QLabel#title { font-family: "@HEAD"; font-size: 18px; font-weight: 600; color: #fff; }
QLabel#muted { color: @MUTED; }
QLabel#hint { color: @DIM; font-size: 12px; }
QLabel#big { font-family: "@HEAD"; font-size: 34px; font-weight: 600; color: #fff; }
QLabel#reporttext { font-size: 16px; color: #fff; }
QLabel#reportEyebrow { color: @DIM; font-size: 10px; font-weight: 700; letter-spacing: 1px; }
QLabel#reportIdentity { color: #fff; font-family: "@HEAD"; font-size: 20px; font-weight: 700; }
QLabel#reportId { background: #202c3d; border: 1px solid #30445f; color: #9dc2ff; border-radius: 9px;
  padding: 4px 9px; font-size: 11px; font-weight: 700; }
QLabel#reportMeta { color: @MUTED; font-size: 11px; }
QLabel#charCounter { background: #1b2430; color: @MUTED; border: 1px solid #2a394c; border-radius: 9px;
  padding: 4px 9px; font-size: 11px; font-weight: 700; }
QLabel#empty { color: @DIM; font-size: 13px; }
QLabel#warnbar { background: rgba(255,123,123,28); border-left: 3px solid @BAD; color: #ffb9b9; padding: 9px 12px;
  border-top-right-radius: 6px; border-bottom-right-radius: 6px; }
QLabel#toast { background: @SURF2; border: 1px solid #2b3a4d; border-left: 3px solid @DONE; border-radius: 8px;
  padding: 11px 18px; color: #fff; font-weight: 500; }

/* поверхні */
QFrame#card { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #171f2a,stop:1 #131a23);
  border: 1px solid #253242; border-radius: 13px; }
QFrame#quote { background: @FIELD; border: none; border-left: 3px solid @ACC; border-top-right-radius: 8px;
  border-bottom-right-radius: 8px; }
QFrame#reportHero { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #1b2737,stop:1 #151d29);
  border: 1px solid #2b3b50; border-radius: 14px; }
QFrame#reportMessage { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #111b29,stop:1 #101720);
  border: 1px solid #26364a; border-left: 3px solid @ACC; border-radius: 12px; }
QLabel#playerReportCount { background: #17253a; border: 1px solid #2a4264; border-radius: 7px;
  color: #a9c7ff; padding: 7px 10px; font-size: 11px; font-weight: 600; }
QFrame#punishmentRow { background: #111821; border: 1px solid #263448; border-radius: 8px; }
QLabel#punishmentCommand { color: @ACC_H; font-family: @MONO; font-weight: 700; }
QPushButton#punishSend { padding: 5px 8px; min-width: 96px; }
QFrame#reportActionBar { background: #111821; border: 1px solid #222e3d; border-radius: 10px; }
QLabel#overlayLatest { background: #111923; border: 1px solid #263548; border-radius: 8px;
  padding: 7px 10px; color: @MUTED; font-size: 11px; }
QFrame#overlayStatTile { background: @SURF2; border: 1px solid #283447; border-radius: 10px; }
QFrame#alert { background: @SURF; border: none; border-left: 3px solid @DIM; border-radius: 10px; }
QFrame#alert[armed="true"] { background: #1d1619; border-left: 3px solid @BAD; }
QFrame#savebar { background: @SIDE; border-top: 1px solid @LINE; }
QFrame#sep { background: @LINE; border: none; min-height: 1px; max-height: 1px; }

/* кнопки */
QPushButton { background: @SURF2; border: 1px solid #2a394c; border-radius: 8px; padding: 8px 14px; font-weight: 550; }
QPushButton:hover { background: #222f3e; border-color: #40536c; }
QPushButton:pressed { background: #18212c; }
QPushButton:disabled { color: @DIM; background: #111820; border-color: #1b2531; }
QPushButton:focus { border-color: @ACC; }
QPushButton#primary { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #83b5ff,stop:1 #5a91ed);
  color: #07111f; border: 1px solid #82b4ff; font-weight: 700; }
QPushButton#primary:hover { background: #92bdff; border-color: #a2c8ff; }
QPushButton#primary:pressed { background: #5b93e6; }
QPushButton#primary:disabled { background: #1c2a3d; color: #5f7391; border-color: #1c2a3d; }
QPushButton#ok { background: #173a26; border: 1px solid #25673f; color: @DONE; font-weight: 700; }
QPushButton#ok:hover { background: #1c4730; }
QPushButton#ok:disabled { background: #111820; color: @DIM; border-color: #1b2531; }
QPushButton#ghost { background: transparent; border: 1px solid transparent; color: @MUTED; }
QPushButton#ghost:hover { background: @SURF2; color: @TEXT; }
QPushButton#danger { background: transparent; border: 1px solid #4a2a30; color: @BAD; }
QPushButton#danger:hover { background: #2a171b; border-color: #6a3640; }
QPushButton#chip { background: @FIELD; border: 1px solid #24303f; border-radius: 6px; padding: 6px 10px;
  color: #b4c0cd; text-align: left; font-weight: 400; }
QPushButton#chip:hover { border-color: @ACC; color: #fff; background: #111b28; }
QPushButton#keyCapture { background: #111a26; border: 1px solid #2d405b; color: @ACC_H; padding: 5px 7px;
  font-family: @MONO; font-size: 11px; font-weight: 650; }
QPushButton#keyCapture:hover { background: #1a2940; border-color: @ACC; }
QPushButton#keyCapture:focus { border: 1px solid @ACC; }
QLabel#bindKey { background: #202b39; border: 1px solid #304157; border-radius: 5px;
  color: @ACC_H; padding: 2px 6px; font-size: 10px; font-weight: 700; }
QPushButton#seg { background: transparent; border: 1px solid #24303f; color: @MUTED; padding: 5px 14px; }
QPushButton#seg:hover { color: @TEXT; }
QPushButton#seg:checked { background: @ACC_D; border-color: #2d4466; color: #fff; }

/* поля */
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
  background: @FIELD; border: 1px solid #293747; border-radius: 8px; padding: 8px 11px;
  selection-background-color: #2d5aa0; selection-color: #fff; }
QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover { border-color: #31415a; }
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus { border: 1px solid @ACC; }
QLineEdit[readOnly="true"], QPlainTextEdit[readOnly="true"], QTextEdit[readOnly="true"] { background: #0b1117; }
QComboBox { padding-right: 28px; }
QComboBox::drop-down { border: none; width: 28px; subcontrol-origin: padding; subcontrol-position: center right; }
QComboBox::down-arrow { image: url(@DOWN); width: 10px; height: 10px; }
QComboBox QAbstractItemView { background: #121a23; border: 1px solid #2b3a4d; selection-background-color: @ACC_D;
  selection-color: #fff; outline: none; padding: 4px; }
QSpinBox, QDoubleSpinBox { padding-right: 24px; }
QSpinBox::up-button, QDoubleSpinBox::up-button { subcontrol-origin: border; subcontrol-position: top right; width: 22px; border: none; background: transparent; }
QSpinBox::down-button, QDoubleSpinBox::down-button { subcontrol-origin: border; subcontrol-position: bottom right; width: 22px; border: none; background: transparent; }
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow { image: url(@UP); width: 8px; height: 8px; }
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow { image: url(@DOWN); width: 8px; height: 8px; }
QSplitter#reportSplitter::handle { background: #202b38; border-radius: 3px; }
QSplitter#reportSplitter::handle:hover { background: @ACC; }
/* списки */
QListWidget { background: @FIELD; border: none; border-radius: 8px; padding: 4px; outline: none; }
QListWidget#rlist, QListWidget#feed { background: transparent; padding: 0; }
QListWidget#sections { background: transparent; padding: 0; }
QListWidget#sections::item { padding: 8px 12px; color: @MUTED; border-radius: 6px; margin: 1px 0; }
QListWidget#sections::item:hover { color: @TEXT; }
QListWidget#sections::item:selected { background: @SURF2; color: #fff; }

/* таблиця */
QTableWidget { background: @FIELD; border: 1px solid #24303f; border-radius: 8px; gridline-color: transparent;
  alternate-background-color: #121a23; selection-background-color: @ACC_D; padding: 2px; outline: none; }
QTableWidget::item { padding: 4px 10px; border: none; }
QTableWidget::item:selected { background: @ACC_D; color: #fff; }
QTableWidget QLineEdit { padding: 2px 6px; border-radius: 4px; }
QHeaderView { background: transparent; }
QHeaderView::section { background: transparent; color: @MUTED; border: none; border-bottom: 1px solid @LINE;
  padding: 9px 10px; font-weight: 500; }
QTableCornerButton::section { background: transparent; border: none; }
QTableView::indicator { width: 16px; height: 16px; border-radius: 4px; border: 1px solid #3a4a5e; background: @FIELD; }
QTableView::indicator:checked { background: @ACC; border-color: @ACC; image: url(@CHECK); }

/* вкладки */
QTabWidget::pane { border: none; border-top: 1px solid @LINE; top: -1px; }
QTabBar { background: transparent; }
QTabBar::tab { background: transparent; color: @MUTED; padding: 10px 14px; margin-right: 6px; border-bottom: 2px solid transparent; }
QTabBar::tab:hover:!selected { color: @TEXT; }
QTabBar::tab:selected { color: #fff; border-bottom: 2px solid @ACC; }

/* скролбари */
QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #26323f; border-radius: 3px; min-height: 36px; }
QScrollBar::handle:vertical:hover { background: #34445a; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: #26323f; border-radius: 3px; min-width: 36px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
"""


GLASS_ON = False


def glass_qss(transparency=40, edge_level=75):
    """Liquid Glass: напівпрозорі панелі зі світлою кромкою. Фон застосунку не змінюється."""
    k = 1.0 - max(0, min(100, int(transparency))) / 100.0
    e = max(0, min(100, int(edge_level))) / 100.0
    a1, a2, a3 = int(16 + 36 * k), int(6 + 14 * k), int(10 + 26 * k)   # верх / середина / низ скла
    ln, hi = int(26 + 26 * k), int(40 + 150 * e)                       # кромка / верхній відблиск
    fld = int(70 + 70 * k)                                              # затемнення полів
    W = lambda a: f"rgba(255,255,255,{a})"
    glass = (f"qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {W(a1)},stop:0.5 {W(a2)},stop:1 {W(a3)})")
    soft = (f"qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 {W(a2 + 6)},stop:1 {W(a2 - 2)})")
    edge = f"border: 1px solid {W(ln)}; border-top: 1px solid {W(hi)};"
    return f"""
/* ===== Liquid Glass ===== */
QMainWindow, QWidget#root {{ background: #060a13; }}
QFrame#sidebar {{ background: {glass}; {edge} border-radius: 24px; margin: 14px 0 14px 14px; }}
QListWidget#sections {{ background: {glass}; {edge} border-radius: 22px; padding: 10px; }}
QListWidget#sections::item {{ padding: 10px 14px; border-radius: 12px; border: 1px solid transparent; }}
QSlider::groove:horizontal {{ height: 6px; background: {W(40)}; border-radius: 3px; }}
QSlider::sub-page:horizontal {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #6ea8ff,stop:1 #a2c6ff); border-radius: 3px; }}
QSlider::handle:horizontal {{ width: 30px; height: 20px; margin: -8px 0; border-radius: 10px; background: #ffffff; }}
QPushButton#nav {{ border-radius: 14px; border-left: 1px solid transparent; margin: 2px 10px; }}
QPushButton#nav:hover {{ background: {W(a2 + 8)}; border-color: {W(ln)}; }}
QPushButton#nav:checked {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 rgba(110,168,255,{int(70 + 70 * k)}),stop:1 rgba(110,168,255,{int(26 + 30 * k)}));
  border: 1px solid rgba(160,200,255,{int(90 + 70 * k)}); border-top: 1px solid rgba(200,225,255,{int(130 + 90 * k)}); color: #fff; }}
QFrame#profile {{ background: {glass}; {edge} border-radius: 16px; }}
QFrame#card {{ background: {glass}; {edge} border-radius: 22px; }}
QFrame#reportHero {{ background: {glass}; {edge} border-radius: 22px; }}
QFrame#reportMessage {{ background: {soft}; border: 1px solid {W(ln)}; border-left: 3px solid @ACC; border-radius: 14px; }}
QFrame#punishmentRow, QFrame#reportActionBar, QFrame#overlayStatTile {{ background: {soft}; {edge} border-radius: 14px; }}
QFrame#alert {{ background: {soft}; border-radius: 14px; }}
QFrame#savebar {{ background: {glass}; border: none; border-top: 1px solid {W(hi)}; }}
QFrame#quote {{ background: rgba(6,10,18,{fld}); }}
QLabel#toast {{ background: {glass}; {edge} border-radius: 14px; }}
QLabel#reportId, QLabel#charCounter, QLabel#playerReportCount, QLabel#bindKey {{ background: {W(a2 + 10)}; border: 1px solid {W(ln)}; border-radius: 10px; }}
QPushButton {{ background: {soft}; {edge} border-radius: 12px; }}
QPushButton:hover {{ background: {W(a1 + 8)}; }}
QPushButton:pressed {{ background: {W(a3)}; }}
QPushButton:disabled {{ background: {W(a2)}; border: 1px solid {W(ln // 2)}; }}
QPushButton#primary {{ border: 1px solid #9cc4ff; border-top: 1px solid #d6e8ff; border-radius: 12px; }}
QPushButton#ghost {{ background: transparent; border: 1px solid transparent; }}
QPushButton#ghost:hover {{ background: {W(a2 + 8)}; border: 1px solid {W(ln)}; }}
QPushButton#danger {{ background: rgba(255,105,116,22); border: 1px solid rgba(255,105,116,90); border-radius: 12px; }}
QPushButton#ok {{ background: rgba(126,212,146,34); border: 1px solid rgba(126,212,146,120); border-radius: 12px; }}
QPushButton#chip, QPushButton#keyCapture, QPushButton#seg {{ background: {W(a2 + 4)}; border: 1px solid {W(ln)}; border-radius: 10px; }}
QPushButton#seg:checked {{ background: rgba(110,168,255,70); border: 1px solid rgba(160,200,255,150); }}
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{ background: rgba(6,10,18,{fld}); border: 1px solid {W(ln)}; border-radius: 12px; }}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{ border: 1px solid @ACC; }}
QLineEdit[readOnly="true"], QPlainTextEdit[readOnly="true"], QTextEdit[readOnly="true"] {{ background: rgba(6,10,18,{max(40, fld - 30)}); }}
QComboBox QAbstractItemView {{ background: #121a23; border: 1px solid {W(hi)}; border-radius: 10px; }}
QListWidget, QTableWidget {{ background: rgba(6,10,18,{max(50, fld - 20)}); border: 1px solid {W(ln)}; border-radius: 14px; alternate-background-color: {W(a2 - 2)}; }}
QFrame#card[thin="true"] {{ border-radius: 14px; }}
QListWidget#sections QScrollBar:vertical {{ width: 8px; margin: 12px 3px; background: transparent; }}
QListWidget#sections QScrollBar::handle:vertical {{ background: {W(70)}; border-radius: 4px; min-height: 30px; }}
QListWidget#sections QScrollBar::add-line:vertical, QListWidget#sections QScrollBar::sub-line:vertical {{ height: 0; }}
QListWidget#rlist, QListWidget#feed {{ background: transparent; border: none; }}
QPushButton#nav {{ color: #c3cfdf; }}
QPushButton#nav:checked {{ color: #ffffff; }}
QLabel#muted {{ color: #b5c1d3; }}
QLabel#hint, QLabel#brandsub, QLabel#psub {{ color: #8f9db2; }}
QListWidget#sections::item:selected {{ background: rgba(110,168,255,{int(40 + 50 * k)}); border: 1px solid rgba(160,200,255,{int(90 + 70 * k)}); color: #fff; }}
QTabWidget::pane {{ border-top: 1px solid {W(ln)}; }}
QTabBar::tab:selected {{ border-bottom: 2px solid @ACC; }}
QToolTip {{ background: #141c27; border: 1px solid {W(hi)}; border-radius: 8px; }}
"""


def build_qss(cfg=None):
    tokens = dict(BG=BG, SIDE=SIDE, SURF2=SURF2, SURF=SURF, FIELD=FIELD, LINE=LINE, TEXT=TEXT, MUTED=MUTED,
                  DIM=DIM, ACC_H=ACC_H, ACC_D=ACC_D, ACC=ACC, NEW=C_NEW, DONE=C_DONE, BAD=C_BAD,
                  BODY=BODY_FONT, HEAD=HEAD_FONT, MONO=MONO_FONT)
    tokens.update(make_assets())
    _sc2 = max(0.7, min(2.0, float((cfg or {}).get("ui_scale", 1.0))))
    q = QSS_T
    if _sc2 != 1.0:
        import re as _re
        q = _re.sub(r'(\d+)px', lambda m: str(round(int(m.group(1)) * _sc2)) + 'px', q)
    for k in sorted(tokens, key=len, reverse=True):
        q = q.replace("@" + k, tokens[k])
    global GLASS_ON
    GLASS_ON = bool(cfg and cfg.get("liquid_glass"))
    if GLASS_ON:
        g = glass_qss(cfg.get("liquid_glass_strength", 40), cfg.get("liquid_glass_edge", 75))
        for k in sorted(tokens, key=len, reverse=True):
            g = g.replace("@" + k, tokens[k])
        q += g
    return q


# ---------------------------------------------------------------- маленькі будівельні блоки
def card():
    f = QFrame()
    f.setObjectName("card")
    return f


def lab(text, name=None, wrap=False):
    l = QLabel(text)
    if name:
        l.setObjectName(name)
    l.setWordWrap(wrap)
    return l


def sep():
    f = QFrame()
    f.setObjectName("sep")
    f.setFixedHeight(1)
    return f


def set_pill(label, text, color):
    label.setText(text)
    label.setStyleSheet(f"background:{tint(color, 34)}; color:{color}; border-radius:11px; padding:4px 12px;"
                        f"font-weight:600; font-size:12px;")


def repolish(w):
    w.style().unpolish(w)
    w.style().polish(w)


def with_empty(lw, text):
    """Список + підказка, коли він порожній."""
    st = QStackedWidget()
    st.addWidget(lw)
    e = lab(text, "empty", True)
    e.setAlignment(Qt.AlignCenter)
    st.addWidget(e)

    def sync(*_):
        st.setCurrentIndex(0 if lw.count() else 1)
    m = lw.model()
    m.rowsInserted.connect(sync)
    m.rowsRemoved.connect(sync)
    m.modelReset.connect(sync)
    sync()
    return st


def add_feed(lw, tag, text, color, limit=300, stamp=True):
    it = QListWidgetItem()
    it.setData(ROLE, (f"{datetime.datetime.now():%H:%M:%S}" if stamp else "", tag, text, color))
    it.setToolTip(text)
    lw.insertItem(0, it)
    while lw.count() > limit:
        lw.takeItem(lw.count() - 1)
    return it


def page_layout(page, spacing=18):
    lay = QVBoxLayout(page)
    lay.setContentsMargins(32, 26, 32, 24)
    lay.setSpacing(spacing)
    return lay


class PageHead(QWidget):
    def __init__(self, title, sub="", right=None):
        super().__init__()
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        v = QVBoxLayout()
        v.setSpacing(3)
        v.addWidget(lab(title, "h1"))
        self.sub = lab(sub, "muted", True)
        self.sub.setVisible(bool(sub))
        v.addWidget(self.sub)
        h.addLayout(v, 1)
        if right is not None:
            h.addWidget(right, 0, Qt.AlignTop | Qt.AlignRight)

    def set_sub(self, t):
        self.sub.setText(t)
        self.sub.setVisible(bool(t))


class Toggle(QCheckBox):
    """Перемикач замість стандартної галочки. API як у QCheckBox."""

    def __init__(self, text=""):
        super().__init__(text)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.TabFocus)
        self._t = 0.0
        self.anim = QPropertyAnimation(self, b"thumb", self)
        self.anim.setDuration(130)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.toggled.connect(self._go)

    def _get(self):
        return self._t

    def _set(self, v):
        self._t = v
        self.update()
    thumb = Property(float, _get, _set)

    def _go(self, on):
        self.anim.stop()
        self.anim.setStartValue(self._t)
        self.anim.setEndValue(1.0 if on else 0.0)
        self.anim.start()

    def setChecked(self, v):
        super().setChecked(v)
        self.anim.stop()
        self._t = 1.0 if v else 0.0
        self.update()

    def sizeHint(self):
        tw = self.fontMetrics().horizontalAdvance(self.text()) + 12 if self.text() else 0
        return QSize(38 + tw, 26)

    def minimumSizeHint(self):
        return self.sizeHint()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        ty = (self.height() - 20) / 2
        p.setPen(Qt.NoPen)
        if GLASS_ON:
            if self._t > 0.02:
                p.setBrush(QColor(110, 168, 255, int(70 * self._t)))
                p.drawRoundedRect(QRectF(-3, ty - 3, 42, 26), 13, 13)
            g = QLinearGradient(0, ty, 36, ty + 20)
            g.setColorAt(0, mix("#3a4658", "#8bbaff", self._t))
            g.setColorAt(1, mix("#2a3646", "#4f86ec", self._t))
            p.setBrush(g)
            p.setPen(QPen(QColor(255, 255, 255, 60 + int(60 * self._t)), 1))
        else:
            p.setBrush(mix("#2a3646", ACC, self._t))
        p.drawRoundedRect(QRectF(0, ty, 36, 20), 10, 10)
        p.setPen(Qt.NoPen)
        p.setBrush(mix("#9aa7b6", "#ffffff", self._t))
        p.drawEllipse(QRectF(3 + 16 * self._t, ty + 3, 14, 14))
        if self.hasFocus():
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(ACC), 1.5))
            p.drawRoundedRect(QRectF(-1.5, ty - 1.5, 39, 23), 11.5, 11.5)
        if self.text():
            p.setPen(QColor(TEXT if self.isEnabled() else DIM))
            p.drawText(QRect(48, 0, self.width() - 48, self.height()), Qt.AlignVCenter | Qt.AlignLeft, self.text())


class Ring(QWidget):
    """Компактна горизонтальна смуга прогресу норми."""

    def __init__(self):
        super().__init__()
        self.frac, self.big, self.small = 0.0, "", ""
        self.setMinimumHeight(104)

    def set(self, frac, big, small):
        self.frac, self.big, self.small = frac, big, small
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        margin = 12
        track = QRectF(margin, 54, max(0, self.width() - margin * 2), 11)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#202b38"))
        p.drawRoundedRect(track, 5.5, 5.5)
        progress = QRectF(track)
        progress.setWidth(track.width() * min(1.0, max(0.0, self.frac)))
        if progress.width() > 5:
            p.setBrush(QColor(C_DONE if self.frac >= 1 else ACC))
            p.drawRoundedRect(progress, 5.5, 5.5)
        p.setPen(QColor("#ffffff"))
        p.setFont(head_font(28))
        p.drawText(QRectF(margin, 4, self.width() - margin * 2, 38), Qt.AlignCenter, self.big)
        p.setPen(QColor(MUTED))
        f = QFont()
        f.setPixelSize(11)
        p.setFont(f)
        p.drawText(QRectF(margin, 72, self.width() - margin * 2, 20), Qt.AlignCenter, self.small)


class ReportDelegate(QStyledItemDelegate):
    """Картка репорту зі статусним світінням зліва; окрему крапку статусу не малюємо."""

    def sizeHint(self, o, i):
        return QSize(o.rect.width(), 62)

    def paint(self, p, o, idx):
        r = idx.data(ROLE)
        if not isinstance(r, dict):
            return super().paint(p, o, idx)
        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(o.rect).adjusted(2, 2, -2, -2)
        sel = bool(o.state & QStyle.State_Selected)
        hov = bool(o.state & QStyle.State_MouseOver)
        col = QColor(report_color(r))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(ACC_D if sel else "#18212c" if hov else "#151d27"))
        p.drawRoundedRect(rect, 9, 9)
        beam = QRadialGradient(QPointF(rect.left() + 7, rect.center().y()), max(90.0, rect.width() * 0.78))
        beam.setColorAt(0.0, QColor(col.red(), col.green(), col.blue(), 126))
        beam.setColorAt(0.34, QColor(col.red(), col.green(), col.blue(), 68))
        beam.setColorAt(1.0, QColor(col.red(), col.green(), col.blue(), 0))
        p.save()
        card_clip = QPainterPath()
        card_clip.addRoundedRect(rect, 9, 9)
        p.setClipPath(card_clip)
        p.fillRect(rect, beam)
        p.restore()
        if r["flags"]:
            p.setBrush(QColor(C_BAD))
            p.drawRoundedRect(QRectF(rect.left(), rect.top() + 10, 3, rect.height() - 20), 1.5, 1.5)
        x, right = rect.left() + 15, rect.right() - 12
        small = QFont(o.font)
        small.setPixelSize(11)
        fms = QFontMetrics(small)
        p.setFont(small)
        p.setPen(QColor(DIM))
        tw = fms.horizontalAdvance(r["time"])
        p.drawText(QPointF(right - tw, rect.top() + 25), r["time"])
        used = tw + 12
        status_text = report_visual_status(r)
        if status_text != "Новий":
            p.setPen(col)
            sw = fms.horizontalAdvance(status_text)
            p.drawText(QPointF(right - tw - 10 - sw, rect.top() + 25), status_text)
            used += sw + 10
        nf = QFont(o.font)
        nf.setPixelSize(13)
        nf.setBold(True)
        fmn = QFontMetrics(nf)
        p.setFont(nf)
        p.setPen(QColor("#ffffff"))
        p.drawText(QPointF(x, rect.top() + 25), fmn.elidedText(f"{r['name']} [{r['id']}]", Qt.ElideRight,
                                                              int(right - x - used)))
        tf = QFont(o.font)
        tf.setPixelSize(12)
        p.setFont(tf)
        p.setPen(QColor("#b4c0cd" if r["status"] == "Новий" else MUTED))
        p.drawText(QPointF(x, rect.top() + 46), QFontMetrics(tf).elidedText(r["text"], Qt.ElideRight,
                                                                           int(right - x)))
        p.restore()


class FeedDelegate(QStyledItemDelegate):
    """Рядок стрічки: час - мітка - текст."""

    def sizeHint(self, o, i):
        return QSize(o.rect.width(), 30)

    def paint(self, p, o, idx):
        d = idx.data(ROLE)
        if not d:
            return super().paint(p, o, idx)
        t, tag, txt, col = d
        is_ad_row = tag == "РЕКЛАМА"
        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(o.rect).adjusted(0, 1, 0, -1)
        if is_ad_row:
            p.setPen(QPen(QColor("#ff6975", 105), 1))
            p.setBrush(QColor("#51232b" if o.state & QStyle.State_MouseOver else "#3b1d25"))
            p.drawRoundedRect(rect, 6, 6)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#ff5967"))
            p.drawRoundedRect(QRectF(rect.left(), rect.top() + 5, 3, rect.height() - 10), 1.5, 1.5)
        elif o.state & QStyle.State_Selected:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(ACC_D))
            p.drawRoundedRect(rect, 6, 6)
        elif o.state & QStyle.State_MouseOver:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#151e29"))
            p.drawRoundedRect(rect, 6, 6)
        x, base = rect.left() + 8, rect.center().y() + 4.5
        mono = QFont(MONO_FONT)
        mono.setPixelSize(12)
        if t:
            p.setFont(mono)
            p.setPen(QColor(DIM))
            p.drawText(QPointF(x, base), t)
            x += QFontMetrics(mono).horizontalAdvance(t) + 12
        if tag:
            bf = QFont(o.font)
            bf.setPixelSize(12)
            bf.setBold(True)
            p.setFont(bf)
            p.setPen(QColor(col))
            p.drawText(QPointF(x, base), tag)
            x += QFontMetrics(bf).horizontalAdvance(tag) + 12
        nf = QFont(o.font)
        nf.setPixelSize(12)
        p.setFont(nf)
        p.setPen(QColor("#ffd5d8" if is_ad_row else TEXT))
        p.drawText(QPointF(x, base), QFontMetrics(nf).elidedText(txt, Qt.ElideRight, int(rect.right() - x - 8)))
        p.restore()


def feed_list():
    lw = QListWidget()
    lw.setObjectName("feed")
    lw.setItemDelegate(FeedDelegate(lw))
    lw.setMouseTracking(True)
    lw.setVerticalScrollMode(QListWidget.ScrollPerPixel)
    return lw


class GlowCard(QFrame):
    """Rounded dark card with a status-colored light spilling in from the left."""
    def __init__(self, color=ACC, clicked=None, parent=None):
        super().__init__(parent)
        self.glow_color = QColor(color)
        self.clicked_callback = clicked
        self._pressed = False
        self.setAttribute(Qt.WA_StyledBackground, False)
        if clicked:
            self.setCursor(Qt.PointingHandCursor)

    def setGlowColor(self, color):
        self.glow_color = QColor(color)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, 9, 9)
        p.setClipPath(path)
        if getattr(self, "overlay_style", False):
            p.fillPath(path, QColor(255, 255, 255, 20))
        else:
            p.fillPath(path, QColor("#151d27"))
        radius = max(80.0, rect.width() * 0.82)
        beam = QRadialGradient(QPointF(rect.left() + 7, rect.center().y()), radius)
        beam.setColorAt(0.0, QColor(self.glow_color.red(), self.glow_color.green(), self.glow_color.blue(), 126))
        beam.setColorAt(0.34, QColor(self.glow_color.red(), self.glow_color.green(), self.glow_color.blue(), 68))
        beam.setColorAt(1.0, QColor(self.glow_color.red(), self.glow_color.green(), self.glow_color.blue(), 0))
        p.fillRect(rect, beam)
        p.setClipping(False)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(255, 255, 255, 24), 1))
        p.drawPath(path)
        if getattr(self, "overlay_style", False):
            top = QLinearGradient(rect.topLeft(), rect.topRight())
            top.setColorAt(0, QColor(255, 255, 255, 0))
            top.setColorAt(0.5, QColor(255, 255, 255, 70))
            top.setColorAt(1, QColor(255, 255, 255, 0))
            p.setPen(QPen(QBrush(top), 1))
            p.drawLine(QPointF(rect.left() + 12, rect.top() + 0.5), QPointF(rect.right() - 12, rect.top() + 0.5))
        p.end()

    def mouseReleaseEvent(self, event):
        if self.clicked_callback and self._pressed and event.button() == Qt.LeftButton and self.rect().contains(event.pos()):
            self._pressed = False
            self.clicked_callback()
            event.accept()
            return
        self._pressed = False
        super().mouseReleaseEvent(event)

    def mousePressEvent(self, event):
        if self.clicked_callback and event.button() == Qt.LeftButton:
            self._pressed = True
            event.accept()
            return
        super().mousePressEvent(event)


class ScreenNotice(QWidget):
    def __init__(self):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(540, 104)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.panel = GlowCard(C_NEW)
        self.panel.setObjectName("screenNoticePanel")
        self.panel.setAttribute(Qt.WA_StyledBackground, True)
        content = QVBoxLayout(self.panel)
        content.setContentsMargins(16, 11, 16, 11)
        content.setSpacing(3)
        content.setAlignment(Qt.AlignTop)
        self.title_label = QLabel()
        self.title_label.setStyleSheet("background:transparent;border:none;color:#FFFFFF;font-size:14px;font-weight:700;")
        self.body_label = QLabel()
        self.body_label.setWordWrap(True)
        self.body_label.setStyleSheet(f"background:transparent;border:none;color:{MUTED};font-size:12px;font-weight:400;")
        self.body_scroll = QScrollArea()
        self.body_scroll.setFrameShape(QFrame.NoFrame)
        self.body_scroll.setWidgetResizable(True)
        self.body_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.body_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.body_scroll.setStyleSheet("QScrollArea{background:transparent;border:none;} QWidget{background:transparent;}")
        self.body_scroll.setWidget(self.body_label)
        content.addWidget(self.title_label, 0, Qt.AlignLeft | Qt.AlignTop)
        content.addWidget(self.body_scroll, 1)
        outer.addWidget(self.panel)
        self._notice_width = 540
        self._base_height = 104
        self._closing = False
        self.animation = QPropertyAnimation(self, b"geometry", self)
        self.animation.setDuration(260)
        self.animation.setEasingCurve(QEasingCurve.OutBack)
        self.animation.finished.connect(self._animation_finished)
        self.hide()
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.dismiss)

    def apply_size(self, width, height):
        width = max(280, min(800, int(width)))
        height = max(72, min(240, int(height)))
        self._notice_width, self._base_height = width, height
        self._resize_notice(height)

    def _resize_notice(self, height):
        height = max(self._base_height, int(height))
        self.setMinimumSize(self._notice_width, height)
        self.setMaximumSize(self._notice_width, height)
        self.resize(self._notice_width, height)
        self.panel.setMinimumSize(self._notice_width, height)
        self.panel.setMaximumSize(self._notice_width, height)
        self.panel.setGeometry(self.rect())
        self.body_scroll.setFixedHeight(max(28, height - 42))

    def _fit_to_text(self, body):
        screen = QApplication.primaryScreen()
        max_height = screen.availableGeometry().height() - 36 if screen else 760
        inner_width = max(120, self._notice_width - 36)
        bounds = self.body_label.fontMetrics().boundingRect(
            QRect(0, 0, inner_width, max_height * 2), Qt.TextWordWrap, body)
        natural_body_height = max(self.body_label.fontMetrics().height(), bounds.height())
        self._resize_notice(min(max_height, max(self._base_height, natural_body_height + 42)))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "panel"):
            self.panel.setGeometry(self.rect())

    def show_new_report(self):
        self.show_event("report", "Новий репорт!", "Відкрийте вкладку «Репорти», щоб відповісти.")

    def show_event(self, kind, title, body=""):
        self.animation.stop()
        self._closing = False
        accents = {"report": C_NEW, "form": C_DONE, "vip": C_BAD,
                   "vipad": C_BAD, "vip_possible": C_NEW, "ac": C_BAD,
                   "warning": C_BAD, "info": ACC, "ok": C_DONE, "mine": C_TAKEN}
        accent = accents.get(kind, ACC)
        self.title_label.setText(str(title))
        self.body_label.setText(str(body))
        self.body_label.setVisible(bool(body))
        self.body_scroll.setVisible(bool(body))
        self._fit_to_text(str(body))
        self.panel.setGlowColor(accent)
        screen = QApplication.primaryScreen()
        if screen:
            x = screen.availableGeometry().left() + 18
            y = screen.availableGeometry().top() + 18
        else:
            x, y = 18, 18
        end = QRect(x, y, self.width(), self.height())
        start = QRect(x, y - 24, self.width(), self.height())
        self.setGeometry(start)
        self.show()
        self.raise_()
        self.animation.setStartValue(start)
        self.animation.setEndValue(end)
        self.animation.start()
        self.timer.start(4200)

    def dismiss(self):
        if not self.isVisible():
            return
        self.animation.stop()
        self._closing = True
        start = self.geometry()
        end = QRect(start.x(), start.y() - 24, start.width(), start.height())
        self.animation.setStartValue(start)
        self.animation.setEndValue(end)
        self.animation.start()

    def _animation_finished(self):
        if self._closing:
            self.hide()


class DynamicIsland(QWidget):
    """Dynamic Island: капсула вистрибує зверху по центру екрана, показує подію 3 с і ховається."""
    HOLD_MS, MARGIN, TOP = 3000, 24, 8
    ACCENTS = {"report": "#27d9e8", "form": "#ff2fa8", "ok": "#ff2fa8", "reply": "#2f8bff", "action": "#b04dff",
               "mine": "#2f8bff", "ac": "#ff4d5e", "vipad": "#ff4d5e", "vip": "#ff4d5e", "warning": "#ff5a4d",
               "vip_possible": "#ffb020", "info": "#6ea8ff", "music": "#1ed760"}

    def __init__(self):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._e, self._closing = 0.0, False
        self._kind, self._lines, self._title = "info", [], ""
        self._maxw, self._base_h = 540, 68
        self._pw, self._ph, self._tw = 320, 68, 200
        self._logo_cache = {}
        self._t0 = QElapsedTimer()
        self._left = -1
        self.anim = QPropertyAnimation(self, b"expand", self)
        self.anim.finished.connect(self._anim_done)
        self.clock = QTimer(self)
        self.clock.setInterval(100)
        self.clock.timeout.connect(self._tick)
        self.hide()

    # --- властивість анімації (0 = крапелька, 1 = повна капсула, >1 = пружинний вихлест)
    def _get_e(self):
        return self._e

    def _set_e(self, v):
        self._e = v
        self.update()

    expand = Property(float, _get_e, _set_e)

    def _logo_for(self, size, dpr):
        """Логотип у фізичних пікселях екрана (без розмиття на HiDPI)."""
        key = (size, round(dpr, 2))
        pm = self._logo_cache.get(key)
        if pm is None:
            src = QPixmap(resource_path(os.path.join("assets", "yavir_icon.png")))
            if src.isNull():
                src = logo_pix(size * 4)
            box = int(src.width() * 0.84)                       # без зайвих полів: літери займають більше місця
            off = (src.width() - box) // 2
            src = src.copy(off, off, box, box)
            px = max(1, int(round(size * dpr)))
            img = src.scaled(px, px, Qt.KeepAspectRatio, Qt.SmoothTransformation).toImage().convertToFormat(QImage.Format_ARGB32)
            for yy in range(img.height()):                      # підсилюємо тонкі білі лінії, щоб не виглядали розмитими
                for xx in range(img.width()):
                    col = img.pixelColor(xx, yy)
                    v = min(255, int(col.red() * 2.4))
                    img.setPixelColor(xx, yy, QColor(v, v, v, 255))
            pm = QPixmap.fromImage(img)
            pm.setDevicePixelRatio(dpr)
            self._logo_cache[key] = pm
        return pm

    def apply_size(self, width, height):
        self._maxw = max(320, min(800, int(width)))
        self._base_h = max(46, min(100, int(int(height) * 0.5)))

    def show_new_report(self):
        self.show_event("report", "Новий репорт!", "")

    @staticmethod
    def _wrap(text, fm, width, max_lines):
        lines, cur, cut = [], "", False
        for w in text.split(" "):
            t = (cur + " " + w).strip()
            if fm.horizontalAdvance(t) <= width:
                cur = t
                continue
            if cur:
                lines.append(cur)
            cur = w
            if len(lines) >= max_lines:
                cut = True
                break
        if cur and not cut:
            lines.append(cur)
        if len(lines) > max_lines:
            lines, cut = lines[:max_lines], True
        lines = lines or [""]
        last = lines[-1]
        if cut:
            while last and fm.horizontalAdvance(last + "…") > width:
                last = last[:-1]
            last += "…"
        lines[-1] = fm.elidedText(last, Qt.ElideRight, width)
        return lines

    def _fonts(self):
        f1, f2 = QFont(self.font()), QFont(self.font())
        f1.setPixelSize(14)
        f1.setBold(True)
        f2.setPixelSize(12)
        for f in (f1, f2):
            f.setHintingPreference(QFont.PreferFullHinting)
        return f1, f2

    def show_event(self, kind, title, body=""):
        self._kind, self._title = kind, str(title)
        body = " ".join(str(body).split())
        f1, f2 = self._fonts()
        m1, m2 = QFontMetrics(f1), QFontMetrics(f2)
        pad, icon, gap, right = 14, 38, 11, 54
        avail = self._maxw - (pad * 2 + icon + gap * 3 + 1 + right)
        if body:
            self._lines = self._wrap(body, m2, avail, 4)
            natural = max(m1.horizontalAdvance(self._title), max(m2.horizontalAdvance(x) for x in self._lines))
            text_h = m1.height() + 2 + m2.height() * len(self._lines)
        else:
            self._lines = []
            natural = max(m1.horizontalAdvance(self._title), m2.horizontalAdvance("Yavir Tools"))
            text_h = m1.height() + 2 + m2.height()
        self._title = m1.elidedText(self._title, Qt.ElideRight, avail)
        self._tw = max(120, min(avail, natural))
        self._pw = pad * 2 + icon + gap * 3 + 1 + right + self._tw
        self._ph = max(self._base_h, text_h + 22)
        W, H = self._maxw + self.MARGIN * 2, self._ph + self.MARGIN * 2
        self.setFixedSize(W, H)
        scr = QApplication.primaryScreen()
        g = scr.availableGeometry() if scr else QRect(0, 0, 1920, 1080)
        self.move(g.center().x() - W // 2, g.top() + self.TOP - self.MARGIN)
        first = (not self.isVisible()) or self._closing
        self._closing = False
        self.anim.stop()
        self._e = 0.0 if first else 0.82
        self._t0.start()
        self._left = -1
        self.clock.start()
        self.show()
        self.raise_()
        curve = QEasingCurve(QEasingCurve.OutBack)
        curve.setOvershoot(1.25)
        self.anim.setEasingCurve(curve)
        self.anim.setDuration(460 if first else 380)
        self.anim.setStartValue(self._e)
        self.anim.setEndValue(1.0)
        self.anim.start()

    def dismiss(self):
        if not self.isVisible() or self._closing:
            return
        self._closing = True
        self.clock.stop()
        self.anim.stop()
        curve = QEasingCurve(QEasingCurve.InBack)
        curve.setOvershoot(0.9)
        self.anim.setEasingCurve(curve)
        self.anim.setDuration(300)
        self.anim.setStartValue(self._e)
        self.anim.setEndValue(0.0)
        self.anim.start()

    def _anim_done(self):
        if self._closing:
            self._closing = False
            self.hide()

    def _tick(self):
        if self._t0.elapsed() >= self.HOLD_MS:
            self.dismiss()
            return
        self.update()

    def mousePressEvent(self, event):
        self.dismiss()

    def hideEvent(self, event):
        self.clock.stop()
        super().hideEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        dpr = self.devicePixelRatioF()
        sn = lambda v: round(v * dpr) / dpr          # прив'язка до фізичних пікселів — чіткий текст і лінії
        e, M = self._e, self.MARGIN
        ea = max(0.0, min(1.0, e))
        acc = QColor(self.ACCENTS.get(self._kind, "#6ea8ff"))
        w = 100 + (self._pw - 100) * e
        h = 28 + (self._ph - 28) * e
        cx = self.width() / 2
        r = QRectF(cx - w / 2, M, w, h)
        rad = h / 2
        p.setBrush(Qt.NoBrush)
        for spread, alpha in ((16, 9), (11, 15), (7, 24), (4, 38)):      # м'яке неонове світіння
            c = QColor(acc)
            c.setAlpha(int(alpha * ea))
            p.setPen(QPen(c, spread))
            p.drawRoundedRect(r, rad, rad)
        body = QLinearGradient(r.topLeft(), r.bottomLeft())
        body.setColorAt(0, QColor(13, 17, 27))
        body.setColorAt(1, QColor(3, 5, 10))
        p.setPen(Qt.NoPen)
        p.setBrush(body)
        p.drawRoundedRect(r, rad, rad)
        edge = QLinearGradient(r.topLeft(), r.bottomLeft())
        top, mid = QColor(acc), QColor(acc)
        top.setAlpha(255)
        mid.setAlpha(120)
        edge.setColorAt(0, top)
        edge.setColorAt(0.5, mid)
        edge.setColorAt(1, top)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QBrush(edge), 1.7))
        p.drawRoundedRect(r.adjusted(0.8, 0.8, -0.8, -0.8), rad, rad)
        ca = max(0.0, min(1.0, (e - 0.55) / 0.45))
        if ca <= 0:
            return
        clip = QPainterPath()
        clip.addRoundedRect(r, rad, rad)
        p.setClipPath(clip)
        p.setOpacity(ca)
        pad, icon, gap = 14, 38, 11
        fx, cy = sn(cx - self._pw / 2), sn(M + self._ph / 2)
        ir = QRectF(fx + pad, sn(cy - icon / 2), icon, icon)
        if self._kind == "music":
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(5, 7, 12))
            p.drawRoundedRect(ir, 10, 10)
            t = self._t0.elapsed() / 180.0
            p.setBrush(acc)
            for i in range(4):
                bh = 8 + 18 * abs(math.sin(t + i * 1.3))
                p.drawRoundedRect(QRectF(ir.left() + 7 + i * 7, ir.center().y() - bh / 2, 4, bh), 2, 2)
        else:
            path = QPainterPath()
            path.addRoundedRect(ir, 10, 10)
            p.save()
            p.setClipPath(path, Qt.IntersectClip)
            p.drawPixmap(QPointF(ir.left(), ir.top()), self._logo_for(icon, dpr))
            p.restore()
            ring = QColor(acc)
            ring.setAlpha(110)
            p.setPen(QPen(ring, 1))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(ir, 10, 10)
        dx = ir.right() + gap
        dx = sn(dx)
        p.setPen(QPen(QColor(255, 255, 255, 70), 1))
        p.drawLine(QPointF(dx + 0.5 / dpr, cy - 15), QPointF(dx + 0.5 / dpr, cy + 15))
        tx = sn(dx + 1 + gap)
        f1, f2 = self._fonts()
        m1, m2 = QFontMetrics(f1), QFontMetrics(f2)
        if self._lines:
            th = m1.height() + 2 + m2.height() * len(self._lines)
            y = sn(cy - th / 2)
            p.setFont(f1)
            p.setPen(QColor("#ffffff"))
            p.drawText(QPointF(tx, y + m1.ascent()), self._title)
            p.setFont(f2)
            p.setPen(QColor(190, 200, 215))
            for i, line in enumerate(self._lines):
                p.drawText(QPointF(tx, y + m1.height() + 2 + m2.height() * i + m2.ascent()), line)
        else:
            th = m1.height() + 2 + m2.height()
            y = sn(cy - th / 2)
            p.setFont(f2)
            p.setPen(QColor(150, 162, 182))
            p.drawText(QPointF(tx, y + m2.ascent()), "Yavir Tools")
            p.setFont(f1)
            p.setPen(QColor("#ffffff"))
            p.drawText(QPointF(tx, y + m2.height() + 2 + m1.ascent()), self._title)
        secs = max(1, -(-(self.HOLD_MS - self._t0.elapsed()) // 1000))
        p.setFont(f2)
        p.setPen(QColor(170, 182, 205))
        p.drawText(QPointF(sn(fx + self._pw - pad - 16 - 10 - m2.horizontalAdvance(f"{secs}s")), sn(cy + m2.ascent() / 2 - 1)), f"{secs}s")
        xr = QRectF(fx + self._pw - pad - 13, cy - 5, 11, 11)
        p.setPen(QPen(QColor(255, 255, 255, 190), 1.8, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(xr.topLeft(), xr.bottomRight())
        p.drawLine(xr.topRight(), xr.bottomLeft())


class GameOverlayMenu(QWidget):
    """Compact Alt+Z control panel shown above the game window."""
    def __init__(self, core, navigate, open_report, game_running):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.core, self.navigate, self.open_report, self.game_running = core, navigate, open_report, game_running
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowTitle("Yavir Tools · Game Overlay")
        self.setFixedWidth(408)
        self._drag_offset = None
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        panel = QFrame()
        panel.setObjectName("overlayMenu")
        panel.setStyleSheet(f"QFrame#overlayMenu{{background:{SURF};border:1px solid #34465d;border-radius:16px;}}")
        outer.addWidget(panel)
        box = QVBoxLayout(panel)
        box.setContentsMargins(15, 13, 15, 13)
        box.setSpacing(9)
        self.drag_header = QWidget()
        self.drag_header.setCursor(Qt.SizeAllCursor)
        self.drag_header.installEventFilter(self)
        head = QHBoxLayout(self.drag_header)
        head.setContentsMargins(0, 0, 0, 0)
        logo = QLabel(); logo.setPixmap(logo_pix(34)); logo.setFixedSize(34, 34)
        logo.setAttribute(Qt.WA_TransparentForMouseEvents)
        head.addWidget(logo)
        titles = QVBoxLayout(); titles.setSpacing(0)
        title_label = lab("YAVIR TOOLS", "brand")
        sub_label = lab("Ігрова панель  ·  Alt+Z  ·  перетягніть шапку", "brandsub")
        title_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        sub_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        titles.addWidget(title_label)
        titles.addWidget(sub_label)
        head.addLayout(titles, 1)
        close = QPushButton("×"); close.setObjectName("ghost"); close.setFixedSize(34, 30)
        close.clicked.connect(self.hide_animated); head.addWidget(close)
        box.addWidget(self.drag_header)
        self.game_label = lab("○  Гра не запущена", "muted")
        box.addWidget(self.game_label)
        self.norm_label = lab("Норма: —", "hint")
        box.addWidget(self.norm_label)
        self.norm_progress = QProgressBar()
        self.norm_progress.setRange(0, 1000)
        self.norm_progress.setTextVisible(False)
        self.norm_progress.setFixedHeight(7)
        self.norm_progress.setStyleSheet(
            "QProgressBar{background:#252f3d;border:0;border-radius:3px;}"
            f"QProgressBar::chunk{{background:{ACC};border-radius:3px;}}"
        )
        box.addWidget(self.norm_progress)
        self.music_label = lab("♫  Spotify: не відтворюється", "hint", True)
        box.addWidget(self.music_label)
        stats = QGridLayout(); stats.setSpacing(8)
        self.stat_labels = []
        for i, (title, color) in enumerate((("Репорти", C_NEW), ("Форми", C_DONE), ("VIP", "#F3B34C"), ("Античіт", C_BAD))):
            tile = QFrame(); tile.setObjectName("overlayStatTile")
            v = QVBoxLayout(tile); v.setContentsMargins(11, 8, 11, 8); v.setSpacing(1)
            v.addWidget(lab(title, "hint"))
            value = lab("0", "title"); value.setStyleSheet(f"font-size:20px;font-weight:700;color:{color};")
            v.addWidget(value); stats.addWidget(tile, i // 2, i % 2); self.stat_labels.append(value)
        box.addLayout(stats)
        box.addWidget(lab("ОСТАННІ РЕПОРТИ", "hint"))
        self.report_scroll = QScrollArea()
        self.report_scroll.setWidgetResizable(True)
        self.report_scroll.setFrameShape(QFrame.NoFrame)
        self.report_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.report_scroll.setFixedHeight(214)
        self.report_scroll.setStyleSheet("QScrollArea{background:transparent;border:none;} QWidget#recentReports{background:transparent;}")
        self.report_widget = QWidget()
        self.report_widget.setObjectName("recentReports")
        self.report_rows = QVBoxLayout(self.report_widget)
        self.report_rows.setContentsMargins(0, 0, 0, 0)
        self.report_rows.setSpacing(6)
        self._reports_signature = None
        self.report_scroll.setWidget(self.report_widget)
        box.addWidget(self.report_scroll)
        self.recent = lab("Очікування подій…", "hint", True)
        self.recent.setObjectName("overlayLatest")
        self.recent.setWordWrap(True); self.recent.setMinimumHeight(34); self.recent.setMaximumHeight(52)
        self.latest = ""
        box.addWidget(self.recent)
        actions = QGridLayout(); actions.setSpacing(8)
        for i, (title, page) in enumerate((("Дашборд", 0), ("Репорти", 1), ("Користувачі", 2),
                                           ("VIP чат", 3), ("Бінди", 4), ("Адмін ПО", 5),
                                           ("Форми покарань", 6), ("Розгляд скарги", 7))):
            button = QPushButton(title); button.setObjectName("primary" if i == 0 else "ghost")
            button.clicked.connect(lambda _=False, page=page: self._open_page(page))
            actions.addWidget(button, i // 2, i % 2)
        box.addLayout(actions)
        self.opacity = QGraphicsOpacityEffect(self); self.setGraphicsEffect(self.opacity)
        self.anim = QPropertyAnimation(self.opacity, b"opacity", self)
        self.anim.setDuration(170); self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.is_open = False
        self.refresh()

    def refresh(self, latest=""):
        if latest:
            self.latest = latest
        stats = self.core.stats
        for label, key in zip(self.stat_labels, ("reports", "forms", "ads", "ac")):
            label.setText(str(stats.get(key, 0)))
        self.game_label.setText("●  Гра запущена" if self.game_running() else "○  Гра не запущена")
        norm_total = max(1, int(float(self.core.cfg.get("norm_hours", 4)) * 3600))
        norm_done = max(0, int(self.core.cfg.get("norm_seconds", 0)))
        norm = max(0, norm_total - norm_done)
        waiting = sum(1 for r in self.core.reports if r.get("status") not in ("Відповів", "Колега відповів"))
        self.norm_label.setText(f"До норми {fmt(norm)}   ·   В черзі {waiting}")
        self.norm_progress.setValue(min(1000, int(norm_done * 1000 / norm_total)))
        signature = tuple((r["rid"], r.get("status"), r.get("unanswered"), r.get("text")) for r in self.core.reports[:3])
        if signature != self._reports_signature:
            self._reports_signature = signature
            while self.report_rows.count():
                item = self.report_rows.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
            if not self.core.reports:
                empty = lab("Поки що репортів немає", "hint")
                empty.setAlignment(Qt.AlignCenter)
                self.report_rows.addWidget(empty)
            else:
                for report in self.core.reports[:3]:
                    self.report_rows.addWidget(self._report_card(report))
            self.report_rows.addStretch(1)
        if self.latest:
            self.recent.setText(self.latest)
        elif self.core.reports:
            r = self.core.reports[0]
            self.recent.setText(f"Останній репорт · {r['name']}: {r['text']}")
        if self.is_open:
            self.adjustSize()

    def _report_card(self, report):
        color = report_color(report)
        row = GlowCard(color, clicked=lambda r=report: self.open_report(r))
        layout = QVBoxLayout(row)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(2)
        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        _pid = str(report.get("id", ""))
        _newbie = any(_pid.startswith(pfx) for pfx in ("691", "692"))
        name_text = (f"{report.get('name', 'Гравець')} [{_pid}]"
                     + ("  ★ Новачок" if _newbie else ""))
        name = QLabel()
        name.setStyleSheet("background:transparent;color:#f3f6fb;font-size:12px;font-weight:700;")
        name.setAttribute(Qt.WA_TransparentForMouseEvents)
        name.setMinimumWidth(0)
        name.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        name.setToolTip(name_text)
        name_font = name.font()
        name.setText(QFontMetrics(name_font).elidedText(name_text, Qt.ElideRight, 178))
        top.addWidget(name, 1)
        state = QLabel(report_visual_status(report).upper())
        state.setStyleSheet(f"background:transparent;color:{color};font-size:9px;font-weight:700;")
        state.setAttribute(Qt.WA_TransparentForMouseEvents)
        top.addWidget(state)
        stamp = QLabel(str(report.get("time", "")))
        stamp.setStyleSheet(f"background:transparent;color:{MUTED};font-size:9px;")
        stamp.setAttribute(Qt.WA_TransparentForMouseEvents)
        top.addWidget(stamp)
        layout.addLayout(top)
        message_text = notification_text(report["text"], limit=None)
        message = QLabel()
        message.setText(QFontMetrics(message.font()).elidedText(message_text, Qt.ElideRight, 348))
        message.setStyleSheet(f"background:transparent;color:{MUTED};font-size:11px;")
        message.setAttribute(Qt.WA_TransparentForMouseEvents)
        message.setMinimumWidth(0)
        message.setToolTip(message_text)
        layout.addWidget(message)
        row.setFixedHeight(52)
        row.setToolTip(f"{report_visual_status(report)} · {name_text} · {report.get('time', '')}\n{message_text}")
        return row

    def set_music(self, data):
        if data.get("playing"):
            self.music_label.setText(f"♫  {data.get('artist', '')} — {data.get('title', 'Spotify')}")
        else:
            self.music_label.setText("♫  Spotify: не відтворюється")

    def toggle(self):
        if self.is_open:
            self.hide_animated()
        else:
            self.refresh()
            self.adjustSize()
            screen = QApplication.primaryScreen()
            if screen:
                area = screen.availableGeometry()
                saved_x = int(self.core.cfg.get("game_overlay_x", -1))
                saved_y = int(self.core.cfg.get("game_overlay_y", 28))
                x = saved_x if saved_x >= 0 else area.center().x() - self.width() // 2
                self.move(max(area.left(), min(x, area.right() - self.width() + 1)),
                          max(area.top(), min(saved_y, area.bottom() - self.height() + 1)))
            try: self.anim.finished.disconnect(self._finish_hide)
            except Exception: pass
            self.opacity.setOpacity(0.0); self.show(); self.raise_()
            self.anim.stop(); self.anim.setStartValue(0.0); self.anim.setEndValue(1.0); self.anim.start()
            self.is_open = True

    def hide_animated(self):
        if not self.is_open: return
        self.anim.stop(); self.anim.setStartValue(self.opacity.opacity()); self.anim.setEndValue(0.0)
        try: self.anim.finished.disconnect()
        except Exception: pass
        self.anim.finished.connect(self._finish_hide)
        self.anim.start()

    def _finish_hide(self):
        self.hide(); self.is_open = False

    def _open_page(self, page):
        self.navigate(page); self.hide_animated()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide_animated()
            event.accept()
            return
        super().keyPressEvent(event)

    def eventFilter(self, watched, event):
        if watched is self.drag_header:
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                watched.grabMouse()
                return True
            if event.type() == QEvent.MouseMove and self._drag_offset is not None and event.buttons() & Qt.LeftButton:
                self.move(event.globalPosition().toPoint() - self._drag_offset)
                return True
            if event.type() == QEvent.MouseButtonRelease and self._drag_offset is not None:
                self._drag_offset = None
                watched.releaseMouse()
                self.core.cfg["game_overlay_x"], self.core.cfg["game_overlay_y"] = self.x(), self.y()
                save_cfg(self.core.cfg)
                return True
        return super().eventFilter(watched, event)


class Toast(QLabel):
    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("toast")
        self.hide()
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide)

    def show_text(self, text):
        self.setText(text)
        self.adjustSize()
        self.place()
        self.show()
        self.raise_()
        self.timer.start(2200)

    def place(self):
        p = self.parentWidget()
        self.move(p.width() - self.width() - 28, p.height() - self.height() - 28)


# ---------------------------------------------------------------- сторінки
class DashboardHeader(QWidget):
    def __init__(self, game_status, parent=None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(16)
        brand = QLabel()
        brand.setPixmap(brand_pix(330))
        brand.setFixedSize(330, 72)
        brand.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        row.addWidget(brand)
        text = QVBoxLayout()
        text.setSpacing(1)
        self.subtitle = lab("Панель адміністратора", "dashBrandSub")
        self.subtitle.setStyleSheet(f"font-family:'{HEAD_FONT}';font-size:26px;font-weight:600;color:#9fb0cc;")
        self.subtitle.setTextFormat(Qt.RichText)
        text.addWidget(self.subtitle)
        row.addLayout(text)
        row.addStretch(1)
        row.addWidget(game_status, 0, Qt.AlignRight | Qt.AlignVCenter)

    def set_sub(self, text):
        self.subtitle.setText(text)

    def set_greeting(self, name):
        from html import escape
        name = (name or "").strip()
        self.subtitle.setText(f"Вітаємо, <span style='color:#ffffff;font-weight:700;'>{escape(name)}</span>" if name else "Вітаємо!")


class Dashboard(QWidget):
    shift_toggle = Signal()

    def __init__(self, core):
        super().__init__()
        self.core = core
        lay = page_layout(self)
        self.game = QLabel()
        self.head = DashboardHeader(self.game)
        lay.addWidget(self.head)

        body = QHBoxLayout()
        body.setSpacing(18)
        lay.addLayout(body, 1)

        # ліва колонка: норма + черга
        left = QVBoxLayout()
        left.setSpacing(18)
        n = card()
        n.setFixedWidth(310)
        nv = QVBoxLayout(n)
        nv.setContentsMargins(20, 18, 20, 18)
        nv.setSpacing(6)
        nv.addWidget(lab("Норма за сьогодні", "h2"))
        self.ring = Ring()
        nv.addWidget(self.ring)
        self.norm_s = lab("", "muted")
        self.norm_s.setAlignment(Qt.AlignCenter)
        nv.addWidget(self.norm_s)
        self.shift_btn = QPushButton("Почати зміну")
        self.shift_btn.setObjectName("primary")
        self.shift_btn.setMinimumHeight(38)
        self.shift_btn.setCursor(Qt.PointingHandCursor)
        self.shift_btn.clicked.connect(self.shift_toggle.emit)
        nv.addWidget(self.shift_btn)
        self._shift_active = None
        left.addWidget(n)
        q = card()
        q.setFixedWidth(310)
        qv = QVBoxLayout(q)
        qv.setContentsMargins(14, 16, 14, 12)
        qh = QHBoxLayout()
        qh.setContentsMargins(6, 0, 6, 0)
        qh.addWidget(lab("Очікують відповіді", "h2"))
        qv.addLayout(qh)
        self.pend = QListWidget()
        self.pend.setObjectName("rlist")
        self.pend.setItemDelegate(ReportDelegate(self.pend))
        self.pend.setMouseTracking(True)
        self.pend.itemClicked.connect(lambda it: self.open_report(it))
        qv.addWidget(with_empty(self.pend, "Усі репорти опрацьовано"), 1)
        left.addWidget(q, 1)
        body.addLayout(left)

        # права колонка: лічильники + стрічка
        right = QVBoxLayout()
        right.setSpacing(18)
        tiles = QHBoxLayout()
        tiles.setSpacing(18)
        self.c_rep, self.c_form, self.c_ad = (lab("0", "big") for _ in range(3))
        for title, hint, w, col in (("Репортів за сесію", "отримано з чату", self.c_rep, C_NEW),
                                    ("Форм прийнято", "авто та вручну", self.c_form, C_DONE),
                                    ("Реклам у VIP", "виявлено", self.c_ad, C_BAD)):
            c = card()
            v = QVBoxLayout(c)
            v.setContentsMargins(20, 16, 20, 16)
            v.setSpacing(0)
            v.addWidget(lab(title, "muted"))
            w.setStyleSheet(f"color:{col};")
            v.addWidget(w)
            v.addWidget(lab(hint, "hint"))
            tiles.addWidget(c)
        right.addLayout(tiles)
        shift_card = card()
        shift_card.setProperty("thin", True)
        shift_layout = QHBoxLayout(shift_card)
        shift_layout.setContentsMargins(18, 10, 18, 10)
        shift_layout.setSpacing(14)
        shift_layout.addWidget(lab("Статистика зміни", "h2"))
        shift_layout.addStretch(1)
        self.btn_report = QPushButton("Копіювати звіт зміни")
        self.btn_report.setObjectName("ghost")
        self.btn_report.setCursor(Qt.PointingHandCursor)
        self.btn_report.clicked.connect(self.copy_shift_report)
        shift_layout.addWidget(self.btn_report)
        self.c_reply = lab("0", "title")
        self.c_punishment = lab("0", "title")
        for caption, value, color in (("Відповідей", self.c_reply, ACC_H),
                                      ("Покарань", self.c_punishment, C_BAD)):
            value.setStyleSheet(f"font-size:18px;font-weight:700;color:{color};")
            shift_layout.addWidget(lab(caption, "hint"))
            shift_layout.addWidget(value)
        right.addWidget(shift_card)
        f = card()
        fv = QVBoxLayout(f)
        fv.setContentsMargins(14, 16, 14, 12)
        fh = QHBoxLayout()
        fh.setContentsMargins(6, 0, 6, 0)
        fh.addWidget(lab("Остання активність", "h2"))
        fv.addLayout(fh)
        self.act = feed_list()
        fv.addWidget(with_empty(self.act, "Подій поки немає. Тут з'являтимуться спрацювання античіта, форми та порушення."), 1)
        right.addWidget(f, 1)
        body.addLayout(right, 1)

        core.stats_changed.connect(self.refresh)
        core.reports_changed.connect(self.refresh)
        core.event.connect(self.on_event)
        self.go_reports = None
        self._dirty = True
        self._recent_events = collections.deque(maxlen=100)
        self.refresh()

    def showEvent(self, event):
        super().showEvent(event)
        if getattr(self, "_dirty", False):
            self.refresh()
            self._dirty = False
            self.act.clear()
            for tag, text, col in self._recent_events:
                add_feed(self.act, tag, text, col, 100)

    def open_report(self, it):
        r = it.data(ROLE)
        if r:
            self.core.selected = r["rid"]
            self.core.reports_changed.emit()
            if self.go_reports:
                self.go_reports()

    EV = {"ac": ("Античіт", C_BAD), "bad": ("Слово", C_NEW), "vipviol": ("VIP", C_ADMIN),
          "repviol": ("Репорт", C_NEW), "form": ("ФОРМА", C_DONE), "info": ("Інфо", MUTED)}

    def on_event(self, kind, text):
        tag, col = self.EV.get(kind, ("", MUTED))
        self._recent_events.append((tag, text, col))
        if self.isVisible():
            add_feed(self.act, tag, text, col, 100)
        else:
            self._dirty = True

    def refresh(self):
        if not self.isVisible():
            self._dirty = True
            return
        c = self.core
        self.head.set_greeting(c.cfg["admin_name"])
        s = c.stats
        self.c_rep.setText(str(s["reports"]))
        self.c_form.setText(str(s["forms"]))
        self.c_ad.setText(str(s["ads"]))
        self.c_reply.setText(str(s.get("replies", 0)))
        self.c_punishment.setText(str(s.get("punishments", 0)))
        self.pend.clear()
        for r in c.reports:
            if r["status"] == "Новий":
                it = QListWidgetItem()
                it.setData(ROLE, dict(r))
                it.setToolTip(r["text"])
                self.pend.addItem(it)
        self._dirty = False

    def shift_report_text(self):
        c, s = self.core.cfg, self.core.stats
        secs, norm = int(c.get("norm_seconds", 0)), int(c.get("norm_hours", 4.0) * 3600)
        pending = [r for r in self.core.reports if r["status"] != "Відповів"]
        top = collections.Counter(r["name"] for r in self.core.reports).most_common(3)
        lines = [f"Звіт зміни · {datetime.date.today().strftime('%d.%m.%Y')} · {c.get('admin_name', '')}",
                 f"Відіграно: {fmt(secs)} з {fmt(norm)}" + (" (норму виконано)" if secs >= norm else f" (залишилось {fmt(norm - secs)})"),
                 f"Репортів: {s['reports']} · відповідей: {s.get('replies', 0)} · форм: {s['forms']} · покарань: {s.get('punishments', 0)}",
                 f"Античіт: {s.get('ac', 0)} · реклама у VIP: {s['ads']} · без відповіді: {len(pending)}"]
        if top:
            lines.append("Найактивніші за репортами: " + ", ".join(f"{n} ({k})" for n, k in top))
        return "\n".join(lines)

    def copy_shift_report(self):
        QApplication.clipboard().setText(self.shift_report_text())
        self.btn_report.setText("Скопійовано ✔")
        QTimer.singleShot(1600, lambda: self.btn_report.setText("Копіювати звіт зміни"))

    def set_shift_state(self, active):
        if active == self._shift_active:
            return
        self._shift_active = active
        self.shift_btn.setText("Завершити зміну" if active else "Почати зміну")
        self.shift_btn.setObjectName("danger" if active else "primary")
        repolish(self.shift_btn)

    def tick(self, running, secs, norm, active=True):
        self.set_shift_state(active)
        set_pill(self.game, "●  Гра запущена" if running else "○  Гру не запущено", C_DONE if running else DIM)
        left = norm - secs
        frac = min(1.0, secs / norm) if norm else 0.0
        if left > 0:
            self.ring.set(frac, fmt(left), "залишилось до норми")
        else:
            self.ring.set(1.0, "Готово", "норму виконано")
        if active:
            self.norm_s.setText(f"Відіграно {fmt(secs)} з {fmt(norm)}")
        else:
            self.norm_s.setText("Зміну не розпочато" if secs == 0 else f"Пауза · відіграно {fmt(secs)} з {fmt(norm)}")


class QuickBindButton(QPushButton):
    """Compact shortcut badge plus a correctly elided bind preview."""
    def __init__(self, keys, message, parent=None):
        super().__init__(parent)
        self.keys = keys
        self.message = message
        self.setText("")
        self.setMinimumWidth(0)
        self.setMinimumHeight(38)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setToolTip(f"{keys}\n{message}")
        row = QHBoxLayout(self)
        row.setContentsMargins(10, 4, 10, 4)
        row.setSpacing(8)
        self.key_badge = QLabel(keys.upper())
        self.key_badge.setObjectName("bindKey")
        self.key_badge.setAlignment(Qt.AlignCenter)
        self.key_badge.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.key_badge.setFixedWidth(max(44, QFontMetrics(self.font()).horizontalAdvance(keys.upper()) + 14))
        self.message_label = QLabel()
        self.message_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.message_label.setStyleSheet(f"color:{TEXT}; background:transparent; font-size:11px;")
        self.message_label.setMinimumWidth(0)
        self.message_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        row.addWidget(self.key_badge)
        row.addWidget(self.message_label, 1)
        self._refresh_label()

    def _refresh_label(self):
        if not hasattr(self, "message_label"):
            return
        available = max(24, self.message_label.width())
        self.message_label.setText(QFontMetrics(self.message_label.font()).elidedText(
            self.message, Qt.ElideRight, available))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_label()


class ResponsiveButtonGrid(QWidget):
    """Button grid that reduces its column count as its card gets narrower."""
    def __init__(self, min_cell_width=250, spacing=8, parent=None):
        super().__init__(parent)
        self.min_cell_width = min_cell_width
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(spacing)
        self._buttons = []
        self._column_count = 0

    def addWidget(self, widget, *_position):
        if widget not in self._buttons:
            widget.setMinimumWidth(0)
            self._buttons.append(widget)
        self._relayout()

    def clear(self):
        for widget in self._buttons:
            self.grid.removeWidget(widget)
        self._buttons.clear()

    def _relayout(self):
        if not hasattr(self, "grid"):
            return
        spacing = max(0, self.grid.horizontalSpacing())
        columns = max(1, min(len(self._buttons),
                             (max(1, self.width()) + spacing) // (self.min_cell_width + spacing)))
        for col in range(self._column_count):
            self.grid.setColumnStretch(col, 0)
        while self.grid.count():
            self.grid.takeAt(0)
        for index, button in enumerate(self._buttons):
            self.grid.addWidget(button, index // columns, index % columns)
        for col in range(columns):
            self.grid.setColumnStretch(col, 1)
        self._column_count = columns

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._relayout()


class ReportsPage(QWidget):
    def __init__(self, core):
        super().__init__()
        self.core = core
        self.workers = []
        self.filter = "all"
        self._test_report = None
        lay = page_layout(self, 16)
        self.head = PageHead("Репорти", "Нові репорти з'являються автоматично з чату гри.")
        lay.addWidget(self.head)
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setObjectName("reportSplitter")
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(8)
        self.splitter.setOpaqueResize(True)
        lay.addWidget(self.splitter, 1)

        list_panel = QWidget()
        # Keep the report cards readable when the detail pane is resized.
        list_panel.setMinimumWidth(350)
        left = QVBoxLayout(list_panel)
        left.setContentsMargins(0, 0, 6, 0)
        left.setSpacing(10)
        seg = QHBoxLayout()
        seg.setSpacing(6)
        grp = QButtonGroup(self)
        self.b_all, self.b_new = QPushButton("Усі"), QPushButton("Нові")
        for b, key in ((self.b_all, "all"), (self.b_new, "new")):
            b.setObjectName("seg")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            grp.addButton(b)
            b.clicked.connect(lambda _=False, k=key: self.set_filter(k))
            seg.addWidget(b)
        self.b_all.setChecked(True)
        seg.addStretch(1)
        self.clear_btn = QPushButton("Очистити репорти")
        self.clear_btn.setObjectName("danger")
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.clicked.connect(self.clear_reports)
        seg.addWidget(self.clear_btn)
        left.addLayout(seg)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Пошук за гравцем, ID або текстом репорту…")
        self.search.setClearButtonEnabled(True)
        self.search.setFixedHeight(40)
        self.search.textChanged.connect(self.refresh)
        QShortcut(QKeySequence("Ctrl+F"), self, activated=self.search.setFocus)
        left.addWidget(self.search)
        self.lst = QListWidget()
        self.lst.setObjectName("rlist")
        self.lst.setItemDelegate(ReportDelegate(self.lst))
        self.lst.setMouseTracking(True)
        self.lst.setMinimumWidth(330)
        self.lst.currentItemChanged.connect(self.select)
        left.addWidget(with_empty(self.lst, "Репортів поки немає.\nВони з'являться тут, щойно надійдуть у чат."), 1)
        self.splitter.addWidget(list_panel)

        self.rs = QStackedWidget()
        self.rs.setMinimumWidth(520)
        emp = card()
        ev = QVBoxLayout(emp)
        e = lab("Оберіть репорт зліва,\nщоб відповісти гравцю", "empty")
        e.setAlignment(Qt.AlignCenter)
        ev.addWidget(e)
        self.rs.addWidget(emp)

        det = card()
        dv = QVBoxLayout(det)
        dv.setContentsMargins(18, 16, 18, 14)
        dv.setSpacing(9)
        hero = QFrame()
        hero.setObjectName("reportHero")
        hv = QHBoxLayout(hero)
        hv.setContentsMargins(16, 13, 16, 13)
        hv.setSpacing(13)
        self.avatar = lab("", "avatar")
        self.avatar.setFixedSize(48, 48)
        self.avatar.setAlignment(Qt.AlignCenter)
        self.avatar.setStyleSheet("border-radius:24px; font-size:19px; border:1px solid #46618a;")
        hv.addWidget(self.avatar)
        tv = QVBoxLayout()
        tv.setSpacing(3)
        self.title = lab("", "reportIdentity")
        tv.addWidget(self.title)
        meta_row = QHBoxLayout()
        meta_row.setSpacing(7)
        self.report_id = lab("ID —", "reportId")
        self.meta = lab("", "reportMeta")
        meta_row.addWidget(self.report_id, 0, Qt.AlignLeft)
        meta_row.addWidget(self.meta, 0, Qt.AlignVCenter)
        meta_row.addStretch(1)
        tv.addLayout(meta_row)
        hv.addLayout(tv, 1)
        self.pill = QLabel()
        hv.addWidget(self.pill, 0, Qt.AlignVCenter)
        dv.addWidget(hero)

        quote = QFrame()
        quote.setObjectName("reportMessage")
        qv = QVBoxLayout(quote)
        qv.setContentsMargins(17, 12, 17, 15)
        qv.setSpacing(7)
        qv.addWidget(lab("ТЕКСТ РЕПОРТУ", "reportEyebrow"))
        self.text = lab("", "reporttext", True)
        self.text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.text.setWordWrap(True)
        qv.addWidget(self.text)
        dv.addWidget(quote)
        self.player_report_count = lab("", "playerReportCount")
        dv.addWidget(self.player_report_count)
        self.player_report_count.hide()
        self.flag = lab("", "warnbar", True)
        dv.addWidget(self.flag)
        bind_head = QHBoxLayout()
        bind_head.addWidget(lab("Швидкі відповіді", "h2"))
        bind_head.addStretch(1)
        bind_hint = lab("Натисніть, щоб вставити", "hint")
        bind_head.addWidget(bind_hint)
        dv.addLayout(bind_head)
        self.binds = ResponsiveButtonGrid(min_cell_width=250, spacing=8)
        dv.addWidget(self.binds)
        self.command_buttons = ResponsiveButtonGrid(min_cell_width=190, spacing=8)
        self.command_heading = lab("Команди", "h2")
        dv.addWidget(self.command_heading)
        dv.addWidget(self.command_buttons)
        reply_head = QHBoxLayout()
        reply_head.addWidget(lab("Відповідь", "h2"))
        reply_head.addStretch(1)
        reply_head.addWidget(lab("Текст можна відредагувати перед відправкою", "hint"))
        dv.addLayout(reply_head)
        self.reply = QTextEdit()
        self.reply.setPlaceholderText("Напишіть відповідь або оберіть швидку вище…")
        self.reply.setFixedHeight(82)
        self.reply_max_chars = 110
        self._reply_clamping = False
        self._reply_last_valid_text = ""
        self.reply.textChanged.connect(self.limit_reply_input)
        dv.addWidget(self.reply)
        counter_row = QHBoxLayout()
        counter_row.setContentsMargins(0, -5, 0, 0)
        counter_row.addStretch(1)
        self.reply_counter = lab("0/110", "charCounter")
        counter_row.addWidget(self.reply_counter)
        dv.addLayout(counter_row)
        self.update_reply_counter()
        r1 = QHBoxLayout()
        r1.setSpacing(8)
        for txt, name, fn in (("Надіслати", "primary", self.send), ("ШІ-відповідь", None, self.ai)):
            b = QPushButton(txt)
            if name:
                b.setObjectName(name)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(fn)
            r1.addWidget(b)
        r1.addStretch(1)
        self.ai_note = lab("", "hint", True)
        r1.addWidget(self.ai_note, 0, Qt.AlignRight | Qt.AlignVCenter)
        self.ai_loading_timer = QTimer(self)
        self.ai_loading_timer.timeout.connect(self.animate_ai_loading)
        self.ai_loading_dots = 0
        self.ai_type_timer = QTimer(self)
        self.ai_type_timer.timeout.connect(self.animate_ai_result)
        self.ai_result_text = ""
        self.ai_result_pos = 0
        dv.addLayout(r1)
        dv.addStretch(1)
        dv.addWidget(sep())
        dv.addWidget(lab("ДОДАТКОВІ ДІЇ", "reportEyebrow"))
        r2 = QHBoxLayout()
        r2.setSpacing(8)
        for txt, fn in (("Вставити /pm ID", self.take), ("Слідкувати", self.spectate),
                        ("Телепортуватися", self.warp), ("В адмін-чат", self.admin)):
            b = QPushButton(txt)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(fn)
            r2.addWidget(b)
        r2.addStretch(1)
        dv.addLayout(r2)
        r3 = QHBoxLayout()
        r3.setSpacing(8)
        for txt, fn in (("Відповідь колеги", self.insert_colleague_reply),
                        ("Скопіювати репорт", self.copy_report)):
            b = QPushButton(txt)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(fn)
            r3.addWidget(b)
        r3.addStretch(1)
        rm = QPushButton("Прибрати")
        rm.setObjectName("danger")
        rm.setCursor(Qt.PointingHandCursor)
        rm.clicked.connect(self.remove)
        r3.addWidget(rm)
        dv.addLayout(r3)
        self.rs.addWidget(det)
        self.splitter.addWidget(self.rs)
        sizes = self.core.cfg.get("report_splitter_sizes", [370, 860])
        try:
            sizes = [max(350, int(sizes[0])), max(520, int(sizes[1]))]
        except (TypeError, ValueError, IndexError):
            sizes = [370, 860]
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes(sizes)
        self.splitter.splitterMoved.connect(self.save_splitter_sizes)

        core.reports_changed.connect(self.refresh)
        self._dirty = True
        self.rebuild_binds()
        self.refresh()

    def showEvent(self, event):
        super().showEvent(event)
        if getattr(self, "_dirty", False):
            self.refresh()


    def set_filter(self, k):
        self.filter = k
        self.refresh()

    def save_splitter_sizes(self, *_):
        self.core.cfg["report_splitter_sizes"] = self.splitter.sizes()

    def rebuild_binds(self):
        for i in range(self.binds.grid.count()):
            w = self.binds.grid.itemAt(i).widget()
            if w:
                w.deleteLater()
        self.binds.clear()
        for i, b in enumerate(self.core.cfg["binds"][:max(0, int(self.core.cfg.get("quick_binds_count", 6)))]):
            btn = QuickBindButton(b.get("keys") or "None", b["text"])
            btn.setObjectName("chip")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _=False, t=b["text"]: self.allow("rep_quick") and self.reply.setPlainText(self.core.render(t, self.cur())))
            self.binds.addWidget(btn)
        for i in range(self.command_buttons.grid.count()):
            w = self.command_buttons.grid.itemAt(i).widget()
            if w:
                w.deleteLater()
        self.command_buttons.clear()
        commands = self.core.cfg.get("commands", [])
        self.command_heading.setVisible(bool(commands))
        for i, command in enumerate(commands):
            name = (command.get("name") or f"Команда {i + 1}").strip()
            btn = QPushButton(name)
            btn.setObjectName("chip")
            btn.setToolTip(command.get("text", ""))
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _=False, t=command.get("text", ""): self.insert_command(t))
            self.command_buttons.addWidget(btn)
        self.apply_access()

    def insert_command(self, template):
        if not self.allow("rep_commands"):
            return
        r = self.cur()
        self.reply.setPlainText(self.core.render(template, r))
        self.reply.setFocus()

    def cur(self):
        it = self.lst.currentItem()
        if not it:
            return None
        row_data = it.data(ROLE)
        if isinstance(row_data, dict) and row_data.get("test_preview"):
            return row_data
        return self.core.by_rid(it.data(Qt.UserRole))

    def show_test_report(self, name, player_id, text):
        self._test_report = {
            "rid": "__settings_test_report__",
            "name": (name or "").strip() or "Тестовий гравець",
            "id": (player_id or "").strip() or "123456",
            "text": (text or "").strip() or "Тестовий репорт",
            "time": datetime.datetime.now().strftime("%H:%M:%S"),
            "status": "Тест", "unanswered": True, "flags": [],
            "colleague_reply": "", "colleague_admin": "", "test_preview": True,
        }
        self.refresh()
        for row in range(self.lst.count()):
            item = self.lst.item(row)
            if item.data(Qt.UserRole) == "__settings_test_report__":
                self.lst.setCurrentItem(item)
                break

    def clear_test_report(self):
        if self.cur() and self.cur().get("test_preview"):
            self.lst.setCurrentRow(-1)
        self._test_report = None
        self.refresh()

    def refresh(self):
        if not self.isVisible():
            self._dirty = True
            return
        current = self.cur()
        keep = current["rid"] if current else self.core.selected
        n_new = sum(1 for r in self.core.reports if r["status"] == "Новий")
        self.head.set_sub(f"Усього репортів: {len(self.core.reports)}  ·  Нових: {n_new}  ·  Ctrl+F — пошук")
        self.b_new.setText(f"Нові  {n_new}" if n_new else "Нові")
        query = self.search.text().strip().casefold()
        visible = []
        source_reports = list(self.core.reports)
        if self._test_report:
            source_reports.append(self._test_report)
        for r in source_reports:
            if self.filter == "new" and not r.get("test_preview") and r["status"] not in ("Новий", "Колега відповів"):
                continue
            searchable = f"{r['name']} {r['id']} {r['text']}".casefold()
            if query and query not in searchable:
                continue
            visible.append(r)

        visible_ids = {r["rid"] for r in visible}
        self.lst.blockSignals(True)
        self.lst.setUpdatesEnabled(False)
        existing = {}
        for row in range(self.lst.count() - 1, -1, -1):
            item = self.lst.item(row)
            rid = item.data(Qt.UserRole)
            if rid not in visible_ids:
                self.lst.takeItem(row)
            else:
                existing[rid] = item

        selected_item = None
        for index, r in enumerate(visible):
            item = existing.get(r["rid"])
            if item is None:
                item = QListWidgetItem()
            old_row = self.lst.row(item)
            if old_row < 0:
                self.lst.insertItem(index, item)
            elif old_row != index:
                self.lst.takeItem(old_row)
                self.lst.insertItem(index, item)
            if item.data(Qt.UserRole) != r["rid"]:
                item.setData(Qt.UserRole, r["rid"])
            row_data = dict(r)
            if item.data(ROLE) != row_data:
                item.setData(ROLE, row_data)
                item.setToolTip(r["text"])
            if r["rid"] == keep:
                selected_item = item
        if selected_item is not None:
            self.lst.setCurrentItem(selected_item)
        else:
            self.lst.setCurrentRow(-1)
        self.lst.setUpdatesEnabled(True)
        self.lst.blockSignals(False)
        if selected_item is None:
            self.core.selected = None
        self.show_cur()
        self._dirty = False

    def select(self, *_):
        r = self.cur()
        self.core.selected = r["rid"] if r and not r.get("test_preview") else None
        self.show_cur()
        if r and self.core.cfg["ai_auto"] and r["status"] == "Новий":
            self.ai()

    def show_cur(self):
        r = self.cur()
        self.rs.setCurrentIndex(1 if r else 0)
        if not r:
            return
        self.avatar.setText((r["name"][:1] or "?").upper())
        self.title.setText(r["name"])
        _pid2 = str(r.get("id", ""))
        _nb2 = any(_pid2.startswith(p) for p in ("691", "692"))
        self.report_id.setText(("★ Новачок · " if _nb2 else "") + f"ID {_pid2}")
        self.meta.setText("ТЕСТОВИЙ РЕПОРТ" if r.get("test_preview") else f"НАДІЙШОВ О {r['time']}")
        set_pill(self.pill, report_visual_status(r), report_color(r))
        self.text.setText(r["text"])
        seen_reports_today = self.core.players.reports_today(r["id"])
        self.player_report_count.setText(f"Репортів від гравця сьогодні: {seen_reports_today}")
        self.player_report_count.setVisible(seen_reports_today > 0)
        self.flag.setText(("Підозра на порушення: " + ", ".join(r["flags"])) if r["flags"] else "")
        self.flag.setVisible(bool(r["flags"]))

    def limit_reply_input(self):
        if self._reply_clamping:
            return
        text = self.reply.toPlainText()
        if len(text) > self.reply_max_chars:
            old = self._reply_last_valid_text
            prefix = 0
            while prefix < min(len(old), len(text)) and old[prefix] == text[prefix]:
                prefix += 1
            suffix = 0
            while (suffix < len(old) - prefix and suffix < len(text) - prefix and
                   old[len(old) - suffix - 1] == text[len(text) - suffix - 1]):
                suffix += 1
            inserted_end = len(text) - suffix
            inserted = text[prefix:inserted_end]
            old_end = len(old) - suffix
            remaining = self.reply_max_chars - (len(old) - (old_end - prefix))
            accepted = inserted[:max(0, remaining)]
            text = old[:prefix] + accepted + old[old_end:]
            cursor_pos = min(prefix + len(accepted), len(text))
            self._reply_clamping = True
            self.reply.setPlainText(text)
            cursor = self.reply.textCursor()
            cursor.setPosition(cursor_pos)
            self.reply.setTextCursor(cursor)
            self._reply_clamping = False
        self._reply_last_valid_text = text
        self.update_reply_counter()

    def update_reply_counter(self):
        if not hasattr(self, "reply_counter"):
            return
        count = min(len(self.reply.toPlainText()), self.reply_max_chars)
        if count >= 100:
            color, background, border = "#ff7882", "#351d25", "#71353e"
        elif count >= 90:
            color, background, border = "#ffc45c", "#332a1b", "#6a512b"
        else:
            color, background, border = MUTED, "#1b2430", "#2a394c"
        suffix = " · ліміт" if count == self.reply_max_chars else ""
        self.reply_counter.setText(f"{count}/{self.reply_max_chars}{suffix}")
        self.reply_counter.setStyleSheet(
            f"background:{background};color:{color};border:1px solid {border};"
            "border-radius:9px;padding:4px 9px;font-size:11px;font-weight:700;"
        )

    ACCESS_BUTTONS = {"Надіслати": "rep_send", "ШІ-відповідь": "rep_ai", "Вставити /pm ID": "rep_take",
                      "Слідкувати": "rep_spectate", "Телепортуватися": "rep_warp", "В адмін-чат": "rep_admin",
                      "Відповідь колеги": "rep_colleague", "Скопіювати репорт": "rep_copy", "Прибрати": "rep_remove"}

    def allow(self, feature):
        if can(feature):
            return True
        self.ai_note.setText("Немає доступу: " + ACCESS_BY_ID[feature][1])
        return False

    def apply_access(self):
        for b in self.findChildren(QPushButton):
            feature = self.ACCESS_BUTTONS.get(b.text())
            if feature:
                b.setVisible(can(feature))
        if hasattr(self, "clear_btn"):
            self.clear_btn.setVisible(can("rep_remove"))
        self.binds.setVisible(can("rep_quick"))
        has_commands = bool(self.core.cfg.get("commands", []))
        self.command_buttons.setVisible(can("rep_commands"))
        self.command_heading.setVisible(can("rep_commands") and has_commands)

    def send(self):
        if not self.allow("rep_send"):
            return
        report = self.cur()
        if report and report.get("test_preview"):
            self.ai_note.setText("Тестовий репорт не можна відправити в гру.")
            return
        text = self.core.render(self.reply.toPlainText(), report)[:self.reply_max_chars]
        self.core.send_reply(text, report)
        self.reply.clear()

    def take(self):
        if not self.allow("rep_take"):
            return
        if self.cur() and self.cur().get("test_preview"):
            self.ai_note.setText("Тестовий репорт не виконує ігрових команд.")
            return
        self.core.take(self.cur())

    def spectate(self):
        if not self.allow("rep_spectate"):
            return
        if self.cur() and self.cur().get("test_preview"):
            self.ai_note.setText("Тестовий репорт не виконує ігрових команд.")
            return
        self.core.spectate_report(self.cur())

    def warp(self):
        if not self.allow("rep_warp"):
            return
        if self.cur() and self.cur().get("test_preview"):
            self.ai_note.setText("Тестовий репорт не виконує ігрових команд.")
            return
        self.core.warp_report(self.cur())

    def admin(self):
        if not self.allow("rep_admin"):
            return
        if self.cur() and self.cur().get("test_preview"):
            self.ai_note.setText("Тестовий репорт не виконує ігрових команд.")
            return
        self.core.to_admin(self.cur())

    def insert_colleague_reply(self):
        if not self.allow("rep_colleague"):
            return
        r = self.cur()
        if not r:
            return
        text = (r.get("colleague_reply") or "").strip()
        if not text:
            self.ai_note.setText("У логах ще немає відповіді колеги на цей репорт.")
            return
        QApplication.clipboard().setText(text)
        self.reply.setPlainText(text)
        admin = r.get("colleague_admin", "")
        self.ai_note.setText(f"Відповідь колеги скопійована й вставлена{': ' + admin if admin else ''}.")
        self.reply.setFocus()

    def copy_report(self):
        if not self.allow("rep_copy"):
            return
        r = self.cur()
        if not r:
            return
        QApplication.clipboard().setText(f"Репорт від гравця {r['name']}[{r['id']}]: {r['text']}")
        self.ai_note.setText("Текст репорту скопійовано в буфер обміну.")

    def colleague(self):
        r = self.cur()
        if r:
            r["status"] = "Колега відповів"
            self.core.reports_changed.emit()

    def clear_reports(self):
        if not self.allow("rep_remove"):
            return
        self.core.reports.clear()
        self.core._report_seen.clear()
        self.core.selected = None
        self.core.reports_changed.emit()
        self.reply.clear()
        self.ai_note.clear()

    def animate_ai_loading(self):
        self.ai_loading_dots = (self.ai_loading_dots + 1) % 4
        self.ai_note.setText("ШІ генерує відповідь" + "." * self.ai_loading_dots)

    def animate_ai_result(self):
        self.ai_result_pos = min(len(self.ai_result_text), self.ai_result_pos + 4)
        self.reply.setPlainText(self.ai_result_text[:self.ai_result_pos][:self.reply_max_chars])
        if self.ai_result_pos >= len(self.ai_result_text):
            self.ai_type_timer.stop()
            self.ai_note.setText("Згенеровану відповідь вставлено — перевірте її перед відправкою.")

    def remove(self):
        if not self.allow("rep_remove"):
            return
        r = self.cur()
        if r:
            if r.get("test_preview"):
                self.clear_test_report()
                return
            self.core.reports.remove(r)
            self.core.selected = None
            self.core.reports_changed.emit()

    def ai(self):
        if not self.allow("rep_ai"):
            return
        r = self.cur()
        if not r:
            return
        self.ai_type_timer.stop()
        self.ai_loading_dots = 0
        self.ai_note.setText("ШІ генерує відповідь")
        self.ai_loading_timer.start(350)
        c = self.core.cfg
        prompt = (f"Рівень адміна: {c['admin_level']}. Репорт від гравця {r['name']}: {r['text']}\n"
                  "Підготуй доречну відповідь не довшу за 110 символів разом із пробілами. "
                  "Поверни тільки текст відповіді.")
        ai_instructions = (c["ai_report_prompt"] + " Обов'язково вкладися максимум у 110 символів разом із пробілами; "
                           "поверни лише текст без лапок і пояснень.")
        w = Worker(lambda: gemini(c, prompt, ai_instructions))

        def done(txt, ok):
            self.ai_loading_timer.stop()
            if ok:
                self.ai_result_text = (txt or "")[:self.reply_max_chars]
                self.ai_result_pos = 0
                self.reply.clear()
                self.ai_note.setText("Згенерована відповідь:")
                self.ai_type_timer.start(18)
            else:
                self.ai_note.setText("Помилка ШІ: " + txt)
        w.done.connect(done)
        self.workers.append(w)
        w.start()


class PunishmentRow(QFrame):
    """Одна команда покарання для вибраного ID; перед відправленням показуємо preview."""

    def __init__(self, core, command, get_player_id, parent=None):
        super().__init__(parent)
        self.core, self.command, self.get_player_id = core, command, get_player_id
        self.setObjectName("punishmentRow")
        row = QHBoxLayout(self)
        row.setContentsMargins(8, 5, 8, 5)
        row.setSpacing(6)
        self.command_label = lab("/" + command, "mono")
        self.command_label.setObjectName("punishmentCommand")
        self.command_label.setFixedWidth(104)
        row.addWidget(self.command_label)
        self.time_input = QLineEdit()
        self.time_input.setPlaceholderText("Час")
        self.time_input.setMaximumWidth(72)
        self.time_input.setToolTip("Тривалість покарання: значення, яке вимагає команда сервера")
        row.addWidget(self.time_input)
        self.reason_input = QLineEdit()
        self.reason_input.setPlaceholderText("Причина покарання")
        row.addWidget(self.reason_input, 1)
        self.send_button = QPushButton("Відправити")
        self.send_button.setObjectName("punishSend")
        self.send_button.setFixedWidth(108)
        self.send_button.setToolTip("Перевірити команду й підтвердити відправлення в гру")
        self.send_button.clicked.connect(self.send)
        row.addWidget(self.send_button)
        self.time_input.textChanged.connect(self.update_enabled)
        self.reason_input.textChanged.connect(self.update_enabled)
        self.update_enabled()

    def update_enabled(self, *_):
        self.send_button.setEnabled(bool(self.get_player_id()) and bool(self.time_input.text().strip())
                                    and bool(self.reason_input.text().strip()))

    def clear_fields(self):
        self.time_input.clear()
        self.reason_input.clear()
        self.update_enabled()

    def send(self):
        player_id = str(self.get_player_id() or "").strip()
        duration = re.sub(r"\s+", "", self.time_input.text())
        reason = re.sub(r"\s+", " ", self.reason_input.text()).strip()
        if not player_id or not duration or not reason:
            return
        command = f"/{self.command} {player_id} {duration} {reason}"
        answer = QMessageBox.question(
            self, "Підтвердження покарання",
            f"Надіслати в гру команду для ID {player_id}?\n\n{command}",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        self.core.send_raw(command, True)
        self.core.event.emit("action", f"Відправлено {self.command} для ID {player_id}")
        self.clear_fields()


class PlayerReportChart(QWidget):
    """Компактний нейтральний графік репортів гравця за останній тиждень."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.values = []
        self.setMinimumHeight(125)

    def set_values(self, values):
        self.values = list(values or [])
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(8, 8, -8, -8)
        if rect.width() < 20 or rect.height() < 30:
            p.end()
            return
        left, right = rect.left() + 20, rect.right() - 8
        top, bottom = rect.top() + 8, rect.bottom() - 24
        p.setPen(QPen(QColor("#2b3544"), 1))
        p.drawLine(int(left), int(bottom), int(right), int(bottom))
        values = self.values[-7:]
        if not values:
            p.setPen(QColor(DIM))
            p.setFont(QFont(BODY_FONT, 9))
            p.drawText(rect, Qt.AlignCenter, "Історії поки немає")
            p.end()
            return
        max_value = max(1, max(amount for _day, amount in values))
        span = max(1, len(values) - 1)
        points = []
        for index, (_day, amount) in enumerate(values):
            x = left + (right - left) * index / span
            y = bottom - (bottom - top) * amount / max_value
            points.append(QPointF(x, y))
        path = QPainterPath(points[0])
        for point in points[1:]:
            path.lineTo(point)
        pen = QPen(QColor(ACC_H), 2.5)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        p.drawPath(path)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(ACC_H))
        for point in points:
            p.drawEllipse(point, 3.2, 3.2)
        p.setPen(QColor(MUTED))
        p.setFont(QFont(BODY_FONT, 8))
        for index, (day, amount) in enumerate(values):
            x = left + (right - left) * index / span
            p.drawText(QRectF(x - 24, bottom + 5, 48, 16), Qt.AlignHCenter | Qt.AlignTop, day.strftime("%d.%m"))
            if amount:
                p.setPen(QColor(TEXT))
                p.drawText(QRectF(x - 15, points[index].y() - 19, 30, 14), Qt.AlignCenter, str(amount))
                p.setPen(QColor(MUTED))
        p.end()


class UsersPage(QWidget):
    """Пошук локально збережених гравців та їхньої історії репортів."""

    def __init__(self, core, open_reports):
        super().__init__()
        self.core, self.open_reports = core, open_reports
        self._current_detail_id = ""
        self._note_drafts = {}
        self._history_signature = None
        self._rendered_query = None
        self._users_dirty = True
        self.punishment_rows = []
        lay = page_layout(self, 14)
        self.head = PageHead("Користувачі", "Гравці, помічені в console.log. Двічі клацніть гравця, щоб відкрити картку швидких дій.")
        lay.addWidget(self.head)
        search_row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Знайти за нікнеймом або ID…")
        self.search.setClearButtonEnabled(True)
        self.search.setFixedHeight(40)
        self.search.textChanged.connect(self.schedule_refresh)
        search_row.addWidget(self.search, 1)
        self.total_label = lab("У базі: 0", "hint")
        search_row.addWidget(self.total_label)
        lay.addLayout(search_row)

        split = QSplitter(Qt.Horizontal)
        split.setChildrenCollapsible(False)
        split.setHandleWidth(8)
        list_card = card()
        lv = QVBoxLayout(list_card)
        lv.setContentsMargins(12, 12, 12, 12)
        self.bulk_delete_btn = QPushButton("Видалити вибраних")
        self.bulk_delete_btn.setObjectName("danger")
        self.bulk_delete_btn.setCursor(Qt.PointingHandCursor)
        self.bulk_delete_btn.clicked.connect(self.delete_checked_users)
        self.bulk_delete_btn.setVisible(bool(self.core.cfg.get("users_bulk_delete_mode", False)))
        lv.addWidget(self.bulk_delete_btn, 0, Qt.AlignLeft)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["", "Нікнейм", "ID", "Сьогодні", "Усього", "Востаннє бачили"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setFont(QFont(BODY_FONT, 10))
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(46)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 34)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        for col, width in ((2, 92), (3, 78), (4, 72), (5, 126)):
            header.setSectionResizeMode(col, QHeaderView.Fixed)
            self.table.setColumnWidth(col, width)
        self.table.setColumnHidden(0, not bool(self.core.cfg.get("users_bulk_delete_mode", False)))
        self.table.itemSelectionChanged.connect(self.show_user)
        self.table.cellDoubleClicked.connect(self.open_user_menu)
        lv.addWidget(self.table)
        split.addWidget(list_card)

        detail = card()
        dv = QVBoxLayout(detail)
        dv.setContentsMargins(14, 14, 14, 14)
        dv.setSpacing(10)

        # Profile header: identity, dates and the two most-used copy actions.
        hero = card()
        hero_row = QHBoxLayout(hero)
        hero_row.setContentsMargins(14, 11, 14, 11)
        hero_row.setSpacing(12)
        self.avatar_badge = QLabel("YT")
        self.avatar_badge.setFixedSize(62, 62)
        self.avatar_badge.setAlignment(Qt.AlignCenter)
        self.avatar_badge.setStyleSheet(
            "background:#203452;border:1px solid #456391;border-radius:18px;"
            "color:#e2ebff;font-size:18px;font-weight:700;"
        )
        hero_row.addWidget(self.avatar_badge)
        identity = QVBoxLayout()
        identity.setSpacing(3)
        identity.addWidget(lab("ПРОФІЛЬ ГРАВЦЯ", "hint"))
        self.user_name = lab("Оберіть гравця зі списку", "title")
        self.user_name.setWordWrap(True)
        identity.addWidget(self.user_name)
        self.user_meta = lab("", "muted", True)
        identity.addWidget(self.user_meta)
        hero_row.addLayout(identity, 1)
        self.copy_id_btn = QPushButton("Копіювати ID")
        self.copy_id_btn.clicked.connect(lambda: self.copy_selected("id"))
        self.copy_name_btn = QPushButton("Копіювати нік")
        self.copy_name_btn.clicked.connect(lambda: self.copy_selected("nickname"))
        hero_actions = QVBoxLayout()
        hero_actions.addWidget(self.copy_id_btn)
        hero_actions.addWidget(self.copy_name_btn)
        hero_row.addLayout(hero_actions)
        dv.addWidget(hero)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(8)
        self.stat_today = self._profile_stat("СЬОГОДНІ", "—", "репорт", ACC_H)
        self.stat_total = self._profile_stat("ЗА ВЕСЬ ЧАС", "—", "звернень", C_NEW)
        self.stat_first = self._profile_stat("ВПЕРШЕ ПОМІЧЕНИЙ", "—", "", "#75cbd4")
        self.stat_last = self._profile_stat("ВОСТАННЄ БАЧИЛИ", "—", "", C_DONE)
        for stat in (self.stat_today, self.stat_total, self.stat_first, self.stat_last):
            stats_row.addWidget(stat, 1)
        dv.addLayout(stats_row)

        middle = QHBoxLayout()
        middle.setSpacing(9)
        history_card = card()
        history_box = QVBoxLayout(history_card)
        history_box.setContentsMargins(12, 11, 12, 10)
        history_box.setSpacing(7)
        history_box.addWidget(lab("ОСТАННІ РЕПОРТИ", "h2"))
        history_box.addWidget(lab("Збережені звернення цього гравця", "hint"))
        self.history_list = QListWidget()
        self.history_list.setObjectName("userHistory")
        self.history_list.setAlternatingRowColors(True)
        self.history_list.setStyleSheet(
            "QListWidget#userHistory{background:transparent;border:0;padding:0;}"
            "QListWidget#userHistory::item{background:#111822;border:1px solid #283344;"
            "border-radius:8px;padding:9px 11px;margin:3px 0;color:#e7ebf0;}"
            "QListWidget#userHistory::item:selected{background:#1a2432;color:#fff;}"
        )
        history_box.addWidget(self.history_list, 1)
        middle.addWidget(history_card, 3)

        actions_card = card()
        actions_box = QVBoxLayout(actions_card)
        actions_box.setContentsMargins(12, 11, 12, 10)
        actions_box.setSpacing(7)
        actions_box.addWidget(lab("ШВИДКІ ДІЇ", "h2"))
        actions_box.addWidget(lab("Дії з профілем і репортами", "hint"))
        action_grid = QGridLayout()
        action_grid.setSpacing(7)
        self.quick_action_buttons = []
        action_grid.addWidget(self._action_tile("#", "ID гравця", "Скопіювати ID", lambda: self.copy_selected("id")), 0, 0)
        action_grid.addWidget(self._action_tile("Aa", "Нікнейм", "Скопіювати ім’я", lambda: self.copy_selected("nickname")), 0, 1)
        report_action = self._action_tile("▤", "Репорти", "Відкрити звернення", self.open_selected_reports)
        self.open_reports_btn = report_action.action_button
        action_grid.addWidget(report_action, 1, 0)
        action_grid.addWidget(self._action_tile("⌕", "Пошук", "Знайти гравця в базі", self.search.setFocus), 1, 1)
        actions_box.addLayout(action_grid)
        actions_box.addStretch(1)
        middle.addWidget(actions_card, 2)
        dv.addLayout(middle, 3)

        bottom = QHBoxLayout()
        bottom.setSpacing(9)
        activity_card = card()
        activity_box = QVBoxLayout(activity_card)
        activity_box.setContentsMargins(12, 11, 12, 10)
        activity_box.addWidget(lab("АКТИВНІСТЬ ЗВЕРНЕНЬ", "h2"))
        activity_box.addWidget(lab("Кількість репортів за останні 7 днів", "hint"))
        self.report_chart = PlayerReportChart()
        activity_box.addWidget(self.report_chart, 1)
        bottom.addWidget(activity_card, 3)

        note_card = card()
        note_box = QVBoxLayout(note_card)
        note_box.setContentsMargins(12, 11, 12, 10)
        note_box.addWidget(lab("ПРИМІТКА АДМІНІСТРАТОРА", "h2"))
        note_box.addWidget(lab("Приватна нотатка до профілю", "hint"))
        self.user_note = QPlainTextEdit()
        self.user_note.setPlaceholderText("Напиши контекст або важливу деталь…")
        self.user_note.setMaximumHeight(104)
        note_box.addWidget(self.user_note, 1)
        self.save_note_btn = QPushButton("Зберегти нотатку")
        self.save_note_btn.clicked.connect(self.save_user_note)
        note_box.addWidget(self.save_note_btn, 0, Qt.AlignRight)
        bottom.addWidget(note_card, 2)
        dv.addLayout(bottom, 2)

        split.addWidget(detail)
        split.setSizes([620, 1100])
        lay.addWidget(split, 1)

        self.core.users_changed.connect(self.refresh_if_visible)
        self._refresh_debounce = QTimer(self)
        self._refresh_debounce.setSingleShot(True)
        self._refresh_debounce.setInterval(120)
        self._refresh_debounce.timeout.connect(self.refresh)
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(60000)
        self.refresh_timer.timeout.connect(self.schedule_refresh)
        self.refresh_timer.start()
        self.refresh()

    def _punishment_tab(self, commands, heading):
        page = QWidget()
        box = QVBoxLayout(page)
        box.setContentsMargins(8, 8, 8, 8)
        box.setSpacing(7)
        box.addWidget(lab(heading + " · ID береться з вибраного профілю", "hint", True))
        for command in commands:
            item = PunishmentRow(self.core, command, self.selected_id, page)
            self.punishment_rows.append(item)
            box.addWidget(item)
        box.addStretch(1)
        return page

    def _profile_stat(self, heading, value, caption, color):
        tile = card()
        tile.setMinimumHeight(76)
        box = QVBoxLayout(tile)
        box.setContentsMargins(11, 8, 11, 7)
        box.setSpacing(2)
        title = lab(heading, "hint")
        title.setStyleSheet(f"color:{MUTED};font-size:9px;font-weight:700;")
        box.addWidget(title)
        value_row = QHBoxLayout()
        value_label = lab(value, "title")
        value_label.setStyleSheet(f"color:{color};font-size:19px;font-weight:700;")
        value_note = lab(caption, "hint")
        value_row.addWidget(value_label)
        value_row.addWidget(value_note, 1, Qt.AlignVCenter)
        box.addLayout(value_row)
        tile.value_label = value_label
        tile.value_note = value_note
        tile.heading_label = title
        return tile

    def _action_tile(self, icon, title, hint, callback):
        tile = card()
        tile.setMinimumHeight(77)
        box = QVBoxLayout(tile)
        box.setContentsMargins(9, 7, 9, 7)
        box.setSpacing(2)
        button = QPushButton(f"{icon}   {title}")
        button.setObjectName("chip")
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(lambda _checked=False: callback())
        tile.action_button = button
        self.quick_action_buttons.append(button)
        box.addWidget(button)
        box.addWidget(lab(hint, "hint", True))
        return tile

    def _set_stat(self, tile, value, caption=""):
        tile.value_label.setText(str(value))
        tile.value_note.setText(str(caption))

    def save_user_note(self):
        player_id = self.selected_id()
        if not player_id:
            return
        note = self.user_note.toPlainText().strip()
        notes = self.core.cfg.get("player_notes")
        if not isinstance(notes, dict):
            notes = {}
            self.core.cfg["player_notes"] = notes
        if note:
            notes[player_id] = note
        else:
            notes.pop(player_id, None)
        self._note_drafts[player_id] = note
        save_cfg(self.core.cfg)
        self.core.event.emit("info", "Нотатку профілю збережено")

    def selected_id(self):
        row = self.table.currentRow()
        item = self.table.item(row, 2) if row >= 0 else None
        return str(item.data(Qt.UserRole)) if item else ""

    def set_bulk_delete_mode(self, enabled):
        enabled = bool(enabled)
        self.bulk_delete_btn.setVisible(enabled)
        self.table.setColumnHidden(0, not enabled)
        if not enabled:
            for row in range(self.table.rowCount()):
                checkbox = self.table.item(row, 0)
                if checkbox:
                    checkbox.setCheckState(Qt.Unchecked)

    @staticmethod
    def pretty_time(value):
        try:
            return datetime.datetime.fromisoformat(value).strftime("%d.%m.%Y %H:%M")
        except (TypeError, ValueError):
            return str(value or "—")

    def refresh(self, *_):
        query = self.search.text().strip()
        if query == self._rendered_query and not self._users_dirty:
            return
        keep_id = self.selected_id()
        checked_ids = set()
        for old_row in range(self.table.rowCount()):
            checkbox = self.table.item(old_row, 0)
            id_item = self.table.item(old_row, 2)
            if checkbox and checkbox.checkState() == Qt.Checked and id_item:
                checked_ids.add(str(id_item.data(Qt.UserRole)))
        rows = self.core.players.list_users(query)
        self.total_label.setText(f"У базі: {self.core.players.count():,}".replace(",", " "))
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        selected_row = -1
        for entry in rows:
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = (entry["nickname"], entry["id"], str(entry["reports_today"]),
                      str(entry["reports_total"]), self.pretty_time(entry["last_seen"]))
            checkbox = QTableWidgetItem()
            checkbox.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable)
            checkbox.setCheckState(Qt.Checked if entry["id"] in checked_ids else Qt.Unchecked)
            self.table.setItem(row, 0, checkbox)
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                target_col = col + 1
                if col == 1:
                    item.setData(Qt.UserRole, entry["id"])
                    item.setForeground(QColor(ACC_H))
                if col in (2, 3):
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, target_col, item)
            if entry["id"] == keep_id:
                selected_row = row
        self.table.blockSignals(False)
        if self.table.rowCount():
            self.table.selectRow(max(0, selected_row))
        else:
            self.show_user()
        self._rendered_query = query
        self._users_dirty = False

    def schedule_refresh(self, *_):
        self._users_dirty = True
        if self.isVisible():
            self._refresh_debounce.start()

    def refresh_if_visible(self):
        self.schedule_refresh()

    def showEvent(self, event):
        super().showEvent(event)
        if self._rendered_query is None or self._users_dirty:
            self.schedule_refresh()

    def show_user(self):
        player_id = self.selected_id()
        user = self.core.players.get_user(player_id) if player_id else None
        selection_changed = player_id != self._current_detail_id
        if selection_changed:
            if self._current_detail_id and hasattr(self, "user_note"):
                self._note_drafts[self._current_detail_id] = self.user_note.toPlainText()
            for row in self.punishment_rows:
                row.clear_fields()
            self._current_detail_id = player_id
        enabled = bool(user)
        self.copy_id_btn.setEnabled(enabled)
        self.copy_name_btn.setEnabled(enabled)
        self.open_reports_btn.setEnabled(enabled)
        self.save_note_btn.setEnabled(enabled)
        for button in self.quick_action_buttons:
            button.setEnabled(enabled)
        if self.quick_action_buttons:
            self.quick_action_buttons[-1].setEnabled(True)
        for row in self.punishment_rows:
            row.update_enabled()
        if not user:
            self.history_list.clear()
            self._history_signature = None
            self.user_name.setText("Оберіть гравця зі списку")
            self.user_meta.clear()
            self.avatar_badge.setText("YT")
            self._set_stat(self.stat_today, "—", "репорт")
            self._set_stat(self.stat_total, "—", "звернень")
            self._set_stat(self.stat_first, "—", "")
            self._set_stat(self.stat_last, "—", "")
            self.report_chart.set_values([])
            self.user_note.clear()
            return
        today = self.core.players.reports_today(player_id)
        self.user_name.setText(user["nickname"])
        initials = "".join(part[0] for part in user["nickname"].split()[:2]).upper() or "YT"
        self.avatar_badge.setText(initials)
        self.user_meta.setText(f"ID {player_id}  ·  уперше помічений {self.pretty_time(user['first_seen'])}  ·  востаннє {self.pretty_time(user['last_seen'])}")
        self._set_stat(self.stat_today, today, "репорт" if today == 1 else "репорти")
        self._set_stat(self.stat_total, user["reports_total"], "звернень")
        first_seen = self.pretty_time(user["first_seen"])
        last_seen = self.pretty_time(user["last_seen"])
        self._set_stat(self.stat_first, first_seen.split(" ")[0], first_seen.split(" ")[1] if " " in first_seen else "")
        self._set_stat(self.stat_last, last_seen.split(" ")[0], last_seen.split(" ")[1] if " " in last_seen else "")
        self.report_chart.set_values(self.core.players.report_counts_by_day(player_id, 7))
        if selection_changed:
            notes = self.core.cfg.get("player_notes", {})
            saved_note = notes.get(player_id, "") if isinstance(notes, dict) else ""
            self.user_note.setPlainText(self._note_drafts.get(player_id, saved_note))
        history = self.core.players.history(player_id)
        history_signature = tuple((item["created_at"], item["message"]) for item in history)
        if history_signature != self._history_signature:
            self.history_list.clear()
            for item in history:
                stamp = self.pretty_time(item["created_at"])
                line = f"{stamp}  ·  {item['message']}"
                entry = QListWidgetItem(notification_text(line, limit=170))
                entry.setToolTip(line)
                self.history_list.addItem(entry)
            if not self.history_list.count():
                self.history_list.addItem("Репортів від цього гравця ще не було.")
            self._history_signature = history_signature

    def copy_selected(self, field):
        player_id = self.selected_id()
        user = self.core.players.get_user(player_id) if player_id else None
        if user:
            QApplication.clipboard().setText(str(user[field]))
            self.core.event.emit("info", f"Скопійовано: {user[field]}")

    def open_selected_reports(self):
        player_id = self.selected_id()
        if player_id:
            self.open_reports(player_id)

    def open_user_menu(self, *_):
        """Card-style action menu for the selected profile (double-click a row)."""
        player_id = self.selected_id()
        user = self.core.players.get_user(player_id) if player_id else None
        if not user:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Профіль користувача")
        dialog.setMinimumWidth(520)
        outer = QVBoxLayout(dialog)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(12)
        header = card()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(16, 14, 16, 14)
        header_layout.setSpacing(5)
        header_layout.addWidget(lab(user["nickname"], "title"))
        header_layout.addWidget(lab(
            f"ID {player_id}  ·  Репортів сьогодні: {self.core.players.reports_today(player_id)}  ·  Усього: {user['reports_total']}",
            "hint", True))
        outer.addWidget(header)
        outer.addWidget(lab("Швидкі дії", "h2"))
        grid = QGridLayout()
        grid.setSpacing(9)
        actions = [
            ("Копіювати ID", "Скопіювати числовий ідентифікатор", lambda: self.copy_selected("id")),
            ("Копіювати нік", "Скопіювати ім’я гравця", lambda: self.copy_selected("nickname")),
            ("Показати репорти", "Відкрити звернення цього гравця", lambda: self.open_selected_reports()),
            ("Історія профілю", "Переглянути збережені репорти", lambda: self.history_list.setFocus()),
        ]
        for index, (title, hint, callback) in enumerate(actions):
            tile = card()
            tile_layout = QVBoxLayout(tile)
            tile_layout.setContentsMargins(12, 10, 12, 10)
            tile_layout.setSpacing(4)
            button = QPushButton(title)
            button.setObjectName("chip")
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda _=False, action=callback: (dialog.accept(), action()))
            tile_layout.addWidget(button)
            tile_layout.addWidget(lab(hint, "hint", True))
            grid.addWidget(tile, index // 2, index % 2)
        outer.addLayout(grid)
        close_button = QPushButton("Готово")
        close_button.clicked.connect(dialog.accept)
        outer.addWidget(close_button, 0, Qt.AlignRight)
        dialog.exec()

    def delete_checked_users(self):
        if not self.core.cfg.get("users_bulk_delete_mode", False):
            return
        selected = []
        for row in range(self.table.rowCount()):
            checkbox = self.table.item(row, 0)
            id_item = self.table.item(row, 2)
            name_item = self.table.item(row, 1)
            if checkbox and checkbox.checkState() == Qt.Checked and id_item:
                selected.append((str(id_item.data(Qt.UserRole)), name_item.text() if name_item else "гравець"))
        if not selected:
            QMessageBox.information(self, "Видалення користувачів", "Спочатку познач користувачів галочками.")
            return
        answer = QMessageBox.question(
            self, "Видалити вибраних",
            f"Видалити {len(selected)} користувач(ів) з локальної бази разом з історією їхніх репортів?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        for player_id, _name in selected:
            self.core.players.delete_user(player_id)
        self._current_detail_id = ""
        self.refresh()
        self.core.users_changed.emit()
        self.core.event.emit("info", f"Видалено користувачів: {len(selected)}")


class VipPage(QWidget):
    def __init__(self, core):
        super().__init__()
        self.core = core
        lay = page_layout(self)
        lay.addWidget(PageHead("VIP чат", "Реклама та порушення у /vip. Мут відправляється лише після вашого підтвердження."))
        self.alert = QFrame()
        self.alert.setObjectName("alert")
        self.alert.setProperty("armed", False)
        cv = QVBoxLayout(self.alert)
        cv.setContentsMargins(22, 18, 22, 18)
        cv.setSpacing(10)
        self.state = lab("Реклами не виявлено", "title")
        cv.addWidget(self.state)
        self.info = lab("Коли в /vip з'явиться реклама, тут буде готова форма муту.", "muted", True)
        cv.addWidget(self.info)
        self.form = QLineEdit()
        self.form.setPlaceholderText("Команда муту…")
        self.form.setStyleSheet(f"font-family:{MONO_FONT}; font-size:13px;")
        self.form.textChanged.connect(self._sync_btn)
        cv.addWidget(self.form)
        row = QHBoxLayout()
        row.setSpacing(8)
        self.ok = QPushButton("Підтвердити і відправити")
        self.ok.setObjectName("ok")
        self.ok.setCursor(Qt.PointingHandCursor)
        self.ok.clicked.connect(self.confirm)
        self.no = QPushButton("Відхилити")
        self.no.setObjectName("danger")
        self.no.setCursor(Qt.PointingHandCursor)
        self.no.clicked.connect(self.dismiss)
        row.addWidget(self.ok)
        row.addWidget(self.no)
        row.addStretch(1)
        cv.addLayout(row)
        lay.addWidget(self.alert)
        sc = card()
        sv = QVBoxLayout(sc)
        sv.setContentsMargins(14, 16, 14, 12)
        h = QHBoxLayout()
        h.setContentsMargins(6, 0, 6, 0)
        h.addWidget(lab("Потік /vip", "h2"))
        sv.addLayout(h)
        self.stream = feed_list()
        self.stream.itemClicked.connect(self.select_stream_item)
        sv.addWidget(with_empty(self.stream, "Повідомлення з /vip з'являться тут."), 1)
        lay.addWidget(sc, 1)
        self._recent_messages = collections.deque(maxlen=300)
        self._seen_vip_messages = set()
        self._history_loaded = False
        core.vip_msg.connect(self.on_msg)
        core.vip_ad.connect(self.on_ad)
        self._sync_btn()

    def showEvent(self, event):
        super().showEvent(event)
        if not self._history_loaded:
            # Replace preloaded live-only entries with one chronological log snapshot.
            self._recent_messages.clear()
            self._seen_vip_messages.clear()
            self._load_recent_history()
        self.stream.clear()
        for text, color, tag, candidate in self._recent_messages:
            item = add_feed(self.stream, tag, text, color, 300)
            if candidate:
                item.setData(Qt.UserRole + 2, candidate)

    def _load_recent_history(self):
        self._history_loaded = True
        path = find_console_log(self.core.cfg)
        if not path or not os.path.isfile(path):
            return
        try:
            with open(path, "rb") as source:
                source.seek(0, os.SEEK_END)
                size = source.tell()
                source.seek(max(0, size - 2_000_000))
                lines = source.read().decode("utf-8", "replace").splitlines()[-6000:]
        except OSError:
            return
        for raw in lines:
            line = clean(raw)
            match = self.core.rx("vip_regex").search(line)
            if not match:
                continue
            data = match.groupdict()
            text = f"{data.get('name', '').strip()} [{data.get('id', '').strip()}]: {data.get('text', '').strip()}"
            entry = self._make_entry(text)
            self._remember_entry(entry)

    def _make_entry(self, text):
        match = re.match(r"^(?P<name>.+?)\s*\[(?P<id>\d+)\]:\s*(?P<text>.*)$", text)
        if not match:
            return text, TEXT, "", None
        data = match.groupdict()
        active = self.core.vip_monitor_active()
        exact = active and self.core.is_ad(data["text"])
        candidate = active and not exact and self.core.vip_candidate(data["text"])
        color = C_BAD if exact else C_NEW if candidate else TEXT
        tag = "РЕКЛАМА" if exact else "МОЖЛИВО" if candidate else ""
        candidate_data = {"id": data["id"], "name": data["name"], "text": data["text"]} if candidate else None
        return text, color, tag, candidate_data

    def _remember_entry(self, entry):
        text = entry[0]
        if text in self._seen_vip_messages:
            return False
        if len(self._recent_messages) == self._recent_messages.maxlen:
            oldest = self._recent_messages[0][0]
            self._seen_vip_messages.discard(oldest)
        self._recent_messages.append(entry)
        self._seen_vip_messages.add(text)
        return True

    def _sync_btn(self):
        self.ok.setEnabled(bool(self.form.text().strip()))

    def _arm(self, on):
        self.alert.setProperty("armed", on)
        repolish(self.alert)

    def on_msg(self, t):
        entry = self._make_entry(t)
        if not self._remember_entry(entry):
            return
        if not self.isVisible():
            return
        text, color, tag, candidate_data = entry
        it = add_feed(self.stream, tag, text, color, 300)
        if candidate_data:
            it.setData(Qt.UserRole + 2, candidate_data)

    def select_stream_item(self, item):
        candidate = item.data(Qt.UserRole + 2)
        if not candidate:
            return
        command = self.core.cfg["mute_cmd"].format_map(Safe(id=candidate["id"], name=candidate["name"]))
        self.form.setText(command)
        self._arm(True)
        self.state.setText("Можлива реклама — перевірте перед надсиланням")
        self.info.setText(f"{candidate['name']} [{candidate['id']}]: {candidate['text']}")

    def on_ad(self, gd):
        self._arm(True)
        self.state.setText("Виявлено рекламу")
        self.info.setText(f"{gd['name']} [{gd['id']}]: {gd['text']}")
        self.form.setText(self.core.cfg["mute_cmd"].format_map(Safe(id=gd["id"], name=gd["name"])))

    def confirm(self):
        t = self.form.text().strip()
        if t:
            self.core.send_raw(t, True)
            self._arm(False)
            self.state.setText("Мут відправлено")
            self.info.setText(t)
            self.form.clear()

    def dismiss(self):
        self.form.clear()
        self._arm(False)
        self.state.setText("Форму відхилено")
        self.info.setText("Чекаємо наступної реклами.")


class KeyCaptureButton(QPushButton):
    """Кнопка для призначення клавіші або комбінації з модифікаторами."""

    captured = Signal(str)
    capture_state = Signal(bool)

    def __init__(self, keys="", parent=None):
        super().__init__(parent)
        self._keys = (keys or "").strip().lower()
        self._capturing = False
        self._capture_timer = QTimer(self)
        self._capture_timer.setSingleShot(True)
        self._capture_timer.setInterval(10000)
        self._capture_timer.timeout.connect(lambda: self._finish(False))
        self.setObjectName("keyCapture")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(32)
        self.clicked.connect(self.begin_capture)
        self._show_key()

    def key_value(self):
        return self._keys

    def _show_key(self):
        self.setText(self._keys.upper() if self._keys else "Не призначено")

    def begin_capture(self):
        if self._capturing:
            return
        self._capturing = True
        self._previous = self._keys
        self.setText("Очікуємо натиснення клавіші…")
        self.setToolTip("Натисніть клавішу або комбінацію з Ctrl, Alt, Shift чи Win. Escape — очистити призначення.")
        self.setFocus(Qt.MouseFocusReason)
        app = QApplication.instance()
        if app:
            app.installEventFilter(self)
        self._capture_timer.start()
        self.capture_state.emit(True)

    def _finish(self, accepted=False):
        if not self._capturing:
            return
        self._capturing = False
        self._capture_timer.stop()
        app = QApplication.instance()
        if app:
            app.removeEventFilter(self)
        if not accepted:
            self._keys = getattr(self, "_previous", self._keys)
        self._show_key()
        self.setToolTip("Натисніть, щоб призначити клавішу або комбінацію. Escape під час запису очищає призначення.")
        self.capture_state.emit(False)

    def _capture_key_event(self, event):
        key = event.key()
        if key == Qt.Key_Escape:
            self._keys = ""
            self._finish(True)
            self.captured.emit("")
            return True
        if key in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta):
            names = []
            mods = event.modifiers()
            if mods & Qt.ControlModifier: names.append("Ctrl")
            if mods & Qt.AltModifier: names.append("Alt")
            if mods & Qt.ShiftModifier: names.append("Shift")
            if mods & Qt.MetaModifier: names.append("Win")
            self.setText((" + ".join(names) + " + …") if names else "Натисніть клавішу…")
            return True
        if key == Qt.Key_unknown or event.isAutoRepeat():
            return True
        try:
            modifiers = event.modifiers() & (Qt.ControlModifier | Qt.AltModifier | Qt.ShiftModifier | Qt.MetaModifier)
            base_key = self._base_key_name(event, key)
            modifier_names = []
            if modifiers & Qt.ControlModifier: modifier_names.append("ctrl")
            if modifiers & Qt.AltModifier: modifier_names.append("alt")
            if modifiers & Qt.ShiftModifier: modifier_names.append("shift")
            if modifiers & Qt.MetaModifier: modifier_names.append("windows")
            value = "+".join(modifier_names + [base_key]) if base_key else ""
        except Exception:
            value = ""
        value = value.strip().lower().replace("return", "enter")
        if not value:
            self.setText("Натисніть одну звичайну клавішу…")
            return True
        self._keys = value
        self._finish(True)
        self.captured.emit(self._keys)
        return True

    @staticmethod
    def _base_key_name(event, qt_key):
        """Use the physical Windows key code so Shift+1 stays Shift+1, not Shift+!."""
        vk = int(event.nativeVirtualKey()) if hasattr(event, "nativeVirtualKey") else 0
        if 0x30 <= vk <= 0x39:
            return chr(vk)
        if 0x41 <= vk <= 0x5A:
            return chr(vk).lower()
        if 0x70 <= vk <= 0x87:
            return f"f{vk - 0x6f}"
        if 0x60 <= vk <= 0x69:
            return f"num {vk - 0x60}"
        vk_names = {
            0x08: "backspace", 0x09: "tab", 0x0D: "enter", 0x13: "pause",
            0x14: "caps lock", 0x1B: "esc", 0x20: "space", 0x21: "page up",
            0x22: "page down", 0x23: "end", 0x24: "home", 0x25: "left",
            0x26: "up", 0x27: "right", 0x28: "down", 0x2D: "insert",
            0x2E: "delete", 0x6A: "num *", 0x6B: "num +", 0x6D: "num -",
            0x6E: "num .", 0x6F: "num /", 0x90: "num lock", 0x91: "scroll lock",
            0xBA: ";", 0xBB: "=", 0xBC: ",", 0xBD: "-", 0xBE: ".",
            0xBF: "/", 0xC0: "`", 0xDB: "[", 0xDC: "\\", 0xDD: "]", 0xDE: "'",
        }
        if vk in vk_names:
            return vk_names[vk]
        fallback = QKeySequence(int(qt_key)).toString(QKeySequence.PortableText)
        return fallback.strip().lower().replace("return", "enter")

    def eventFilter(self, watched, event):
        if self._capturing and event.type() == QEvent.KeyPress:
            return self._capture_key_event(event)
        return super().eventFilter(watched, event)

    def keyPressEvent(self, event):
        if self._capturing and self._capture_key_event(event):
            event.accept()
            return
        super().keyPressEvent(event)

    def focusOutEvent(self, event):
        # Qt may move focus while routing a key through a table; keep listening.
        super().focusOutEvent(event)


BUILTIN_BINDS = [
    {"keys": "alt+f1", "name": "реп", "text": "Вітаю, на зв'язку {admin}. Накрив вашу заявку крилом захисту. Працюю.", "send": True, "open_chat": True},
    {"keys": "shift+f3", "name": "домкрат", "text": "Вітаю, скористайтесь домкратом з заправки.", "send": True, "open_chat": True},
    {"keys": "alt+f7", "name": "новини", "text": "Вітаю, слідкуйте за офіційними новинами UKRAINE GTA.", "send": True, "open_chat": True},
    {"keys": "alt+f8", "name": "скарга", "text": "Вітаю, якщо у вас є відеодокази, подавайте скаргу на форум.", "send": True, "open_chat": True},
    {"keys": "alt+f5", "name": "в. квиток", "text": "Вітаю, вступіть в ЗСУ та дослужіть до 3 рангу або отримайте його за донат.", "send": True, "open_chat": True},
    {"keys": "shift+f7", "name": "набір", "text": "Вітаю, очікуйте на набір, вас повідомить SMS у телефоні.", "send": True, "open_chat": True},
    {"keys": "shift+n", "name": "приємної гри", "text": "Приємної гри! Нехай ваше везіння завжди буде під крилом успіху в UKRAINE GTA.", "send": True, "open_chat": True},
    {"keys": "shift+f2", "name": "переподайте", "text": "Вітаю, уточніть ваше питання у наступному репорті.", "send": True, "open_chat": True},
    {"keys": "shift+f1", "name": "не виконуємо", "text": "Вітаю, адміністрація не виконує таких дій.", "send": True, "open_chat": True},
    {"keys": "shift+f5", "name": "звільнення", "text": "Вітаю, команда /uninvite якщо у вас є преміум, або зверніться до лідера/заступника.", "send": True, "open_chat": True},
    {"keys": "shift+f8", "name": "евакуація", "text": "Вітаю, /p (англ) — евакуація транспорту.", "send": True, "open_chat": True},
    {"keys": "shift+1", "name": "віп", "text": "Вітаю. /vip", "send": True, "open_chat": True},
    {"keys": "shift+f9", "name": "ремка", "text": "Вітаю, відремонтуйте авто на СТО або ремкомплектом із заправки.", "send": True, "open_chat": True},
    {"keys": "shift+f6", "name": "цр", "text": "Вітаю, перевірка буде здійснена, щойно з'явиться вільний адміністратор.", "send": True, "open_chat": True},
    {"keys": "shift+f12", "name": "тех підтримка", "text": "Вітаю, зверніться до технічної підтримки Telegram @ukrainegtabot.", "send": True, "open_chat": True},
    {"keys": "alt+f3", "name": "допомога", "text": "Вітаю, чим можу допомогти?", "send": True, "open_chat": True},
    {"keys": "shift+f11", "name": "номера", "text": "Вітаю, O (англ) → Навігація → Важливі місця → Головний сервісний центр.", "send": True, "open_chat": True},
    {"keys": "shift+'", "name": "паспорт", "text": "Вітаю, у будні дні з 18:00 до 19:00 у будівлі ЦНАП. Із собою мати 300 000 грн.", "send": True, "open_chat": True},
]


class BindsPage(QWidget):
    def __init__(self, core, on_save):
        super().__init__()
        self.core, self.on_save = core, on_save
        lay = page_layout(self, 14)
        lay.addWidget(PageHead(
            "Бінди",
            "Макроси: {id} — ID гравця, {name} — ім'я, {admin} — ваш профіль, {time} — поточний час. "
            "Працюють у звичайних біндах і командах. Увімкни «Відкривати чат», щоб натискати T."))
        help_card = card()
        help_l = QVBoxLayout(help_card)
        help_l.setContentsMargins(14, 10, 14, 10)
        help_l.addWidget(lab("{id} — ID активного гравця/репорту  ·  {name} — його ім'я  ·  {admin} — ваш нік  ·  {time} — час ГГ:ХХ:СС", "hint", True))
        lay.addWidget(help_card)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setObjectName("bindTabs")
        binds_page = QWidget()
        binds_layout = QVBoxLayout(binds_page)
        binds_layout.setContentsMargins(14, 14, 14, 12)
        binds_layout.setSpacing(10)
        commands_page = QWidget()
        commands_layout = QVBoxLayout(commands_page)
        commands_layout.setContentsMargins(14, 14, 14, 12)
        commands_layout.setSpacing(10)

        bind_actions = QHBoxLayout()
        bind_actions.addWidget(lab("Бінди", "h2"), 1)
        clear_bind_checks = QPushButton("Прибрати всі галочки")
        clear_bind_checks.clicked.connect(self.clear_bind_checks)
        bind_actions.addWidget(clear_bind_checks)
        presets = QPushButton("Вставити головні бінди")
        presets.clicked.connect(self.insert_defaults)
        bind_actions.addWidget(presets)
        binds_layout.addLayout(bind_actions)
        binds_layout.addWidget(lab("Призначення: натисніть кнопку в рядку, а потім клавішу або комбінацію з Ctrl, Alt, Shift чи Win.", "hint", True))
        self.t = QTableWidget(0, 4)
        self.t.setHorizontalHeaderLabels(["Клавіші (напр. alt+f1)", "Текст", "Надсилати", "Відкривати чат перед відправкою"])
        hh = self.t.horizontalHeader()
        hh.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        hh.setSectionResizeMode(0, QHeaderView.Fixed)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.Fixed)
        hh.setSectionResizeMode(3, QHeaderView.Fixed)
        self.t.setColumnWidth(0, 200)
        self.t.setColumnWidth(2, 86)
        self.t.setColumnWidth(3, 220)
        self.t.verticalHeader().setVisible(False)
        self.t.verticalHeader().setDefaultSectionSize(40)
        self.t.setAlternatingRowColors(True)
        self.t.setShowGrid(False)
        self.t.setSelectionBehavior(QTableWidget.SelectRows)
        self.t.setMinimumHeight(180)
        binds_layout.addWidget(self.t, 1)
        row = QHBoxLayout()
        row.setSpacing(8)
        a = QPushButton("+ Додати бінд")
        a.clicked.connect(lambda: self.add({"keys": "", "text": "", "send": True, "open_chat": True}, True))
        d = QPushButton("Видалити вибраний")
        d.setObjectName("danger")
        d.clicked.connect(lambda: self.t.removeRow(self.t.currentRow()))
        s = QPushButton("Зберегти")
        s.setObjectName("primary")
        s.setMinimumWidth(130)
        s.clicked.connect(self.save)
        row.addWidget(a)
        row.addWidget(d)
        row.addStretch(1)
        row.addWidget(s)
        binds_layout.addLayout(row)

        commands_layout.addWidget(lab("Команди", "h2"))
        commands_layout.addWidget(lab("Команда в картці репорту підставляється у поле відповіді. Призначена клавіша вставляє її у чат гри без надсилання.", "hint", True))
        commands_layout.addWidget(lab("Щоб призначити клавішу або комбінацію, натисніть кнопку в рядку й натисніть потрібні клавіші разом.", "hint", True))
        self.ct = QTableWidget(0, 4)
        self.ct.setHorizontalHeaderLabels(["Назва кнопки", "Команда (наприклад /sp {id})", "Клавіші", "Відкривати чат перед вставкою"])
        self.ct.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.ct.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.ct.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.ct.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.ct.setColumnWidth(0, 170)
        self.ct.setColumnWidth(2, 170)
        self.ct.setColumnWidth(3, 220)
        self.ct.verticalHeader().setVisible(False)
        self.ct.verticalHeader().setDefaultSectionSize(40)
        self.ct.setShowGrid(False)
        self.ct.setAlternatingRowColors(True)
        self.ct.setSelectionBehavior(QTableWidget.SelectRows)
        commands_layout.addWidget(self.ct, 1)
        command_actions = QHBoxLayout()
        add_command = QPushButton("+ Додати команду")
        add_command.clicked.connect(lambda: self.add_command({"name": "", "text": "", "keys": "", "open_chat": True}, True))
        remove_command = QPushButton("Видалити команду")
        remove_command.setObjectName("danger")
        remove_command.clicked.connect(lambda: self.ct.removeRow(self.ct.currentRow()))
        clear_command_checks = QPushButton("Прибрати всі галочки")
        clear_command_checks.clicked.connect(self.clear_command_checks)
        save_commands = QPushButton("Зберегти команди")
        save_commands.setObjectName("primary")
        save_commands.clicked.connect(self.save_commands)
        command_actions.addWidget(add_command)
        command_actions.addWidget(remove_command)
        command_actions.addWidget(clear_command_checks)
        command_actions.addStretch(1)
        command_actions.addWidget(save_commands)
        commands_layout.addLayout(command_actions)
        self.tabs.addTab(commands_page, "Команди")
        self.tabs.addTab(binds_page, "Бінди")
        lay.addWidget(self.tabs, 1)
        for b in core.cfg["binds"]:
            self.add(b)
        for command in core.cfg.get("commands", []):
            self.add_command(command)

    def add(self, b, edit=False):
        r = self.t.rowCount()
        self.t.insertRow(r)
        key_button = KeyCaptureButton(b.get("keys", ""))
        key_button.capture_state.connect(self.set_capture_state)
        key_button.captured.connect(lambda _key: self.save())
        self.t.setCellWidget(r, 0, key_button)
        self.t.setItem(r, 1, QTableWidgetItem(b["text"]))
        it = QTableWidgetItem()
        it.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        it.setCheckState(Qt.Checked if b.get("send", True) else Qt.Unchecked)
        it.setTextAlignment(Qt.AlignCenter)
        self.t.setItem(r, 2, it)
        open_it = QTableWidgetItem()
        open_it.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        open_it.setCheckState(Qt.Checked if b.get("open_chat", True) else Qt.Unchecked)
        open_it.setTextAlignment(Qt.AlignCenter)
        self.t.setItem(r, 3, open_it)
        if edit:
            self.t.setCurrentCell(r, 0)
            key_button.setFocus()

    def save(self):
        out = []
        for r in range(self.t.rowCount()):
            key_button = self.t.cellWidget(r, 0)
            ti, si, oi = (self.t.item(r, col) for col in range(1, 4))
            k = key_button.key_value() if isinstance(key_button, KeyCaptureButton) else ""
            tx = (ti.text() if ti else "").strip()
            if tx:
                out.append({"keys": k, "text": tx, "send": bool(si) and si.checkState() == Qt.Checked,
                            "open_chat": bool(oi) and oi.checkState() == Qt.Checked})
        self.core.cfg["binds"] = out
        self.on_save()

    def set_capture_state(self, active):
        self.core.key_capture_active = bool(active)
        if not active:
            self.core.key_capture_cooldown = time.monotonic() + 0.35

    def clear_bind_checks(self):
        for row in range(self.t.rowCount()):
            for column in (2, 3):
                item = self.t.item(row, column)
                if item:
                    item.setCheckState(Qt.Unchecked)
        self.save()

    def insert_defaults(self):
        answer = QMessageBox.question(
            self, "Вставити головні бінди",
            "Поточні бінди буде очищено! Чи точно бажаєте вставити головні бінди?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        self.t.setRowCount(0)
        for bind in BUILTIN_BINDS:
            self.add(bind)
        self.save()

    def add_command(self, command, edit=False):
        row = self.ct.rowCount()
        self.ct.insertRow(row)
        self.ct.setItem(row, 0, QTableWidgetItem(command.get("name", "")))
        self.ct.setItem(row, 1, QTableWidgetItem(command.get("text", "")))
        key_button = KeyCaptureButton(command.get("keys", ""))
        key_button.capture_state.connect(self.set_capture_state)
        key_button.captured.connect(lambda _key: self.save_commands())
        self.ct.setCellWidget(row, 2, key_button)
        open_item = QTableWidgetItem()
        open_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        open_item.setCheckState(Qt.Checked if command.get("open_chat", True) else Qt.Unchecked)
        open_item.setTextAlignment(Qt.AlignCenter)
        self.ct.setItem(row, 3, open_item)
        if edit:
            self.ct.setCurrentCell(row, 0)
            self.ct.editItem(self.ct.item(row, 0))

    def clear_command_checks(self):
        for row in range(self.ct.rowCount()):
            item = self.ct.item(row, 3)
            if item:
                item.setCheckState(Qt.Unchecked)
        self.save_commands()

    def save_commands(self):
        commands = []
        for row in range(self.ct.rowCount()):
            name_item, text_item, open_item = (self.ct.item(row, col) for col in (0, 1, 3))
            name = name_item.text().strip() if name_item else ""
            text = text_item.text().strip() if text_item else ""
            if name and text:
                key_button = self.ct.cellWidget(row, 2)
                keys = key_button.key_value() if isinstance(key_button, KeyCaptureButton) else ""
                commands.append({"name": name, "text": text, "keys": keys,
                                 "open_chat": bool(open_item) and open_item.checkState() == Qt.Checked})
        self.core.cfg["commands"] = commands
        self.on_save()


class PunishmentQueueWorker(QThread):
    progress = Signal(str)

    def __init__(self, cfg, commands, interval):
        super().__init__()
        self.cfg = cfg
        self.commands = list(commands)
        self.interval = max(0.0, float(interval))
        self.stop_requested = False
        self.result = ""

    def stop(self):
        self.stop_requested = True

    def run(self):
        sent = 0
        for index, command in enumerate(self.commands, 1):
            if self.stop_requested:
                break
            if not IS_WIN or not game_hwnd(self.cfg["game_process"]):
                self.result = f"Зупинено: гру не знайдено. Відправлено {sent} з {len(self.commands)} команд."
                return
            try:
                say(self.cfg, command, True)
            except Exception as exc:
                self.result = f"Помилка під час відправлення команди {index}: {exc}. Успішно відправлено {sent}."
                return
            sent += 1
            self.progress.emit(f"Відправлено {sent} з {len(self.commands)}: {command}")
            if index < len(self.commands):
                steps = int(self.interval / 0.05)
                for _ in range(steps):
                    if self.stop_requested:
                        break
                    time.sleep(0.05)
                remainder = self.interval - steps * 0.05
                if remainder > 0 and not self.stop_requested:
                    time.sleep(remainder)
        if self.stop_requested:
            self.result = f"Чергу зупинено. Відправлено {sent} з {len(self.commands)} команд."
        else:
            self.result = f"Готово. Відправлено {sent} команд."


class PunishmentQueuePage(QWidget):
    def __init__(self, core):
        super().__init__()
        self.core = core
        self.worker = None
        lay = page_layout(self, 16)
        lay.addWidget(PageHead("Відправка покарань", "Додай команди у потрібному порядку — тулс відправить їх у гру по черзі."))

        panel = card()
        body = QVBoxLayout(panel)
        body.setContentsMargins(22, 20, 22, 20)
        body.setSpacing(12)
        body.addWidget(lab("Одна команда на рядок. Команда має починатися з /.", "muted"))
        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText("/jail 123456 10 Причина\n/pmute 234567 30 Причина")
        self.editor.setMinimumHeight(250)
        self.editor.setStyleSheet(f"font-family:{MONO_FONT}; font-size:13px;")
        body.addWidget(self.editor, 1)

        controls = QHBoxLayout()
        controls.addWidget(lab("Пауза між командами", "muted"))
        self.interval = QDoubleSpinBox()
        self.interval.setRange(0.2, 15.0)
        self.interval.setDecimals(1)
        self.interval.setSingleStep(0.2)
        self.interval.setSuffix(" с")
        self.interval.setValue(1.0)
        controls.addWidget(self.interval)
        controls.addStretch(1)
        self.start_button = QPushButton("Надіслати чергу")
        self.start_button.setObjectName("primary")
        self.start_button.clicked.connect(self.start_queue)
        controls.addWidget(self.start_button)
        self.stop_button = QPushButton("Зупинити")
        self.stop_button.setObjectName("danger")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_queue)
        controls.addWidget(self.stop_button)
        body.addLayout(controls)
        self.status = lab("Черга не запущена", "hint")
        body.addWidget(self.status)
        lay.addWidget(panel, 1)

    def start_queue(self):
        commands = [line.strip() for line in self.editor.toPlainText().splitlines()
                    if line.strip() and not line.strip().startswith("#")]
        if not commands:
            QMessageBox.information(self, "Відправка покарань", "Додай хоча б одну команду.")
            return
        invalid = [f"{i}: {line}" for i, line in enumerate(commands, 1) if not line.startswith("/")]
        if invalid:
            QMessageBox.warning(self, "Невірний формат", "Кожен рядок має починатися з «/»:\n\n" + "\n".join(invalid[:8]))
            return
        preview = "\n".join(commands[:4])
        if len(commands) > 4:
            preview += f"\n… та ще {len(commands) - 4} команд"
        answer = QMessageBox.question(
            self, "Підтвердження черги",
            f"Буде відправлено {len(commands)} команд у гру в цьому порядку:\n\n{preview}\n\nПродовжити?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status.setText("Запуск черги…")
        self.worker = PunishmentQueueWorker(self.core.cfg, commands, self.interval.value())
        self.worker.progress.connect(self.status.setText)
        self.worker.finished.connect(self.queue_thread_finished)
        self.worker.start()

    def stop_queue(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.status.setText("Зупиняю після поточної команди…")
            self.stop_button.setEnabled(False)

    def queue_finished(self, message):
        self.status.setText(message)
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.worker = None

    def queue_thread_finished(self):
        if self.worker:
            message = self.worker.result
            self.worker.deleteLater()
            self.queue_finished(message)


class AdminPO(QWidget):
    def __init__(self, core, on_save):
        super().__init__()
        self.core, self.on_save = core, on_save
        lay = page_layout(self, 16)
        lay.addWidget(PageHead("Адмін ПО", "Автоматика, моніторинг чату та списки слів."))
        c = card()
        cv = QVBoxLayout(c)
        cv.setContentsMargins(22, 18, 22, 18)
        cv.setSpacing(14)
        self.chk = {}
        for key, txt in (("auto_id_pm", "Авто ID (PM) на F3 і вставка ID на F4"),
                         ("report_reminder_enabled", "Нагадувати про репорт без відповіді"),
                         ("log_chat", "Логувати весь чат сервера у файл")):
            cb = Toggle(txt)
            cb.setChecked(core.cfg[key])
            cb.toggled.connect(lambda v, k=key: self.toggle(k, v))
            cv.addWidget(cb)
            self.chk[key] = cb
        cv.addWidget(lab("Нагадування надходить один раз для кожного нового репорту після заданого часу очікування.", "hint", True))
        lr = QHBoxLayout()
        lr.addWidget(lab(f"Логи чату: {os.path.join(DATA, 'chatlogs')}", "hint"), 1)
        if IS_WIN:
            ob = QPushButton("Відкрити папку")
            ob.setObjectName("ghost")
            ob.clicked.connect(lambda: os.startfile(os.path.join(DATA, "chatlogs")))
            lr.addWidget(ob)
        cv.addLayout(lr)
        lay.addWidget(c)

        tabs_card = card()
        tv = QVBoxLayout(tabs_card)
        tv.setContentsMargins(18, 8, 18, 14)
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.lists = {}
        self._event_history = {key: collections.deque(maxlen=300) for key in ("ac", "bad", "vipviol", "repviol", "form")}
        self._chat_history = collections.deque(maxlen=3000)
        self.EV = {"ac": ("Античіт", C_BAD), "bad": ("Слово", C_NEW), "vipviol": ("VIP", C_ADMIN),
                   "repviol": ("Репорт", C_NEW), "form": ("ФОРМА", C_DONE)}
        for key, title in (("ac", "Античіт"), ("bad", "Заборонені слова"), ("vipviol", "Порушення у VIP"),
                           ("repviol", "Репорти з порушеннями"), ("form", "Форми")):
            lw = feed_list()
            self.lists[key] = lw
            if key == "form":
                form_page = QWidget()
                form_layout = QVBoxLayout(form_page)
                form_layout.setContentsMargins(0, 12, 0, 0)
                form_layout.setSpacing(8)
                self.pending_form_card = card()
                pending_layout = QVBoxLayout(self.pending_form_card)
                pending_layout.setContentsMargins(14, 12, 14, 12)
                pending_layout.setSpacing(8)
                pending_header = QHBoxLayout()
                self.pending_form_badge = lab("ФОРМА", "title")
                self.pending_form_badge.setStyleSheet(f"color:{C_DONE};font-weight:800;letter-spacing:1px;")
                pending_header.addWidget(self.pending_form_badge)
                pending_header.addStretch(1)
                pending_layout.addLayout(pending_header)
                self.pending_form_text = lab("Очікуємо нову форму…", "muted", True)
                self.pending_form_text.setWordWrap(True)
                pending_layout.addWidget(self.pending_form_text)
                pending_actions = QHBoxLayout()
                self.pending_form_accept = QPushButton("Прийняти")
                self.pending_form_accept.setObjectName("ok")
                self.pending_form_accept.clicked.connect(core.accept_pending_form_from_ui)
                self.pending_form_decline = QPushButton("Відхилити")
                self.pending_form_decline.setObjectName("danger")
                self.pending_form_decline.clicked.connect(core.decline_pending_form_from_ui)
                pending_actions.addWidget(self.pending_form_accept)
                pending_actions.addWidget(self.pending_form_decline)
                pending_actions.addStretch(1)
                pending_layout.addLayout(pending_actions)
                form_layout.addWidget(self.pending_form_card)
                test_row = QHBoxLayout()
                test_button = QPushButton("Перевірити форму")
                test_button.setObjectName("primary")
                test_button.clicked.connect(self.test_form_detection)
                test_row.addWidget(test_button)
                form_layout.addLayout(test_row)
                form_layout.addWidget(lab("Команду можна перевірити локально або окремо надіслати в гру.", "hint"))
                command_row = QHBoxLayout()
                command_row.addWidget(lab("Тестова команда", "muted"))
                self.form_test_command = QLineEdit("jail 999999999 1 Yavir Tools test")
                self.form_test_command.setPlaceholderText("jail {ID} {час} причина")
                command_row.addWidget(self.form_test_command, 1)
                form_layout.addLayout(command_row)
                self.form_test_send = QCheckBox("Надіслати тестову команду в гру")
                self.form_test_send.setChecked(bool(core.cfg.get("form_test_send", False)))
                self.form_test_send.toggled.connect(self.set_form_test_send)
                form_layout.addWidget(self.form_test_send)
                form_layout.addWidget(with_empty(lw, "Подій поки немає."), 1)
                self.tabs.addTab(form_page, title)
            else:
                self.tabs.addTab(with_empty(lw, "Подій поки немає."), title)
        self.chatlog = QPlainTextEdit()
        self.chatlog.setReadOnly(True)
        self.chatlog.setMaximumBlockCount(3000)
        self.chatlog.setStyleSheet(f"font-family:{MONO_FONT}; font-size:12px;")
        self.tabs.addTab(self.chatlog, "Лог чату")
        w = QWidget()
        wv = QVBoxLayout(w)
        wv.setContentsMargins(0, 14, 0, 0)
        wv.setSpacing(6)
        wv.addWidget(lab("Заборонені слова (по одному в рядок або через кому)", "muted"))
        self.words = QPlainTextEdit(core.cfg["banned_words"])
        wv.addWidget(self.words)
        wv.addSpacing(6)
        wv.addWidget(lab("Слова-маркери реклами у VIP та репортах", "muted"))
        self.ads = QPlainTextEdit(core.cfg["vip_ad_words"])
        wv.addWidget(self.ads)
        sv = QPushButton("Зберегти списки")
        sv.setObjectName("primary")
        sv.clicked.connect(self.save_words)
        wv.addWidget(sv, 0, Qt.AlignLeft)
        self.tabs.addTab(w, "Списки слів")

        archive_page = QWidget()
        archive_layout = QVBoxLayout(archive_page)
        archive_layout.setContentsMargins(0, 12, 0, 0)
        archive_layout.setSpacing(10)
        archive_layout.addWidget(lab("Архів чатів", "h2"))
        archive_layout.addWidget(lab(
            "Щоденні файли чату зберігаються 7 днів від створення, після чого видаляються автоматично.",
            "hint", True))
        archive_actions = QHBoxLayout()
        self.archive_info = lab("", "muted")
        archive_actions.addWidget(self.archive_info, 1)
        self.archive_refresh = QPushButton("Оновити")
        self.archive_refresh.setObjectName("ghost")
        self.archive_refresh.clicked.connect(self.refresh_chat_archive)
        archive_actions.addWidget(self.archive_refresh)
        self.archive_open = QPushButton("Відкрити файл")
        self.archive_open.setObjectName("ghost")
        self.archive_open.setEnabled(False)
        self.archive_open.clicked.connect(self.open_chat_archive)
        archive_actions.addWidget(self.archive_open)
        open_folder = QPushButton("Папка архіву")
        open_folder.setObjectName("ghost")
        open_folder.clicked.connect(self.open_chat_archive_folder)
        archive_actions.addWidget(open_folder)
        archive_layout.addLayout(archive_actions)
        self.archive_list = QListWidget()
        self.archive_list.setObjectName("rlist")
        self.archive_list.setToolTip("Подвійне натискання відкриває файл чату")
        self.archive_list.itemDoubleClicked.connect(lambda _item: self.open_chat_archive())
        self.archive_list.itemSelectionChanged.connect(
            lambda: self.archive_open.setEnabled(self.archive_list.currentItem() is not None))
        archive_layout.addWidget(self.archive_list, 1)
        self.archive_empty = lab("Файлів архіву поки немає. Увімкніть логування чату вище.", "hint")
        self.archive_empty.setAlignment(Qt.AlignCenter)
        archive_layout.addWidget(self.archive_empty)
        self.tabs.addTab(archive_page, "Архів чатів")

        tv.addWidget(self.tabs)
        lay.addWidget(tabs_card, 1)
        self.tabs.currentChanged.connect(self._sync_visible_tab)
        core.event.connect(self.on_event)
        core.pending_form_changed.connect(self.sync_pending_form)
        self.sync_pending_form(core.pending_form)
        core.chat_line.connect(self.append_chat_batch)
        core.chatlog_created.connect(lambda _path: self.refresh_chat_archive())
        self.archive_timer = QTimer(self)
        self.archive_timer.setInterval(60_000)
        self.archive_timer.timeout.connect(self.refresh_chat_archive)
        self.archive_timer.start()
        self.refresh_chat_archive()

    def refresh_chat_archive(self):
        self.core.prune_chatlogs()
        entries = []
        try:
            for name in os.listdir(CHATLOG_DIR):
                if not (name.startswith("chat_") and name.lower().endswith(".txt")):
                    continue
                path = os.path.join(CHATLOG_DIR, name)
                try:
                    stat = os.stat(path)
                    created = os.path.getctime(path)
                except OSError:
                    continue
                expires = datetime.datetime.fromtimestamp(created + CHATLOG_RETENTION_SECONDS)
                try:
                    day = datetime.datetime.strptime(name[5:-4], "%Y-%m-%d").strftime("%d.%m.%Y")
                except ValueError:
                    day = name
                size_kb = max(1, (stat.st_size + 1023) // 1024)
                entries.append((created, path, f"{day}   ·   {size_kb} КБ   ·   до {expires:%d.%m %H:%M}"))
        except OSError:
            entries = []
        entries.sort(key=lambda row: row[0], reverse=True)
        self.archive_list.clear()
        for _created, path, label_text in entries:
            item = QListWidgetItem(label_text)
            item.setData(Qt.UserRole, path)
            item.setToolTip(path)
            self.archive_list.addItem(item)
        self.archive_info.setText(f"Файлів: {len(entries)}  ·  зберігання 7 днів")
        self.archive_empty.setVisible(not entries)
        self.archive_list.setVisible(bool(entries))
        self.archive_open.setEnabled(self.archive_list.currentItem() is not None)

    def open_chat_archive(self):
        item = self.archive_list.currentItem()
        path = item.data(Qt.UserRole) if item else None
        if path and os.path.isfile(path) and IS_WIN:
            os.startfile(path)

    def open_chat_archive_folder(self):
        os.makedirs(CHATLOG_DIR, exist_ok=True)
        if IS_WIN:
            os.startfile(CHATLOG_DIR)

    def toggle(self, k, v):
        self.core.cfg[k] = v
        self.on_save()

    def sync(self):
        for k, cb in self.chk.items():
            cb.blockSignals(True)
            cb.setChecked(self.core.cfg[k])
            cb.blockSignals(False)
        self.form_test_send.blockSignals(True)
        self.form_test_send.setChecked(bool(self.core.cfg.get("form_test_send", False)))
        self.form_test_send.blockSignals(False)
        self.words.setPlainText(self.core.cfg["banned_words"])
        self.ads.setPlainText(self.core.cfg["vip_ad_words"])

    def save_words(self):
        self.core.cfg["banned_words"] = self.words.toPlainText()
        self.core.cfg["vip_ad_words"] = self.ads.toPlainText()
        self.on_save()

    def set_form_test_send(self, checked):
        self.core.cfg["form_test_send"] = bool(checked)
        self.on_save()

    def sync_pending_form(self, form):
        active = bool(form)
        self.pending_form_card.setProperty("active", active)
        self.pending_form_text.setText(form or "Очікуємо нову форму…")
        self.pending_form_accept.setEnabled(active)
        self.pending_form_decline.setEnabled(active)

    def test_form_detection(self):
        command_text = self.form_test_command.text().strip()
        if not command_text:
            QMessageBox.warning(self, "Перевірка форми", "Вкажи команду для перевірки.")
            return
        sample = "[Мл.Адміністратор] Тестовий Гравець [6900308]: " + command_text
        matched = self.core.rx("form_regex").search(sample)
        data = matched.groupdict() if matched else {}
        detected = ((data.get("form") or data.get("form_rank") or matched.group(0)).strip()
                    if matched else "")
        if not detected:
            message = "Поточний шаблон не розпізнав приклад форми jail. Команду в гру не надсилали."
            add_feed(self.lists["form"], "ТЕСТ", message, C_BAD, 300)
            QMessageBox.warning(self, "Перевірка форми", message)
            return
        command_match = re.search(r":\s*(/?" + FORM_COMMAND_PATTERN + r"\b.+)$", detected, re.I)
        if not command_match:
            message = f"Форму розпізнано, але команду не вдалося витягнути — F2 її не відправить. Знайдено: {detected}"
            add_feed(self.lists["form"], "ТЕСТ", message, C_BAD, 300)
            QMessageBox.warning(self, "Перевірка форми", message)
            return
        command = command_match.group(1).strip()
        if not command.startswith("/"):
            command = "/" + command
        if not self.form_test_send.isChecked():
            message = f"Успіх: форма розпізнана. F2 відправить команду: {command}. Тестове надсилання вимкнене."
            add_feed(self.lists["form"], "ТЕСТ", message, C_DONE, 300)
            QMessageBox.information(self, "Перевірка форми", message)
            return
        if not IS_WIN or not game_hwnd(self.core.cfg["game_process"]):
            message = "Гру не знайдено. Команду не відправлено. Запусти гру та повтори перевірку."
            add_feed(self.lists["form"], "ТЕСТ", message, C_BAD, 300)
            QMessageBox.warning(self, "Перевірка форми", message)
            return
        choice = QMessageBox.question(
            self, "Підтвердження надсилання",
            f"Буде відправлено команду в гру:\n\n{command}\n\nПереконайся, що тестовий ID безпечний. Надіслати?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if choice != QMessageBox.Yes:
            return
        say(self.core.cfg, command, True)
        play(self.core.cfg, "accept")
        message = f"Тестову команду відправлено в гру: {command}"
        add_feed(self.lists["form"], "ТЕСТ", message, C_DONE, 300)
        QMessageBox.information(self, "Перевірка форми", message)

    def on_event(self, kind, text):
        lw = self.lists.get(kind)
        if lw:
            tag, col = self.EV[kind]
            self._event_history[kind].append((text, col))
            if self.isVisible() and self.tabs.currentIndex() == ("ac", "bad", "vipviol", "repviol", "form").index(kind):
                add_feed(lw, "", text, col, 300)

    def append_chat_batch(self, text):
        stamp = datetime.datetime.now().strftime("%H:%M:%S")
        lines = [f"{stamp}  {line}" for line in str(text).splitlines() if line]
        if lines:
            self._chat_history.extend(lines)
            if self.isVisible() and self.tabs.currentWidget() is self.chatlog:
                self.chatlog.appendPlainText("\n".join(lines))

    def _sync_visible_tab(self, index=None):
        if not self.isVisible():
            return
        if self.tabs.currentWidget() is self.chatlog:
            self.chatlog.setPlainText("\n".join(self._chat_history))
            return
        keys = ("ac", "bad", "vipviol", "repviol", "form")
        if 0 <= self.tabs.currentIndex() < len(keys):
            key = keys[self.tabs.currentIndex()]
            lw = self.lists[key]
            lw.clear()
            _tag, color = self.EV[key]
            for text, _stored_color in self._event_history[key]:
                add_feed(lw, "", text, color, 300)

    def showEvent(self, event):
        super().showEvent(event)
        self._sync_visible_tab()


class ComplaintPage(QWidget):
    def __init__(self, core, on_save):
        super().__init__()
        self.core, self.on_save = core, on_save
        self.workers = []
        lay = page_layout(self, 16)
        lay.addWidget(PageHead("Розгляд скарги", "ШІ перевіряє лише відповідність скарги правилам подачі, а не суть конфлікту."))
        sp = QHBoxLayout()
        sp.setSpacing(18)
        a = card()
        av = QVBoxLayout(a)
        av.setContentsMargins(18, 16, 18, 16)
        av.addWidget(lab("Текст скарги", "h2"))
        av.addWidget(lab("Вставте повністю: заголовок, опис і посилання на докази.", "hint"))
        self.inp = QPlainTextEdit()
        self.inp.setPlaceholderText("Вставте скаргу…")
        av.addWidget(self.inp)
        self.doc_tabs = QTabWidget()
        self.doc_tabs.setDocumentMode(True)
        self.doc_tabs.setObjectName("complaintDocs")
        form_tab = QWidget()
        fv = QVBoxLayout(form_tab)
        fv.setContentsMargins(12, 12, 12, 12)
        fv.addWidget(lab("Шаблон форми подачі скарги", "h2"))
        fv.addWidget(lab("Змініть поля під формат вашого сервера; шаблон можна скопіювати.", "hint"))
        self.template = QPlainTextEdit(core.cfg.get("complaint_template", ""))
        fv.addWidget(self.template, 1)
        copy_form = QPushButton("Скопіювати форму")
        copy_form.clicked.connect(lambda: QApplication.clipboard().setText(self.template.toPlainText()))
        fv.addWidget(copy_form, 0, Qt.AlignLeft)
        rules_tab = QWidget()
        rv = QVBoxLayout(rules_tab)
        rv.setContentsMargins(12, 12, 12, 12)
        rv.addWidget(lab("Правила подачі скарг", "h2"))
        rv.addWidget(lab("Ці правила використовує ШІ під час перевірки.", "hint"))
        self.rules = QPlainTextEdit(core.cfg["complaint_rules"])
        rv.addWidget(self.rules, 1)
        self.doc_tabs.addTab(form_tab, "Форма подачі")
        self.doc_tabs.addTab(rules_tab, "Правила подачі скарг")
        sp.addWidget(a, 1)
        sp.addWidget(self.doc_tabs, 1)
        lay.addLayout(sp, 3)
        row = QHBoxLayout()
        row.setSpacing(8)
        self.go = QPushButton("Перевірити скаргу")
        self.go.setObjectName("primary")
        self.go.setMinimumWidth(170)
        self.go.clicked.connect(self.check)
        sv = QPushButton("Зберегти форму й правила")
        sv.clicked.connect(self.save_rules)
        cl = QPushButton("Очистити")
        cl.setObjectName("ghost")
        cl.clicked.connect(lambda: (self.inp.clear(), self.out.clear()))
        row.addWidget(self.go)
        row.addWidget(sv)
        row.addWidget(cl)
        row.addStretch(1)
        lay.addLayout(row)
        res = card()
        rv = QVBoxLayout(res)
        rv.setContentsMargins(18, 16, 18, 16)
        rv.addWidget(lab("Вердикт", "h2"))
        self.out = QTextEdit()
        self.out.setReadOnly(True)
        self.out.setPlaceholderText("Тут з'явиться вердикт ШІ.")
        self.out.setStyleSheet("font-size:14px;")
        rv.addWidget(self.out)
        lay.addWidget(res, 2)

    def save_rules(self):
        self.core.cfg["complaint_template"] = self.template.toPlainText()
        self.core.cfg["complaint_rules"] = self.rules.toPlainText()
        self.on_save()

    def check(self):
        text = self.inp.toPlainText().strip()
        if not text:
            self.out.setPlainText("Спочатку вставте текст скарги.")
            return
        self.save_rules()
        c = self.core.cfg
        system = ("Ти асистент адміністратора. Перевіряй ТІЛЬКИ відповідність скарги правилам її подачі "
                  "(оформлення, обов'язкові поля, докази, терміни, тон), а не суть конфлікту. Відповідай українською "
                  "у форматі:\nВЕРДИКТ: ✅ Порушень правил подачі немає / ❌ Є порушення правил подачі\n"
                  "ПЕРЕЛІК: кожне порушення з номером пункту правил\nЩО ВИПРАВИТИ: коротко.\n"
                  "Якщо даних недостатньо (напр. не видно доказів) - так і напиши.")
        prompt = f"ПРАВИЛА ПОДАЧІ СКАРГ:\n{c['complaint_rules']}\n\nСКАРГА:\n{text}"
        self.out.setPlainText("ШІ перевіряє скаргу…")
        self.go.setEnabled(False)
        w = Worker(lambda: gemini(c, prompt, system))

        def done(t, ok):
            self.out.setPlainText(t if ok else "Помилка: " + t)
            self.go.setEnabled(True)
        w.done.connect(done)
        self.workers.append(w)
        w.start()


AI_CHAT_SUGGESTIONS = [
    ("Відповідь на репорт", "Склади ввічливу відповідь гравцеві на репорт: "),
    ("Причина покарання", "Сформулюй коротку причину покарання за порушення: "),
    ("Перевірити текст", "Перевір цей текст на помилки й тон, виправ його:\n"),
    ("Пояснити правило", "Поясни простими словами, як застосовувати це правило: "),
]


class ChatText(QTextBrowser):
    """Текст повідомлення без рамки: Markdown, сама підлаштовує висоту під ширину."""
    def __init__(self, text, md=True):
        super().__init__()
        self.setFrameShape(QFrame.NoFrame)
        self.setOpenExternalLinks(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet(f"QTextBrowser{{background:transparent;border:none;border-radius:0;padding:0;margin:0;color:{TEXT};font-size:14px;}}")
        self.setViewportMargins(0, 0, 0, 0)
        self.document().setDocumentMargin(0)
        self.setMinimumHeight(22)
        if md:
            self.setMarkdown(text)
        else:
            self.setPlainText(text)
        self.fit()

    def fit(self):
        w = self.viewport().width()
        if w < 60:
            return
        self.document().setTextWidth(w)
        h = int(self.document().size().height()) + 4
        if h != self.height():
            self.setFixedHeight(max(22, h))
        self.verticalScrollBar().setValue(0)

    def showEvent(self, e):
        super().showEvent(e)
        self.fit()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.fit()


class ChatInput(QPlainTextEdit):
    submit = Signal()

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Return, Qt.Key_Enter) and not (e.modifiers() & Qt.ShiftModifier):
            self.submit.emit()
            return
        super().keyPressEvent(e)


class ChatPage(QWidget):
    """Чат із Gemini. Ключ і модель беруться з Налаштування → ШІ Gemini."""
    MAX_SENT, MAX_SAVED = 24, 80

    def __init__(self, core, open_settings):
        super().__init__()
        self.core, self.open_settings = core, open_settings
        self.workers, self.history, self.token, self.busy = [], [], 0, False
        self.typing_row = None
        self.setStyleSheet(
            f"QFrame#chatUser{{background:{ACC_D};border:1px solid #2a4468;border-radius:14px;}}"
            f"QFrame#chatAI{{background:{SURF};border:1px solid {LINE};border-radius:14px;}}"
            f"QFrame#chatErr{{background:#2a1519;border:1px solid #5a2a31;border-radius:14px;}}"
            f"QFrame#chatWarn{{background:#2b2412;border:1px solid #5b4a1c;border-radius:12px;}}"
            f"QLabel#chatMeta{{color:{DIM};font-size:11px;}}"
            f"QLabel#chatPill{{background:{SURF2};border:1px solid {LINE};border-radius:11px;color:{MUTED};padding:3px 10px;font-size:12px;}}"
            f"QLabel#chatHero{{color:{TEXT};font-size:24px;font-weight:600;}}")
        lay = page_layout(self, 14)
        head = QHBoxLayout()
        head.addWidget(PageHead("Чат з ШІ", "Питайте про правила, складайте відповіді гравцям і перевіряйте тексти."), 1)
        self.pill = lab("", "chatPill")
        head.addWidget(self.pill, 0, Qt.AlignTop)
        new = QPushButton("Новий чат")
        new.clicked.connect(self.new_chat)
        cp = QPushButton("Копіювати діалог")
        cp.setObjectName("ghost")
        cp.clicked.connect(self.copy_all)
        head.addWidget(new, 0, Qt.AlignTop)
        head.addWidget(cp, 0, Qt.AlignTop)
        lay.addLayout(head)

        self.warn = QFrame()
        self.warn.setObjectName("chatWarn")
        wl = QHBoxLayout(self.warn)
        wl.setContentsMargins(16, 10, 16, 10)
        wl.addWidget(lab("Не вказано Gemini API ключ — чат не зможе відповідати.", "hint"), 1)
        go = QPushButton("Відкрити налаштування")
        go.clicked.connect(self.open_settings)
        wl.addWidget(go)
        lay.addWidget(self.warn)

        box = card()
        bl = QVBoxLayout(box)
        bl.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.body = QWidget()
        self.rows = QVBoxLayout(self.body)
        self.rows.setContentsMargins(20, 18, 20, 18)
        self.rows.setSpacing(12)
        self.rows.addStretch(1)
        self.scroll.setWidget(self.body)
        bl.addWidget(self.scroll)
        lay.addWidget(box, 1)

        self.empty = QWidget(self.body)
        ev = QVBoxLayout(self.empty)
        ev.setAlignment(Qt.AlignCenter)
        ev.addWidget(lab("Чим допомогти?", "chatHero"), 0, Qt.AlignCenter)
        ev.addWidget(lab("Оберіть заготовку або напишіть своє питання.", "hint"), 0, Qt.AlignCenter)
        ev.addSpacing(10)
        grid = QGridLayout()
        grid.setSpacing(8)
        for i, (title, tpl) in enumerate(AI_CHAT_SUGGESTIONS):
            b = QPushButton(title)
            b.setObjectName("ghost")
            b.clicked.connect(lambda _=False, t=tpl: self.use_template(t))
            grid.addWidget(b, i // 2, i % 2)
        ev.addLayout(grid)
        self.rows.insertWidget(0, self.empty)

        ctx = QHBoxLayout()
        ctx.setSpacing(18)
        self.use_rules = QCheckBox("Правила скарг у контексті")
        self.use_report = QCheckBox("Вибраний репорт у контексті")
        ctx.addWidget(self.use_rules)
        ctx.addWidget(self.use_report)
        ctx.addStretch(1)
        ctx.addWidget(lab("Enter — надіслати · Shift+Enter — новий рядок", "hint"))
        lay.addLayout(ctx)
        row = QHBoxLayout()
        row.setSpacing(10)
        self.inp = ChatInput()
        self.inp.setPlaceholderText("Напишіть повідомлення…")
        self.inp.setFixedHeight(48)
        self.inp.textChanged.connect(self.grow_input)
        self.inp.submit.connect(self.send)
        row.addWidget(self.inp, 1)
        self.btn = QPushButton("Надіслати")
        self.btn.setObjectName("primary")
        self.btn.setMinimumSize(130, 48)
        self.btn.clicked.connect(self.on_button)
        row.addWidget(self.btn)
        lay.addLayout(row)
        self.load()
        self.refresh_state()

    # ---- стан
    def showEvent(self, e):
        super().showEvent(e)
        self.refresh_state()

    def refresh_state(self):
        c = self.core.cfg
        self.pill.setText("Модель: " + (c.get("gemini_model") or "gemini-2.5-flash"))
        self.warn.setVisible(not c.get("gemini_key", "").strip())
        self.empty.setVisible(not self.history)

    def grow_input(self):
        h = int(self.inp.document().size().height()) + 18
        self.inp.setFixedHeight(max(48, min(150, h)))

    def use_template(self, tpl):
        self.inp.setPlainText(tpl)
        self.inp.setFocus()
        self.inp.moveCursor(QTextCursor.End)

    # ---- повідомлення
    def add_message(self, role, text, ts=None, err=False):
        ts = ts or datetime.datetime.now().strftime("%H:%M")
        bubble = QFrame()
        bubble.setObjectName("chatErr" if err else ("chatUser" if role == "user" else "chatAI"))
        bv = QVBoxLayout(bubble)
        bv.setContentsMargins(16, 10, 16, 12)
        bv.setSpacing(4)
        who = "Ви" if role == "user" else ("Помилка" if err else "Gemini")
        bv.addWidget(lab(f"{who} · {ts}", "chatMeta"))
        bv.addWidget(ChatText(text, md=(role == "model" and not err)))
        if role == "model" and not err:
            cp = QPushButton("Копіювати")
            cp.setObjectName("ghost")
            cp.setFixedHeight(28)
            cp.setStyleSheet("padding:2px 12px;font-size:12px;")
            cp.clicked.connect(lambda _=False, t=text: QApplication.clipboard().setText(t))
            bv.addWidget(cp, 0, Qt.AlignLeft)
        if role == "user":
            fm = QFontMetrics(self.font())
            est = max((fm.horizontalAdvance(x) for x in text.split("\n")), default=100) + 56
            bubble.setMaximumWidth(max(160, min(640, est)))
        else:
            bubble.setMaximumWidth(860)
        wrap = QWidget()
        hl = QHBoxLayout(wrap)
        hl.setContentsMargins(0, 0, 0, 0)
        if role == "user":
            hl.addStretch(1)
        hl.addWidget(bubble, 1 if role != "user" else 0)
        if role != "user":
            hl.addStretch(0)
        self.rows.insertWidget(self.rows.count() - 1, wrap)
        self.empty.hide()
        QTimer.singleShot(40, self.to_bottom)
        return wrap

    def to_bottom(self):
        bar = self.scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    def show_typing(self):
        self.typing_row = self.add_message("model", "ШІ думає…", err=False)
        self.typing_row.findChild(QPushButton).hide()

    def hide_typing(self):
        if self.typing_row is not None:
            self.typing_row.setParent(None)
            self.typing_row.deleteLater()
            self.typing_row = None

    # ---- відправка
    def system_text(self):
        c = self.core.cfg
        parts = [c.get("ai_chat_prompt", "").strip()]
        if self.use_rules.isChecked() and c.get("complaint_rules", "").strip():
            parts.append("ПРАВИЛА СЕРВЕРУ (для довідки):\n" + c["complaint_rules"].strip())
        if self.use_report.isChecked():
            r = next((x for x in self.core.reports if x["rid"] == self.core.selected), None)
            if r:
                parts.append(f"ВИБРАНИЙ РЕПОРТ: гравець {r['name']} (ID {r['id']}): {r['text']}")
        return "\n\n".join(p for p in parts if p)

    def on_button(self):
        if self.busy:
            self.token += 1
            self.hide_typing()
            self.set_busy(False)
        else:
            self.send()

    def set_busy(self, busy):
        self.busy = busy
        self.btn.setText("Зупинити" if busy else "Надіслати")
        self.btn.setObjectName("ghost" if busy else "primary")
        repolish(self.btn)

    def send(self):
        text = self.inp.toPlainText().strip()
        if not text or self.busy:
            return
        c = self.core.cfg
        if not c.get("gemini_key", "").strip():
            self.refresh_state()
            self.add_message("model", "Спочатку вкажіть Gemini API ключ у Налаштування → ШІ Gemini.", err=True)
            return
        self.inp.clear()
        self.history.append({"role": "user", "text": text, "ts": datetime.datetime.now().strftime("%H:%M")})
        self.add_message("user", text, self.history[-1]["ts"])
        sent = [{"role": m["role"], "text": m["text"]} for m in self.history[-self.MAX_SENT:]]
        while sent and sent[0]["role"] != "user":
            sent.pop(0)
        system = self.system_text()
        self.token += 1
        token = self.token
        self.set_busy(True)
        self.show_typing()
        w = Worker(lambda: gemini_chat(c, sent, system))
        w.done.connect(lambda t, ok, tok=token: self.on_done(t, ok, tok))
        w.finished.connect(lambda w=w: self.workers.remove(w) if w in self.workers else None)
        self.workers.append(w)
        w.start()

    def on_done(self, text, ok, token):
        if token != self.token:
            return
        self.hide_typing()
        self.set_busy(False)
        if ok:
            self.history.append({"role": "model", "text": text, "ts": datetime.datetime.now().strftime("%H:%M")})
            self.add_message("model", text, self.history[-1]["ts"])
            self.save()
        else:
            self.add_message("model", text, err=True)

    # ---- службове
    def new_chat(self):
        self.token += 1
        self.hide_typing()
        self.set_busy(False)
        self.history.clear()
        while self.rows.count() > 2:
            item = self.rows.takeAt(1)
            if item.widget():
                item.widget().deleteLater()
        self.save()
        self.refresh_state()

    def copy_all(self):
        out = "\n\n".join(("Ви: " if m["role"] == "user" else "ШІ: ") + m["text"] for m in self.history)
        QApplication.clipboard().setText(out)

    def save(self):
        try:
            with open(AI_CHAT_PATH, "w", encoding="utf-8") as f:
                json.dump(self.history[-self.MAX_SAVED:], f, ensure_ascii=False)
        except OSError:
            pass

    def load(self):
        try:
            with open(AI_CHAT_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            return
        for m in data if isinstance(data, list) else []:
            if isinstance(m, dict) and m.get("role") in ("user", "model") and m.get("text"):
                self.history.append({"role": m["role"], "text": str(m["text"]), "ts": str(m.get("ts", ""))})
                self.add_message(m["role"], str(m["text"]), str(m.get("ts", "")) or None)


SCHEMA = [
    ("Налаштування профілю", [("admin_name", "Ім'я адміністратора", "str"),
                 ("admin_level", "Рівень адмін. прав", "level"),
                 ("admin_position", "Посада", "position"),
                 ("avatar_path", "Аватар профілю (JPG/JPEG/PNG/IMG)", "image")]),
    ("Користувачі", [("users_bulk_delete_mode", "Режим видалення користувачів", "bool")]),
    ("Гра та лог чату", [("game_process", "Процес гри", "str"),
                         ("log_path", "Файл console.log MTA (порожньо = авто)", "file"),
                         ("chat_open_delay", "Затримка після відкриття чату, мс", "int")]),
    ("Гарячі клавіші", [("key_pm", "Авто ID (PM)", "str"), ("key_id", "F4: ID останнього взятого або вибраного репорту", "str"),
                        ("id_open_chat", "Відкривати чат перед вставленням ID через F4", "bool"),
                        ("key_form", "Прийняти останню форму", "str"),
                        ("key_reject_form", "Відхилити форму (F1)", "str"),
                        ("key_overlay_menu", "Відкрити ігрову панель Yavir Tools (Alt+Z)", "str")]),
    ("Команди", [("admin_chat_cmd", "Команда адмін-чату", "str"), ("reply_cmd", "Відповідь на репорт", "str"),
                 ("mute_cmd", "Форма муту за рекламу", "str"),
                 ("form_accepted_msg", "Повідомлення в адмін-чаті після прийняття форми", "str"),
                 ("form_declined_msg", "Повідомлення в адмін-чаті після відхилення форми", "str")]),
    ("Оформлення", [("liquid_glass", "Liquid Glass", "bool"),
                    ("liquid_glass_blur", "Розмиття кольорового фону", "int"),
                    ("liquid_glass_strength", "Прозорість панелей", "int"),
                    ("liquid_glass_edge", "Відблиск на краях", "int")]),
    ("Формати рядків чату (regex)", [("report_regex", "Репорт", "str"), ("colleague_regex", "Відповідь колеги", "str"),
                                     ("form_regex", "Форма", "str"), ("form_reject_regex", "Відхилення форми", "str"),
                                     ("vip_regex", "VIP чат", "str"), ("ac_regex", "Античіт", "str")]),
    ("Інтерфейс", [("ui_scale", "Масштаб інтерфейсу (0.7–2.0, типово 1.0)", "float")]),
    ("Оновлення", [("update_version_url_cfg", "URL файлу з останньою версією (порожньо = не перевіряти)", "str")]),
    ("Норма та оверлей", [("norm_hours", "Норма, годин на добу", "float"),
                          ("norm_overlay", "Показувати норму оверлеєм на екрані", "bool"),
                          ("overlay_compact", "Компактний оверлей (тільки норма, без репортів і плеєра)", "bool"),
                          ("overlay_enabled", "Показувати оверлей репортів", "bool"),
                          ("overlay_test_mode", "Тест оверлею з нормою (показувати на робочому столі)", "bool"),
                          ("overlay_edit_mode", "Режим редагування оверлею (перетягування заголовка та ручки розміру)", "bool"),
                          ("overlay_scale", "Масштаб оверлею (можна змінити мишкою в режимі редагування)", "int"),
                          ("overlay_x", "Позиція оверлею по горизонталі (X)", "int"),
                          ("overlay_y", "Позиція оверлею по вертикалі (Y)", "int"),
                          ("overlay_max_rows", "Максимум рядків репортів в оверлеї", "int"),
                          ("report_expire_minutes", "Прибирати репорт через хвилин (0 = вимкнено)", "int")]),
    ("Відповіді та сповіщення", [("report_sound", "Звук для нового репорту (спочатку вимкнено)", "bool"),
                                  ("report_reminder_minutes", "Нагадати про невідповіданий репорт через хвилин", "int")]),
    ("Dynamic Island", [("dynamic_island", "Dynamic Island замість спливаючих сповіщень", "bool"),
                        ("notification_width", "Максимальна ширина (px)", "int"),
                        ("notification_height", "Мінімальна висота (px)", "int")]),
    ("Spotify", [("spotify_overlay_enabled", "Показувати плашку поточного треку Spotify", "bool")]),
    ("Новорічне оформлення", [
        ("winter_garland", "Легка гірлянда", "bool"),
        ("winter_snowfall", "Маленькі сніжинки", "bool"),
    ]),
    ("Збереження", [("autosave_settings", "Автозбереження налаштувань", "bool")]),
    ("Моніторинг VIP", [("vip_monitor_start", "Початок перевірки VIP-чату", "time"),
                        ("vip_monitor_end", "Завершення перевірки VIP-чату", "time")]),
    ("Картка репорту", [("quick_binds_count", "Кількість швидких відповідей на картці", "int")]),
    ("Звуки (.wav; порожньо = потужний стандартний сигнал)", [
        ("sound_volume", "Гучність звуків (%)", "int"),
        ("snd_take", "Взято репорт", "file"), ("snd_reply", "Відповідь надіслано", "file"),
        ("snd_reject", "Форму відхилено", "file"), ("snd_accept", "Форму надіслано", "file"),
        ("snd_warn", "Попередження", "file"), ("snd_vip", "Реклама у VIP", "file"),
        ("snd_ac", "Спрацював античіт", "file"), ("snd_report", "Новий репорт", "file"),
        ("snd_ui", "Збереження налаштувань", "file")]),
    ("ШІ Gemini", [("gemini_key", "API ключ", "pass"), ("gemini_model", "Модель", "str"),
                   ("ai_auto", "Автоматично пропонувати відповідь при виборі репорту", "bool"),
                   ("ai_report_prompt", "Інструкція ШІ для репортів", "text"),
                   ("ai_chat_prompt", "Інструкція ШІ для чату", "text")]),
]


class SliderField(QWidget):
    """Повзунок зі значенням у %. API як у QSpinBox (value/setValue/valueChanged)."""
    valueChanged = Signal(int)

    def __init__(self):
        super().__init__()
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 4, 0, 4)
        h.setSpacing(14)
        self.sl = QSlider(Qt.Horizontal)
        self.sl.setRange(0, 100)
        self.sl.setSingleStep(5)
        self.sl.setPageStep(10)
        self.sl.setMinimumHeight(22)
        self.val = QLabel("0 %")
        self.val.setMinimumWidth(48)
        self.val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        h.addWidget(self.sl, 1)
        h.addWidget(self.val)
        self.sl.valueChanged.connect(self._ch)
        self.setStyleSheet("QSlider::groove:horizontal{height:6px;background:rgba(255,255,255,40);border-radius:3px;}"
                           "QSlider::sub-page:horizontal{background:#6ea8ff;border-radius:3px;}"
                           "QSlider::handle:horizontal{width:30px;height:20px;margin:-8px 0;border-radius:10px;background:#fff;}")

    def _ch(self, v):
        self.val.setText(f"{v} %")
        self.valueChanged.emit(v)

    def value(self):
        return self.sl.value()

    def setValue(self, v):
        self.sl.setValue(int(v))
        self.val.setText(f"{int(v)} %")


class SettingsPage(QWidget):
    def __init__(self, core, on_save, on_config_import=None):
        super().__init__()
        self.core, self.on_save = core, on_save
        self.on_config_import = on_config_import
        self.w = {}
        self.island_test, self._island_i = None, 0
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        top = QWidget()
        tl = QVBoxLayout(top)
        tl.setContentsMargins(32, 26, 32, 10)
        tl.addWidget(PageHead("Налаштування", "Збереження вручну або автоматично — на ваш вибір."))
        outer.addWidget(top)

        mid = QHBoxLayout()
        mid.setContentsMargins(32, 0, 12, 0)
        mid.setSpacing(20)
        self.nav = QListWidget()
        self.nav.setObjectName("sections")
        self.nav.setFixedWidth(260)
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.nav.setTextElideMode(Qt.ElideRight)
        mid.addWidget(self.nav)
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setFrameShape(QFrame.NoFrame)
        body = QWidget()
        body.setObjectName("sbody")
        body.setStyleSheet("QWidget#sbody { background: transparent; }")
        bv = QVBoxLayout(body)
        bv.setContentsMargins(0, 0, 20, 16)
        bv.setSpacing(16)
        self.cards = []
        for title, fields in SCHEMA:
            main, _, hint = title.partition("(")
            c = card()
            g = QGridLayout(c)
            g.setContentsMargins(22, 18, 22, 20)
            g.setHorizontalSpacing(20)
            g.setVerticalSpacing(12)
            r0 = 1
            if main.strip() == "Оформлення":
                badge = QLabel("НОВЕ")
                badge.setStyleSheet("background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #8bbaff,stop:1 #6a8cff);"
                                    "color:#06101f;font-size:11px;font-weight:700;border-radius:9px;padding:2px 9px;")
                badge.setFixedHeight(20)
                head_row = QHBoxLayout()
                head_row.setSpacing(10)
                head_row.addWidget(lab(main.strip(), "title"))
                head_row.addWidget(badge)
                head_row.addStretch(1)
                g.addLayout(head_row, 0, 0, 1, 2)
                g.addWidget(lab("Напівпрозорі скляні панелі, кольорове тло та відблиск на краях.", "hint", True), 1, 0, 1, 2)
                r0 = 2
            else:
                g.addWidget(lab(main.strip(), "title"), 0, 0, 1, 2)
            if hint:
                g.addWidget(lab(hint.rstrip(") ").capitalize(), "hint", True), 1, 0, 1, 2)
                r0 = 2
            for i, (key, label, typ) in enumerate(fields, r0):
                g.addWidget(lab(label, "muted", True), i, 0, Qt.AlignTop)
                g.addWidget(self.make(key, typ), i, 1)
            if main.strip() == "Dynamic Island":
                box = QFrame()
                box.setObjectName("reportMessage")
                bl = QVBoxLayout(box)
                bl.setContentsMargins(14, 12, 14, 12)
                bl.setSpacing(9)
                bl.addWidget(lab("Тестове повідомлення", "h2"))
                bl.addWidget(lab("Кожне натискання показує наступний тип: репорт, форма, відповідь, дія, античіт, музика. Тест нікуди не записується і не надсилається в гру.", "hint", True))
                btn = QPushButton("Тестове повідомлення")
                btn.setObjectName("primary")
                btn.setCursor(Qt.PointingHandCursor)
                btn.clicked.connect(self.run_island_test)
                row_btn = QHBoxLayout()
                row_btn.addWidget(btn)
                row_btn.addStretch(1)
                bl.addLayout(row_btn)
                g.addWidget(box, r0 + len(fields), 0, 1, 2)
            if main.strip() == "Оформлення":
                tiles = QHBoxLayout()
                tiles.setSpacing(12)
                for txt, css in (("Вимкнено · класична тема", "background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #1a2230,stop:1 #0d1218);border:1px solid #2a3547;"),
                                 ("Увімкнено · Liquid Glass", "background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 rgba(150,110,255,150),stop:1 rgba(110,168,255,60));border:1px solid rgba(255,255,255,90);border-top:1px solid rgba(255,255,255,170);")):
                    t = QLabel(txt)
                    t.setStyleSheet(css + "border-radius:16px;padding:12px;font-weight:600;")
                    t.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
                    t.setFixedHeight(84)
                    tiles.addWidget(t, 1)
                g.addLayout(tiles, r0 + len(fields), 0, 1, 2)
            if main.strip() == "Картка репорту":
                test_box = QFrame()
                test_box.setObjectName("reportMessage")
                test_layout = QVBoxLayout(test_box)
                test_layout.setContentsMargins(14, 12, 14, 12)
                test_layout.setSpacing(9)
                test_layout.addWidget(lab("Тестовий репорт", "h2"))
                test_layout.addWidget(lab("Покажіть приклад в оверлеї та вкладці «Репорти». Тест не записується в базу гравців і не надсилається в гру.", "hint", True))
                self.test_report_name = QLineEdit("Ігор Гринюк")
                self.test_report_name.setPlaceholderText("Ім'я гравця")
                self.test_report_id = QLineEdit("6754126")
                self.test_report_id.setPlaceholderText("ID гравця")
                self.test_report_text = QLineEdit("Я застряг")
                self.test_report_text.setPlaceholderText("Текст тестового репорту")
                test_layout.addWidget(self.test_report_name)
                test_layout.addWidget(self.test_report_id)
                test_layout.addWidget(self.test_report_text)
                test_actions = QHBoxLayout()
                test_report_button = QPushButton("Показати тестовий репорт")
                test_report_button.setObjectName("primary")
                test_report_button.setCursor(Qt.PointingHandCursor)
                test_report_button.clicked.connect(self.preview_report_overlay)
                test_actions.addWidget(test_report_button)
                hide_test_report_button = QPushButton("Приховати тестовий репорт")
                hide_test_report_button.clicked.connect(self.hide_report_overlay_preview)
                test_actions.addWidget(hide_test_report_button)
                test_actions.addStretch(1)
                test_layout.addLayout(test_actions)
                g.addWidget(test_box, r0 + len(fields), 0, 1, 2)
            g.setColumnMinimumWidth(0, 230)
            g.setColumnStretch(1, 1)
            bv.addWidget(c)
            self.cards.append(c)
            self.nav.addItem(main.strip())
        words_card = card()
        words_layout = QVBoxLayout(words_card)
        words_layout.setContentsMargins(22, 18, 22, 20)
        words_layout.setSpacing(10)
        words_layout.addWidget(lab("Типові списки слів", "title"))
        words_layout.addWidget(lab("Встановлює рекомендовані маркери реклами одночасно для заборонених слів і VIP-чату. Після встановлення списки зберігаються між запусками.", "hint", True))
        default_words = QPushButton("Встановити вказані заборонені слова за замовчуванням")
        default_words.clicked.connect(self.reset_word_defaults)
        words_layout.addWidget(default_words, 0, Qt.AlignLeft)
        bv.addWidget(words_card)
        self.cards.append(words_card)
        self.nav.addItem("Типові слова")
        t = card()
        tv = QVBoxLayout(t)
        tv.setContentsMargins(22, 18, 22, 20)
        tv.setSpacing(10)
        tv.addWidget(lab("Тест формату рядка", "title"))
        tv.addWidget(lab("Вставте рядок з чату, щоб перевірити, які правила його розпізнають.", "hint"))
        self.test_in = QLineEdit()
        self.test_in.setPlaceholderText("Рядок з чату…")
        tv.addWidget(self.test_in)
        tb = QPushButton("Перевірити regex")
        tb.clicked.connect(lambda: self.test_out.setPlainText(self.core.test_line(self.test_in.text())))
        tv.addWidget(tb, 0, Qt.AlignLeft)
        self.test_out = QPlainTextEdit()
        self.test_out.setReadOnly(True)
        self.test_out.setFixedHeight(130)
        self.test_out.setStyleSheet(f"font-family:{MONO_FONT}; font-size:12px;")
        tv.addWidget(self.test_out)
        bv.addWidget(t)
        self.cards.append(t)
        self.nav.addItem("Тест regex")
        backup_card = card()
        backup_layout = QVBoxLayout(backup_card)
        backup_layout.setContentsMargins(22, 18, 22, 20)
        backup_layout.setSpacing(10)
        backup_layout.addWidget(lab("Резервна копія налаштувань", "title"))
        backup_layout.addWidget(lab("Збережіть параметри у JSON або відновіть їх з копії. Відновлення замінить поточні налаштування.", "hint", True))
        backup_layout.addWidget(lab("Файл може містити ключ ШІ та локальні шляхи. Не передавайте його іншим.", "hint", True))
        backup_actions = QHBoxLayout()
        export_button = QPushButton("Зберегти копію…")
        export_button.clicked.connect(self.export_backup)
        import_button = QPushButton("Відновити з файлу…")
        import_button.clicked.connect(self.import_backup)
        backup_actions.addWidget(export_button)
        backup_actions.addWidget(import_button)
        backup_actions.addStretch(1)
        backup_layout.addLayout(backup_actions)
        bv.addWidget(backup_card)
        self.cards.append(backup_card)
        self.nav.addItem("Резервна копія")
        rn = QPushButton("Скинути норму за сьогодні")
        rn.setObjectName("danger")
        rn.clicked.connect(self.reset_norm)
        bv.addWidget(rn, 0, Qt.AlignLeft)
        bv.addStretch(1)
        sc.setWidget(body)
        mid.addWidget(sc, 1)
        outer.addLayout(mid, 1)
        self.sc = sc
        self.nav.setCurrentRow(0)
        self.nav.currentRowChanged.connect(lambda i: sc.verticalScrollBar().setValue(self.cards[i].y()) if i >= 0 else None)

        bar = QFrame()
        bar.setObjectName("savebar")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(32, 12, 32, 12)
        bl.addWidget(lab("Ключ ШІ та regex зберігаються локально у вашому профілі.", "hint"), 1)
        sv = QPushButton("Зберегти налаштування")
        sv.setObjectName("primary")
        self.save_button = sv
        sv.setMinimumWidth(200)
        sv.setCursor(Qt.PointingHandCursor)
        sv.clicked.connect(lambda: None if self._autosave_enabled() else self.save())
        bl.addWidget(sv)
        outer.addWidget(bar)
        self.load()
        self.autosave_timer = QTimer(self)
        self.autosave_timer.setSingleShot(True)
        self.autosave_timer.setInterval(450)
        self.autosave_timer.timeout.connect(self._run_autosave)
        self._connect_autosave_signals()
        self._update_autosave_button()

    def run_island_test(self):
        i, self._island_i = self._island_i, self._island_i + 1
        if callable(self.island_test):
            self.island_test(i)

    def make(self, key, typ):
        if typ in ("str", "pass"):
            w = QLineEdit()
            if typ == "pass":
                w.setEchoMode(QLineEdit.Password)
            if key.endswith("_regex") or key.endswith("_cmd") or key.endswith("_msg"):
                w.setStyleSheet(f"font-family:{MONO_FONT}; font-size:12px;")
        elif typ == "int" and key in ("liquid_glass_blur", "liquid_glass_strength", "liquid_glass_edge"):
            w = SliderField()
        elif typ == "int":
            w = QSpinBox()
            if key == "overlay_scale":
                w.setRange(70, 150)
                w.setSingleStep(5)
                w.setSuffix(" %")
            elif key == "notification_width":
                w.setRange(280, 800)
                w.setSingleStep(10)
                w.setSuffix(" px")
            elif key == "notification_height":
                w.setRange(72, 240)
                w.setSingleStep(4)
                w.setSuffix(" px")
            else:
                w.setRange(0, 100 if key == "sound_volume" else 30 if key == "quick_binds_count" else 5000)
            w.setMaximumWidth(150)
        elif typ == "float":
            w = QDoubleSpinBox()
            w.setRange(0, 24)
            w.setSingleStep(0.25)
            w.setMaximumWidth(150)
        elif typ == "bool":
            w = Toggle()
        elif typ == "time":
            w = QTimeEdit()
            w.setDisplayFormat("HH:mm")
            w.setMaximumWidth(150)
        elif typ == "level":
            w = QComboBox()
            w.addItems(LEVELS)
        elif typ == "position":
            w = QComboBox()
            w.addItems(POSITIONS)
        elif typ == "text":
            w = QPlainTextEdit()
            w.setFixedHeight(100)
        elif typ == "choice":
            w = QComboBox()
        elif typ == "folder":
            box = QWidget()
            h = QHBoxLayout(box)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(6)
            le = QLineEdit()
            br = QPushButton("Обрати папку…")
            br.clicked.connect(lambda: le.setText(QFileDialog.getExistingDirectory(self, "Папка для відео", le.text() or "") or le.text()))
            h.addWidget(le, 1)
            h.addWidget(br)
            self.w[key] = (le, "str")
            return box
        elif typ in ("file", "image"):
            box = QWidget()
            h = QHBoxLayout(box)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(6)
            le = QLineEdit()
            br = QPushButton("Огляд…")
            filter_text = "Зображення (*.jpg *.jpeg *.png *.bmp *.webp *.img);;Усі файли (*)" if typ == "image" else "Усі файли (*)"
            br.clicked.connect(lambda: le.setText(QFileDialog.getOpenFileName(self, "Файл", "", filter_text)[0] or le.text()))
            h.addWidget(le, 1)
            h.addWidget(br)
            if key.startswith("snd_"):
                tst = QPushButton("▶")
                tst.setFixedWidth(38)
                tst.setToolTip("Прослухати")
                tst.clicked.connect(lambda _=False, k=key[4:], e=le: play({**self.core.cfg, "snd_" + k: e.text()}, k))
                h.addWidget(tst)
            self.w[key] = (le, "str")
            return box
        self.w[key] = (w, typ)
        return w

    def load(self):
        c = self.core.cfg
        for k, (w, t) in self.w.items():
            v = c[k]
            if t in ("str", "pass"):
                w.setText(str(v))
            elif t in ("int", "float"):
                w.setValue(v)
            elif t == "bool":
                w.setChecked(bool(v))
            elif t in ("level", "position"):
                w.setCurrentText(v)
            elif t == "choice":
                w.setCurrentText(str(v))
            elif t == "text":
                w.setPlainText(v)
            elif t == "time":
                parsed = QTime.fromString(str(v), "HH:mm")
                fallback = QTime(22, 0) if k == "vip_monitor_end" else QTime(11, 0)
                w.setTime(parsed if parsed.isValid() else fallback)

    def _connect_autosave_signals(self):
        for key, (widget, typ) in self.w.items():
            if typ in ("str", "pass") and isinstance(widget, QLineEdit):
                signal = widget.textEdited
            elif typ in ("int", "float"):
                signal = widget.valueChanged
            elif typ == "bool":
                signal = widget.toggled
            elif typ in ("level", "choice", "position"):
                signal = widget.currentTextChanged
            elif typ == "text":
                signal = widget.textChanged
            elif typ == "time":
                signal = widget.timeChanged
            else:
                continue
            signal.connect(lambda *_args, setting=key: self._setting_changed(setting))

    def _autosave_enabled(self):
        field = self.w.get("autosave_settings")
        return bool(field and field[0].isChecked())

    def _setting_changed(self, key):
        if key == "autosave_settings":
            self._update_autosave_button()
            self.autosave_timer.start()
        elif self._autosave_enabled():
            self.autosave_timer.start()

    def _update_autosave_button(self):
        enabled = self._autosave_enabled()
        self.save_button.setText("Автозбереження увімкнено" if enabled else "Зберегти налаштування")
        self.save_button.setObjectName("ok" if enabled else "primary")
        self.save_button.setEnabled(True)
        self.save_button.setStyleSheet("background:#173a26; border:1px solid #25673f; color:#89d7a5; font-weight:700;" if enabled else "")
        self.save_button.style().unpolish(self.save_button)
        self.save_button.style().polish(self.save_button)

    def _run_autosave(self):
        if self._autosave_enabled() or self.w["autosave_settings"][0].isChecked() != bool(self.core.cfg.get("autosave_settings", False)):
            self.save(silent=True)

    def _protected_changed(self):
        c = self.core.cfg
        changed = []
        for k in ("admin_level", "admin_name"):
            if k not in self.w:
                continue
            w, t = self.w[k]
            new = w.currentText() if t == "level" else w.text().strip()
            if new != c.get(k, DEFAULT.get(k)):
                changed.append((k, w, t))
        return changed

    def save(self, silent=False):
        c = self.core.cfg
        if POLICY is not None and POLICY.has_password():
            changed = self._protected_changed()
            if changed:
                ok = (not silent) and ask_owner_password(self, "Зміна імені або рівня адміністратора потребує пароля власника.")
                if not ok:
                    for k, w, t in changed:
                        old = c.get(k, DEFAULT.get(k))
                        if t == "level":
                            w.setCurrentText(old)
                        else:
                            w.setText(old)
                    if not silent:
                        QMessageBox.warning(self, "Доступ заборонено", "Ім'я та рівень адміна можна змінити лише з паролем власника.")
        for k, (w, t) in self.w.items():
            if t in ("str", "pass"):
                c[k] = w.text().strip()
            elif t in ("int", "float"):
                c[k] = w.value()
            elif t == "bool":
                c[k] = w.isChecked()
            elif t in ("level", "position"):
                c[k] = w.currentText()
            elif t == "choice":
                c[k] = w.currentText()
            elif t == "text":
                c[k] = w.toPlainText()
            elif t == "time":
                c[k] = w.time().toString("HH:mm")
        self._update_autosave_button()
        self._quiet_save = bool(silent)
        try:
            self.on_save()
        finally:
            self._quiet_save = False

    def export_backup(self):
        suggested = "YavirTools-settings-" + datetime.datetime.now().strftime("%Y%m%d") + ".json"
        path, _ = QFileDialog.getSaveFileName(self, "Зберегти резервну копію", suggested, "JSON (*.json)")
        if not path:
            return
        if not path.lower().endswith(".json"):
            path += ".json"
        payload = {"app": APP, "format_version": 1,
                   "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
                   "settings": self.core.cfg}
        temporary = path + ".tmp"
        try:
            with open(temporary, "w", encoding="utf-8") as stream:
                json.dump(payload, stream, ensure_ascii=False, indent=2)
            os.replace(temporary, path)
            QMessageBox.information(self, "Копію створено", "Резервну копію налаштувань збережено.")
        except Exception as exc:
            try:
                if os.path.exists(temporary):
                    os.remove(temporary)
            except OSError:
                pass
            QMessageBox.critical(self, "Не вдалося зберегти копію", str(exc))

    def import_backup(self):
        path, _ = QFileDialog.getOpenFileName(self, "Відновити налаштування", "", "JSON (*.json)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8-sig") as stream:
                payload = json.load(stream)
            restored = payload.get("settings", payload) if isinstance(payload, dict) else None
            if not isinstance(restored, dict):
                raise ValueError("Файл не містить об'єкта налаштувань.")
            known = {}
            for key, default in DEFAULT.items():
                if key not in restored:
                    continue
                value = restored[key]
                if isinstance(default, bool):
                    valid = isinstance(value, bool)
                elif isinstance(default, int):
                    valid = isinstance(value, int) and not isinstance(value, bool)
                elif isinstance(default, float):
                    valid = isinstance(value, (int, float)) and not isinstance(value, bool)
                else:
                    valid = isinstance(value, type(default))
                if valid:
                    known[key] = value
            if not known:
                raise ValueError("У файлі немає сумісних параметрів Yavir Tools.")
        except Exception as exc:
            QMessageBox.critical(self, "Не вдалося прочитати копію", str(exc))
            return
        answer = QMessageBox.question(
            self, "Відновити налаштування",
            "Поточні налаштування буде замінено параметрами з файлу. Продовжити?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        replacement = json.loads(json.dumps(DEFAULT, ensure_ascii=False))
        replacement.update(known)
        keep_access = self.core.cfg.get("access")
        if keep_access is not None:
            replacement["access"] = keep_access
        if POLICY is not None and POLICY.has_password():
            for k in ("admin_level", "admin_name"):
                replacement[k] = self.core.cfg.get(k, DEFAULT[k])
        self.core.cfg.clear()
        self.core.cfg.update(replacement)
        self.load()
        self.on_save()
        if self.on_config_import:
            self.on_config_import()
        QMessageBox.information(self, "Налаштування відновлено", "Параметри застосовано та збережено.")

    def reset_word_defaults(self):
        answer = QMessageBox.question(
            self, "Встановити типові списки",
            "Обидва поточні списки слів буде замінено рекомендованими маркерами купівлі, продажу й реклами. Продовжити?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        self.core.cfg["banned_words"] = DEFAULT["vip_ad_words"]
        self.core.cfg["vip_ad_words"] = DEFAULT["vip_ad_words"]
        self.on_save()

    def preview_report_overlay(self):
        window = self.window()
        preview = getattr(window, "preview_test_report", None)
        if callable(preview):
            preview(self.test_report_name.text(), self.test_report_id.text(), self.test_report_text.text())

    def hide_report_overlay_preview(self):
        window = self.window()
        hide_preview = getattr(window, "hide_test_report_preview", None)
        if callable(hide_preview):
            hide_preview()

    def reset_norm(self):
        self.core.cfg["norm_seconds"] = 0
        self.on_save()



class AccessPage(QWidget):
    """Редактор прав: захищений паролем власника. Галочка = функція ДОЗВОЛЕНА."""
    published = Signal(bool, str)
    checked = Signal(str)

    def __init__(self, core, on_apply):
        super().__init__()
        self.core, self.on_apply = core, on_apply
        self.unlocked = False
        self.current_profile = None
        self.checks = {}
        self._pending = set()
        lay = page_layout(self, 16)
        lay.addWidget(PageHead("Права доступу", "Керування тим, що дозволено адміністраторам. Лише для власника."))
        self.stack = QStackedWidget()
        lay.addWidget(self.stack, 1)

        # --- екран блокування
        lock = QWidget()
        lv = QVBoxLayout(lock)
        lv.setContentsMargins(0, 0, 0, 0)
        c = card()
        cv = QVBoxLayout(c)
        cv.setContentsMargins(24, 22, 24, 22)
        cv.setSpacing(12)
        self.lock_title = lab("", "title")
        self.lock_hint = lab("", "hint", True)
        self.pw1 = QLineEdit()
        self.pw1.setEchoMode(QLineEdit.Password)
        self.pw1.setPlaceholderText("Пароль власника")
        self.lock_btn = QPushButton("Відкрити")
        self.lock_btn.setObjectName("primary")
        self.lock_btn.setCursor(Qt.PointingHandCursor)
        self.lock_btn.clicked.connect(self.unlock_or_create)
        self.pw1.returnPressed.connect(self.unlock_or_create)
        self.lock_msg = lab("", "hint", True)
        for w in (self.lock_title, self.lock_hint, self.pw1, self.lock_btn, self.lock_msg):
            cv.addWidget(w)
        row = QHBoxLayout()
        row.addWidget(c, 1)
        row.addStretch(1)
        lv.addLayout(row)
        lv.addStretch(1)
        self.stack.addWidget(lock)

        # --- редактор
        ed = QWidget()
        ev = QVBoxLayout(ed)
        ev.setContentsMargins(0, 0, 0, 0)
        ev.setSpacing(12)
        self.who = lab("", "hint", True)
        ev.addWidget(self.who)
        mid = QHBoxLayout()
        mid.setSpacing(16)
        left = QVBoxLayout()
        self.profiles = QListWidget()
        self.profiles.setObjectName("sections")
        self.profiles.setFixedWidth(280)
        self.profiles.currentRowChanged.connect(self.on_profile)
        left.addWidget(lab("Профілі", "h2"))
        left.addWidget(self.profiles, 1)
        add = QPushButton("+ Профіль за ніком")
        add.clicked.connect(self.add_nick)
        dele = QPushButton("Видалити нік-профіль")
        dele.setObjectName("danger")
        dele.clicked.connect(self.del_nick)
        left.addWidget(add)
        left.addWidget(dele)
        mid.addLayout(left)
        right = QVBoxLayout()
        self.prof_title = lab("", "h2")
        right.addWidget(self.prof_title)
        right.addWidget(lab("Порядок: «Усі користувачі» → рівень → нік. ☑ = дозволено, ☐ = заборонено. "
                            "У рівнях і ніках є ще третій стан ◪ — «не чіпати»: пункт лишається таким, "
                            "як у попередньому шарі. Кожен профіль змінює лише себе.", "hint", True))
        self.scope_lbl = lab("", "hint", True)
        right.addWidget(self.scope_lbl)
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setFrameShape(QFrame.NoFrame)
        body = QWidget()
        body.setStyleSheet("background: transparent;")
        bv = QVBoxLayout(body)
        bv.setContentsMargins(0, 0, 12, 12)
        bv.setSpacing(6)
        group = None
        for fid, label, grp, danger in ACCESS_FEATURES:
            if grp != group:
                group = grp
                bv.addSpacing(8)
                bv.addWidget(lab(grp.upper(), "reportEyebrow"))
            cb = QCheckBox(label)
            cb.setChecked(True)
            cb.stateChanged.connect(self.mark_dirty)
            self.checks[fid] = cb
            bv.addWidget(cb)
        bv.addStretch(1)
        sc.setWidget(body)
        right.addWidget(sc, 1)
        btns = QHBoxLayout()
        self.reset_btn = QPushButton("Скинути заборони рівнів")
        self.reset_btn.setCursor(Qt.PointingHandCursor)
        self.reset_btn.clicked.connect(self.reset_current)
        for text, fn, name in (("Дозволити все", lambda: self.set_all(True), None),
                               ("Заборонити все", lambda: self.set_all(False), None),
                               ("Не чіпати (◪)", lambda: self.set_all(None), None),
                               ("Зберегти", self.save, "primary"),
                               ("Заблокувати", self.lock, None)):
            b = QPushButton(text)
            if text.startswith("Не чіпати"):
                self.inherit_btn = b
            if name:
                b.setObjectName(name)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(fn)
            btns.addWidget(b)
        btns.addWidget(self.reset_btn)
        pub = QPushButton("Опублікувати всім")
        pub.setObjectName("primary")
        pub.setCursor(Qt.PointingHandCursor)
        pub.clicked.connect(lambda: self.publish_async(manual=True))
        btns.addWidget(pub)
        for text, fn in (("Перевірити нік", self.check_nick), ("Перевірити публікацію", self.check_publication)):
            cb_btn = QPushButton(text)
            cb_btn.setCursor(Qt.PointingHandCursor)
            cb_btn.clicked.connect(fn)
            btns.addWidget(cb_btn)
        exp = QPushButton("Експорт прав у файл")
        exp.setCursor(Qt.PointingHandCursor)
        exp.clicked.connect(self.export_policy)
        btns.addWidget(exp)
        btns.addStretch(1)
        self.dirty_lbl = lab("", "hint")
        btns.addWidget(self.dirty_lbl)
        right.addLayout(btns)
        mid.addLayout(right, 1)
        ev.addLayout(mid, 1)
        self.stack.addWidget(ed)
        self.published.connect(self._on_published)
        self.checked.connect(self._on_checked)
        self.refresh_lock()

    # --- блокування
    def refresh_lock(self):
        self.pw1.clear()
        self.lock_msg.clear()
        self.lock_title.setText("Введіть пароль власника")
        self.lock_hint.setText("Пароль власника вже встановлений. Без нього не можна змінювати права "
                               "та ім'я або рівень адміністратора.")
        self.lock_btn.setText("Відкрити")
        self.stack.setCurrentIndex(0)
        self.unlocked = False

    def unlock_or_create(self):
        if POLICY.check_password(self.pw1.text()):
            self.open_editor()
        else:
            self.lock_msg.setText("Невірний пароль.")

    def lock(self):
        self.refresh_lock()

    def hideEvent(self, e):
        super().hideEvent(e)
        if self.unlocked:
            self.refresh_lock()

    # --- редактор
    def open_editor(self):
        self.unlocked = True
        if POLICY.tampered:
            POLICY.commit()
            save_cfg(self.core.cfg)
            self._after_change()
            QMessageBox.information(self, "Права доступу",
                                    "Файл прав було змінено поза програмою. Підпис оновлено — перевірте профілі.")
        self.stack.setCurrentIndex(1)
        self.rebuild_profiles()

    def _profile_title(self, key):
        if key == "all":
            return "Усі користувачі"
        kind, _, val = key.partition(":")
        if kind == "level":
            return ("● " if POLICY.denied_set(key) else "") + val
        return "Нік: " + val

    def rebuild_profiles(self, select=None):
        self.profiles.blockSignals(True)
        self.profiles.clear()
        keys = ["all"] + ["level:" + lv for lv in LEVELS]
        nick_keys = {k for k in POLICY.profile_keys() if str(k).startswith("nick:")}
        nick_keys |= {k for k in self._pending if str(k).startswith("nick:")}
        keys += sorted(nick_keys)
        for k in keys:
            it = QListWidgetItem(self._profile_title(k))
            it.setData(Qt.UserRole, k)
            self.profiles.addItem(it)
        self.profiles.blockSignals(False)
        target = select or "all"
        for i in range(self.profiles.count()):
            if self.profiles.item(i).data(Qt.UserRole) == target:
                self.profiles.setCurrentRow(i)
                break
        else:
            self.profiles.setCurrentRow(0)
        self.update_who()

    def update_who(self):
        lvl = self.core.cfg.get("admin_level", "")
        nick = self.core.cfg.get("admin_name", "")
        warn = "  ⚠ Файл прав пошкоджено — діють аварійні обмеження." if POLICY.tampered else ""
        self.who.setText(f"Поточний користувач: {nick} · {lvl}. Зараз діють: {POLICY.layer_label()}.{warn}")

    def _show_profile(self, key):
        is_all = key == "all"
        base = set(POLICY.layer("all")[0])
        deny, allow = POLICY.layer(key) if not is_all else (base, set())
        for fid, cb in self.checks.items():
            cb.blockSignals(True)
            cb.setEnabled(True)
            label = ACCESS_BY_ID[fid][1]
            if is_all:
                cb.setTristate(False)
                cb.setText(label)
                cb.setChecked(fid not in deny)
                cb.setToolTip("")
            else:
                cb.setTristate(True)
                cb.setText(label + ("   (загальне: заборонено)" if fid in base else ""))
                if fid in deny:
                    cb.setCheckState(Qt.CheckState.Unchecked)
                elif fid in allow:
                    cb.setCheckState(Qt.CheckState.Checked)
                else:
                    cb.setCheckState(Qt.CheckState.PartiallyChecked)
                cb.setToolTip("☑ дозволити явно · ☐ заборонити явно · ◪ не чіпати (як у попередньому шарі)")
            cb.blockSignals(False)

    def on_profile(self, row):
        it = self.profiles.item(row)
        if not it:
            return
        key = it.data(Qt.UserRole)
        self.current_profile = key
        self.inherit_btn.setVisible(key != "all")
        if key == "all":
            self.prof_title.setText("Усі користувачі")
            self.scope_lbl.setText("Базові заборони для кожного адміна. Рівні та нік-профілі можуть "
                                   "додати заборони або явно дозволити пункт поверх них.")
            self.reset_btn.setText("Скинути заборони рівнів")
            self.reset_btn.setVisible(True)
        elif str(key).startswith("level:"):
            level_name = str(key).split(":", 1)[1]
            self.prof_title.setText("Рівень: " + level_name)
            self.scope_lbl.setText("Діє на всіх з рівнем «" + level_name + "» поверх загальних прав. "
                                   "◪ = як у загальних, ☐ = заборонити, ☑ = дозволити, навіть якщо загальне забороняє.")
            self.reset_btn.setText("Прибрати налаштування рівня")
            self.reset_btn.setVisible(True)
        else:
            nick = str(key).split(":", 1)[1]
            self.prof_title.setText("Нік: " + nick)
            pending = key in self._pending and key not in POLICY.profile_keys()
            self.scope_lbl.setText(("Новий нік ще не збережено. " if pending else "") +
                                   "Діє лише на цього адміна, поверх загальних прав і його рівня. "
                                   "◪ = як у загальних/рівня, ☐ = заборонити, ☑ = дозволити.")
            self.reset_btn.setVisible(False)
        self._show_profile(key)
        self.dirty_lbl.clear()

    def mark_dirty(self, *_):
        self.dirty_lbl.setText("Є незбережені зміни")

    def set_all(self, value):
        is_all = self.current_profile == "all"
        for cb in self.checks.values():
            cb.blockSignals(True)
            if is_all:
                cb.setChecked(bool(value))
            elif value is None:
                cb.setCheckState(Qt.CheckState.PartiallyChecked)
            else:
                cb.setCheckState(Qt.CheckState.Checked if value else Qt.CheckState.Unchecked)
            cb.blockSignals(False)
        self.mark_dirty()

    def add_nick(self):
        nick, ok = QInputDialog.getText(self, "Профіль за ніком",
                                        "Нік адміністратора (як у «Ім'я адміністратора»):")
        if not ok:
            return
        nick = nick.strip().casefold()
        if not nick:
            return
        key = "nick:" + nick
        if key not in POLICY.profile_keys():
            self._pending.add(key)
        self.rebuild_profiles(select=key)

    def del_nick(self):
        if not self.current_profile or not str(self.current_profile).startswith("nick:"):
            QMessageBox.information(self, "Профіль", "Видаляти можна лише профілі за ніком.")
            return
        self._pending.discard(self.current_profile)
        if self.current_profile in POLICY.profile_keys():
            POLICY.delete_profile(self.current_profile)
            save_cfg(self.core.cfg)
            self._after_change()
        self.rebuild_profiles()

    def reset_current(self):
        key = self.current_profile
        if key == "all":
            answer = QMessageBox.question(
                self, "Скинути рівні",
                "Прибрати додаткові заборони всіх рівнів? Загальні права й нік-профілі лишаться.",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if answer != QMessageBox.Yes:
                return
            POLICY.clear_level_overrides()
            save_cfg(self.core.cfg)
            self.rebuild_profiles(select="all")
            self.dirty_lbl.setText("Рівні знову без додаткових заборон")
            self._after_change()
            return
        if key and str(key).startswith("level:"):
            POLICY.delete_profile(key)
            save_cfg(self.core.cfg)
            self.rebuild_profiles(select=key)
            self.dirty_lbl.setText("Додаткові заборони рівня прибрано")
            self._after_change()

    def save(self):
        it = self.profiles.currentItem()
        if it is None:
            return
        key = it.data(Qt.UserRole)
        self.current_profile = key
        if key == "all":
            POLICY.set_layer("all", [fid for fid, cb in self.checks.items() if not cb.isChecked()])
        elif str(key).startswith(("level:", "nick:")):
            deny = [fid for fid, cb in self.checks.items() if cb.checkState() == Qt.CheckState.Unchecked]
            allow = [fid for fid, cb in self.checks.items() if cb.checkState() == Qt.CheckState.Checked]
            POLICY.set_layer(key, deny, allow)
        else:
            return
        self._pending.discard(key)
        save_cfg(self.core.cfg)
        self.rebuild_profiles(select=key)
        self.dirty_lbl.setText("Збережено ✔")
        self._after_change()

    def export_policy(self):
        path, _ = QFileDialog.getSaveFileName(self, "Експорт прав", "access_policy.json", "JSON (*.json)")
        if not path:
            return
        profiles = POLICY.data.get("profiles", {})
        payload = {"v": 2, "profiles": profiles, "sig": _profiles_sig(profiles)}
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)
        except Exception as exc:
            QMessageBox.critical(self, "Експорт прав", str(exc))
            return
        QMessageBox.information(
            self, "Експорт прав",
            "Файл збережено. Покладіть його під назвою access_policy.json поруч із програмою на ПК адмінів — "
            "при запуску ці права підтягнуться самі й замінять локальні.")

    def check_nick(self):
        nick, ok = QInputDialog.getText(self, "Перевірка прав", "Нік адміна (так, як він вписаний у його налаштуваннях):")
        if not ok or not nick.strip():
            return
        level, ok = QInputDialog.getItem(self, "Перевірка прав", "Рівень адміна:", LEVELS, 0, False)
        if not ok:
            return
        denied = POLICY.compute(level, nick.strip())
        names = [f[1] for f in ACCESS_FEATURES if f[0] in denied]
        head = ("Нік-профіль «" + nick.strip() + "» знайдено." if POLICY.nick_profile_key(nick)
                else "Нік-профілю немає — діють загальні права й рівень.")
        QMessageBox.information(self, "Права адміна",
                                head + "\n\nЗаборонено (" + str(len(names)) + "):\n" +
                                ("\n".join("• " + n for n in names) if names else "нічого"))

    def check_publication(self):
        url = ACCESS_URL or str(self.core.cfg.get("gist_raw", "") or "")
        if not url:
            QMessageBox.information(self, "Публікація", "Права ще не опубліковано. Натисніть «Опублікувати всім».")
            return
        local = json.loads(json.dumps(POLICY.data.get("profiles", {})))
        self.dirty_lbl.setText("Перевіряю публікацію…")

        def work():
            try:
                remote = fetch_policy_remote(url)
                if remote is None:
                    res = "Файл за посиланням є, але підпис не збігається або формат неправильний."
                elif remote == local:
                    res = "OK: опубліковані права збігаються з вашими. Колеги отримають саме їх."
                else:
                    res = "Опубліковані права ВІДРІЗНЯЮТЬСЯ від ваших. Натисніть «Опублікувати всім»."
                    res += "\n(GitHub іноді віддає стару копію до кількох хвилин — спробуйте перевірити ще раз.)"
            except Exception as exc:
                res = "Не вдалося відкрити посилання:\n" + repr(exc)
            self.checked.emit(res)
        threading.Thread(target=work, daemon=True).start()

    def _on_checked(self, text):
        self.dirty_lbl.clear()
        QMessageBox.information(self, "Публікація прав", text)

    def _after_change(self):
        self.on_apply()
        if self.core.cfg.get("gh_token"):
            self.publish_async()

    def publish_async(self, manual=False):
        token = str(self.core.cfg.get("gh_token", "") or "")
        if not token:
            if not manual:
                return
            token, ok = QInputDialog.getText(
                self, "Публікація прав",
                "GitHub token з правом «gist» (github.com → Settings → Developer settings → "
                "Personal access tokens). Зберігається лише на цьому ПК:", QLineEdit.Password)
            token = token.strip()
            if not ok or not token:
                return
            self.core.cfg["gh_token"] = token
            save_cfg(self.core.cfg)
        profiles = json.loads(json.dumps(POLICY.data.get("profiles", {})))
        gist_id = str(self.core.cfg.get("gist_id", "") or "")
        self.dirty_lbl.setText("Публікую…")

        def work():
            try:
                gid, raw = publish_policy_remote(token, gist_id, profiles)
                self.published.emit(True, gid + "|" + raw)
            except Exception as exc:
                self.published.emit(False, str(exc))
        threading.Thread(target=work, daemon=True).start()

    def _on_published(self, ok, text):
        if not ok:
            self.dirty_lbl.setText("Не вдалося опублікувати")
            QMessageBox.warning(self, "Публікація прав", "Не вдалося опублікувати права:\n" + text)
            return
        gid, raw = text.split("|", 1)
        self.dirty_lbl.setText("Опубліковано ✔")
        changed = self.core.cfg.get("gist_raw") != raw
        self.core.cfg["gist_id"], self.core.cfg["gist_raw"] = gid, raw
        save_cfg(self.core.cfg)
        if changed and not ACCESS_URL:
            QMessageBox.information(
                self, "Публікація прав",
                "Права опубліковано. Щоб інші копії їх підтягували, один раз впишіть у коді рядок:\n\n"
                'ACCESS_URL = "' + raw + '"\n\nі перезберіть exe. Далі будь-яка зміна прав дійде сама.')



# ---------------------------------------------------------------- Spotify / системна медіасесія Windows
class SpotifyWatcher(QThread):
    updated = Signal(dict)
    error = Signal(str)

    def __init__(self):
        super().__init__()
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    async def _cover_bytes(self, props):
        stream = reader = None
        try:
            if not WinDataReader or not props.thumbnail:
                return b""
            stream = await props.thumbnail.open_read_async()
            size = min(int(stream.size), 2 * 1024 * 1024)
            if size <= 0:
                return b""
            reader = WinDataReader(stream.get_input_stream_at(0))
            await reader.load_async(size)
            data = bytearray(size)
            reader.read_bytes(data)
            return bytes(data)
        except Exception:
            return b""
        finally:
            for resource in (reader, stream):
                try:
                    if resource is not None:
                        resource.close()
                except Exception:
                    pass

    async def _poll(self):
        manager = None
        last_key = None
        last_playing = False
        last_error = ""
        while not self._stop_event.is_set():
            try:
                if MediaSessionManager is None:
                    self.error.emit("Медіаконтроль Windows недоступний: перевірте пакет winsdk у збірці.")
                    return
                if manager is None:
                    manager = await MediaSessionManager.request_async()
                sessions = manager.get_sessions()
                session = next((s for s in sessions
                                if "spotify" in str(s.source_app_user_model_id).casefold()), None)
                payload = None
                if session is not None:
                    playback = session.get_playback_info()
                    status = getattr(playback.playback_status, "name", str(playback.playback_status)).upper()
                    playing = status.endswith("PLAYING")
                    if playing:
                        props = await session.try_get_media_properties_async()
                        title = str(props.title or "").strip()
                        artist = str(props.artist or props.album_artist or "").strip()
                        album = str(props.album_title or "").strip()
                        key = (title, artist, album)
                        cover = await self._cover_bytes(props) if key != last_key else b""
                        timeline = session.get_timeline_properties()
                        position = max(0.0, float(timeline.position.total_seconds()))
                        duration = max(0.0, float((timeline.end_time - timeline.start_time).total_seconds()))
                        payload = {"playing": bool(title), "title": title, "artist": artist,
                                   "album": album, "position": position, "duration": duration,
                                   "cover": cover, "track_key": key}
                        last_key = key
                if payload:
                    self.updated.emit(payload)
                    last_playing = bool(payload["playing"])
                elif last_playing:
                    self.updated.emit({"playing": False})
                    last_playing = False
                    last_key = None
                last_error = ""
            except Exception as exc:
                manager = None
                message = str(exc) or exc.__class__.__name__
                if message != last_error:
                    self.error.emit(f"Spotify: {message}")
                    last_error = message
                if last_playing:
                    self.updated.emit({"playing": False})
                    last_playing = False
                    last_key = None
            await asyncio.sleep(1.5)

    def run(self):
        try:
            asyncio.run(self._poll())
        except Exception as exc:
            self.error.emit(f"Spotify: {exc}")


# ---------------------------------------------------------------- оверлей у грі
class Overlay(QWidget):
    position_changed = Signal(int, int)
    size_changed = Signal(int)

    def __init__(self, core, get_norm):
        super().__init__()
        self.core, self.get_norm = core, get_norm
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.NoFocus)
        self.setStyleSheet(f"""
          QFrame#ov {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 rgba(32,42,66,236),stop:1 rgba(10,14,24,240));
                      border: 1px solid rgba(255,255,255,46); border-top: 1px solid rgba(255,255,255,120); border-radius: 20px; }}
          QFrame#ov[editMode="true"] {{ border: 2px solid {C_NEW}; }}
          QLabel {{ color: {TEXT}; background: transparent; }}
          QProgressBar {{ background: rgba(255,255,255,34); border: none; border-radius: 4px; max-height: 8px; min-height: 8px; }}
          QProgressBar::chunk {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #30cfec,stop:0.6 #398bff,stop:1 #7ad59a); border-radius: 4px; }}""")
        o = QVBoxLayout(self)
        o.setContentsMargins(0, 0, 0, 0)
        self.fr = QFrame()
        self.fr.setObjectName("ov")
        o.addWidget(self.fr)
        self.v = QVBoxLayout(self.fr)
        self.v.setContentsMargins(11, 9, 11, 10)
        self.v.setSpacing(5)
        self.v.setAlignment(Qt.AlignTop)
        header = QWidget()
        self.header = header
        header.setMaximumHeight(30)
        header_row = QHBoxLayout(header)
        header_row.setContentsMargins(1, 0, 1, 0)
        header_row.setSpacing(7)
        self.logo = QLabel()
        self.logo.setPixmap(logo_pix(26))
        self.logo.setFixedSize(26, 26)
        self.logo.setAttribute(Qt.WA_TransparentForMouseEvents)
        header_row.addWidget(self.logo)
        self.title = QLabel("Yavir Tools")
        self.title.setStyleSheet(f"color:{TEXT}; font-weight:650; font-size:11px;")
        self.title.installEventFilter(self)
        header_row.addWidget(self.title, 1)
        self.resize_handle = QLabel("◢", self.fr)
        self.resize_handle.setAlignment(Qt.AlignCenter)
        self.resize_handle.setStyleSheet("background:rgba(10,14,19,170); color:#88b4ff; border:1px solid rgba(120,170,240,100); border-radius:5px; font-size:13px;")
        self.resize_handle.setFixedSize(20, 20)
        self.resize_handle.setCursor(Qt.SizeFDiagCursor)
        self.resize_handle.setToolTip("Перетягніть, щоб змінити розмір оверлею")
        self.resize_handle.installEventFilter(self)
        self.resize_handle.hide()
        self.v.addWidget(header)
        self.norm_caption = QLabel("НОРМА ЗА СЬОГОДНІ")
        self.norm_caption.setStyleSheet(f"color:{MUTED}; font-size:9px; font-weight:700; letter-spacing:1px;")
        self.norm = QLabel("")
        self.norm.setTextFormat(Qt.RichText)
        self.norm.setStyleSheet(f"color:{TEXT}; font-weight:800; font-size:15px;")
        self.bar = QProgressBar()
        self.bar.setRange(0, 1000)
        self.bar.setTextVisible(False)
        self.v.addWidget(self.norm_caption)
        self.v.addWidget(self.norm)
        self.v.addWidget(self.bar)
        self.report_heading = QLabel("")
        self.report_heading.setStyleSheet(f"color:{MUTED}; font-size:8px; font-weight:700; letter-spacing:0.5px;")
        self.report_heading.hide()
        self.items = QVBoxLayout()
        self.items.setSpacing(4)
        self.items.setAlignment(Qt.AlignTop)
        self.report_section = QWidget()
        report_section_layout = QVBoxLayout(self.report_section)
        report_section_layout.setContentsMargins(0, 0, 0, 0)
        report_section_layout.setSpacing(3)
        report_section_layout.addWidget(self.report_heading)
        report_section_layout.addLayout(self.items)
        self.report_section.hide()
        self.report_section.setMinimumHeight(0)
        self.report_section.setMaximumHeight(0)
        self.v.addWidget(self.report_section)
        self.music_frame = QFrame()
        self.music_frame.setObjectName("spotifyMusic")
        self.music_frame.setStyleSheet(f"""
          QFrame#spotifyMusic {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 rgba(25,30,44,248), stop:1 rgba(12,16,24,248)); border: 1px solid rgba(110,168,255,100); border-radius: 12px; }}
          QLabel {{ background: transparent; }}
        """)
        music_row = QHBoxLayout(self.music_frame)
        music_row.setContentsMargins(7, 6, 9, 6)
        music_row.setSpacing(8)
        self.music_art = QLabel("♫")
        self.music_art.setFixedSize(46, 46)
        self.music_art.setAlignment(Qt.AlignCenter)
        self.music_art.setStyleSheet(f"background:{ACC_D}; border-radius:8px; color:#fff; font-size:21px; font-weight:600;")
        music_row.addWidget(self.music_art)
        self.music_bg_color = ACC_D
        music_info = QVBoxLayout()
        music_info.setContentsMargins(0, 0, 0, 0)
        music_info.setSpacing(1)
        self.music_title = QLabel("Spotify")
        self.music_title.setStyleSheet(f"color:{TEXT}; font-size:11px; font-weight:700;")
        self.music_title.setMaximumWidth(220)
        self.music_artist = QLabel("")
        self.music_artist.setStyleSheet(f"color:{MUTED}; font-size:10px;")
        self.music_artist.setMaximumWidth(220)
        info_row = QHBoxLayout()
        info_row.setSpacing(5)
        self.music_progress = QProgressBar()
        self.music_progress.setRange(0, 1000)
        self.music_progress.setTextVisible(False)
        self.music_progress.setFixedHeight(4)
        self.music_progress.setStyleSheet(f"QProgressBar {{ background:#303744; border:0; border-radius:2px; }} QProgressBar::chunk {{ background:{ACC}; border-radius:2px; }}")
        self.music_time = QLabel("0:00 / 0:00")
        self.music_time.setStyleSheet(f"color:{MUTED}; font-size:9px;")
        info_row.addWidget(self.music_progress, 1)
        info_row.addWidget(self.music_time)
        music_info.addWidget(self.music_title)
        music_info.addWidget(self.music_artist)
        music_info.addLayout(info_row)
        music_row.addLayout(music_info, 1)
        self.v.addWidget(self.music_frame)
        self.music_frame.hide()
        self.music_frame.setMaximumHeight(0)
        self.music_opacity = QGraphicsOpacityEffect(self.music_frame)
        self.music_opacity.setOpacity(1.0)
        self.music_frame.setGraphicsEffect(self.music_opacity)
        self.music_animation = None
        self.music_expanded = False
        self.music_active = False
        self.music_track_key = None
        self._report_widgets = {}
        self._report_buttons = []
        self._test_preview_report = None
        self._test_preview_generation = 0
        self._overlay_dirty = True
        self._scale_percent = -1
        self._drag = None
        self._resize_anchor = None
        self._resize_start_scale = 100
        self._apply_scale(self.core.cfg.get("overlay_scale", 100), force=True)
        self._edit_mode_cache = None
        self._clickthrough = None
        self._pending_clickthrough = None
        self._pending_clickthrough_since = 0.0
        self.input_timer = QTimer(self)
        self.input_timer.setInterval(40)
        self.input_timer.timeout.connect(self._sync_clickthrough)
        self.input_timer.start()
        self.music_position = 0.0
        self.music_duration = 0.0
        self.music_position_at = time.monotonic()
        self.music_progress_timer = QTimer(self)
        self.music_progress_timer.setInterval(50)
        self.music_progress_timer.timeout.connect(self._tick_music_progress)
        self.music_dismissed_track_key = None
        self._compact_cache = None
        self._rep_cache = {}
        self.wait_timer = QTimer(self)
        self.wait_timer.setInterval(1000)
        self.wait_timer.timeout.connect(self._tick_wait)
        self.wait_timer.start()
        core.reports_changed.connect(self.refresh)

    def showEvent(self, event):
        super().showEvent(event)
        self.input_timer.start()
        if self.music_active:
            self.music_progress_timer.start()
        if self._overlay_dirty:
            self.refresh()

    def hideEvent(self, event):
        self.input_timer.stop()
        self.music_progress_timer.stop()
        super().hideEvent(event)

    def _repeat_count(self, player_id):
        """Скільки звернень від гравця за 7 днів (кеш на хвилину, щоб не смикати базу)."""
        now = time.monotonic()
        cached = self._rep_cache.get(player_id)
        if cached and now - cached[0] < 60:
            return cached[1]
        try:
            n = sum(c for _, c in self.core.players.report_counts_by_day(player_id, 7))
        except Exception:
            n = 0
        self._rep_cache[player_id] = (now, n)
        return n

    @staticmethod
    def _wait_text(report):
        try:
            t = datetime.datetime.strptime(report.get("time", ""), "%H:%M:%S").time()
        except ValueError:
            return ""
        now = datetime.datetime.now()
        sec = (now - datetime.datetime.combine(now.date(), t)).total_seconds()
        if sec < 0:
            sec += 86400
        return f"{int(sec) // 60}:{int(sec) % 60:02d}"

    def _state_text(self, widget, report):
        parts = [report_visual_status(report).upper()]
        wait = self._wait_text(report)
        if wait:
            parts.append(wait)
        n = self._repeat_count(str(report.get("id", "")))
        if n >= 3:
            parts.append(f"×{n}")
        return "  ·  ".join(parts)

    def _tick_wait(self):
        if not self.isVisible() or not self._report_widgets:
            return
        for rid, widget in self._report_widgets.items():
            report = self._test_preview_report if rid == "__settings_test_report__" else self.core.by_rid(rid)
            if not report:
                continue
            text = self._state_text(widget, report)
            if widget.state_label.text() != text:
                widget.state_label.setText(text)

    def _tick_music_progress(self):
        if not self.music_active:
            return
        position = min(self.music_duration, self.music_position + max(0.0, time.monotonic() - self.music_position_at))
        fraction = min(1.0, position / self.music_duration) if self.music_duration else 0.0
        self.music_progress.setValue(int(fraction * 1000))
        elapsed_text = self._time_label(position)
        if not self._last_music_second or int(position) != self._last_music_second:
            self._last_music_second = int(position)
            self.music_time.setText(f"{elapsed_text} / {self._time_label(self.music_duration)}")

    @staticmethod
    def _time_label(seconds):
        seconds = max(0, int(seconds))
        return f"{seconds // 60}:{seconds % 60:02d}"

    def set_music(self, data):
        if (not self.core.cfg.get("spotify_overlay_enabled", True) or not data.get("playing")
                or self.core.cfg.get("overlay_compact", False)):
            self.music_active = False
            self.music_progress_timer.stop()
            if self.music_expanded:
                self._animate_music(False)
            return
        self.music_active = True
        if self.isVisible() and not self.music_progress_timer.isActive():
            self.music_progress_timer.start()
        title = data.get("title", "") or "Spotify"
        artist = data.get("artist", "") or data.get("album", "") or "Зараз відтворюється"
        self.music_title.setText(QFontMetrics(self.music_title.font()).elidedText(title, Qt.ElideRight, 220))
        self.music_title.setToolTip(title)
        self.music_artist.setText(QFontMetrics(self.music_artist.font()).elidedText(artist, Qt.ElideRight, 220))
        self.music_artist.setToolTip(artist)
        album = data.get("album", "") or "Альбом невідомий"
        self.music_frame.setToolTip(f"{title}\n{artist}\n{album}")
        track_key = data.get("track_key")
        if track_key != self.music_dismissed_track_key:
            self.music_dismissed_track_key = None
        elif self.music_dismissed_track_key is not None:
            self.music_active = False
            self.music_progress_timer.stop()
            return
        same_track = track_key == self.music_track_key
        if not same_track:
            self.music_track_key = track_key
            cover = data.get("cover") or b""
            image = QImage.fromData(cover) if cover else QImage()
            if not image.isNull():
                self._music_cover_image = image.copy()
                sample = image.scaled(1, 1, Qt.IgnoreAspectRatio, Qt.SmoothTransformation).pixelColor(0, 0)
                # Pick a deep, muted version of the cover color so the text stays legible.
                r, g, b = sample.red(), sample.green(), sample.blue()
                r, g, b = int(r * 0.40), int(g * 0.40), int(b * 0.40)
                self.music_bg_color = f"rgb({r},{g},{b})"
                self.music_frame.setStyleSheet(f"QFrame#spotifyMusic {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 {self.music_bg_color}, stop:1 rgba(12,16,24,248)); border:1px solid rgba({min(255,r+48)},{min(255,g+48)},{min(255,b+48)},150); border-radius:12px; }} QLabel {{ background:transparent; }}")
                pix = QPixmap.fromImage(image).scaled(self.music_art.size(), Qt.KeepAspectRatioByExpanding,
                                                       Qt.SmoothTransformation)
                self.music_art.setPixmap(pix)
                self.music_art.setText("")
            else:
                self.music_art.setPixmap(QPixmap())
                self.music_art.setText("♫")
        duration = max(0.0, float(data.get("duration", 0)))
        position = max(0.0, float(data.get("position", 0)))
        now = time.monotonic()
        if same_track:
            predicted = min(self.music_duration, self.music_position + max(0.0, now - self.music_position_at))
            # Windows can report a timeline sample from just before the last poll.
            # Keep the clock moving forward for small sampling jitter; larger jumps are seeks.
            if abs(position - predicted) < 2.5:
                position = predicted
        self.music_position = position
        self.music_duration = duration
        self.music_position_at = now
        self._last_music_second = -1
        self._tick_music_progress()
        self.music_progress.setToolTip(
            f"{self._time_label(position)} / {self._time_label(duration)} · залишилось "
            f"{self._time_label(max(0.0, duration - position))}")
        if not self.music_expanded:
            self._animate_music(True)

    def _animate_music(self, show):
        if self.music_animation:
            self.music_animation.stop()
            self.music_animation.deleteLater()
        current_geometry = self.geometry()
        if show:
            self.music_frame.show()
            self.music_frame.setMaximumHeight(16777215)
            self.music_opacity.setOpacity(0.0)
            self.adjustSize()
            target_geometry = self.geometry()
            target_geometry.moveTopLeft(current_geometry.topLeft())
            self.setGeometry(current_geometry)
            self.music_frame.setMaximumHeight(0)
            start_height, start_opacity = 0, 0.0
            end_height, end_opacity = max(round(56 * self._scale_percent / 100.0), self.music_frame.sizeHint().height()), 1.0
        else:
            self.music_frame.hide()
            self.adjustSize()
            target_geometry = self.geometry()
            target_geometry.moveTopLeft(current_geometry.topLeft())
            self.setGeometry(current_geometry)
            self.music_frame.show()
            start_height = max(1, self.music_frame.height())
            start_opacity = self.music_opacity.opacity()
            end_height, end_opacity = 0, 0.0
        self.music_expanded = bool(show)
        group = QParallelAnimationGroup(self)
        height = QPropertyAnimation(self.music_frame, b"maximumHeight", group)
        height.setDuration(260)
        height.setEasingCurve(QEasingCurve.OutCubic if show else QEasingCurve.InCubic)
        height.setStartValue(start_height)
        height.setEndValue(end_height)
        opacity = QPropertyAnimation(self.music_opacity, b"opacity", group)
        opacity.setDuration(220)
        opacity.setEasingCurve(QEasingCurve.OutCubic if show else QEasingCurve.InCubic)
        opacity.setStartValue(start_opacity)
        opacity.setEndValue(end_opacity)
        geometry = QPropertyAnimation(self, b"geometry", group)
        geometry.setDuration(260)
        geometry.setEasingCurve(QEasingCurve.OutCubic if show else QEasingCurve.InCubic)
        geometry.setStartValue(current_geometry)
        geometry.setEndValue(target_geometry)
        group.addAnimation(height)
        group.addAnimation(opacity)
        group.addAnimation(geometry)
        group.finished.connect(lambda target=bool(show): self._music_animation_finished(target))
        self.music_animation = group
        group.start()

    def _music_animation_finished(self, expanded):
        if expanded:
            self.music_frame.setMaximumHeight(16777215)
            self.music_opacity.setOpacity(1.0)
        else:
            self.music_frame.hide()
            self.music_frame.setMaximumHeight(16777215)
            self.music_opacity.setOpacity(1.0)
        self.adjustSize()

    def _position_resize_handle(self):
        if hasattr(self, "resize_handle"):
            self.resize_handle.move(max(0, self.fr.width() - self.resize_handle.width() - 5),
                                    max(0, self.fr.height() - self.resize_handle.height() - 5))
            if self.resize_handle.isVisible():
                self.resize_handle.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_resize_handle()

    def _apply_scale(self, percent, force=False):
        percent = max(70, min(150, int(percent)))
        if not force and percent == self._scale_percent:
            return
        self._scale_percent = percent
        factor = percent / 100.0
        self.setFixedWidth(round(456 * factor))
        self.header.setMaximumHeight(round(34 * factor))
        self.logo.setFixedSize(round(32 * factor), round(32 * factor))
        self.logo.setPixmap(logo_pix(round(32 * factor)))
        self.resize_handle.setFixedSize(round(20 * factor), round(20 * factor))
        self.resize_handle.setStyleSheet(f"background:rgba(10,14,19,170); color:#88b4ff; border:1px solid rgba(120,170,240,100); border-radius:{max(3,round(5*factor))}px; font-size:{max(9,round(13*factor))}px;")
        self.v.setContentsMargins(*(round(v * factor) for v in (12, 9, 12, 10)))
        self.v.setSpacing(max(3, round(6 * factor)))
        self.title.setStyleSheet(f"color:{TEXT}; font-weight:650; font-size:{max(8,round(11*factor))}px;")
        self.norm_caption.setStyleSheet(f"color:{MUTED}; font-size:{max(7,round(9*factor))}px;")
        self.norm.setStyleSheet(f"color:{TEXT}; font-weight:700; font-size:{max(10,round(15*factor))}px;")
        self.report_heading.setStyleSheet(f"color:{MUTED}; font-size:{max(6,round(8*factor))}px; font-weight:700; letter-spacing:0.5px;")
        self.bar.setStyleSheet(f"QProgressBar {{ background:rgba(255,255,255,22); border:none; border-radius:{max(2,round(3*factor))}px; min-height:{max(3,round(5*factor))}px; max-height:{max(3,round(5*factor))}px; }} QProgressBar::chunk {{ background:{ACC}; border-radius:{max(2,round(3*factor))}px; }}")
        self.items.setSpacing(max(2, round(4 * factor)))
        self.music_art.setFixedSize(round(46 * factor), round(46 * factor))
        self.music_art.setStyleSheet(f"background:{ACC_D}; border-radius:{max(5,round(8*factor))}px; color:#fff; font-size:{max(13,round(21*factor))}px; font-weight:600;")
        self.music_title.setStyleSheet(f"color:{TEXT}; font-size:{max(8,round(11*factor))}px; font-weight:700;")
        self.music_artist.setStyleSheet(f"color:{MUTED}; font-size:{max(7,round(10*factor))}px;")
        self.music_title.setMaximumWidth(round(220 * factor))
        self.music_artist.setMaximumWidth(round(220 * factor))
        self.music_progress.setFixedHeight(max(3, round(4 * factor)))
        self.music_time.setStyleSheet(f"color:{MUTED}; font-size:{max(7,round(9*factor))}px;")
        music_layout = self.music_frame.layout()
        if music_layout:
            music_layout.setContentsMargins(*(round(v * factor) for v in (7, 6, 9, 6)))
            music_layout.setSpacing(max(3, round(8 * factor)))
        for widget in self._report_widgets.values():
            layout = widget.layout()
            if layout:
                layout.setContentsMargins(*(round(v * factor) for v in (10, 5, 10, 5)))
            widget.setFixedHeight(round(90 * factor))
            widget.name_label.setStyleSheet(f"background:transparent;color:#f2f5fb;font-size:{max(11,round(12*factor))}px;font-weight:650;")
            widget.state_label.setStyleSheet(f"background:transparent;color:{getattr(widget, '_overlay_color', ACC)};font-size:{max(9,round(9*factor))}px;font-weight:700;")
            widget.message_label.setStyleSheet(f"background:transparent;color:#b2bdce;font-size:{max(10,round(11*factor))}px;")
            widget._overlay_signature = None
        cover = getattr(self, "_music_cover_image", None)
        if cover is not None and not cover.isNull():
            pix = QPixmap.fromImage(cover).scaled(self.music_art.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            self.music_art.setPixmap(pix)
        self._position_resize_handle()
        self.adjustSize()

    def _save_scale(self):
        self.core.cfg["overlay_scale"] = self._scale_percent
        save_cfg(self.core.cfg)
        if hasattr(self, "size_changed"):
            self.size_changed.emit(self._scale_percent)

    def refresh(self):
        if not self.isVisible():
            self._overlay_dirty = True
            return
        self._overlay_dirty = False
        cfg = self.core.cfg
        compact = bool(cfg.get("overlay_compact", False))
        norm_visible = bool(cfg["norm_overlay"] or cfg.get("overlay_test_mode", False) or compact)
        norm_changed = self.norm.isHidden() == norm_visible or compact != self._compact_cache
        self._compact_cache = compact
        self.norm_caption.setVisible(norm_visible and not compact)
        self.norm.setVisible(norm_visible)
        self.bar.setVisible(norm_visible)
        edit_mode = bool(cfg.get("overlay_edit_mode", False))
        if edit_mode != self._edit_mode_cache:
            self.fr.setProperty("editMode", edit_mode)
            self.fr.style().unpolish(self.fr)
            self.fr.style().polish(self.fr)
            title_text = "Yavir Tools · редагування" if edit_mode else "Yavir Tools"
            if self.title.text() != title_text:
                self.title.setText(title_text)
            self.title.setCursor(Qt.SizeAllCursor if edit_mode else Qt.ArrowCursor)
            self._edit_mode_cache = edit_mode
        scale = max(70, min(150, int(cfg.get("overlay_scale", 100))))
        scale_changed = scale != self._scale_percent
        if scale_changed:
            self._apply_scale(scale)
        self.resize_handle.setVisible(edit_mode)
        self._position_resize_handle()
        structure_changed = norm_changed or scale_changed
        rows = []
        if compact and self.music_active:
            self.set_music({})
        if cfg["overlay_enabled"] and not compact:
            max_rows = max(0, int(cfg.get("overlay_max_rows", 6)))
            rows = [r for r in self.core.reports if r["status"] != "Відповів"][:max_rows]
        if self._test_preview_report and not compact:
            rows = [self._test_preview_report] + rows

        has_rows = bool(rows)
        self.report_heading.setVisible(has_rows)
        self.report_section.setMaximumHeight(16777215 if has_rows else 0)
        self.report_section.setVisible(has_rows)
        if rows:
            self.report_heading.setText(f"РЕПОРТИ  ·  {len(rows)} В ОВЕРЛЕЇ")
        wanted_ids = {r["rid"] for r in rows}
        for rid, widget in list(self._report_widgets.items()):
            if rid not in wanted_ids:
                self.items.removeWidget(widget)
                widget.hide()
                widget.deleteLater()
                del self._report_widgets[rid]
                structure_changed = True

        self._report_buttons = []
        for index, report in enumerate(rows):
            rid = report["rid"]
            widget = self._report_widgets.get(rid)
            if widget is None:
                widget = self._make_report_card(rid)
                self._report_widgets[rid] = widget
                self.items.insertWidget(index, widget)
                structure_changed = True
            self._update_report_card(widget, report)
            current_index = self.items.indexOf(widget)
            if current_index != index:
                self.items.removeWidget(widget)
                self.items.insertWidget(index, widget)
                structure_changed = True
            self._report_buttons.append(widget)
        if structure_changed:
            # Recalculate after deferred card deletions and hidden-layout changes settle.
            QTimer.singleShot(0, self._finish_refresh_layout)

    def _finish_refresh_layout(self):
        self.adjustSize()
        self._sync_clickthrough()

    def _make_report_card(self, rid):
        if rid == "__settings_test_report__":
            widget = GlowCard(ACC, clicked=lambda: None)
        else:
            widget = GlowCard(ACC, clicked=lambda rid=rid: self.core.take(self.core.by_rid(rid)))
        widget.overlay_style = True
        scale = self._scale_percent / 100.0
        widget.setFixedHeight(round(74 * scale))
        content = QVBoxLayout(widget)
        content.setContentsMargins(round(10 * scale), round(5 * scale), round(10 * scale), round(5 * scale))
        content.setSpacing(0)
        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(5)
        name = QLabel()
        name.setStyleSheet(f"background:transparent;color:#f2f5fb;font-size:{max(11,round(12*scale))}px;font-weight:650;")
        name.setAttribute(Qt.WA_TransparentForMouseEvents)
        state = QLabel()
        state.setStyleSheet(f"background:transparent;font-size:{max(9,round(9*scale))}px;font-weight:700;")
        state.setAttribute(Qt.WA_TransparentForMouseEvents)
        top.addWidget(name, 1)
        top.addWidget(state)
        content.addLayout(top)
        message = QLabel()
        message.setStyleSheet(f"background:transparent;color:#b2bdce;font-size:{max(10,round(11*scale))}px;")
        message.setAttribute(Qt.WA_TransparentForMouseEvents)
        content.addWidget(message)
        widget._rid = rid
        widget.name_label = name
        widget.state_label = state
        widget.message_label = message
        widget._overlay_signature = None
        return widget

    def show_test_report(self, name, player_id, text):
        self._test_preview_generation += 1
        self._test_preview_report = {
            "rid": "__settings_test_report__", "name": name.strip() or "Тестовий гравець",
            "id": str(player_id).strip() or "123456", "text": text.strip() or "Тестовий репорт",
            "time": datetime.datetime.now().strftime("%H:%M:%S"), "status": "Новий",
            "unanswered": True, "test_preview": True,
        }
        self.refresh()
        self.adjustSize()
        return self._test_preview_generation

    def clear_test_report(self, generation=None):
        if generation is not None and generation != self._test_preview_generation:
            return
        self._test_preview_report = None
        self.refresh()
        self.adjustSize()

    def _update_report_card(self, widget, report):
        color = report_color(report)
        status = report_visual_status(report)
        signature = (report.get("name"), report.get("id"), report.get("text"), status, color, self._scale_percent)
        if signature == widget._overlay_signature:
            return
        widget.setGlowColor(color)
        widget._overlay_color = color
        full_name = f"{report['name']} [{report['id']}]"
        name_font = QFont(BODY_FONT, max(11, round(12 * self._scale_percent / 100.0)), QFont.DemiBold)
        widget.name_label.setText(QFontMetrics(name_font).elidedText(
            full_name, Qt.ElideRight, max(100, self.width() - 155)))
        widget.name_label.setToolTip(full_name)
        widget.state_label.setText(self._state_text(widget, report))
        widget.state_label.setStyleSheet(
            f"background:transparent;color:{color};font-size:{max(9,round(9*self._scale_percent/100.0))}px;font-weight:700;")
        message_text = notification_text(report["text"], limit=None)
        widget.message_label.setText(QFontMetrics(widget.message_label.font()).elidedText(
            message_text, Qt.ElideRight, max(100, self.width() - round(42 * self._scale_percent / 100.0))))
        widget.setToolTip(f"{status}\n{full_name}: {report['text']}")
        widget._overlay_signature = signature

    def _set_clickthrough(self, enabled):
        if not IS_WIN or self._clickthrough == enabled:
            return
        try:
            hwnd = wintypes.HWND(int(self.winId()))
            user32 = ctypes.windll.user32
            index = -20  # GWL_EXSTYLE
            mask = 0x00000020  # WS_EX_TRANSPARENT
            if ctypes.sizeof(ctypes.c_void_p) == 8:
                get_style = user32.GetWindowLongPtrW
                set_style = user32.SetWindowLongPtrW
                get_style.argtypes = [wintypes.HWND, ctypes.c_int]
                get_style.restype = ctypes.c_ssize_t
                set_style.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
                set_style.restype = ctypes.c_ssize_t
            else:
                get_style = user32.GetWindowLongW
                set_style = user32.SetWindowLongW
                get_style.argtypes = [wintypes.HWND, ctypes.c_int]
                get_style.restype = ctypes.c_long
                set_style.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
                set_style.restype = ctypes.c_long
            style = get_style(hwnd, index)
            new_style = (style | mask) if enabled else (style & ~mask)
            if new_style != style:
                set_style(hwnd, index, new_style)
                set_pos = user32.SetWindowPos
                set_pos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                    ctypes.c_int, ctypes.c_int, wintypes.UINT]
                set_pos.restype = wintypes.BOOL
                set_pos(hwnd, 0, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0004 | 0x0010 | 0x0020)
            self._clickthrough = enabled
        except Exception:
            self._clickthrough = False

    def _sync_clickthrough(self):
        if not IS_WIN or not self.isVisible():
            return
        if self.core.cfg.get("overlay_edit_mode", False):
            self._pending_clickthrough = False
            self._set_clickthrough(False)
            return
        cursor = QCursor.pos()
        over_report = any(button.isVisible() and button.rect().contains(button.mapFromGlobal(cursor))
                          for button in self._report_buttons)
        desired = not over_report
        now = time.monotonic()
        if desired != self._pending_clickthrough:
            self._pending_clickthrough = desired
            self._pending_clickthrough_since = now
        elif desired != self._clickthrough and now - self._pending_clickthrough_since >= 0.12:
            self._set_clickthrough(desired)

    def set_norm(self, text, frac=0.0, secs=None, total=None):
        value = int(max(0.0, min(1.0, frac)) * 1000)
        if secs is not None:
            left = max(0, total - secs)
            caption = f"НОРМА · ЗАЛИШИЛОСЬ {fmt(left)}" if left > 0 else "НОРМУ ВИКОНАНО ✔"
            if self.norm_caption.text() != caption:
                self.norm_caption.setText(caption)
            text = (f"<span style='font-size:22px;font-weight:800;'>{fmt(secs)}</span> "
                    f"<span style='color:{MUTED};font-size:12px;font-weight:500;'>/ {fmt(total)}</span>")
        if getattr(self, "_norm_text_cache", None) != text:
            self._norm_text_cache = text
            self.norm.setText(text)
        if getattr(self, "_norm_value_cache", None) != value:
            self._norm_value_cache = value
            self.bar.setValue(value)

    def eventFilter(self, obj, e):
        # Qt can dispatch an event to the title while __init__ is still building
        # the overlay, before the resize handle attribute has been created.
        if obj is getattr(self, "resize_handle", None) and self.core.cfg.get("overlay_edit_mode", False):
            if e.type() == QEvent.MouseButtonPress and e.button() == Qt.LeftButton:
                self._resize_anchor = e.globalPosition().toPoint()
                self._resize_start_scale = self._scale_percent
                return True
            if e.type() == QEvent.MouseMove and self._resize_anchor is not None:
                point = e.globalPosition().toPoint()
                delta = ((point.x() - self._resize_anchor.x()) + (point.y() - self._resize_anchor.y())) / 2
                scale = max(70, min(150, self._resize_start_scale + round(delta / 4)))
                if scale != self._scale_percent:
                    self.core.cfg["overlay_scale"] = scale
                    self._apply_scale(scale)
                    self.refresh()
                return True
            if e.type() == QEvent.MouseButtonRelease and self._resize_anchor is not None:
                self._resize_anchor = None
                self._save_scale()
                return True
        if obj is self.title and self.core.cfg.get("overlay_edit_mode", False):
            if e.type() == QEvent.MouseButtonPress and e.button() == Qt.LeftButton:
                self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
                return True
            if e.type() == QEvent.MouseMove and self._drag is not None:
                self.move(e.globalPosition().toPoint() - self._drag)
                return True
            if e.type() == QEvent.MouseButtonRelease and self._drag is not None:
                self._drag = None
                self.save_position()
                return True
        return super().eventFilter(obj, e)

    def mousePressEvent(self, e):
        if self.core.cfg.get("overlay_edit_mode", False) and e.button() == Qt.LeftButton:
            self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag is not None and self.core.cfg.get("overlay_edit_mode", False):
            self.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, e):
        if self._drag is not None:
            self._drag = None
            self.save_position()

    def save_position(self):
        self.core.cfg["overlay_x"], self.core.cfg["overlay_y"] = self.x(), self.y()
        save_cfg(self.core.cfg)
        self.position_changed.emit(self.x(), self.y())


def dark_titlebar(win):
    """Темний заголовок вікна Windows 10/11 у колір інтерфейсу."""
    if not IS_WIN:
        return
    try:
        hwnd = int(win.winId())
        dwm = ctypes.windll.dwmapi
        on = ctypes.c_int(1)
        for attr in (20, 19):
            if dwm.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(on), 4) == 0:
                break
        col = QColor(BG)
        cref = ctypes.c_int(col.red() | (col.green() << 8) | (col.blue() << 16))
        dwm.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(cref), 4)
        txt = QColor(TEXT)
        tref = ctypes.c_int(txt.red() | (txt.green() << 8) | (txt.blue() << 16))
        dwm.DwmSetWindowAttribute(hwnd, 36, ctypes.byref(tref), 4)
    except Exception:
        pass


class GlassBackdrop(QWidget):
    """Кольорове сяйво за скляними панелями. Видиме лише при увімкненому Liquid Glass."""
    ORBS = ((0.03, 0.03, 0.46, "#2f6bff", 175), (0.97, 0.20, 0.42, "#8b4dff", 160),
            (0.42, 1.00, 0.48, "#12c2b0", 130), (0.04, 0.82, 0.26, "#ff5fa2", 115))

    def __init__(self, parent, cfg):
        super().__init__(parent)
        self.cfg = cfg
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def paintEvent(self, e):
        b = max(0, min(100, int(self.cfg.get("liquid_glass_blur", 60)))) / 100.0
        p = QPainter(self)
        w, h = self.width(), self.height()
        for fx, fy, r, col, a in self.ORBS:
            g = QRadialGradient(QPointF(fx * w, fy * h), r * max(w, h) * (0.65 + 0.7 * b))
            c = QColor(col)
            c.setAlpha(a)
            g.setColorAt(0, c)
            c = QColor(col)
            c.setAlpha(int(a * 0.45))
            g.setColorAt(0.5, c)
            c = QColor(col)
            c.setAlpha(0)
            g.setColorAt(1, c)
            p.fillRect(self.rect(), g)
        p.end()


class WinterEffects(QWidget):
    """Економна click-through прикраса з кешованою гірляндою та легким снігом."""

    def __init__(self, parent, cfg):
        super().__init__(parent)
        self.cfg = cfg
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFocusPolicy(Qt.NoFocus)
        rng = random.Random(2026)
        self.rng = rng
        self.flakes = [[rng.uniform(0, 1600), rng.uniform(0, 900),
                        rng.uniform(1.2, 2.8), rng.uniform(-0.25, 0.25)] for _ in range(24)]
        self._garland_cache = QPixmap()
        self._garland_size = QSize()
        self.timer = QTimer(self)
        # Only tiny snow regions are invalidated; the garland itself is cached.
        self.timer.setInterval(70)
        self.timer.timeout.connect(self.advance)

    def has_effects(self):
        return bool(self.cfg.get("winter_garland", True) or self.cfg.get("winter_snowfall", True))

    def showEvent(self, event):
        super().showEvent(event)
        self.sync_animation()

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def sync_animation(self):
        animated = bool(self.cfg.get("winter_snowfall", True))
        if self.isVisible() and animated:
            if not self.timer.isActive():
                self.timer.start()
        else:
            self.timer.stop()

    def advance(self):
        if not self.cfg.get("winter_snowfall", True):
            self.timer.stop()
            return
        height = max(1, self.height())
        width = max(1, self.width())
        dirty = QRegion()
        for flake in self.flakes:
            x, y, speed, drift = flake
            dirty |= QRegion(QRect(round(x)-3, round(y)-3, 7, 7))
            flake[1] += speed
            flake[0] += drift
            if flake[1] > height + 4:
                flake[0] = self.rng.uniform(0, width)
                flake[1] = -4
            dirty |= QRegion(QRect(round(flake[0])-3, round(flake[1])-3, 7, 7))
        if not dirty.isEmpty():
            self.update(dirty)

    def paintEvent(self, event):
        if not self.has_effects():
            return
        p = QPainter(self)
        width = self.width()
        if self.cfg.get("winter_garland", True):
            size = self.size()
            if self._garland_size != size or self._garland_cache.isNull():
                self._build_garland_cache(size)
            p.drawPixmap(0, 0, self._garland_cache)
        if self.cfg.get("winter_snowfall", True):
            # Дрібні білі точки без мерехтіння та згладжування.
            p.setRenderHint(QPainter.Antialiasing, False)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(245, 249, 255, 185))
            for x, y, _speed, _drift in self.flakes:
                p.drawEllipse(round(x), round(y), 3, 3)
        p.end()

    def _build_garland_cache(self, size):
        self._garland_size = size
        self._garland_cache = QPixmap(size)
        self._garland_cache.fill(Qt.transparent)
        if size.isEmpty() or not self.cfg.get("winter_garland", True):
            return
        p = QPainter(self._garland_cache)
        p.setRenderHint(QPainter.Antialiasing, True)
        width = size.width()
        span = 190.0
        cord = QPainterPath(QPointF(0, 5))
        x0 = 0.0
        while x0 < width:
            x1 = min(width, x0 + span)
            sag = 9.0 if int(x0 / span) % 2 == 0 else 7.0
            length = x1 - x0
            cord.cubicTo(x0 + length * .28, 5 + sag, x0 + length * .72, 5 + sag, x1, 5)
            x0 = x1
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(66, 78, 96, 155), 1.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPath(cord)
        colors = (QColor("#ff626d"), QColor("#62e1a2"), QColor("#ffd16a"),
                  QColor("#73b4ff"), QColor("#c295ff"), QColor("#fff0c4"))
        for i, x in enumerate(range(18, width, 62)):
            segment = int(x / span)
            local = (x - segment * span) / span
            sag = 9.0 if segment % 2 == 0 else 7.0
            cable_y = 5 + sag * (4 * local * (1 - local))
            y = round(cable_y + 7)
            color = colors[i % len(colors)]
            # Static glow baked into the cache: visual halo without per-frame gradient work.
            halo = QRadialGradient(QPointF(x, y + 1), 13)
            halo.setColorAt(0.0, QColor(color.red(), color.green(), color.blue(), 48))
            halo.setColorAt(0.45, QColor(color.red(), color.green(), color.blue(), 18))
            halo.setColorAt(1.0, QColor(color.red(), color.green(), color.blue(), 0))
            p.setPen(Qt.NoPen)
            p.setBrush(halo)
            p.drawEllipse(QRectF(x - 13, y - 12, 26, 26))
            p.setPen(QPen(QColor(130, 143, 162, 150), 1))
            p.drawLine(x, round(cable_y), x, y - 3)
            p.setPen(QPen(QColor(255, 255, 255, 65), .6))
            p.setBrush(color)
            p.drawRoundedRect(QRectF(x - 2.8, y - 3.2, 5.6, 7.5), 2.8, 2.8)
        p.end()


class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP)
        self.setWindowIcon(QIcon(logo_pix(64)))
        self.resize(1480, 940)
        self.setMinimumSize(1120, 720)
        global POLICY
        self.cfg = load_cfg()
        POLICY = AccessPolicy(self.cfg)
        if POLICY.needs_save:
            save_cfg(self.cfg)
        _policy_log("start", "нік=" + repr(self.cfg.get("admin_name", "")) + ", рівень=" + repr(self.cfg.get("admin_level", ""))
                    + ", заборонено=" + ",".join(sorted(POLICY.effective_denied())) + ", ACCESS_URL=" + ("є" if ACCESS_URL else "ПОРОЖНІЙ")
                    + ", токен=" + ("є (мережа не підтягується)" if self.cfg.get("gh_token") else "немає"))
        self._policy_sync = None
        if ACCESS_URL and not self.cfg.get("gh_token"):  # на ПК власника (з токеном) права не перезаписуємо з мережі
            self._policy_sync = PolicySync(ACCESS_URL)
            self._policy_sync.fetched.connect(self.on_remote_policy)
            self._policy_sync.start()
        boot_pulse()
        self.core = Core(self.cfg)
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        h = QHBoxLayout(root)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)

        side = QFrame()
        side.setObjectName("sidebar")
        side.setFixedWidth(276)
        sv = QVBoxLayout(side)
        sv.setContentsMargins(0, 22, 0, 16)
        sv.setSpacing(0)
        brand = QHBoxLayout()
        brand.setContentsMargins(20, 0, 20, 0)
        brand.setSpacing(12)
        mark = QLabel()
        mark.setPixmap(logo_pix(38))
        mark.setFixedSize(38, 38)
        brand.addWidget(mark)
        bt = QVBoxLayout()
        bt.setSpacing(0)
        bt.addWidget(lab("Yavir Tools", "brand"))
        bt.addWidget(lab("Панель адміністратора", "brandsub"))
        brand.addLayout(bt, 1)
        sv.addLayout(brand)
        sv.addSpacing(26)

        self.stack = QStackedWidget()
        self.page_opacity = QGraphicsOpacityEffect(self.stack)
        self.page_opacity.setOpacity(1.0)
        self.stack.setGraphicsEffect(self.page_opacity)
        self.page_animation = QPropertyAnimation(self.page_opacity, b"opacity", self)
        self.page_animation.setDuration(180)
        self.page_animation.setEasingCurve(QEasingCurve.OutCubic)
        self.dash = Dashboard(self.core)
        self.dash.shift_toggle.connect(self.toggle_shift)
        self.dash.set_shift_state(bool(self.cfg.get("shift_active")))
        boot_pulse()
        self.reports = ReportsPage(self.core)
        self.users_page = UsersPage(self.core, self.open_user_reports)
        self.vip = VipPage(self.core)
        self.binds = BindsPage(self.core, self.apply)
        self.po = AdminPO(self.core, self.apply)
        self.punishments = PunishmentQueuePage(self.core)
        boot_pulse()
        self.complaint = ComplaintPage(self.core, self.apply)
        self.chat = ChatPage(self.core, lambda: self.go(self.stack.indexOf(self.settings)))
        boot_pulse()
        self.settings = SettingsPage(self.core, self.apply, self.reload_config_views)
        self.settings.island_test = self.show_island_test
        pages = [("Дашборд", "dash", self.dash), ("Репорти", "inbox", self.reports),
                 ("Користувачі", "users", self.users_page), ("VIP чат", "star", self.vip),
                 ("Бінди", "keys", self.binds), ("Адмін ПО", "shield", self.po),
                 ("Відправка покарань", "ban", self.punishments),
                 ("Розгляд скарги", "doc", self.complaint),
                 ("Чат з ШІ", "chat", self.chat)]
        self.navs = []
        for i, (t, ic, p) in enumerate(pages):
            self.stack.addWidget(p)
            self.navs.append(self.nav(t, ic, i, sv))
        sv.addStretch(1)
        self.stack.addWidget(self.settings)
        self.navs.append(self.nav("Налаштування", "gear", len(pages), sv))
        self.access_page = AccessPage(self.core, self.apply_access)
        self.stack.addWidget(self.access_page)
        self.navs.append(self.nav("Права доступу", "shield", len(pages) + 1, sv))
        self.PAGE_FEATURES = ["page_dash", "page_reports", "page_users", "page_vip", "page_binds", "page_po",
                              "page_punishments", "page_complaint", "page_chat", "page_settings"]
        self.navs[0].setChecked(True)
        self.dash.go_reports = lambda: self.go(1)

        sv.addSpacing(14)
        self.status = lab("", "hint", True)
        self.status.setContentsMargins(20, 0, 20, 0)
        self.status.setMinimumHeight(34)
        self.status.setAlignment(Qt.AlignBottom)
        sv.addWidget(self.status)
        sv.addSpacing(10)
        prof = QFrame()
        prof.setObjectName("profile")
        pl = QHBoxLayout(prof)
        pl.setContentsMargins(10, 10, 10, 10)
        pl.setSpacing(10)
        self.p_av = lab("", "avatar")
        self.p_av.setFixedSize(38, 38)
        self.p_av.setAlignment(Qt.AlignCenter)
        pl.addWidget(self.p_av)
        pv = QVBoxLayout()
        pv.setSpacing(0)
        self.p_position = lab("", "psub")
        self.p_name, self.p_lvl = lab("", "pname"), lab("", "psub")
        pv.addWidget(self.p_position)
        pv.addWidget(self.p_name)
        pv.addWidget(self.p_lvl)
        pl.addLayout(pv, 1)
        pw = QHBoxLayout()
        pw.setContentsMargins(14, 0, 14, 0)
        pw.addWidget(prof)
        sv.addLayout(pw)
        h.addWidget(side)
        h.addWidget(self.stack, 1)
        boot_pulse()
        self.glass_bg = GlassBackdrop(root, self.cfg)
        self.glass_bg.setGeometry(root.rect())
        self.glass_bg.setVisible(bool(self.cfg.get("liquid_glass")))
        self.glass_bg.lower()
        self.winter = WinterEffects(root, self.cfg)
        self.winter.setGeometry(root.rect())
        self.winter.setVisible(self.winter.has_effects())
        self.winter.sync_animation()
        self.winter.raise_()
        root.installEventFilter(self)

        self.toast = Toast(self)
        self.notice = DynamicIsland() if self.cfg.get("dynamic_island", True) else ScreenNotice()
        self._update_signal = Signal_()
        self._update_signal.value.connect(self._on_update_found)
        self._norm_notified = (self.cfg.get("norm_seconds", 0) >=
                               int(self.cfg.get("norm_hours", 4.0) * 3600))
        _url_cfg = self.cfg.get("update_version_url_cfg", "").strip()
        if _url_cfg:
            globals()["UPDATE_VERSION_URL"] = _url_cfg
        if UPDATE_VERSION_URL or _url_cfg:
            threading.Thread(target=self._check_update_bg, daemon=True).start()
        self.notice.apply_size(self.cfg.get("notification_width", 540), self.cfg.get("notification_height", 104))
        self.core.event.connect(self.handle_event)
        self.core.reports_changed.connect(self.refresh_game_menu)
        self.core.stats_changed.connect(self.refresh_game_menu)
        self.game_menu = GameOverlayMenu(self.core, self.open_game_menu_page, self.open_report_from_menu,
                                         lambda: getattr(self, "_running", False))
        self.core.overlay_menu_toggle.connect(self.game_menu.toggle)
        for i in range(len(self.navs)):
            QShortcut(QKeySequence(f"Ctrl+{i + 1}"), self, activated=lambda i=i: self.go(i))

        self.overlay = Overlay(self.core, None)
        self.overlay.position_changed.connect(self.sync_overlay_position_fields)
        self.overlay.size_changed.connect(self.sync_overlay_scale_field)
        self.overlay.move(self.cfg["overlay_x"], self.cfg["overlay_y"])
        self.spotify_watcher = None
        self.ensure_spotify_watcher()

        self.watch = LogWatcher(self.core)
        self.watch.batch.connect(self.core.on_lines, Qt.QueuedConnection)
        self.watch.status.connect(self.status.setText)
        self.watch.start()
        self.core.register_hotkeys()
        self.core.event.connect(lambda k, t: self.status.setText(t) if k == "info" else None)
        self.core.reports_changed.connect(self.update_badge)

        self._running, self._chk, self._sv = False, 0, 0
        self.game_watcher = GameProcessWatcher(self.cfg)
        self.game_watcher.running_changed.connect(self._on_game_running_changed)
        self.game_watcher.start()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(1000)
        self.overlay.refresh()
        self.update_profile()
        self.update_badge()
        self.apply_access()
        if POLICY.tampered:
            self.status.setText("⚠ Файл прав доступу змінено вручну — діють аварійні обмеження.")
        self.tick()
        self._glass_state = (bool(self.cfg.get("liquid_glass")), int(self.cfg.get("liquid_glass_strength", 40)), int(self.cfg.get("liquid_glass_edge", 75)), int(self.cfg.get("liquid_glass_blur", 60)))

    def _on_game_running_changed(self, running):
        self._running = bool(running)
    def nav(self, text, icon, idx, lay):
        b = QPushButton("  " + text)
        b.setObjectName("nav")
        b.setIcon(nav_icon(icon))
        b.setIconSize(QSize(20, 20))
        b.setCheckable(True)
        b.setFixedHeight(42)
        b.setCursor(Qt.PointingHandCursor)
        b.clicked.connect(lambda: self.go(idx))
        bl = QHBoxLayout(b)
        bl.setContentsMargins(0, 0, 14, 0)
        bl.addStretch(1)
        badge = QLabel()
        badge.setObjectName("badge")
        badge.setAlignment(Qt.AlignCenter)
        badge.setAttribute(Qt.WA_TransparentForMouseEvents)
        badge.hide()
        bl.addWidget(badge)
        b.badge = badge
        lay.addWidget(b)
        return b

    def update_badge(self):
        n = sum(1 for r in self.core.reports if r["status"] == "Новий")
        b = self.navs[1].badge
        b.setText(str(n) if n < 100 else "99+")
        b.setVisible(n > 0)

    def eventFilter(self, obj, event):
        if obj is self.centralWidget() and event.type() == QEvent.Resize and hasattr(self, "winter"):
            self.winter.setGeometry(obj.rect())
            self.glass_bg.setGeometry(obj.rect())
            self.glass_bg.lower()
            self.winter.raise_()
        return super().eventFilter(obj, event)

    def open_user_reports(self, player_id):
        self.go(1)
        self.reports.search.setText(str(player_id))

    def update_profile(self):
        n = self.cfg["admin_name"] or "?"
        avatar_path = self.cfg.get("avatar_path", "")
        pix = QPixmap(avatar_path) if avatar_path and os.path.isfile(avatar_path) else QPixmap()
        if not pix.isNull():
            size = self.p_av.size()
            scaled = pix.scaled(size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            x = max(0, (scaled.width() - size.width()) // 2)
            y = max(0, (scaled.height() - size.height()) // 2)
            cropped = scaled.copy(x, y, size.width(), size.height())
            rounded = QPixmap(size)
            rounded.fill(Qt.transparent)
            painter = QPainter(rounded)
            painter.setRenderHint(QPainter.Antialiasing)
            path = QPainterPath()
            path.addEllipse(0, 0, size.width(), size.height())
            painter.setClipPath(path)
            painter.drawPixmap(0, 0, cropped)
            painter.end()
            self.p_av.setText("")
            self.p_av.setPixmap(rounded)
        else:
            self.p_av.setPixmap(QPixmap())
            self.p_av.setText(n[:1].upper())
        self.p_name.setText(n)
        position = str(self.cfg.get("admin_position", "Немає посади")).strip()
        self.p_position.setText(position if position and position != "Немає посади" else "")
        self.p_position.setVisible(bool(position and position != "Немає посади"))
        self.p_lvl.setText(self.cfg["admin_level"])

    def on_remote_policy(self, profiles):
        if profiles == POLICY.data.get("profiles"):
            return
        _policy_log("apply", "застосовую нові права з мережі")
        POLICY.data["profiles"] = json.loads(json.dumps(profiles))
        POLICY.commit()
        save_cfg(self.cfg)
        self.apply_access()
        page = getattr(self, "access_page", None)
        if page is not None and page.unlocked:
            page.rebuild_profiles(select=page.current_profile)

    def apply_access(self):
        for i, feature in enumerate(self.PAGE_FEATURES):
            self.navs[i].setVisible(can(feature))
        self.reports.apply_access()
        cur = self.stack.currentIndex()
        if cur < len(self.PAGE_FEATURES) and not can(self.PAGE_FEATURES[cur]):
            for i, feature in enumerate(self.PAGE_FEATURES):
                if can(feature):
                    self.go(i)
                    break
        if hasattr(self, "access_page"):
            self.access_page.update_who()

    def go(self, idx):
        if idx < len(self.PAGE_FEATURES) and not can(self.PAGE_FEATURES[idx]):
            self.toast.show_text("Немає доступу: " + ACCESS_BY_ID[self.PAGE_FEATURES[idx]][1])
            return
        changed = self.stack.currentIndex() != idx
        for i, b in enumerate(self.navs):
            b.setChecked(i == idx)
        if not changed:
            return
        self.page_animation.stop()
        self.stack.setCurrentIndex(idx)
        self.page_opacity.setOpacity(0.0)
        self.page_animation.setStartValue(0.0)
        self.page_animation.setEndValue(1.0)
        self.page_animation.start()

    def open_game_menu_page(self, idx):
        if self.isMinimized():
            self.showNormal()
        else:
            self.show()
        self.raise_()
        self.activateWindow()
        self.go(idx)

    def open_report_from_menu(self, report):
        self.core.selected = report["rid"]
        self.open_game_menu_page(1)
        self.reports.refresh()

    def preview_test_report(self, name, player_id, text):
        self.reports.show_test_report(name, player_id, text)
        self.overlay.show_test_report(name, player_id, text)
        self.tick()
        self.overlay.show()
        self.overlay.raise_()

    def hide_test_report_preview(self):
        self.reports.clear_test_report()
        self.overlay.clear_test_report()
        self.tick()

    def sync_overlay_position_fields(self, x, y):
        for key, value in (("overlay_x", x), ("overlay_y", y)):
            field = self.settings.w.get(key)
            if field:
                field[0].setValue(value)

    def sync_overlay_scale_field(self, scale):
        field = self.settings.w.get("overlay_scale")
        if field:
            field[0].setValue(scale)

    def apply(self):
        glass_state = (bool(self.cfg.get("liquid_glass")), int(self.cfg.get("liquid_glass_strength", 40)), int(self.cfg.get("liquid_glass_edge", 75)), int(self.cfg.get("liquid_glass_blur", 60)))
        if glass_state != getattr(self, "_glass_state", glass_state):
            _sc = max(0.7, min(2.0, float(self.cfg.get("ui_scale", 1.0))))
            QApplication.instance().setFont(QFont(BODY_FONT, round(10 * _sc)))
            QApplication.instance().setStyleSheet(build_qss(self.cfg))
        self._glass_state = glass_state
        self.glass_bg.setVisible(glass_state[0])
        self.glass_bg.update()
        self.core._rx.clear()
        self.core.refresh_word_filters()
        save_cfg(self.cfg)
        self.core.register_hotkeys()
        self.users_page.set_bulk_delete_mode(self.cfg.get("users_bulk_delete_mode", False))
        self.ensure_spotify_watcher()
        self.overlay.move(self.cfg["overlay_x"], self.cfg["overlay_y"])
        self.reports.rebuild_binds()
        self.po.sync()
        self.dash.refresh()
        self.overlay.refresh()
        self.update_profile()
        if bool(self.cfg.get("dynamic_island", True)) != isinstance(self.notice, DynamicIsland):
            self.notice.close()
            self.notice = DynamicIsland() if self.cfg.get("dynamic_island", True) else ScreenNotice()
        self.notice.apply_size(self.cfg.get("notification_width", 540), self.cfg.get("notification_height", 104))
        self.winter.setVisible(self.winter.has_effects())
        self.winter.sync_animation()
        self.winter.raise_()
        self.refresh_game_menu()
        self.apply_access()
        self.tick()
        if not getattr(self.settings, "_quiet_save", False):
            play(self.cfg, "ui")
            self.toast.show_text("Збережено")

    def reload_config_views(self):
        self.binds.t.setRowCount(0)
        for bind in self.cfg.get("binds", []):
            self.binds.add(bind)
        self.binds.ct.setRowCount(0)
        for command in self.cfg.get("commands", []):
            self.binds.add_command(command)

    def refresh_game_menu(self, latest=""):
        if hasattr(self, "game_menu"):
            if latest:
                self.game_menu.latest = latest
            if self.game_menu.is_open:
                self.game_menu.refresh()

    def _check_update_bg(self):
        latest = check_for_update(APP_VERSION, UPDATE_VERSION_URL)
        if latest:
            self._update_signal.value.emit(latest)

    def _on_update_found(self, latest):
        self.notice.show_event("ok", f"Доступна версія {latest}",
                               f"Поточна: {APP_VERSION}  ·  перевірте у розробника")
        play(self.cfg, "ui")

    def toggle_shift(self):
        c = self.cfg
        if c.get("shift_active"):
            c["shift_active"] = False
            save_cfg(c)
            self.dash.set_shift_state(False)
            save_cfg(c)
            self.notice.show_event("info", "Зміну завершено", f"Відіграно {fmt(c['norm_seconds'])}")
            return
        if not self._running:
            self.notice.show_event("ac", "Вам потрібно перебувати в грі", "")
            return
        c["shift_active"] = True
        save_cfg(c)
        self.dash.set_shift_state(True)
        self.notice.show_event("ok", "Зміну розпочато", "Таймер норми запущено")

    def show_island_test(self, i):
        tests = (("report", "Новий репорт від Ігор Гринюк", "Я застряг"), ("ok", "Знайдено форму!", ""),
                 ("reply", "Відповідь надіслано", ""), ("action", "Дію виконано", ""),
                 ("ac", "Спрацював античіт", "Перевірте гравця"), ("music", "Музика відтворюється", "Imagine Dragons — Believer"))
        self.notice.show_event(*tests[i % len(tests)])

    def handle_event(self, kind, message):
        if kind == "info":
            return
        if kind == "colleague":
            if not can("notif_colleague"):
                return
            self.refresh_game_menu("Відповідь колеги: " + notification_text(message))
            return
        if kind == "form":
            if message.startswith("Знайдена форма:"):
                kind2, title, detail = "ok", "ФОРМА", message.partition(":")[2].strip()
            elif "відхилено" in message.casefold() or "натиснуто f1" in message.casefold():
                kind2, title, detail = "warning", "Форму відхилено", message
            elif "прийнято" in message.casefold() or "схвалив адміністратор" in message.casefold():
                kind2, title = "ok", "Форму прийнято"
                detail = message.partition(":")[2].strip() if ":" in message else message
                # Keep the accepted-form notification clean even if an older
                # event producer still includes the legacy command payload.
                detail = re.sub(r"\s*\[\d+\]", "", detail).strip()
            else:
                kind2, title, detail = "form", "Подія з формою", message
            detail = notification_text(detail)
            self.notice.show_event(kind2, title, detail)
            self.refresh_game_menu(title + (": " + detail if detail else ""))
            return
        mapping = {
            "report": ("report", "Новий репорт", ""),
            "report_reminder": ("warning", "Репорт очікує відповіді", "Перевірте список репортів"),
            "unanswered": ("warning", "Репорт без відповіді", ""),
            "repviol": ("warning", "Репорт із порушенням", "Перевірте картку репорту"),
            "vipad": ("vipad", "Знайдена реклама у VIP!", ""),
            "vip_possible": ("vip_possible", "Можлива реклама у VIP", ""),
            "vipviol": ("warning", "Заборонене слово у VIP", "Перевірте повідомлення"),
            "ac": ("ac", "Спрацював античіт", "Перевірте гравця"),
            "bad": ("warning", "Знайдено заборонене слово", "Перевірте рядок чату"),
            "take": ("mine", "Репорт узято мною", ""),
            "reply": ("reply", "Відповідь надіслано", ""),
            "action": ("action", "Дію виконано", ""),
        }
        kind2, title, hint = mapping.get(kind, ("info", "Подія Yavir Tools", ""))
        detail = notification_text(message or hint)
        report_player_name = ""
        if kind in ("report", "unanswered", "repviol"):
            report_match = re.match(r"^(?P<name>.+?)\s*\[(?P<id>\d+)\]:\s*", message)
            if report_match:
                player_name, player_id = report_match.group("name", "id")
                report_player_name = player_name
                report = next((r for r in self.core.reports
                               if str(r.get("id")) == player_id and r.get("name") == player_name), None)
                report_body = report.get("text", "") if report else message[report_match.end():]
                # Keep the notice compact: the player's name and full message are useful here;
                # the numeric ID remains available inside the report card.
                title = {"report": f"Новий репорт від {player_name}",
                         "unanswered": "Репорт без відповіді",
                         "repviol": "Репорт із порушенням"}.get(kind, title)
                detail = notification_text(report_body, limit=None)
        self.notice.show_event(kind2, title, detail)
        if kind in ("report", "unanswered", "repviol"):
            latest = title + (f" · {report_player_name}" if report_player_name else "")
        else:
            latest = title + (": " + detail if detail else "")
        self.refresh_game_menu(latest)

    def ensure_spotify_watcher(self):
        enabled = bool(self.cfg.get("spotify_overlay_enabled", True))
        current = self.spotify_watcher
        if current and current.isRunning():
            stopping = current._stop_event.is_set()
            if enabled and not stopping:
                return
            if not enabled:
                current.stop()
                current.wait()
                if current.isRunning():
                    self.on_music_update({"playing": False})
                    return
            self.spotify_watcher = None
        if not enabled:
            self.on_music_update({"playing": False})
            return
        if not IS_WIN:
            return
        if MediaSessionManager is None:
            self.status.setText("Spotify-плашка потребує winsdk. Перезберіть програму через build.ps1.")
            return
        self.spotify_watcher = SpotifyWatcher()
        self.spotify_watcher.updated.connect(self.on_music_update)
        self.spotify_watcher.error.connect(self.status.setText)
        self.spotify_watcher.start()

    def on_music_update(self, data):
        self.overlay.set_music(data)
        if hasattr(self, "game_menu"):
            self.game_menu.set_music(data)
        track_key = (data.get("artist", ""), data.get("title", "")) if data.get("playing") else None
        previous = getattr(self, "_last_notified_track", None)
        if track_key and track_key != previous:
            self._last_notified_track = track_key
            self.notice.show_event("music", "Музика відтворюється", f"{track_key[0]} — {track_key[1]}")
        elif track_key is None:
            self._last_notified_track = None

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, "toast") and self.toast.isVisible():
            self.toast.place()

    def tick(self):
        c = self.cfg
        self.core.flush_log()
        self.core.players.commit_if_due()
        self.core.check_report_reminders()
        self._report_expire_tick = getattr(self, "_report_expire_tick", 0) + 1
        if self._report_expire_tick >= 10:
            self._report_expire_tick = 0
            self.core.expire_reports()
        today = datetime.date.today().isoformat()
        if c["norm_date"] != today:
            c["norm_date"], c["norm_seconds"], c["shift_active"] = today, 0, False
        if self._running and c.get("shift_active"):
            c["norm_seconds"] += 1
            self._sv += 1
            if self._sv >= 15:
                self._sv = 0
                save_cfg(c)
        else:
            self._sv += 1
            if self._sv >= 60:
                self._sv = 0
                save_cfg(c)
        norm = int(c["norm_hours"] * 3600)
        if self.dash.isVisible():
            self.dash.tick(self._running, c["norm_seconds"], norm, bool(c.get("shift_active")))
        left = norm - c["norm_seconds"]
        frac = min(1.0, c["norm_seconds"] / norm) if norm else 0.0
        norm_just_done = (left <= 0 and bool(c.get("shift_active")) and
                           not getattr(self, "_norm_notified", True))
        if left <= 0 and c.get("shift_active"):
            self._norm_notified = True
        elif left > 0:
            self._norm_notified = False
        if norm_just_done:
            self.notice.show_event("ok", "Норму виконано ✔",
                                   f"Відіграно {fmt(c['norm_seconds'])}")
            play(self.cfg, "ui")
        self.overlay.set_norm(("До кінця норми: " + fmt(left)) if left > 0 else "Норму виконано ✔", frac, c["norm_seconds"], norm)
        if self.game_menu.is_open:
            self.game_menu.refresh()
        test_overlay = bool(c.get("overlay_test_mode", False))
        preview_active = bool(self.overlay._test_preview_report)
        show = can("overlay_view") and (c["overlay_enabled"] or c["norm_overlay"] or not self.overlay.music_frame.isHidden() or c.get("overlay_edit_mode", False) or test_overlay or preview_active)
        if show and (self._running or c.get("overlay_edit_mode", False) or test_overlay or preview_active or not IS_WIN):
            if not self.overlay.isVisible():
                self.overlay.show()
        elif self.overlay.isVisible():
            self.overlay.hide()

    def closeEvent(self, e):
        save_cfg(self.cfg)
        self.watch.run_flag = False
        if self.watch.isRunning():
            self.watch.wait(1500)
        self.game_watcher.run_flag = False
        if self.game_watcher.isRunning():
            self.game_watcher.wait(2000)
        self.core.flush_log(force=True)
        queue_worker = getattr(getattr(self, "punishments", None), "worker", None)
        if queue_worker and queue_worker.isRunning():
            queue_worker.stop()
            queue_worker.wait()
        if self.spotify_watcher and self.spotify_watcher.isRunning():
            self.spotify_watcher.stop()
            self.spotify_watcher.wait()
        self.overlay.close()
        self.game_menu.close()
        self.notice.close()
        self.winter.timer.stop()
        self.core.players.close()
        super().closeEvent(e)


BOOT_HOOK = None


def boot_pulse():
    """Малює наступний кадр заставки між важкими кроками запуску (без обробки подій, тому безпечно)."""
    if BOOT_HOOK:
        try:
            BOOT_HOOK()
        except Exception:
            pass


def _ease_out_back(x, k=1.45):
    x = max(0.0, min(1.0, x)) - 1.0
    return 1.0 + (k + 1.0) * x ** 3 + k * x ** 2


class StartupSplash(QWidget):
    STEPS = ("Завантаження налаштувань", "Підготовка інтерфейсу", "Підключення до логу гри",
             "Запуск сповіщень", "Майже готово")

    def __init__(self):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.resize(760, 560)
        screen = QApplication.primaryScreen()
        if screen:
            g = screen.geometry()
            self.move(g.center().x() - self.width() // 2, g.center().y() - self.height() // 2)
        self.started_at = time.monotonic()
        self.minimum_duration = 2.8
        self.color_duration = 1.7
        self.done_at, self.exit_at, self._p_done = None, None, 0.0
        source = QImage(resource_path(os.path.join("assets", "yavir_icon.png")))
        source = source.scaled(152, 152, Qt.KeepAspectRatio, Qt.SmoothTransformation).convertToFormat(QImage.Format_ARGB32)
        self.logo_mono = QImage(source.size(), QImage.Format_ARGB32)
        for y in range(source.height()):
            for x in range(source.width()):
                px = source.pixelColor(x, y)
                gray = round(px.red() * 0.2126 + px.green() * 0.7152 + px.blue() * 0.0722)
                self.logo_mono.setPixelColor(x, y, QColor(gray, gray, gray, px.alpha()))
        self.logo_color = self._tint_logo(self.logo_mono)
        self.main_window = None
        self._finish_timer = None
        self._fade = None
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self.update)
        self.timer.start()

    @staticmethod
    def _tint_logo(source):
        result = QImage(source.size(), QImage.Format_ARGB32)
        w, h = source.width(), source.height()
        stops = ((0.0, (48, 207, 236)), (0.52, (57, 139, 255)), (1.0, (166, 112, 255)))
        for y in range(h):
            for x in range(w):
                px = source.pixelColor(x, y)
                gray = (px.red() + px.green() + px.blue()) // 3
                if gray < 18 or px.alpha() == 0:
                    result.setPixelColor(x, y, px)
                    continue
                t = (x / max(1, w - 1)) * 0.78 + (y / max(1, h - 1)) * 0.22
                if t <= stops[1][0]:
                    lo, hi = stops[0], stops[1]
                else:
                    lo, hi = stops[1], stops[2]
                ratio = (t - lo[0]) / (hi[0] - lo[0])
                rgb = tuple(round((lo[1][i] + (hi[1][i] - lo[1][i]) * ratio) * gray / 255) for i in range(3))
                result.setPixelColor(x, y, QColor(rgb[0], rgb[1], rgb[2], px.alpha()))
        return result

    def _progress(self, now):
        t = now - self.started_at
        if self.done_at is None:
            return 0.93 * (1.0 - math.exp(-t * 1.25))
        k = min(1.0, (now - self.done_at) / 0.4)
        return self._p_done + (1.0 - self._p_done) * (1.0 - (1.0 - k) ** 3)

    def finish(self, main_window):
        self.main_window = main_window
        now = time.monotonic()
        self._p_done, self.done_at = self._progress(now), now
        remaining = max(0, self.minimum_duration - (now - self.started_at))
        self._finish_timer = QTimer(self)
        self._finish_timer.setSingleShot(True)
        self._finish_timer.timeout.connect(self._reveal_main)
        self._finish_timer.start(round(remaining * 1000))

    def _reveal_main(self):
        self.main_window.showMaximized()
        dark_titlebar(self.main_window)
        self.exit_at = time.monotonic()
        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setDuration(340)
        self._fade.setStartValue(1.0)
        self._fade.setEndValue(0.0)
        self._fade.setEasingCurve(QEasingCurve.OutCubic)
        self._fade.finished.connect(self.close)
        self._fade.start()

    def paintEvent(self, event):
        now = time.monotonic()
        t = now - self.started_at
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        xp = 0.0 if self.exit_at is None else min(1.0, (now - self.exit_at) / 0.34)
        card = QRectF(80, 80, self.width() - 160, self.height() - 160)
        c = card.center()
        p.translate(c)
        p.scale((0.9 + 0.1 * _ease_out_back(t / 0.6)) * (1 + 0.06 * xp), (0.9 + 0.1 * _ease_out_back(t / 0.6)) * (1 + 0.06 * xp))
        p.translate(-c)
        base_op = min(1.0, t / 0.3)
        p.setOpacity(base_op)
        p.setBrush(Qt.NoBrush)
        for spread, alpha in ((34, 8), (22, 12), (12, 18), (5, 30)):                       # неонове свічення
            p.setPen(QPen(QColor(90, 140, 255, alpha), spread))
            p.drawRoundedRect(card, 32, 32)
        clip = QPainterPath()
        clip.addRoundedRect(card, 32, 32)
        p.save()
        p.setClipPath(clip)
        p.fillPath(clip, QColor(6, 9, 18))
        sin, cos = math.sin, math.cos
        for fx, fy, r, col in ((0.12 + 0.08 * sin(t * 0.9), 0.08 + 0.06 * cos(t * 0.7), 0.62, QColor(47, 107, 255, 175)),
                               (0.92 + 0.06 * cos(t * 0.8), 0.25 + 0.08 * sin(t * 1.1), 0.55, QColor(139, 77, 255, 150)),
                               (0.45 + 0.10 * sin(t * 0.6), 1.02 + 0.05 * cos(t * 0.9), 0.62, QColor(18, 194, 176, 135)),
                               (0.06 + 0.04 * cos(t * 1.2), 0.92 + 0.04 * sin(t), 0.30, QColor(255, 95, 162, 115))):
            g = QRadialGradient(QPointF(card.left() + fx * card.width(), card.top() + fy * card.height()), r * card.width())
            mid, end = QColor(col), QColor(col)
            mid.setAlpha(col.alpha() // 2)
            end.setAlpha(0)
            g.setColorAt(0, col)
            g.setColorAt(0.5, mid)
            g.setColorAt(1, end)
            p.fillRect(card, g)
        glass = QLinearGradient(card.topLeft(), card.bottomRight())
        glass.setColorAt(0, QColor(255, 255, 255, 30))
        glass.setColorAt(0.5, QColor(255, 255, 255, 8))
        glass.setColorAt(1, QColor(255, 255, 255, 18))
        p.fillRect(card, glass)
        p.restore()
        edge = QLinearGradient(card.topLeft(), card.bottomLeft())
        edge.setColorAt(0, QColor(255, 255, 255, 130))
        edge.setColorAt(0.4, QColor(255, 255, 255, 34))
        edge.setColorAt(1, QColor(255, 255, 255, 55))
        p.setPen(QPen(QBrush(edge), 1.4))
        p.drawRoundedRect(card.adjusted(0.7, 0.7, -0.7, -0.7), 32, 32)

        # --- логотип: пружинна поява, обертове кільце, кольорове заповнення знизу вгору
        lk = _ease_out_back((t - 0.12) / 0.7)
        size = 132.0
        p.save()
        p.translate(QPointF(c.x(), card.top() + 128))
        p.scale(max(0.01, lk), max(0.01, lk))
        p.setOpacity(base_op * max(0.0, min(1.0, (t - 0.1) / 0.3)))
        rect = QRectF(-size / 2, -size / 2, size, size)
        pulse = 0.5 + 0.5 * sin(t * 2.6)
        for spread, alpha in ((28, 9), (17, 15), (8, 26)):
            p.setPen(QPen(QColor(110, 168, 255, int(alpha * (0.6 + 0.4 * pulse))), spread))
            p.drawRoundedRect(rect, 34, 34)
        ring = QConicalGradient(QPointF(0, 0), -(t * 130) % 360)
        for pos, rgb in ((0.0, (48, 207, 236)), (0.33, (57, 139, 255)), (0.66, (166, 112, 255)), (1.0, (48, 207, 236))):
            ring.setColorAt(pos, QColor(*rgb))
        p.setPen(QPen(QBrush(ring), 3))
        p.drawRoundedRect(rect.adjusted(-9, -9, 9, 9), 42, 42)
        tile = QPainterPath()
        tile.addRoundedRect(rect, 34, 34)
        p.save()
        p.setClipPath(tile)
        p.drawImage(rect, self.logo_mono)
        raw = min(1.0, max(0.0, (t - 0.45) / self.color_duration))
        fill = 1.0 - (1.0 - raw) ** 2.2
        if fill > 0:
            fh = rect.height() * fill
            p.save()
            p.setClipRect(QRectF(rect.left(), rect.bottom() - fh, rect.width(), fh), Qt.IntersectClip)
            p.drawImage(rect, self.logo_color)
            p.restore()
            if fill < 1.0:
                y = rect.bottom() - fh
                scan = QLinearGradient(rect.left(), 0, rect.right(), 0)
                scan.setColorAt(0, QColor(255, 255, 255, 0))
                scan.setColorAt(0.5, QColor(255, 255, 255, 210))
                scan.setColorAt(1, QColor(255, 255, 255, 0))
                p.fillRect(QRectF(rect.left(), y - 1.5, rect.width(), 3), scan)
        p.restore()
        p.restore()

        # --- заголовок і підзаголовок
        k = max(0.0, min(1.0, (t - 0.55) / 0.5))
        p.setOpacity(base_op * k)
        tf = QFont(HEAD_FONT, 28)
        tf.setBold(True)
        tf.setLetterSpacing(QFont.AbsoluteSpacing, 1.2)
        p.setFont(tf)
        p.setPen(QColor("#F5F7FB"))
        p.drawText(QRectF(card.left(), card.top() + 218 + (1 - k) * 14, card.width(), 44), Qt.AlignCenter, "Yavir Tools")
        p.setFont(QFont(BODY_FONT, 11))
        p.setPen(QColor("#9FB0CC"))
        p.drawText(QRectF(card.left(), card.top() + 262 + (1 - k) * 14, card.width(), 26), Qt.AlignCenter, "Раді знову вас бачити!")

        # --- смуга завантаження з відблиском і статус
        p.setOpacity(base_op * max(0.0, min(1.0, (t - 0.8) / 0.4)))
        bw = 320.0
        bar = QRectF(c.x() - bw / 2, card.bottom() - 78, bw, 6)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 34))
        p.drawRoundedRect(bar, 3, 3)
        fw = max(6.0, bw * self._progress(now))
        fr = QRectF(bar.left(), bar.top(), fw, bar.height())
        fg = QLinearGradient(bar.left(), 0, bar.right(), 0)
        fg.setColorAt(0, QColor(48, 207, 236))
        fg.setColorAt(0.5, QColor(57, 139, 255))
        fg.setColorAt(1, QColor(166, 112, 255))
        p.setBrush(fg)
        p.drawRoundedRect(fr, 3, 3)
        sx = bar.left() + ((t * 0.9) % 1.5 - 0.25) * fw
        sh = QLinearGradient(sx - 40, 0, sx + 40, 0)
        sh.setColorAt(0, QColor(255, 255, 255, 0))
        sh.setColorAt(0.5, QColor(255, 255, 255, 140))
        sh.setColorAt(1, QColor(255, 255, 255, 0))
        pth = QPainterPath()
        pth.addRoundedRect(fr, 3, 3)
        p.save()
        p.setClipPath(pth)
        p.fillRect(QRectF(sx - 40, bar.top(), 80, bar.height()), sh)
        p.restore()
        if self.done_at is not None:
            status, a = "Готово", 1.0
        else:
            idx = min(len(self.STEPS) - 1, int(t / 0.8))
            ph = (t % 0.8) / 0.8
            a = 1.0 if idx == len(self.STEPS) - 1 else min(1.0, ph * 6, (1.0 - ph) * 6)
            status = self.STEPS[idx]
        p.setOpacity(base_op * max(0.0, a))
        p.setFont(QFont(BODY_FONT, 10))
        p.setPen(QColor("#8393AF"))
        p.drawText(QRectF(card.left(), bar.bottom() + 10, card.width(), 22), Qt.AlignCenter, status)


def main():
    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    except AttributeError:
        pass
    try:
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    except AttributeError:
        pass
    app = QApplication(sys.argv)
    cfg0 = load_cfg()
    _scale = max(0.7, min(2.0, float(cfg0.get("ui_scale", 1.0))))
    app.setFont(QFont(BODY_FONT, round(10 * _scale)))
    app.setStyleSheet(build_qss(cfg0))
    global BOOT_HOOK
    splash = StartupSplash()
    splash.show()
    app.processEvents()
    BOOT_HOOK = splash.repaint

    def open_main_window():
        try:
            window = Main()
            splash.finish(window)
        except Exception:
            details = traceback.format_exc()
            try:
                error_path = os.path.join(DATA, "startup_error.log")
                with open(error_path, "w", encoding="utf-8") as error_file:
                    error_file.write(details)
            except Exception:
                error_path = "(не вдалося записати лог)"
            splash.close()
            QMessageBox.critical(None, "Yavir Tools — помилка запуску",
                                 "Не вдалося відкрити головне вікно.\n"
                                 f"Діагностика записана у:\n{error_path}\n\n{details[-1400:]}")

    QTimer.singleShot(240, open_main_window)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()



