"""Wspólne funkcje testów: wczytywanie konfiguracji, godzin i reguł zakazów."""

import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CZAS = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
DNI_SALONU = {"pon-pt": "Pon–pt", "pon-czw": "Pon–czw", "piatek": "Piątek", "sobota": "Sobota", "niedziela": "Niedziela"}
DNI_DZWONIENIA = {"pon-pt", "pon-czw", "piatek", "sobota"}   # w niedzielę robot nie dzwoni


def klienci():
    """Nazwy klientów = nazwy plików w config/."""
    return sorted(p.stem for p in (ROOT / "config").glob("*.yaml"))


def wczytaj_config(klient):
    return yaml.safe_load((ROOT / "config" / f"{klient}.yaml").read_text(encoding="utf-8"))


def wczytaj_zakazy(klient):
    return json.loads((ROOT / "zakazy" / f"{klient}.json").read_text(encoding="utf-8"))


def wczytaj_wiedze(klient):
    return (ROOT / "wiedza" / f"{klient}.md").read_text(encoding="utf-8")


def minuty(hhmm):
    g, m = hhmm.split(":")
    return int(g) * 60 + int(m)


def godzina_czytelna(hhmm):
    """„09:00” → „9:00” (tak zapisujemy godziny w bazie wiedzy)."""
    g, m = hhmm.split(":")
    return f"{int(g)}:{m}"


_BRAK = object()


def znajdz(dane, sciezka):
    """Wartość pod ścieżką „a.b.c” (klucze mogą zawierać myślniki) albo _BRAK."""
    for klucz in sciezka.split("."):
        if not isinstance(dane, dict) or klucz not in dane:
            return _BRAK
        dane = dane[klucz]
    return dane


def narusza(config, regula):
    """Zwraca opis naruszenia reguły zakazu albo None, gdy konfiguracja ją spełnia."""
    wartosc = znajdz(config, regula["sciezka"])
    if wartosc is _BRAK:
        return f"brak pola {regula['sciezka']}"
    if regula["regula"] == "rowne" and wartosc != regula["wartosc"]:
        return f"{regula['sciezka']} = {wartosc!r}, wymagane {regula['wartosc']!r}"
    if regula["regula"] == "w" and wartosc not in regula["wartosci"]:
        return f"{regula['sciezka']} = {wartosc!r}, dozwolone {regula['wartosci']!r}"
    return None


def sekcja_salonu(wiedza, miasto):
    """Tekst sekcji „### <miasto>” z bazy wiedzy (do następnego nagłówka) albo None."""
    m = re.search(r"^### " + re.escape(miasto) + r"\b.*?$(.*?)(?=^##+ |\Z)", wiedza, re.M | re.S)
    return m.group(1) if m else None


def godziny_z_sekcji(sekcja):
    """{etykieta dnia: (od, do)} z linii „- Sobota: 9:00–15:00” w sekcji salonu."""
    wynik = {}
    for etykieta, od, do in re.findall(r"^- ([^:\n]+): (\d{1,2}:\d{2})–(\d{1,2}:\d{2})\s*$", sekcja, re.M):
        wynik[etykieta] = (od, do)
    return wynik


def adres_z_sekcji(sekcja):
    m = re.search(r"^- Adres: (.+?)\s*$", sekcja, re.M)
    return m.group(1) if m else None
