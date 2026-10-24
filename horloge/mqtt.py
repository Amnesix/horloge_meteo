import gc
import time

# import machine
from umqtt.simple import MQTTClient

from horloge.secret import IDENTITY, MQTT_PASSWD, MQTT_USER
from horloge.utils import TZ, Color, Log, verifier_connexion

SOUSCRIPTIONS = {
    "home/alerte": "-",
    "home/debug": "print('OK, je suis là')",
}

TOPIC_MSG = {}


class MQTT:
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
        # Autoreconnexion par défaut
        self.autoreco = True
        loggin.log("Connexion au broker MQTT OK.")

    def set_fin_init(self):
        self.fin_init = True

    def connect(self):
        # unique = str(binascii.hexlify(machine.unique_id()))[2:-1]
        self.client_id = f'{IDENTITY}' + f"_{time.time() % 10000}"
        self.loggin.log(f"MQTT client id {self.client_id}")
        self.client = MQTTClient(self.client_id,
                                 self.broker,
                                 port=self.port,
                                 keepalive=600,
                                 user=MQTT_USER,
                                 password=MQTT_PASSWD)
        self.client.set_callback(self.mqtt_callback)
        try:
            self.client.connect()
            self.loggin.log("MQTT connecté")
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
            else:
                print("send_msg() : client = None")
                self.reconnect()
        except KeyError:
            print(f"Erreur de clé send_msg({what}, {msg})")
        except OSError as e:
            print(f"Erreur MQTT send_msg : {e}")

    def set_callback(self, fct):
        self.callbacks.append(fct)

    def remove_callback(self, fct):
        self.callbacks.remove(fct)

    def mqtt_callback(self, topic, msg):
        # message_string = msg.decode('utf-8')  # Decode the MQTT message
        topic = topic.decode()
        msg = msg.decode('utf-8')
        self.last_msg = time.time()
        data = time.gmtime(self.last_msg + 3600 * TZ.get_offset(self.last_msg))
        _, _, _, h, m, s, _, _ = data
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
        try:
            if self.client is not None:
                self.client.check_msg()
        except OSError:
            print("Deconnexion MQTT")
            self.connect()
            return True
        except Exception as e:
            print(f"Error while waiting for MQTT messages: {e}")
        return False


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
