import time

import presto
from myapp.alarmes import Alarmes
from picovector import ANTIALIAS_BEST, PicoVector, Transform

from myapp.calendar import Calendar
from myapp.horloge import Horloge
from myapp.mqtt import MQTT, MQTTLog
from myapp.utils import (
    TZ,
    Alerte,
    Color,
    Log,
    get_api,
    update_time,
    wifi_connect,
)
from myapp.version import __title__, __version__

# Initialisation générale
presto = presto.Presto(layers=1, full_res=True)
display = presto.display
display.set_pen(display.create_pen(0, 0, 0))
display.clear()
presto.update()
touch = presto.touch
vector = PicoVector(display)
t = Transform()
vector.set_transform(t)
vector.set_antialiasing(ANTIALIAS_BEST)
Color.init(display)
loggin = Log(presto, display, vector, f"{__title__} - {__version__}")
loggin.log("Connexion Wifi en cours...")

# Connection / Mise à l'heure
wifi_connect(presto, loggin)
update_time(loggin)
TZ.init(loggin)
s = time.time()
start = time.time()
offset = 3600 * TZ.get_offset(s)
y, m, d, H, M, S, _, _ = time.gmtime(s + offset)
loggin.log(f"{y}/{m:02d}/{d:02d} {H:02d}:{M:02d}:{S:02d}")
alerte = Alerte(presto, display, vector, touch, loggin)
alarmes = Alarmes(presto, display, vector, touch, alerte, loggin)
# Initialistion des objets
broker, port = get_api()[1]
mqtt = MQTT(broker, port, alerte, loggin)
# Création des différents objets page
mqttlogs = MQTTLog(presto, display, vector, touch, mqtt, alerte, alarmes)
calendar = Calendar(presto, display, vector, touch, mqtt, alerte, loggin)
horloge = Horloge(presto, display, vector, t, touch, mqtt, calendar, alarmes,
                  alerte, loggin)

# Lancement de l'affichage principal
mqtt.set_fin_init()
loggin.log("Lancement boucle de traitement")
display.set_pen(Color.BLACK)
display.clear()
presto.update()
while True:
    horloge.affiche()

print("The end")
display.set_pen(Color.BLACK)
display.clear()
presto.update()
mqtt.disconnect(False)
# presto.wifi.disconnect(False)
# machine.reset()  # reboot
