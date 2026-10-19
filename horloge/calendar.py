import gc
import time

from horloge.utils import MOIS, TZ, Color

CADRAN = ((0, 0), (240, 0), (0, 240), (240, 240))
nfs = 2


def is_leap_year(year):
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)


def days_in_month(year, month):
    if month == 2:
        return 29 if is_leap_year(year) else 28
    if month in (4, 6, 9, 11):
        return 30
    return 31


def prev_month(year, month):
    if month == 1:
        return year - 1, 12
    return year, month - 1


def next_month(year, month):
    if month == 12:
        return year + 1, 1
    return year, month + 1


def weekday(year, month, day):
    # 0 = lundi, 6 = dimanche
    if month < 3:
        month += 12
        year -= 1
    k = year % 100
    j = year // 100
    h = (day + (13 * (month + 1)) // 5 + k + k // 4 + j // 4 + 5 * j) % 7
    return (h + 5) % 7


def add_days(year, month, day, delta):
    while delta > 0:
        dim = days_in_month(year, month)
        if day + delta <= dim:
            day += delta
            delta = 0
        else:
            delta -= dim - day + 1
            year, month = next_month(year, month)
            day = 1

    while delta < 0:
        if day + delta >= 1:
            day += delta
            delta = 0
        else:
            delta += day
            year, month = prev_month(year, month)
            day = days_in_month(year, month)

    return year, month, day


def iso_week_number(year, month, day):
    # Numéro ISO 8601 basé sur le jeudi de la semaine
    wday = weekday(year, month, day)
    y, m, d = add_days(year, month, day, 3 - wday)  # jeudi de la semaine

    jan4_wday = weekday(y, 1, 4)
    week1_monday_y, week1_monday_m, week1_monday_d = add_days(
        y, 1, 4, -jan4_wday)

    days = 0
    cy, cm, cd = week1_monday_y, week1_monday_m, week1_monday_d
    while (cy, cm, cd) != (y, m, d):
        cy, cm, cd = add_days(cy, cm, cd, 1)
        days += 1

    return 1 + days // 7


def monthly_calendar(year, month):
    month_days = days_in_month(year, month)
    first_wday = weekday(year, month, 1)

    result = []
    result.append(["", "lu", "ma", "me", "je", "ve", "sa", "di"])

    py, pm = prev_month(year, month)
    prev_days = days_in_month(py, pm)

    day = 1
    start_day = prev_days - first_wday + 1

    # Trouver le lundi de la première ligne
    if first_wday == 0:
        line_year, line_month, line_day = year, month, 1
    else:
        line_year, line_month, line_day = py, pm, start_day

    while True:
        week = [str(iso_week_number(line_year, line_month, line_day))]
        cy, cm, cd = line_year, line_month, line_day

        for i in range(7):
            if (cy, cm, cd) == (year, month, day) and day <= month_days:
                week.append(str(day))
                day += 1
            else:
                week.append(str(cd))
            cy, cm, cd = add_days(cy, cm, cd, 1)

        result.append(week)

        # Arrêt quand on a dépassé le mois et fini la semaine courante
        if day > month_days and (cy, cm) != (year, month):
            break

        line_year, line_month, line_day = cy, cm, cd

    return result


class Calendar:
    pen = None
    full_screen = False

    def __init__(self, presto, display, vector, touch, mqtt, alerte, loggin):
        loggin.log("Initialisation calendrier")
        self.presto = presto
        self.display = display
        self.vector = vector
        self.touch = touch
        self.mqtt = mqtt
        self.alerte = alerte
        self.loggin = loggin
        self.color_we = display.create_pen(118, 118, 118)
        self.yoffset = 10
        self.fg = Color.LIGHTGREY
        # Initialisation de l'affichage
        self.init_calendar(time.time())

    def init_calendar(self, s):
        self.offset = 3600 * TZ.get_offset(s)
        self.ny, self.nm, d, _, _, _, _, _ = time.gmtime(s + self.offset)
        self.year = self.ny
        self.month = self.nm
        self.mday = d  # Utilisé pour la surbrillance de la date courante
        self.calendar = monthly_calendar(self.year, self.month)

    def set_year(self, year):
        self.year = year
        self.calendar = monthly_calendar(self.year, self.month)

    def set_month(self, month):
        if month == 0:
            month = 12
            self.set_year(self.year - 1)
        elif month == 13:
            month = 1
            self.set_year(self.year + 1)
        self.month = month
        self.calendar = monthly_calendar(self.year, self.month)

    def set_pen(self, pen):
        if self.pen != pen:
            self.pen = pen
            self.display.set_pen(self.pen)

    def draw_calendar(self, maj, cadran):
        dx, dy = cadran
        self.set_pen(Color.BLACK)
        self.display.rectangle(dx, dy, 240, 240)  # (12, 70, 58, 53)
        # Affichage du text
        # self.set_pen(self.fg)
        self.set_pen(Color.LIGHTGREY)
        s = f"{MOIS[self.month - 1]} {self.year}"
        self.vector.set_font("Roboto-Medium-With-Material-Symbols.af", 28)
        x, y = dx + int(120 - self.vector.measure_text(s)[2] // 2), dy + 40
        self.vector.text(s, x, y + self.yoffset)
        self.vector.set_font("Roboto-Medium-With-Material-Symbols.af", 22)
        y = dy + 55 + self.yoffset
        i = -1
        change_font = True
        for line in self.calendar:
            x = dx + 8
            first = True
            for s in line:
                if first:
                    first = False
                    self.set_pen(Color.ORANGE)
                else:
                    if s == "1" and x != 7:
                        i += 1
                    if i == -1:
                        self.set_pen(self.fg)
                    elif i == 1 or y == 55:
                        # Affichage date du jour en orange (même mois, même année)
                        if str(
                                self.mday
                        ) == s and self.year == self.ny and self.month == self.nm:
                            self.set_pen(Color.LIGHTORANGE)
                        else:
                            self.set_pen(self.fg)
                    else:
                        self.set_pen(Color.GREY)
                l = int((25 - self.vector.measure_text(s)[2]) // 2)
                self.vector.text(s, x + l, y + self.yoffset)
                x += 28
            if i == -1:
                i = 0
            if change_font:
                change_font = False
                self.vector.set_font("Roboto-Medium-With-Material-Symbols.af",
                                     23)
            y += 25
        self.presto.partial_update(dx, dy, 240, 240)

    def affiche(self, full_screen):
        self.init_calendar(time.time())
        self.full_screen = full_screen
        if full_screen:
            for cadran in CADRAN:
                self.draw_calendar(True, cadran)
                self.set_month(self.month + 1)
            while True:
                self.touch.poll()
                if self.touch.state:
                    while self.touch.state:
                        self.touch.poll()
                    return
        else:
            self.draw_calendar(True, CADRAN[2])
        gc.collect()
