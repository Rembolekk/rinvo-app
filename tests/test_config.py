"""Walidacja schematu i spójności konfiguracji klientów (config/<klient>.yaml) i bazy wiedzy (wiedza/<klient>.md)."""

import unittest

from wspolne import (CZAS, DNI_DZWONIENIA, DNI_SALONU, ROOT, adres_z_sekcji, godzina_czytelna, godziny_z_sekcji,
                     klienci, minuty, sekcja_salonu, wczytaj_config, wczytaj_wiedze)

STATUSY_KAMPANII = {"aktywna", "zakonczona", "oczekuje-na-plik"}


def godziny(config):
    """(opis, od, do) dla każdych godzin w konfiguracji: salony i godziny dzwonienia."""
    for id_salonu, salon in config["salony"].items():
        for dzien, g in salon["godziny_salonu"].items():
            yield f"salony.{id_salonu}.godziny_salonu.{dzien}", dzien, g
    for dzien, g in config["godziny_dzwonienia"].items():
        yield f"godziny_dzwonienia.{dzien}", dzien, g


class TestSchemat(unittest.TestCase):

    def test_sa_konfiguracje_klientow(self):
        self.assertTrue(klienci(), "brak plików config/*.yaml")

    def test_wymagane_pola_i_typy(self):
        for klient in klienci():
            with self.subTest(klient=klient):
                c = wczytaj_config(klient)
                self.assertEqual(c["klient"], klient, "pole klient musi być równe nazwie pliku")
                self.assertIsInstance(c["nazwa"], str)
                self.assertIsInstance(c["salony"], dict)
                self.assertTrue(c["salony"], "co najmniej jeden salon")
                self.assertIsInstance(c["godziny_dzwonienia"], dict)
                self.assertIsInstance(c["limit_prob"], int)
                self.assertGreaterEqual(c["limit_prob"], 1)
                self.assertIsInstance(c["limity"], dict)
                self.assertIsInstance(c["teksty_wstepu"]["obecny"], str)
                self.assertIsInstance(c["teksty_wstepu"].get("warianty", []), list)
                for id_salonu, salon in c["salony"].items():
                    for pole in ("miasto", "adres", "godziny_salonu"):
                        self.assertIn(pole, salon, f"salon {id_salonu}: brak pola {pole}")
                    self.assertIsInstance(salon["adres"], str)

    def test_kazdy_klient_ma_wiedze_i_zakazy(self):
        for klient in klienci():
            self.assertTrue((ROOT / "wiedza" / f"{klient}.md").exists(), f"brak wiedza/{klient}.md")
            self.assertTrue((ROOT / "zakazy" / f"{klient}.json").exists(), f"brak zakazy/{klient}.json")


class TestGodziny(unittest.TestCase):

    def test_format_godzin_i_kolejnosc(self):
        for klient in klienci():
            for opis, _, g in godziny(wczytaj_config(klient)):
                with self.subTest(klient=klient, pole=opis):
                    self.assertRegex(g["od"], CZAS, "format HH:MM")
                    self.assertRegex(g["do"], CZAS, "format HH:MM")
                    self.assertLess(minuty(g["od"]), minuty(g["do"]), "„od” musi być przed „do”")

    def test_dozwolone_klucze_dni(self):
        for klient in klienci():
            c = wczytaj_config(klient)
            for id_salonu, salon in c["salony"].items():
                self.assertLessEqual(set(salon["godziny_salonu"]), set(DNI_SALONU), f"{klient}/{id_salonu}")
            self.assertLessEqual(set(c["godziny_dzwonienia"]), DNI_DZWONIENIA, f"{klient}: godziny dzwonienia")

    def test_godziny_dzwonienia_nie_dluzej_niz_ustalone(self):
        """Godziny dzwonienia mieszczą się w granicy z umowy i platformy (limity.godziny_dzwonienia_do)."""
        for klient in klienci():
            c = wczytaj_config(klient)
            granica = c["limity"]["godziny_dzwonienia_do"]
            self.assertRegex(granica, CZAS)
            for dzien, g in c["godziny_dzwonienia"].items():
                with self.subTest(klient=klient, dzien=dzien):
                    self.assertLessEqual(minuty(g["do"]), minuty(granica),
                                         f"dzwonienie do {g['do']} przekracza ustalone {granica}")

    def test_limit_prob_nie_przekracza_ustalonego(self):
        for klient in klienci():
            c = wczytaj_config(klient)
            self.assertLessEqual(c["limit_prob"], c["limity"]["max_prob"], klient)


class TestMarkiIKampanie(unittest.TestCase):

    def test_marki_salonow_i_kampanii_istnieja(self):
        for klient in klienci():
            c = wczytaj_config(klient)
            marki = set(c.get("marki", {}))
            for id_salonu, salon in c["salony"].items():
                self.assertLessEqual(set(salon.get("marki", [])), marki, f"{klient}/{id_salonu}: nieznana marka")
            for id_kampanii, k in c.get("kampanie", {}).items():
                self.assertLessEqual(set(k["marki"]), marki, f"{klient}/{id_kampanii}: nieznana marka")
                self.assertIn(k["status"], STATUSY_KAMPANII, f"{klient}/{id_kampanii}: status")

    def test_marka_nieaktywna_nie_ma_kampanii(self):
        for klient in klienci():
            c = wczytaj_config(klient)
            nieaktywne = {m for m, v in c.get("marki", {}).items() if not v["aktywna"]}
            for id_kampanii, k in c.get("kampanie", {}).items():
                with self.subTest(klient=klient, kampania=id_kampanii):
                    self.assertFalse(nieaktywne & set(k["marki"]),
                                     f"kampania {id_kampanii} dotyczy nieaktywnej marki {sorted(nieaktywne & set(k['marki']))}")


class TestSpojnoscZWiedza(unittest.TestCase):
    """Agent głosowy czyta wiedzę, więc adres i godziny KAŻDEGO salonu muszą być w jego sekcji takie same jak w config
    (porównanie w obie strony: nic nie brakuje i nic nie jest nadmiarowe)."""

    def test_adres_i_godziny_kazdego_salonu_zgodne_z_sekcja_w_bazie_wiedzy(self):
        for klient in klienci():
            c, wiedza = wczytaj_config(klient), wczytaj_wiedze(klient)
            for id_salonu, salon in c["salony"].items():
                with self.subTest(klient=klient, salon=id_salonu):
                    sekcja = sekcja_salonu(wiedza, salon["miasto"])
                    self.assertIsNotNone(sekcja, f"w wiedza/{klient}.md brakuje sekcji „### {salon['miasto']}”")
                    self.assertEqual(adres_z_sekcji(sekcja), salon["adres"],
                                     f"adres salonu {salon['miasto']} w wiedzy różni się od config")
                    oczekiwane = {DNI_SALONU[d]: (godzina_czytelna(g["od"]), godzina_czytelna(g["do"]))
                                  for d, g in salon["godziny_salonu"].items()}
                    self.assertEqual(godziny_z_sekcji(sekcja), oczekiwane,
                                     f"godziny salonu {salon['miasto']} w wiedzy różnią się od config")


class TestTekstyWstepu(unittest.TestCase):

    def test_wstep_mowi_ze_to_wirtualna_asystentka_i_ze_rozmowa_jest_nagrywana(self):
        for klient in klienci():
            c = wczytaj_config(klient)
            teksty = [c["teksty_wstepu"]["obecny"]] + list(c["teksty_wstepu"].get("warianty") or [])
            for t in teksty:
                with self.subTest(klient=klient, tekst=t[:40]):
                    self.assertIn("wirtualn", t.lower())
                    self.assertIn("nagryw", t.lower())


if __name__ == "__main__":
    unittest.main()
