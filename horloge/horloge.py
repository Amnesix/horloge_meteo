import gc
import sys
import time

import jpegdec
from picovector import Polygon
from pngdec import PNG

from horloge.utils import (
    JOURS,
    MOIS,
    TZ,
    Color,
    get_touch,
    get_weather,
    update_time,
    verifier_connexion,
)
from horloge.version import __title__, __version__

v = sys.version
__python__ = "µPython - " + v.split(";")[0]

WIDTH, HEIGHT = 480, 480


class Horloge:
    last_second = 0
    total = 1
    backlight = 1.
    force_backlight = None
    hfs = cfs = mfs = False
    last_NE = None

    def __init__(
        self,
        presto,
        display,
        vector,
        tr,
        touch,
        mqtt,
        calendar,
        alerte,
        loggin,
    ):
        self.presto = presto
        self.display = display
        self.vector = vector
        self.tr = tr
        self.touch = touch
        self.mqtt = mqtt
        self.calendar = calendar
        self.alerte = alerte
        self.loggin = loggin
        self.local = True
        self.vector.set_font("Roboto-Medium-With-Material-Symbols.af", 32)
        self.fg = Color.LIGHTGREY
        self.titre = f"{__title__} - {__version__}"
        self.pos_jours = []
        self.topic = None
        self.t_msg = 0
        self.m_msg = ""
        self.offset = 0
        self.png = PNG(self.display)
        # len = int(self.vector.measure_text(self.titre)[2])
        self.loggin.log(f"Initialisation {self.titre}")
        self.vector.set_font("Roboto-Medium-With-Material-Symbols.af", 25)
        # Pour le décodage de l'image de fond
        self.jpg = jpegdec.JPEG(self.display)

        self.next_update_time = time.time() + 12 * 60 * 60

        self.hub = Polygon()
        self.hub.circle(int(WIDTH / 4), int(HEIGHT / 4), 5)

        self.minute_hand_length = int(HEIGHT / 4) - int(HEIGHT / 16)
        self.minute_hand = Polygon()
        self.minute_hand.path(
            (-3, -self.minute_hand_length),
            (-4, int(HEIGHT / 32)),
            (0, int(HEIGHT / 32) - 1),
            (4, int(HEIGHT / 32)),
            (3, -self.minute_hand_length),
            (0, -self.minute_hand_length - 3),
        )

        self.hour_hand_length = int(HEIGHT / 4) - int(HEIGHT / 9)
        self.hour_hand = Polygon()
        self.hour_hand.path(
            (-4, -self.hour_hand_length),
            (-5, int(HEIGHT / 32)),
            (0, int(HEIGHT / 32) - 1),
            (5, int(HEIGHT / 32)),
            (3, -self.hour_hand_length),
            (0, -self.hour_hand_length - 3),
        )

        self.second_hand_length = int(HEIGHT / 4) - int(HEIGHT / 16)
        self.second_hand = Polygon()
        self.second_hand.path(
            (-1, -self.second_hand_length),
            (-1, int(HEIGHT / 16)),
            (1, int(HEIGHT / 16)),
            (1, -self.second_hand_length),
        )

        self.display.set_pen(Color.BLACK)
        self.display.clear()

    def set_backlight(self, bl):
        self.backlight = bl
        print(f'backlight = {bl}')

    def gere_touch(self):
        data = get_touch(self.touch)
        if data == "NO":
            self.hfs = True
        elif data == "NE":
            pass
        elif data == "SO":
            self.cfs = True
        elif data == "SE":
            self.mfs = True

    def aff_NO(self, hour, minute, second):
        self.tr.reset()
        self.display.set_pen(Color.BLACK)
        self.display.rectangle(0, 0, 240, 240)
        self.jpg.open_file("img/cadran_240.jpg")
        self.jpg.decode(0, 0, jpegdec.JPEG_SCALE_HALF, dither=True)

        x, y = (WIDTH // 4, HEIGHT // 4)
        angle_minute = minute * 6
        angle_minute += second / 10.0
        angle_hour = (hour % 12) * 30
        angle_hour += minute / 2
        angle_second = second * 6

        # Dessin des aiguilles
        self.display.set_pen(Color.ORANGECLAIR)
        self.tr.rotate(angle_minute, (x, y))
        self.tr.translate(x, y)
        self.vector.draw(self.minute_hand)
        self.tr.reset()

        self.tr.rotate(angle_hour, (x, y))
        self.tr.translate(x, y)
        self.vector.draw(self.hour_hand)
        self.tr.reset()

        self.display.set_pen(Color.RED)
        self.tr.rotate(angle_second, (x, y))
        self.tr.translate(x, y)
        self.vector.draw(self.second_hand)
        self.tr.reset()
        self.vector.draw(self.hub)
        self.presto.partial_update(0, 0, 240, 240)

    def aff_NE(self, month, day, wd, hour, minute):
        if self.last_NE == (month, day, wd, hour, minute):
            return
        self.last_NE = (month, day, wd, hour, minute)
        self.display.set_pen(Color.BLACK)
        self.display.rectangle(240, 0, 240, 240)
        self.display.set_pen(self.fg)
        self.vector.set_font("Roboto-Medium.af", 40)
        jour = f"{JOURS[wd]}"
        dim = self.vector.measure_text(jour)
        self.vector.text(jour, 360 - int(dim[2] // 2), 40)
        mois = f"{MOIS[month - 1]}"
        dim = self.vector.measure_text(mois)
        self.vector.text(mois, 360 - int(dim[2] // 2), 140)
        self.vector.set_font("Roboto-Medium.af", 64)
        date = f"{day}"
        dim = self.vector.measure_text(date)
        self.vector.text(date, 360 - int(dim[2] // 2), 100)
        # annee = f"{year}"
        # dim = self.vector.measure_text(annee)
        # self.vector.text(annee, 360 - int(dim[2] // 2), 160)
        self.vector.set_font("Roboto-Bold.af", 64)
        heure = f"{hour}:{minute:02d}"
        dim = self.vector.measure_text(heure)
        self.vector.text(heure, 360 - int(dim[2] // 2), 220)
        self.presto.partial_update(240, 0, 240, 240)

    def aff_SO(self):
        self.calendar.affiche(self.cfs)

    def aff_SE(self):
        meteo = get_weather()
        self.display.set_pen(Color.BLACK)
        self.display.rectangle(240, 240, 240, 240)
        self.display.set_pen(self.fg)
        y = 280
        self.vector.set_font("Roboto-Medium-With-Material-Symbols.af", 64)
        text = f"{meteo['current']['temp_c']}oC"
        log = self.vector.measure_text(text)
        # le symbole ° est mal calculé pour la largeur !
        text = text.replace('o', '°')
        self.vector.text(text, 360 - int(log[2] / 2), y + 30)
        self.vector.set_font("Roboto-Medium.af", 32)
        text = f"{meteo['current']['wind_kph']}km/h {meteo['current']['wind_dir']}"
        log = self.vector.measure_text(text)
        self.vector.text(text, 360 - int(log[2] / 2), y + 70)
        try:
            icon = '/'.join(
                meteo['current']['condition']['icon'].split('/')[-2:])
            icon = f"icons/{icon}"
            self.png.open_file(icon)
            self.png.decode(296, 350)
        except OSError:
            text = meteo['current']['condition']['text']
            log = self.vector.measure_text(text)
            self.vector.text(text, 360 - int(log[2] / 2), 390)
            self.vector.set_font("Roboto-Medium-With-Material-Symbols.af", 20)
            text = f"Icone {meteo['current']['condition']['code']} manquante"
            log = self.vector.measure_text(text)
            self.vector.text(text, 360 - int(log[2] / 2), 440)
        self.presto.partial_update(240, 240, 240, 240)

    def affiche(self):
        self.first = True
        self.presto.set_backlight(self.backlight)
        lst_bl = self.backlight
        while True:
            self.mqtt.check_msg()
            self.gere_touch()
            now = time.time()
            if now == self.next_update_time:
                # Mise à l'heure via NTP
                if verifier_connexion(self.presto, self.loggin):
                    self.mqtt.reconnect()
                update_time(self.loggin, False)
            self.offset = 3600 * TZ.get_offset(now)
            _, month, day, hour, minute, second, wd, _ =\
                time.gmtime(now + self.offset)
            if self.last_second == second:
                # On ne met à jour l'affichage qu'une fois par seconde
                time.sleep_ms(10)
                continue
            if self.force_backlight is None:
                # Gestion luminosité. Plus tard, utilisation d'un capteur de lumière...
                if hour == minute == second == 0:
                    self.first = True  # Réafficher le calendrier
                if hour == 21:
                    if minute < 15:
                        self.backlight = .5
                    elif minute < 30:
                        self.backlight = .4
                    elif minute < 45:
                        self.backlight = .3
                    else:
                        self.backlight = .2
                elif hour == 5 or hour == 22:
                    self.backlight = .1
                elif 23 == hour or hour < 5:
                    self.backlight = .01
                else:
                    self.backlight = 1
            else:
                self.backlight = self.force_backlight
            if self.backlight != lst_bl:
                self.presto.set_backlight(self.backlight)
                lst_bl = self.backlight

            # Quadran NO : Horloge analogique
            self.aff_NO(hour, minute, second)
            # Quadran NE : Date / heure en texte
            self.aff_NE(month, day, wd, hour, minute)
            # Quadran SE : Météo
            if (minute % 5) == 0 and second == 0 or self.first:
                self.aff_SE()
            # Quadran SO : Calendrier
            if self.first or self.cfs:
                self.aff_SO()
                if self.cfs:
                    self.cfs = False
                    self.first = True
                else:
                    self.first = False
            self.last_second = second
            if self.alerte.id_show:
                # self.alerte.show()
                self.first = True
            gc.collect()
            self.total += 1

            self.presto.partial_update(0, 0, 480, 240)
