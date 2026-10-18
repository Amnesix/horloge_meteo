# MyAPP

Cette application utilise HomeAssistant pour récupérer des informations de température et gérer des interrupteurs connectés. Affichage par défaut d'une horloge analogique avec date et température extérieur et intérieur ainsi que le nombre de jours restant avant ma retraite.

J'ai démarré ce code à partir d'un exemple d'horloge récupéré sur le github du pimoroni presto et tout redéfini sous forme de classes.

La date sert de bouton pour afficher le calendrier et le centre de l'horloge pour afficher une autre forme d'horloge. C'est basique mais bien pratique pour le moment. Cela devrait évoluer plus tard.

Les états (températures, switches) sont récupérés via des messages MQTT. Il est donc nécessaire d'installer un broker MQTT. Je suis parti sur Mosquitto installé dans un docker. Cf [Eclipse Mosquitto](https://mosquitto.org) / [docker eclipse-mosquitto](https://hub.docker.com/_/eclipse-mosquitto/)
Je n'utilise aucune protection pour mqtt, ça viendra plus tard.

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

# Autant d'entrée que l'on veut
CONFIG = {
    0: ("SSID1", "MDP1", APIHA_LOCAL, MQTT_LOCAL),
    1: ("SSID2", "MDP2", APIHA, MQTT_DISTANT),
    2: ("SSID3", "MDP3", APIHA, QTT_DISTANT),
}
```
La clé d'authorisation de l'API est à générer sur HomeAssistant : 
 - Dans profile utilisateur (en bas à gauche, clic sur utilisateur) ;
 - Onglet Sécurité ;
 - En bas de page, clic sur Créer un jeton.

 Le scripts permettent via des messages mqtt :
  - page nom -> changement de page
  - alarme (liste|add|del) [hh mm [ss]] -> liste les alarmes / ajoute ou  supprime une alarme
  - alerte 'texte' -> affiche le texte sur l'affichage
  - switche nom 'on|off' -> bascule un switch
  - hadebug 'commande' -> exécute la commande sur le presto

