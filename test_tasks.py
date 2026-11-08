"""tasks.py'deki doğru cevapları tools.py verisinden yeniden hesaplar.

Çalıştırma:  uv run python -m unittest -v test_tasks
"""
import unittest

from tasks import TASKS
from tools import TABLES, web_search

BY_ID = {t["id"]: t for t in TASKS}


def sube(ad):
    return next(r for r in TABLES["subeler"] if r["ad"] == ad)


def urun(ad):
    return next(r for r in TABLES["urunler"] if r["ad"] == ad)


def satis(sube_ad, urun_ad, ay):
    return next(r["adet"] for r in TABLES["satislar"]
                if r["sube_id"] == sube(sube_ad)["sube_id"]
                and r["urun_id"] == urun(urun_ad)["urun_id"] and r["ay"] == ay)


class TestExpectedAnswers(unittest.TestCase):

    def test_shape(self):
        self.assertEqual([t["id"] for t in TASKS], list(range(1, 11)))
        self.assertGreaterEqual(sum(t["tekrar"] for t in TASKS), 2)

    def test_1_to_3(self):
        self.assertEqual(BY_ID[1]["beklenen"], [sube("Alsancak")["calisan_sayisi"]])
        self.assertIn("12 iş", web_search("Lale Basım teslim süresi"))
        nilufer = sube("Nilüfer")["sube_id"]
        ekim = [r for r in TABLES["satislar"] if r["sube_id"] == nilufer and r["ay"] == "2026-10"]
        en_cok = max(ekim, key=lambda r: r["adet"])
        kitap = next(r for r in TABLES["urunler"] if r["urun_id"] == en_cok["urun_id"])
        self.assertEqual(kitap["tedarikci"], "Lale Basım")
        self.assertEqual(BY_ID[3]["beklenen"], [12])

    def test_4_to_7(self):
        self.assertIn("48,50", web_search("euro kuru"))
        ciro = satis("Çankaya", "Küçük Fener", "2026-10") * urun("Küçük Fener")["satis_fiyati_tl"]
        self.assertAlmostEqual(BY_ID[4]["beklenen"][0], ciro / 48.5, places=2)
        self.assertEqual(urun("Kodla Düşün")["tedarikci"], "Pusula Dağıtım")
        self.assertIn("%8", web_search("Pusula zam"))
        self.assertAlmostEqual(BY_ID[5]["beklenen"][0], urun("Kodla Düşün")["alis_fiyati_tl"] * 1.08)
        stok = next(r["adet"] for r in TABLES["stok"] if r["sube_id"] == sube("Beşiktaş")["sube_id"]
                    and r["urun_id"] == urun("Kodla Düşün")["urun_id"])
        self.assertEqual(BY_ID[6]["beklenen"], [stok])
        self.assertIn("45 TL", web_search("kargo transfer ücreti"))
        self.assertEqual(BY_ID[7]["beklenen"], [4 * 45])

    def test_8_and_9(self):
        fiyat = urun("Kodla Düşün")["satis_fiyati_tl"]
        kadikoy = satis("Kadıköy", "Kodla Düşün", "2026-10") * fiyat / 42
        besiktas = satis("Beşiktaş", "Kodla Düşün", "2026-10") * fiyat / 42
        self.assertEqual(BY_ID[8]["beklenen"], [kadikoy, besiktas, besiktas - kadikoy])
        kar = urun("Sessiz Liman")["satis_fiyati_tl"] - urun("Sessiz Liman")["alis_fiyati_tl"]
        self.assertEqual(BY_ID[9]["beklenen"], [kar, satis("Kadıköy", "Sessiz Liman", "2026-10") * kar,
                                                satis("Çankaya", "Sessiz Liman", "2026-10") * kar])

    def test_10_has_no_answer(self):
        self.assertIsNone(BY_ID[10]["beklenen"])
        self.assertNotIn("Karşıyaka", [r["ad"] for r in TABLES["subeler"]])


if __name__ == "__main__":
    unittest.main()
