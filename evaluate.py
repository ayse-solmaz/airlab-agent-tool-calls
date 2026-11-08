"""Agent'ın son cevabını doğru cevapla otomatik karşılaştırır."""
import re

from tools import normalize

# Model "4.500", "4,500", "4 500", "136,08" ya da "136.08" yazabilir.
_NUMBER = re.compile(r"\d{1,3}(?:[   ]\d{3})+(?:[.,]\d+)?|\d[\d.,]*\d|\d")

NOT_FOUND = ("yok", "bulunmuyor", "bulunmamaktadır", "bulunmadı", "bulunamadı", "mevcut değil", "kayıtlı değil")
ZERO_WORDS = ("sıfır", "kalmadı", "kalmamış", "tükendi", "tükenmiş")


def _readings(token: str) -> set[float]:
    """Bir sayı metninin olası değerleri: Türkçe (4.500,5) ve İngilizce (4,500.5) okunuşu."""
    token = re.sub(r"[   ]", "", token)
    values = set()
    for candidate in (token.replace(".", "").replace(",", "."), token.replace(",", "")):
        try:
            values.add(float(candidate))
        except ValueError:
            pass
    return values


def numbers_in(text: str) -> set[float]:
    return {v for token in _NUMBER.findall(text) for v in _readings(token)}


def _close(value: float, expected: float) -> bool:
    # Yuvarlama payı: 136,08 için 136,1 kabul edilir, 136 edilmez.
    return abs(value - expected) <= max(0.01, 0.0005 * abs(expected))


def check_answer(expected: list[float] | None, answer: str | None) -> bool:
    """expected içindeki bütün sayılar cevapta geçiyorsa doğrudur.

    expected None ise doğru cevap "bu bilgi yok" demektir: cevap bunu söylemeli ve
    2026 dışında sayı içermemeli (uydurma bir satış adedi yazmamalı).
    """
    if not answer:
        return False
    found = numbers_in(answer)
    text = normalize(answer)
    if expected is None:
        return any(p in text for p in NOT_FOUND) and not (found - {2026.0})
    for value in expected:
        if any(_close(v, value) for v in found):
            continue
        if value == 0 and any(w in text for w in ZERO_WORDS):
            continue
        return False
    return True
