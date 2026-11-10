WMO = {
    0: "clear",  # ciel dégagé
    1: "partly_cloudy",  # globalement dégagé
    2: "partly_cloudy",  # partiellement nuageux
    3: "cloudy",  # couvert
    45: "fog",  # brouillard
    48: "fog",  # brouillard givrant
    51: "drizzle",  # bruine faible
    53: "drizzle",  # bruine modérée
    55: "drizzle",  # bruine dense
    56: "sleet",  # bruine verglaçante faible
    57: "sleet",  # bruine verglaçante dense
    61: "light_rain",  # pluie faible
    63: "rain",  # pluie modérée
    65: "heavy_rain",  # pluie forte
    66: "sleet",  # pluie verglaçante faible
    67: "sleet",  # pluie verglaçante forte
    71: "light_snow",  # neige faible
    73: "snow",  # neige modérée
    75: "heavy_snow",  # neige forte
    77: "snow_grains",  # grains de neige
    80: "light_showers",  # averses faibles
    81: "showers",  # averses modérées
    82: "heavy_showers",  # averses violentes
    85: "snow_showers",  # averses de neige faibles
    86: "snow_showers",  # averses de neige fortes
    95: "thunderstorm",  # orage
    96: "thunderstorm",  # orage avec grêle faible
    97: "thunderstorm",  # Fort orage avec grêle
    99: "thunderstorm",  # orage avec grêle forte
}


def icon_for(code, is_day):
    cond = WMO.get(code, "unknown")
    suffix = "day" if is_day else "night"
    return f"{cond}_{suffix}.png"
