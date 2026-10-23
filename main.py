import time

import presto
from picovector import ANTIALIAS_BEST, PicoVector, Transform

from horloge.calendar import Calendar
from horloge.horloge import Horloge
from horloge.mqtt import MQTT
from horloge.utils import (
    TZ,
    Alerte,
    Color,
    Log,
    get_api,
    update_time,
    wifi_connect,
)
from horloge.version import __title__, __version__

# Initialisation générale
# layers=1 nécessaire pour partial_update()
presto = presto.Presto(layers=1, full_res=True)
display = presto.display  # = picographics
Color.init(display)
display.set_pen(Color.BLACK)
# Effacer l'écran
display.clear()
presto.update()
# Dalle tactike
touch = presto.touch
# Graphisme évolué
vector = PicoVector(display)
t = Transform()
vector.set_transform(t)
vector.set_antialiasing(ANTIALIAS_BEST)
# Initialisation classe log infos
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
# Initialisation affichage message d'alerte
alerte = Alerte(presto, display, vector, touch, loggin)
# Initialistion du broker MQTT (lien Home Assistant)
broker, port = get_api()[1]
mqtt = MQTT(broker, port, alerte, loggin)
# Création des différents objets page
# mqttlogs = MQTTLog(presto, display, vector, touch, mqtt, alerte)
calendar = Calendar(presto, display, vector, touch, mqtt, alerte, loggin)
horloge = Horloge(presto, display, vector, t, touch, mqtt, calendar, alerte,
                  loggin)

# Lancement de l'affichage principal
mqtt.set_fin_init()
loggin.log("Lancement boucle de traitement")
display.set_pen(Color.BLACK)
display.clear()
presto.update()
while True:
    horloge.affiche()
