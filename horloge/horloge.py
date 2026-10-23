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
    backlight = 1.
    force_backlight = None
    hfs = cfs = mfs = False
    last_NE = None
    meteo = None
    weather = 0
    last_weather = 0

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
        if self.last_NE == (month, day, wd, hour, minute) and not self.first:
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
        self.vector.set_font("Roboto-Medium.af", 72)
        heure = f"{hour}:{minute:02d}"
        dim = self.vector.measure_text(heure)
        self.vector.text(heure, 360 - int(dim[2] // 2), 220)
        self.presto.partial_update(240, 0, 240, 240)

    def aff_SO(self):
        self.calendar.affiche(self.cfs)

    def aff_current_weather(self, _):
        if self.meteo is None:
            self.vector.set_font("Roboto-Medium-With-Material-Symbols.af", 20)
            text = "Pas de météo"
            log = self.presto.measure_text(text)
            self.vector.text(text, 360 - int(log[2] / 2), 360)
            return
        y = 280
        self.vector.set_font("Roboto-Medium-With-Material-Symbols.af", 60)
        try:
            text = f"{self.meteo['current']['temp_c']}°C"
            log = self.vector.measure_text(text)
            # le symbole ° est mal calculé pour la largeur !
            # self.vector.text(text, 360 - int(log[2] / 2), y + 30)
            self.vector.text(text, 250, y + 30)
        except KeyError:
            pass
        self.vector.set_font("Roboto-Medium.af", 38)
        try:
            text = f"{self.meteo['current']['humidity']}%"
            log = self.vector.measure_text(text)
            self.vector.text(text, 470 - int(log[2]), y + 30)
        except KeyError:
            pass
        self.vector.set_font("Roboto-Medium-With-Material-Symbols.af", 36)
        try:
            text = f"{self.meteo['current']['wind_kph']}km/h {self.meteo['current']['wind_dir']}"
            log = self.vector.measure_text(text)
            self.vector.text(text, 360 - int(log[2] / 2), y + 75)
        except KeyError:
            pass
        try:
            icon = '/'.join(
                self.meteo['current']['condition']['icon'].split('/')[-2:])
            icon = f"icons/{icon}"
            self.png.open_file(icon)
            self.png.decode(296, 350, scale=1)
        except OSError:
            try:
                text = self.meteo['current']['condition']['text']
                log = self.vector.measure_text(text)
                self.vector.text(text, 360 - int(log[2] / 2), 390)
                self.vector.set_font("Roboto-Medium-With-Material-Symbols.af",
                                     20)
                text = f"Icone {self.meteo['current']['condition']['code']} manquante"
                log = self.vector.measure_text(text)
                self.vector.text(text, 360 - int(log[2] / 2), 440)
            except KeyError as e:
                print(f"Double exception (237) : {e}")

    def aff_hourly_weather(self, now):
        if self.meteo is None:
            self.vector.set_font("Roboto-Medium-With-Material-Symbols.af", 20)
            text = "Pas de météo"
            log = self.presto.measure_text(text)
            self.vector.text(text, 360 - int(log[2] / 2), 360)
            return
        forecast = self.meteo['forecast']['forecastday'][0]['hour']
        debut = 0
        while forecast[debut]['time_epoch'] < now:
            debut += 1
        x = 248
        self.vector.set_font("Roboto-Medium-With-Material-Symbols.af", 28)
        for _ in '123':
            self.display.set_pen(self.fg)
            y = 300
            try:
                text = forecast[debut]['time'].split()[1]
                # pos = int(self.vector.measure_text(text)[2])
                self.vector.text(text, x, y)
                y += 30
            except IndexError:
                forecast = self.meteo['forecast']['forecastday'][1]['hour']
                debut = 0
                try:
                    text = forecast[debut]['time'].split()[1]
                    self.vector.text(text, x, y)
                    y += 30
                except IndexError as e:
                    print(f"Double exception (269) : {e}")
            try:
                text = f"{forecast[debut]['temp_c']}°C"
                # pos = int(self.vector.measure_text(text)[2])
                self.vector.text(text, x, y)
            except IndexError:
                print("Erreur d'index #2")
            try:
                icon = '/'.join(
                    forecast[debut]['condition']['icon'].split('/')[-2:])
                icon = f"icons64/{icon}"
                self.png.open_file(icon)
            except IndexError:
                print("Erreur d'index #3")
            self.png.decode(x, 350)
            debut += 1
            x += 80

    def aff_daily_weather(self, now):
        if self.meteo is None:
            self.vector.set_font("Roboto-Medium-With-Material-Symbols.af", 20)
            text = "Pas de météo"
            log = self.presto.measure_text(text)
            self.vector.text(text, 360 - int(log[2] / 2), 360)
            return
        forecast = self.meteo['forecast']['forecastday']
        x = 248
        self.vector.set_font("Roboto-Medium-With-Material-Symbols.af", 28)
        for i in range(3):
            self.display.set_pen(self.fg)
            data = forecast[i]['day']
            y = 300
            text = forecast[i]['date'].split('-')
            text = f"{text[2]}/{text[1]}"
            self.vector.text(text, x, y)
            y += 30
            text = f"{data['maxtemp_c']}°C"
            self.vector.text(text, x, y)
            y += 30
            text = f"{data['avgtemp_c']}°C"
            self.vector.text(text, x, y)
            y += 30
            text = f"{data['mintemp_c']}°C"
            self.vector.text(text, x, y)
            y += 10
            icon = '/'.join(data['condition']['icon'].split('/')[-2:])
            icon = f"icons64/{icon}"
            self.png.open_file(icon)
            self.png.decode(x, y)
            x += 80

    def aff_SE(self, now, minute, second):
        fct = (self.aff_current_weather, self.aff_hourly_weather,
               self.aff_daily_weather)
        if now - self.last_weather > 299 and (
                minute % 5) == 0 and second == 0 or self.first:
            self.meteo = get_weather()
            self.last_weather = now
        self.display.set_pen(Color.BLACK)
        self.display.rectangle(240, 240, 240, 240)
        self.display.set_pen(self.fg)
        if self.mfs:
            self.weather = (self.weather + 1) % len(fct)
            self.mfs = False
        fct[self.weather](now)
        self.presto.partial_update(240, 240, 240, 240)

    def gere_backlight(self, hour, minute, second):
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

    def affiche(self):
        self.first = True
        self.presto.set_backlight(self.backlight)
        lst_bl = self.backlight
        while True:
            if self.mqtt.client is not None:
                self.mqtt.check_msg()
            self.gere_touch()
            now = time.time()
            if now == self.next_update_time:
                # Mise à l'heure via NTP
                if verifier_connexion(self.presto, self.loggin):
                    print("verifier_connexion() => mqtt.reconnect()")
                    self.mqtt.reconnect()
                update_time(self.loggin, False)
            self.offset = 3600 * TZ.get_offset(now)
            _, month, day, hour, minute, second, wd, _ =\
                time.gmtime(now + self.offset)
            if self.last_second == second:
                # On ne met à jour l'affichage qu'une fois par seconde
                time.sleep_ms(10)
                continue
            self.gere_backlight(hour, minute, second)
            if self.backlight != lst_bl:
                self.presto.set_backlight(self.backlight)
                lst_bl = self.backlight

            # Quadran NO : Horloge analogique
            # print(f"{time.time()}:NO")
            self.aff_NO(hour, minute, second)
            # Quadran NE : Date / heure en texte
            # print(f"{time.time()}:NE")
            self.aff_NE(month, day, wd, hour, minute)
            # Quadran SE : Météo
            # print(f"{time.time()}:SE")
            self.aff_SE(now, minute, second)
            # Quadran SO : Calendrier
            if self.first or self.cfs:
                # print(f"{time.time()}:SO")
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
                self.alerte.id_show = False
                print("Demande de réaffichage complet")
            gc.collect()
            # self.presto.partial_update(0, 0, 480, 240)
