import json
import math
import random
import time

import ntptime
import requests
from picovector import Polygon
from requests import get

from myapp.secret import APIHA, CONFIG, METEO_KEY, MQTT_DISTANT, headers

OZOIR = (48.763827, 2.671739)
OZOIR_NAME = "ozoir-la-ferriere"
WEATHER_API = "https://api.weatherapi.com/v1/current.json"
METEO_URL = f"{WEATHER_API}?key={METEO_KEY}&q={OZOIR_NAME}&aqi=no&lang=fr"

NTPHOST = (
    "0.fr.pool.ntp.org",
    "1.fr.pool.ntp.org",
    "2.fr.pool.ntp.org",
    "3.fr.pool.ntp.org",
)

JOURS = ("Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi",
         "Dimanche")
MOIS = (
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
)

FILTRES = []
NB_MAX_HISTO = 100
NB_MAX_DISPLAY = 18

net_config = 0
api = APIHA
mqtt = MQTT_DISTANT


def set_api(indice):
    global api, mqtt
    api = CONFIG[indice][2]
    mqtt = CONFIG[indice][3]


def get_api():
    return (api, mqtt)


class Log:

    def __init__(self, presto, display, vector, title):
        self.presto = presto
        self.display = display
        self.vector = vector
        self.title = title
        self.vector.set_font("Roboto-Medium-With-Material-Symbols.af", 32)
        len = self.vector.measure_text(self.title)
        self.title_coord = (int(480 - len[2]) // 2, 25)
        self.ligne = 0
        self.msg = []
        self.new_message = True

    def set_title(self, title):
        self.title = title

    def log(self, msg, color=None, nl=True, aff=True):
        if color is None:
            color = Color.LIGHTGREY
        if nl:
            self.msg.append((time.time(), msg, color))
            if len(self.msg) > NB_MAX_HISTO:
                self.msg.pop(0)
        else:
            # Remplace le dernier message
            self.msg[-1] = (time.time(), msg, color)
        self.new_message = True
        if aff:
            self.update_screen()

    def update_screen(self):
        self.display.set_pen(Color.BLACK)
        self.display.clear()
        self.display.set_pen(Color.LIGHTGREY)
        self.vector.set_font("Roboto-Medium-With-Material-Symbols.af", 32)
        self.vector.text(self.title, *self.title_coord)
        self.vector.set_font("Roboto-Medium-With-Material-Symbols.af", 25)
        for index, data in enumerate(self.msg[-NB_MAX_DISPLAY::]):
            try:
                self.display.set_pen(data[2])
            except IndexError:
                print(data)
            self.vector.text(data[1], 0, (index + 2) * 25)
        self.presto.update()
        self.new_message = False

    def get_stat(self):
        """Nombre de message par minutes sur les len(msg) derniers messages"""
        if len(self.msg) > 0:
            delai = (time.time() - self.msg[0][0]) / 60.
            if delai > 0.:
                return len(self.msg) / delai
        return 0


def wifi_connect(presto, loggin=None):
    global net_config

    def teste_connexion():
        # En cas de reonnexion, j'ai systématiquement un TIMEOUT. Pourquoi ?
        if not presto.wifi.isconnected():
            if loggin:
                loggin.log("Non connecté !")
            return False
        try:
            response = get(api, headers=headers, timeout=5.0)
            if loggin:
                loggin.log(response.text)
            return True
        except Exception as e:
            if loggin:
                loggin.log(f"wifi_connect():Exception ({e})")
            print(f"wifi_connect():Exception ({e})")
        return False

    try:
        with open("wifi.json", "rt") as f:
            d = json.load(f)
    except OSError:
        d = {"indice": 0}
    indice = d["indice"]
    while True:
        if loggin is not None:
            loggin.log(f" * SSID={CONFIG[indice][0]} : ")
        ok = presto.connect(ssid=CONFIG[indice][0], password=CONFIG[indice][1])
        if ok:
            if loggin is not None:
                loggin.log(f" * SSID={CONFIG[indice][0]} : OK", nl=False)
            net_config = indice
            set_api(indice)
            d["indice"] = indice
            if loggin is not None:
                loggin.log(f"IP : {presto.wifi.ipv4()}")
            teste_connexion()
            with open("wifi.json", "wt") as f:
                json.dump(d, f)
            return
        if loggin is not None:
            loggin.log(f" * SSID={CONFIG[indice][0]} : NOK", nl=False)
        indice = (indice + 1) % len(CONFIG)


def verifier_connexion(presto, loggin):
    """En cas de perte de connexion, tentative de reconnexion"""
    if not presto.wifi.isconnected():
        loggin.log("Perte de connexion !")
        loggin.log("Tentative de reconnexion...")
        wifi_connect(presto, loggin)
        return True
    return False


def get_weather():
    rep = requests.get(METEO_URL, timeout=15)
    return rep.json()


def get_touch(touch) -> "tuple[int, int] | str | None":
    touch.poll()
    if touch.state:
        xs, ys = touch.x, touch.y
        while touch.state:
            touch.poll()
        dx, dy = xs - touch.x, ys - touch.y
        if math.sqrt(dx * dx + dy * dy) > 100:
            if abs(dx) < abs(dy):
                if dy < 0:
                    return 'D'
                else:
                    return 'U'
            else:
                if dx < 0:
                    return 'R'
                else:
                    return 'L'
        else:
            return (xs, ys)
    return None


def update_time(loggin, show_log=True):
    # Mise à l'heure
    if show_log:
        loggin.log("Mise à l'heure")
    server = random.choice(range(4))
    while True:
        s = f" * Serveur NTP {NTPHOST[server]}"
        if show_log:
            loggin.log(s)
        ntptime.timeout = 5
        ntptime.host = NTPHOST[server]
        try:
            ntptime.settime()
        except Exception:
            if show_log:
                s += " : Erreur !"
                loggin.log(s, nl=False)
            server = (server + 1) % 4
        else:
            if show_log:
                s += " : OK"
                loggin.log(s, nl=False)
            return


class TZ:
    """Classe minimaliste permettant de connaitre le
    décalage horraire sur le fuseau de Paris en
    tenant compte de l'heure d'été."""
    _ready = False
    start = None
    end = None

    @classmethod
    def init(cls, loggin, year=None):
        if cls._ready:
            return
        if year is None:
            s = time.time()
            year, _, _, _, _, _, _, _ = time.gmtime(s)
        # print(f"Init TZ for year {year}")
        cls.start = cls.dst_start(year)
        cls.end = cls.dst_end(year)
        _, ms, js, _, _, _, _, _ = time.gmtime(cls.start)
        _, me, je, _, _, _, _, _ = time.gmtime(cls.end)
        loggin.log(
            f"{year} : heure été du {js} {MOIS[ms - 1]} au {je} {MOIS[me - 1]}"
        )
        _ready = True

    @classmethod
    def get_offset(cls, s):
        return 2 if cls.start <= s <= cls.end else 1

    @classmethod
    def dst_start(cls, year):
        last_sun_march = 31
        # Rechercher le dernier dimanche du mois de mars
        for day in range(31, 24, -1):
            if (time.localtime(time.mktime(
                (year, 3, day, 2, 0, 0, 0, 0, 0)))[6] == 6):  # dimanche
                last_sun_march = day
                break
        return time.mktime((year, 3, last_sun_march, 2, 0, 0, 0, 0, 0))

    @classmethod
    def dst_end(cls, year):
        last_sun_oct = 31
        # Rechercher le dernier dimanche du mois d'octobre
        for day in range(31, 24, -1):
            if time.localtime(time.mktime(
                (year, 10, day, 3, 0, 0, 0, 0, 0)))[6] == 6:
                last_sun_oct = day
                break
        return time.mktime((year, 10, last_sun_oct, 3, 0, 0, 0, 0, 0))


class Color:
    _ready = False
    BLACK = None
    WHITE = None
    LIGHTGREY = None
    RED = None
    GREEN = None
    BLUE = None
    LIGHTRED = None
    LIGHTGREEN = None
    LIGHTBLUE = None
    ORANGE = None
    CYAN = None
    LIGHTYELLOW = None
    LIGHTORANGE = None
    GREY = None
    DARKGREY = None
    DARKRED = None
    DARKGREEN = None
    DARKBLUE = None
    DARKORANGE = None
    DARKCYAN = None

    @classmethod
    def init(cls, display):
        if cls._ready:
            return
        cls.BLACK = display.create_pen(0, 0, 0)
        cls.WHITE = display.create_pen(255, 255, 255)
        cls.RED = display.create_pen(127, 0, 0)
        cls.GREEN = display.create_pen(0, 127, 0)
        cls.BLUE = display.create_pen(0, 0, 127)
        cls.LIGHTRED = display.create_pen(255, 0, 0)
        cls.LIGHTGREEN = display.create_pen(0, 255, 0)
        cls.LIGHTBLUE = display.create_pen(0, 0, 255)
        cls.ORANGE = display.create_pen(127, 39, 5)
        cls.ORANGECLAIR = display.create_pen(127, 69, 10)
        cls.CYAN = display.create_pen(0, 127, 127)
        cls.LIGHTYELLOW = display.create_pen(126, 130, 94)
        cls.LIGHTORANGE = display.create_pen(162, 71, 3)
        cls.GREY = display.create_pen(96, 96, 96)
        cls.LIGHTGREY = display.create_pen(127, 127, 127)
        cls.DARKGREY = display.create_pen(48, 48, 48)
        cls.DARKRED = display.create_pen(63, 0, 0)
        cls.DARKGREEN = display.create_pen(0, 63, 0)
        cls.DARKBLUE = display.create_pen(0, 0, 63)
        cls.DARKORANGE = display.create_pen(63, 19, 2)
        cls.DARKCYAN = display.create_pen(0, 63, 63)
        cls.DARKVIOLET = display.create_pen(66, 16, 66)
        cls.DARKJAUNE = display.create_pen(86, 86, 26)

        cls._ready = True


class Alerte:
    message = []
    id_show = False

    def __init__(self, presto, display, vector, touch, loggin):
        loggin.log("Initialisation alertes")
        self.presto = presto
        self.display = display
        self.vector = vector
        self.touch = touch
        self.loggin = loggin
        self.cadre = Polygon()
        self.cadre.rectangle(48, 78, 384, 239)
        self.fond = Polygon()
        self.fond.rectangle(50, 80, 380, 235)
        self.w = 374  # Largeur affichage max
        self.h = 235

    def alerte(self, msg):
        self.vector.set_font("Roboto-Medium-With-Material-Symbols.af", 32)
        words = msg.split()
        self.message.clear()
        self.message.append(words.pop(0))
        while len(words):
            word = words.pop(0)
            w = self.vector.measure_text(f"{self.message[-1]} {word}")[2]
            if w > self.w:
                self.message.append(word)
            else:
                self.message[-1] += " " + word
        self.id_show = True

    def show(self, timeout=10):
        # Fin de l'affichage :
        s = time.time() + timeout
        self.display.set_pen(Color.BLACK)
        self.display.clear()
        self.display.set_pen(Color.CYAN)
        self.vector.draw(self.cadre)
        self.display.set_pen(Color.RED)
        self.vector.draw(self.fond)
        self.vector.set_font("Roboto-Medium-With-Material-Symbols.af", 32)
        self.display.set_pen(Color.LIGHTYELLOW)
        hp = 82 + (self.h - len(self.message) * 16) // 2
        for pos, line in enumerate(self.message):
            dim = self.vector.measure_text(line, x=0, y=0, angle=0)
            offset = (self.w - int(dim[2])) // 2
            self.vector.text(line, 52 + offset, hp + pos * 32)
        self.presto.update()
        while time.time() < s:
            if get_touch(self.touch):
                break
            time.sleep(.25)
        Page.set_redraw(True)
        self.id_show = False


class MyButton:

    def __init__(self, touch, x, y, w, h, name):
        self.touch = touch
        self.x1 = x
        self.y1 = y
        self.w = w
        self.h = h
        self.x2 = x + w
        self.y2 = y + h
        self.name = name

    def is_pressed(self):
        if self.touch.state:
            x, y = self.touch.x, self.touch.y
            return self.x1 <= x <= self.x2 and self.y1 <= y <= self.y2
        return False

    def is_clicked(self):
        x, y = self.touch.x, self.touch.y
        if self.is_pressed():
            while self.touch.state:
                x, y = self.touch.x, self.touch.y
                self.touch.poll()
            return self.x1 <= x <= self.x2 and self.y1 <= y <= self.y2

    def bounds(self) -> tuple[int, int, int, int]:
        return self.x1, self.y1, self.w, self.h
