"""Test „zakazy”: konfiguracja nie może zmienić tego, czego klient zakazał (lista w zakazy/<klient>.json)."""

import copy
import unittest

from wspolne import klienci, narusza, wczytaj_config, wczytaj_zakazy

REGULY = {"rowne": {"wartosc"}, "w": {"wartosci"}}


class TestZakazy(unittest.TestCase):

    def test_pliki_zakazow_maja_poprawna_strukture(self):
        for klient in klienci():
            zakazy = wczytaj_zakazy(klient)
            self.assertIsInstance(zakazy, list)
            self.assertTrue(zakazy, f"zakazy/{klient}.json jest pusty")
            ids = [z["id"] for z in zakazy]
            self.assertEqual(len(ids), len(set(ids)), f"{klient}: powtórzone id zakazów")
            for z in zakazy:
                with self.subTest(klient=klient, zakaz=z.get("id")):
                    for pole in ("id", "opis", "regula", "sciezka"):
                        self.assertIn(pole, z)
                    self.assertIn(z["regula"], REGULY, "nieznana reguła")
                    self.assertTrue(REGULY[z["regula"]] <= set(z), f"reguła {z['regula']} wymaga pól {REGULY[z['regula']]}")

    def test_konfiguracja_nie_narusza_zakazow(self):
        for klient in klienci():
            config = wczytaj_config(klient)
            for z in wczytaj_zakazy(klient):
                with self.subTest(klient=klient, zakaz=z["id"]):
                    powod = narusza(config, z)
                    self.assertIsNone(powod, f"zakaz {z['id']} ({z['opis']}): {powod}")

    def test_opel_nie_moze_byc_aktywny(self):
        c = wczytaj_config("auto-tama")
        self.assertFalse(c["marki"]["opel"]["aktywna"], "zakaz Z4: Opel nie może być aktywny")
        self.assertTrue(any(z["id"] == "Z4" for z in wczytaj_zakazy("auto-tama")), "reguła Z4 musi być w zakazy/auto-tama.json")

    def test_test_zakazow_naprawde_wykrywa_naruszenia(self):
        """Zabezpieczenie przed pustym testem: celowo zepsuta konfiguracja musi zostać wykryta."""
        c = copy.deepcopy(wczytaj_config("auto-tama"))
        c["marki"]["opel"]["aktywna"] = True
        c["limit_prob"] = 3
        naruszone = {z["id"] for z in wczytaj_zakazy("auto-tama") if narusza(c, z)}
        self.assertEqual(naruszone, {"Z4", "Z1"})
        k = copy.deepcopy(wczytaj_config("klinika-usmiech"))
        k["grupy_pacjentow"]["ortodoncja"]["dzwonic"] = True
        self.assertEqual({z["id"] for z in wczytaj_zakazy("klinika-usmiech") if narusza(k, z)}, {"Z1"})
        del c["zachowanie"]
        self.assertTrue(any(narusza(c, z) and "brak pola" in narusza(c, z) for z in wczytaj_zakazy("auto-tama")),
                        "brakujące pole to naruszenie, a nie ciche przejście")


if __name__ == "__main__":
    unittest.main()
