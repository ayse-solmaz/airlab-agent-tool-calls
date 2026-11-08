"""evaluate.py ve run_experiments.py testleri. API anahtarı gerektirmez.

Çalıştırma:  uv run python -m unittest -v test_experiments
"""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS

import groq
import httpx

from evaluate import check_answer, numbers_in
from run_experiments import QuotaExhausted, RetryingClient, run_all
from test_agent import FakeClient


class FakeTime:
    """Gerçek bekleme yapmadan saati ilerletir. extra: uyku gibi fazladan geçen süre."""

    def __init__(self, extra=0):
        self.now = 0.0
        self.extra = extra

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds + self.extra


def rate_limit(seconds):
    response = httpx.Response(429, headers={"retry-after": str(seconds)},
                              request=httpx.Request("POST", "http://test"))
    return groq.RateLimitError("limit", response=response, body=None)


class TestCheckAnswer(unittest.TestCase):

    def test_number_formats(self):
        for text in ["4.500 TL", "4,500 TL", "4 500 TL", "**4500** TL", "4500.00"]:
            self.assertIn(4500.0, numbers_in(text), text)
        self.assertIn(136.08, numbers_in("136,08 euro"))
        self.assertIn(280.8, numbers_in("280.80 TL."))

    def test_all_values_required(self):
        self.assertTrue(check_answer([220, 310, 90], "220 dolar, 310 dolar, fark 90 dolar"))
        self.assertFalse(check_answer([220, 310, 90], "220 dolar ve 310 dolar"))

    def test_rounding(self):
        self.assertTrue(check_answer([136.08], "yaklaşık 136,1 euro"))
        self.assertFalse(check_answer([136.08], "136 euro"))

    def test_wrong_or_missing(self):
        self.assertFalse(check_answer([97], "Toplam 96 kitap."))
        self.assertFalse(check_answer([97], None))
        self.assertFalse(check_answer([97], ""))

    def test_zero(self):
        self.assertTrue(check_answer([0], "0 adet stok kaldı."))
        self.assertTrue(check_answer([0], "Stok tükenmiş."))
        self.assertFalse(check_answer([0], "4 adet kaldı."))

    def test_no_answer_task(self):
        self.assertTrue(check_answer(None, "Karşıyaka adında bir şube bulunmuyor."))
        self.assertTrue(check_answer(None, "Ekim 2026 için Karşıyaka şubesi kayıtlı değil."))
        self.assertTrue(check_answer(None, "Karşıyaka adlı bir şube bulunmadığı için belirleyemiyorum."))
        self.assertFalse(check_answer(None, "Karşıyaka şubesi 40 kitap sattı."))
        self.assertFalse(check_answer(None, "Sattığı kitap 40, başka veri yok."))


class TestRetryingClient(unittest.TestCase):

    def _client(self, errors):
        calls = iter(errors)

        def create(**kwargs):
            item = next(calls)
            if isinstance(item, Exception):
                raise item
            return item
        return NS(chat=NS(completions=NS(create=create)))

    def test_waits_and_tracks_sleep(self):
        fake = FakeTime()
        client = RetryingClient(self._client([rate_limit(3), "ok"]), sleep=fake.sleep, clock=fake.clock)
        self.assertEqual(client.chat.completions.create(), "ok")
        self.assertEqual(client.slept_s, 3.0)

    def test_computer_sleep_during_wait_is_not_agent_time(self):
        fake = FakeTime(extra=5000)
        client = RetryingClient(self._client([rate_limit(3), "ok"]), sleep=fake.sleep, clock=fake.clock)
        self.assertEqual(client.chat.completions.create(), "ok")
        self.assertEqual(client.slept_s, 5003.0)

    def test_connection_error_is_retried(self):
        error = groq.APIConnectionError(request=httpx.Request("POST", "http://test"))
        fake = FakeTime()
        client = RetryingClient(self._client([error, "ok"]), sleep=fake.sleep, clock=fake.clock)
        self.assertEqual(client.chat.completions.create(), "ok")
        self.assertEqual(client.slept_s, 30)

    def test_long_connection_loss_does_not_stop_run(self):
        error = groq.APIConnectionError(request=httpx.Request("POST", "http://test"))
        fake = FakeTime()
        client = RetryingClient(self._client([error] * 20 + ["ok"]), sleep=fake.sleep, clock=fake.clock)
        self.assertEqual(client.chat.completions.create(), "ok")

    def test_failed_attempt_time_is_not_agent_time(self):
        error = groq.APIConnectionError(request=httpx.Request("POST", "http://test"))
        ticks = iter([0, 1000, 1000, 1030, 1030])  # ilk deneme 1000 sn asılı kaldı, ikincisi başarılı
        client = RetryingClient(self._client([error, "ok"]), sleep=lambda s: None, clock=lambda: next(ticks))
        self.assertEqual(client.chat.completions.create(), "ok")
        self.assertEqual(client.slept_s, 1030)

    def test_long_wait_stops(self):
        client = RetryingClient(self._client([rate_limit(5000)]), sleep=lambda s: None)
        with self.assertRaises(QuotaExhausted):
            client.chat.completions.create()


class TestRunAll(unittest.TestCase):

    def test_writes_and_resumes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "r.jsonl"
            args = (["baseline", "cache"], [1, 2], [0], "m", 2, 0.6)
            n = run_all(RetryingClient(FakeClient(["7"] * 4)), path, *args)
            self.assertEqual(n, 4)
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), 4)
            self.assertEqual(sum(r["success"] for r in rows if r["task_id"] == 1), 2)
            self.assertFalse(any(r["success"] for r in rows if r["task_id"] == 2))
            self.assertEqual(run_all(RetryingClient(FakeClient([])), path, *args), 0)


if __name__ == "__main__":
    unittest.main()
