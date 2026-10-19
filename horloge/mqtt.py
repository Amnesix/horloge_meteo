import binascii
import gc
import time

import machine
from myapp.secret import MQTT_PASSWD, MQTT_USER
from myapp.utils import TZ, Color, Log, verifier_connexion
from umqtt.simple import MQTTClient

_SOUSCRIPTIONS = {
    # Températures
    "home/temp/dehors": "_dehors",
    "home/temp/buandrie": "buandrie",
    "home/temp/bureau": "bureau",
    "home/temp/cuisine": "cuisine",
    "home/temp/cyril": "cyril",
    "home/temp/douche": "douche",
    "home/temp/parent": "parents",
    "home/temp/salon": "salon",
    # Humidité
    "home/humidity/dehors": "_dehors",
    "home/humidity/buandrie": "buandrie",
    "home/humidity/bureau": "bureau",
    "home/humidity/cuisine": "cuisine",
    "home/humidity/cyril": "cyril",
    "home/humidity/douche": "douche",
    "home/humidity/parent": "parents",
    "home/humidity/salon": "salon",
    # Interrupteurs
    "home/switch/ventilo": "Ventilo",
    "home/switch/rpi": "2nd écran",
    "home/switch/eth": "Ethernet",
    "home/switch/lenovo": "PC LENOVO",
    "home/switch/cuisine": "Cuisine",
    "home/switch/douche": "Douche",
    "home/switch/lave_linge": "Lave linge",
    "home/switch/deshum": "Déshumid.",
    "home/switch/info": "PC Bureau",
    "home/switch/pc_rfu": "PC NOUS RFU",
    # Lave lave_linge
    "home/puissance/lave_linge": "-",
    "home/puissance/deshum": "-",
    "home/lave_linge/fincycle": "-",
    # Autres
    "home/page": "-",
    "home/commandes": "-",
    "home/alarme": "-",
}
SOUSCRIPTIONS = {
    "home/alerte": "-",
    "home/debug": "print('OK, je suis là')",
    "home/pong": ""
}

TOPIC_MSG = {
    "2nd écran": "home/toggle/rpi",
    "Douche": "home/toggle/douche",
    "Cuisine": "home/toggle/cuisine",
    "Ventilo": "home/toggle/ventilo",
    "Lave linge": "home/toggle/lave_linge",
    "Déshumid.": "home/toggle/deshum",
    "PC LENOVO": "home/toggle/lenovo",
    "Ethernet": "home/toggle/eth",
    "PC Bureau": "home/toggle/info",
    "PC NOUS RFU": "home/toggle/pc_rfu",
    "ping": "home/ping",
    "alarme": "cmd/alarme",
    "alerte": "cmd/alerte",
}


class MQTT:
    lt = None
    dh = None
    puissance_lv = "0.0"
    puissance_dh = "0.0"
    last_ping = 0

    def __init__(self, broker, port, alerte, loggin):
        loggin.log("Initialisation MQTT")
        self.broker = broker
        self.port = port
        self.alerte = alerte
        self.loggin = loggin
        self.callbacks = []
        self.pile = []
        self.fin_init = False
        self.last_msg = 0
        self.connect()
        self.pong = True
        # Autoreconnexion par défaut
        self.autoreco = True
        loggin.log("Connexion au broker MQTT OK.")

    def set_fin_init(self):
        self.fin_init = True

    def connect(self):
        unique = str(binascii.hexlify(machine.unique_id()))[2:-1]
        self.client_id = f'{unique}' + f"_{time.time() % 10000}"
        self.client = MQTTClient(self.client_id,
                                 self.broker,
                                 port=self.port,
                                 keepalive=600,
                                 user=MQTT_USER,
                                 password=MQTT_PASSWD)
        self.client.set_callback(self.mqtt_callback)
        try:
            self.client.connect()
            self.loggin.log(f"MQTT connecté id={self.client_id}")
            self.loggin.log("Souscription : 0%")
            t = len(SOUSCRIPTIONS)
            for n, k in enumerate(SOUSCRIPTIONS):
                # ATTENTION : Le loggin ralenti l'intialisation du presto…
                s = f"Souscription : {(n + 1) * 100 / t:.0f}%"
                self.loggin.log(s, nl=False)
                self.client.subscribe(k)
        except OSError as e:
            print(f">> Erreur de connexion : {e}")
            self.loggin.log(f"Erreur MQTT : {e}")
            self.client = None

    def disconnect(self, autoreco=True):
        self.autoreco = autoreco
        if self.client is not None:
            # Ce module MQTTClient n'a pas de méthode unsubscribe !
            # for n, k in enumerate(SOUSCRIPTIONS):
            #     self.client.unsubscribe(k)
            self.client.disconnect()
        self.client = None

    def reconnect(self):
        self.loggin.log("Déconnexion client MQTT")
        if self.client is not None:
            try:
                self.client.disconnect()
            except OSError as e:
                print(f"> Erreur de déconnexion : {e}")
        self.loggin.log("Tentative de reconnexion client MQTT")
        self.connect()

    def send_msg(self, what, msg):
        try:
            if self.client is not None:
                self.client.publish(TOPIC_MSG[what], msg)
        except KeyError:
            print(f"Erreur de clé send_msg({what}, {msg})")

    def set_callback(self, fct):
        self.callbacks.append(fct)

    def remove_callback(self, fct):
        self.callbacks.remove(fct)

    def mqtt_callback(self, topic, msg):
        # message_string = msg.decode('utf-8')  # Decode the MQTT message
        topic = topic.decode()
        msg = msg.decode('utf-8')
        self.last_msg = time.time()
        _, _, _, h, m, s, _, _ = time.gmtime(self.last_msg + 3600 *
                                             TZ.get_offset(self.last_msg))
        if 'pong' in topic:
            # Sur cet app, je ne trace plus le pong.
            # print(f"{h:02d}:{m:02d}:{s:02d}:Reception MQTT {topic} : {msg}")
            self.pong = True
            if len(self.pile) == 0:
                return
        else:
            print(f"{h:02d}:{m:02d}:{s:02d}:Reception MQTT {topic} : {msg}")
            self.pile.append((topic, msg))
        if not self.fin_init:
            return
        while len(self.pile):
            topic, msg = self.pile.pop(0)
            for fct in self.callbacks:
                try:
                    fct(topic, msg)
                except Exception as e:
                    print(f"Erreur mqtt_callback() : {e} ({topic}, {msg})")
                    print(fct.__name__)

    def get_room(self, topic):
        return SOUSCRIPTIONS[topic]

    def check_msg(self):
        if time.time() - self.last_ping >= 120:
            # S'il s'est écoulé plus de 120s sans pong, on se reconnecte
            if not self.pong and self.autoreco:
                print("Tentative de reconnexion de mqtt")
                self.reconnect()
            self.send_msg("ping", "")
            self.last_ping = time.time()
            self.pong = False
        try:
            if self.client is not None:
                self.client.check_msg()
        except OSError:
            print("Deconnexion MQTT")
            self.connect()
        except Exception as e:
            print(f"Error while waiting for MQTT messages: {e}")
        if self.lt and time.time() - self.lt > 60\
           and self.puissance_lv == "0.0"\
           and self.puissance_dh == "0.0":
            self.lt = None


class MQTTLog:
    nb_msg = 0

    def __init__(self, presto, display, vector, touch, mqtt, alerte):
        self.presto = presto
        self.display = display
        self.vector = vector
        self.touch = touch
        self.mqtt = mqtt
        self.alerte = alerte
        self.loggin = Log(presto, display, vector, "Messages MQTT")
        self.start = time.time()
        self.mqtt.set_callback(self.cb)

    def cb(self, topic, msg):
        """CallBack messages MQTT"""
        t = time.time()
        _, _, _, h, m, s, _, _ = time.gmtime(t + TZ.get_offset(t) * 3600)
        if 'alert' in topic:
            self.alerte.alerte(msg)
        elif 'debug' in topic:
            # TODO >JMO< À VÉRIFIER !!!
            print(f'exec({msg})')
            exec(msg)
        self.nb_msg += 1

    def affiche(self):
        self.display.set_pen(Color.BLACK)  # Black background
        self.display.clear()
        self.presto.update()
        # forcer le premier affichage
        self.loggin.new_message = True
        while True:
            verifier_connexion(self.presto, self.loggin)
            try:
                # Wait for MQTT messages (non-blocking check)
                self.mqtt.check_msg()
            except Exception as e:
                print(f"Error while waiting for MQTT messages: {e}")
            if self.loggin.new_message:
                self.loggin.update_screen()
            time.sleep(.1)
            t = time.time()
            offset = 3600 * TZ.get_offset(t)
            _, _, _, h, m, s, _, _ = time.gmtime(t + offset)
            self.display.set_pen(Color.BLACK)
            self.display.rectangle(0, 0, 120, 28)
            self.display.set_pen(Color.LIGHTGREY)
            self.vector.set_font("Roboto-Medium-With-Material-Symbols.af", 24)
            self.vector.text(f"{h:02d}:{m:02d}:{s:02d}", 0, 24)
            self.presto.update()
            gc.collect()
            time.sleep(.1)
