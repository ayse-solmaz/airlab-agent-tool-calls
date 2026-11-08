"""tools.py testleri. Çalıştırma:  uv run python -m unittest -v test_tools"""
import json
import unittest

from tools import TABLES, call_key, calculator, database, normalize, web_search


class TestNormalize(unittest.TestCase):

    def test_same_values(self):
        self.assertEqual(normalize(1), normalize("1"))
        self.assertEqual(normalize("Kadıköy"), normalize(" kadıköy "))
        self.assertEqual(normalize("İSTANBUL"), "istanbul")
        self.assertEqual(normalize("Sessiz  Liman"), "sessiz liman")

    def test_deliberately_different(self):
        self.assertNotEqual(normalize(1), normalize(1.0))
        self.assertNotEqual(normalize("Kadıköy"), normalize("Kadikoy"))

    def test_call_key_nested_filter_and_order(self):
        a = call_key("database", {"tablo": "satislar", "filtre": {"sube_id": 1, "ay": "2026-10"}})
        b = call_key("database", {"filtre": {"ay": "2026-10", "sube_id": "1"}, "tablo": "SATISLAR".lower()})
        self.assertEqual(a, b)

    def test_call_key_empty_filter(self):
        a = call_key("database", {"tablo": "subeler"})
        self.assertEqual(a, call_key("database", {"tablo": "subeler", "filtre": {}}))
        self.assertEqual(a, call_key("database", {"tablo": "subeler", "filtre": None}))

    def test_call_key_calculator_spaces(self):
        self.assertEqual(call_key("calculator", {"expression": "2 * 3"}),
                         call_key("calculator", {"expression": "2*3"}))

    def test_call_key_search_keeps_spaces(self):
        self.assertNotEqual(call_key("web_search", {"query": "sessiz liman"}),
                            call_key("web_search", {"query": "sessizliman"}))

    def test_different_tools_differ(self):
        self.assertNotEqual(call_key("web_search", {"query": "x"}), call_key("calculator", {"query": "x"}))


class TestDatabase(unittest.TestCase):

    def test_no_filter_returns_all(self):
        self.assertEqual(len(json.loads(database("satislar"))), 15)
        self.assertEqual(json.loads(database("subeler", {})), TABLES["subeler"])

    def test_filter(self):
        rows = json.loads(database("satislar", {"sube_id": 1, "ay": "2026-10"}))
        self.assertEqual(sum(r["adet"] for r in rows), 97)

    def test_equal_keys_give_equal_results(self):
        self.assertEqual(database("subeler", {"sube_id": 1}), database("subeler", {"sube_id": "1"}))
        self.assertEqual(database("subeler", {"ad": "kadıköy "}), database("subeler", {"ad": "Kadıköy"}))
        self.assertEqual(database("subeler", {"sehir": "İZMİR"}), database("subeler", {"sehir": "İzmir"}))

    def test_zero_stock_is_a_row(self):
        self.assertEqual(json.loads(database("stok", {"sube_id": 2, "urun_id": 103}))[0]["adet"], 0)

    def test_no_match_is_empty(self):
        self.assertEqual(database("subeler", {"ad": "Karşıyaka"}), "[]")

    def test_errors(self):
        self.assertIn("Hata", database("musteriler"))
        self.assertIn("subeler", database("musteriler"))
        self.assertIn("Hata", database("subeler", {"isim": "x"}))
        self.assertIn("Hata", database("subeler", "sube_id=1"))


class TestWebSearch(unittest.TestCase):

    def test_finds_expected_record(self):
        cases = {"dolar kuru": "42,00", "USD kaç TL": "42,00", "euro kuru": "48,50",
                 "Pusula Dağıtım zammı": "%8", "Mavi Yayın indirimi": "%5",
                 "Lale Basım teslim süresi": "12 iş", "Okyanus Kodla Düşün fiyatı": "399",
                 "Okyanus Kitap Sessiz Liman": "255", "kargo ücreti": "45 TL",
                 "Kadıköy Beşiktaş paket gönderim fiyatı": "45 TL"}
        for query, expected in cases.items():
            self.assertIn(expected, web_search(query).split("\n")[0], query)

    def test_no_result(self):
        self.assertEqual(web_search("hava durumu"), "Sonuç bulunamadı.")

    def test_deterministic(self):
        self.assertEqual(web_search("rakip fiyat"), web_search("rakip fiyat"))


class TestCalculator(unittest.TestCase):

    def test_valid(self):
        self.assertEqual(calculator("2 + 3 * 4"), "14")
        self.assertEqual(calculator("(1 + 2) * 3"), "9")
        self.assertEqual(calculator("-5 + 1"), "-4")
        self.assertEqual(calculator("10 / 4"), "2.5")
        self.assertEqual(calculator("10 / 3"), "3.3333")

    def test_rejected(self):
        for bad in ["__import__('os')", "abs(-3)", "x + 1", "'merhaba'", "True + 1",
                    "2 ** 3", "2 +", "", "42,00 * 3", "1 / 0"]:
            self.assertTrue(calculator(bad).startswith("Hata"), bad)


if __name__ == "__main__":
    unittest.main()
