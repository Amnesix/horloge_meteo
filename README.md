# MyAPP

Affichage sur le Pimoroni Presto d'une horloge numérique et texte, d'un calendrier et de la météo courante.

## Configuration
Créer le fichier `myapp/secret.pMy` avec le contenu suivant :
```python
APIHA = "http://url-externe:port/api/"
APIHA_LOCAL = "http://url-locale:port/api/"
headers ={ 
    "Authorization": "Bearer #####",
    "content-type": "application/json",
}

MQTT_LOCAL = ("IP_LOCALE", 1883)
MQTT_DISTANT = ("IP_DISTANTE", xxxxx)
MQTT_CREDENTIAL = ("login", "mdp")
METEO_KEY = "À récupérer ici https://www.weatherapi.com/my/

# Autant d'entrée que l'on veut
CONFIG = {
    0: ("SSID1", "MDP1", APIHA_LOCAL, MQTT_LOCAL),
    1: ("SSID2", "MDP2", APIHA, MQTT_DISTANT),
    2: ("SSID3", "MDP3", APIHA, QTT_DISTANT),
}
```

