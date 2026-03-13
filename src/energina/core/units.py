"""Conversioni unita di misura per energia e valuta."""


def kwh_to_mwh(kwh: float) -> float:
    return kwh / 1000.0


def mwh_to_kwh(mwh: float) -> float:
    return mwh * 1000.0


def kw_to_mw(kw: float) -> float:
    return kw / 1000.0


def mw_to_kw(mw: float) -> float:
    return mw * 1000.0


def w_to_kw(w: float) -> float:
    return w / 1000.0


def kw_to_w(kw: float) -> float:
    return kw * 1000.0


def eur_mwh_to_eur_kwh(eur_mwh: float) -> float:
    return eur_mwh / 1000.0


def eur_kwh_to_eur_mwh(eur_kwh: float) -> float:
    return eur_kwh * 1000.0


def wp_to_kwp(wp: float) -> float:
    return wp / 1000.0


def kwp_to_wp(kwp: float) -> float:
    return kwp * 1000.0


def celsius_to_kelvin(c: float) -> float:
    return c + 273.15


def kelvin_to_celsius(k: float) -> float:
    return k - 273.15


def gradi_to_radianti(gradi: float) -> float:
    import math
    return gradi * math.pi / 180.0


def radianti_to_gradi(rad: float) -> float:
    import math
    return rad * 180.0 / math.pi
