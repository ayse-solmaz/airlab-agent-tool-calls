"""Mock tool'lar: database, web_search, calculator.

Hepsi deterministik: aynı girdi her zaman aynı çıktıyı verir.
Veriler kurgusaldır, ayrıntılar SENARYO.md'de. Kararların nedenleri DESIGN.md'de.
"""
import ast
import json
import operator
import re


# ---------------------------------------------------------------- normalizasyon

def tr_lower(text: str) -> str:
    # Python'da "İ".lower() düz "i" vermez, "i" + birleşik nokta verir.
    return text.replace("İ", "i").replace("I", "ı").lower()


def normalize(value):
    """Bir değeri karşılaştırılabilir hâle getirir. Tekrar tespiti ve filtre aynı kuralı kullanır."""
    if isinstance(value, dict):
        # None ve {} atılır: {"tablo": "x"} ile {"tablo": "x", "filtre": {}} aynı çağrıdır.
        return {k: normalize(v) for k, v in value.items() if v is not None and v != {}}
    if isinstance(value, list):
        return [normalize(v) for v in value]
    return " ".join(tr_lower(str(value)).split())


def call_key(name: str, args: dict) -> str:
    """Tekrar tespiti ve cache için anahtar. Anahtarı aynı olan iki çağrı aynı çağrıdır."""
    norm = normalize(args)
    if name == "calculator" and "expression" in norm:
        # Matematik ifadesinde boşluk anlam taşımaz: "2 * 3" ile "2*3" aynıdır.
        norm["expression"] = norm["expression"].replace(" ", "")
    return name + ":" + json.dumps(norm, sort_keys=True, ensure_ascii=False)


# ---------------------------------------------------------------- database

def _rows(columns, *rows):
    return [dict(zip(columns, row)) for row in rows]


TABLES = {
    "subeler": _rows(
        ("sube_id", "ad", "sehir", "acilis_yili", "calisan_sayisi"),
        (1, "Kadıköy", "İstanbul", 2016, 12),
        (2, "Beşiktaş", "İstanbul", 2019, 8),
        (3, "Çankaya", "Ankara", 2018, 9),
        (4, "Alsancak", "İzmir", 2020, 7),
        (5, "Nilüfer", "Bursa", 2022, 5),
    ),
    "urunler": _rows(
        ("urun_id", "ad", "kategori", "alis_fiyati_tl", "satis_fiyati_tl", "tedarikci"),
        (101, "Sessiz Liman", "roman", 140, 240, "Mavi Yayın"),
        (102, "Yıldız Atlası", "bilim", 210, 350, "Pusula Dağıtım"),
        (103, "Kodla Düşün", "bilgisayar", 260, 420, "Pusula Dağıtım"),
        (104, "Küçük Fener", "çocuk", 90, 165, "Mavi Yayın"),
        (105, "Akdeniz Mutfağı", "yemek", 180, 310, "Lale Basım"),
        (106, "Unutulan Harita", "roman", 120, 225, "Lale Basım"),
    ),
    "satislar": _rows(
        ("sube_id", "urun_id", "ay", "adet"),
        (1, 101, "2026-09", 38),
        (1, 101, "2026-10", 45),
        (1, 103, "2026-10", 22),
        (1, 106, "2026-10", 30),
        (2, 102, "2026-10", 17),
        (2, 103, "2026-09", 25),
        (2, 103, "2026-10", 31),
        (3, 101, "2026-10", 27),
        (3, 104, "2026-10", 40),
        (3, 105, "2026-10", 12),
        (4, 104, "2026-09", 18),
        (4, 104, "2026-10", 24),
        (4, 106, "2026-10", 15),
        (5, 102, "2026-10", 9),
        (5, 105, "2026-10", 14),
    ),
    "stok": _rows(
        ("sube_id", "urun_id", "adet"),
        (1, 101, 12),
        (1, 103, 4),
        (2, 103, 0),
        (3, 104, 25),
        (4, 104, 6),
        (5, 105, 9),
    ),
}


def database(tablo: str, filtre: dict | None = None) -> str:
    """Tablodan eşitlik filtresine uyan satırları JSON olarak döndürür. Sadece okuma."""
    if tablo not in TABLES:
        return f"Hata: '{tablo}' tablosu yok. Tablolar: {', '.join(TABLES)}"
    if filtre is not None and not isinstance(filtre, dict):
        return 'Hata: filtre bir nesne olmalı, ör. {"sube_id": 1}'
    rows = TABLES[tablo]
    wanted = normalize(filtre or {})
    unknown = [col for col in wanted if col not in rows[0]]
    if unknown:
        return f"Hata: '{unknown[0]}' sütunu yok. Sütunlar: {', '.join(rows[0])}"
    result = [r for r in rows if all(normalize(r[col]) == val for col, val in wanted.items())]
    return json.dumps(result, ensure_ascii=False)


# ---------------------------------------------------------------- web_search

KNOWLEDGE_BASE = [
    ("Kuzey Kitabevi muhasebesinin Ekim 2026 için kullandığı sabit kur: 1 ABD doları = 42,00 TL.",
     {"dolar", "usd", "kur"}),
    ("Kuzey Kitabevi muhasebesinin Ekim 2026 için kullandığı sabit kur: 1 euro = 48,50 TL.",
     {"euro", "eur", "avro", "kur"}),
    ("Pusula Dağıtım, Kasım 2026'dan itibaren tüm ürünlerinin alış fiyatına %8 zam yapacağını duyurdu.",
     {"pusula", "zam"}),
    ("Mavi Yayın, Kasım 2026'da tüm ürünlerinin alış fiyatında %5 indirim uygulayacak.",
     {"mavi", "indirim"}),
    ("Lale Basım'ın sipariş teslim süresi 12 iş günüdür.",
     {"lale", "teslim", "süre"}),
    ('Rakip zincir Okyanus Kitap, "Kodla Düşün" kitabını 399 TL\'ye satıyor.',
     {"okyanus", "rakip", "kodla", "düşün"}),
    ('Rakip zincir Okyanus Kitap, "Sessiz Liman" kitabını 255 TL\'ye satıyor.',
     {"okyanus", "rakip", "sessiz", "liman"}),
    ("Anlaşmalı kargo firması Hızlı Kargo'nun şubeler arası transfer ücreti paket başına 45 TL'dir.",
     {"kargo", "transfer", "hızlı", "paket", "gönderim"}),
]


def web_search(query: str) -> str:
    """Sorgu kelimelerini kayıtların anahtar kelimeleriyle eşleştirip en iyi 2 sonucu döndürür."""
    words = re.findall(r"\w+", normalize(query))
    scored = []
    for i, (text, keywords) in enumerate(KNOWLEDGE_BASE):
        # Türkçe ekler için kelimenin başına bakılır: "doları", "zammı", "pusula'nın".
        score = sum(any(w.startswith(k) for w in words) for k in keywords)
        if score:
            scored.append((-score, i))  # eşitlikte kayıt sırası korunur (determinizm)
    if not scored:
        return "Sonuç bulunamadı."
    return "\n".join(KNOWLEDGE_BASE[i][0] for _, i in sorted(scored)[:2])


# ---------------------------------------------------------------- calculator

_BIN_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}
_UNARY_OPS = {ast.USub: operator.neg, ast.UAdd: operator.pos}


def _eval(node):
    # Sadece izin verilen düğümler hesaplanır; Call, Name gibi her şey en alttaki hataya düşer.
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):  # bool ve metin elenir
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        return _BIN_OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval(node.operand))
    raise ValueError("sadece sayılar ve + - * / ( ) kullanılabilir, ondalık ayırıcı nokta olmalı")


def calculator(expression: str) -> str:
    """Aritmetik ifadeyi eval() kullanmadan hesaplar, sonucu 4 basamağa yuvarlar."""
    try:
        result = _eval(ast.parse(expression.strip(), mode="eval").body)
    except ZeroDivisionError:
        return "Hata: sıfıra bölme."
    except (SyntaxError, ValueError, RecursionError) as e:
        return f"Hata: geçersiz ifade ({e})"
    return str(round(result, 4))


# ---------------------------------------------------------------- kayıt ve şemalar

TOOLS = {"database": database, "web_search": web_search, "calculator": calculator}

# Groq (OpenAI uyumlu) tool calling formatı
TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "database",
        "description": "Kuzey Kitabevi veritabanını okur. Tablolar: "
                       "subeler(sube_id, ad, sehir, acilis_yili, calisan_sayisi), "
                       "urunler(urun_id, ad, kategori, alis_fiyati_tl, satis_fiyati_tl, tedarikci), "
                       "satislar(sube_id, urun_id, ay, adet), stok(sube_id, urun_id, adet). "
                       "ay biçimi: '2026-10'.",
        "parameters": {"type": "object", "properties": {
            "tablo": {"type": "string", "enum": list(TABLES)},
            "filtre": {"type": "object",
                       "description": "Sütun adı -> istenen değer (sadece eşitlik). "
                                      "Verilmezse tüm tablo döner. Ör. {\"sube_id\": 1, \"ay\": \"2026-10\"}"}},
            "required": ["tablo"]}}},
    {"type": "function", "function": {
        "name": "web_search",
        "description": "Mağaza dışındaki bilgileri arar: döviz kuru, tedarikçi zam ve indirimleri, "
                       "teslim süreleri, rakip fiyatları, kargo ücreti.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "Arama sorgusu, ör. 'dolar kuru'"}},
            "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "calculator",
        "description": "Aritmetik ifade hesaplar. Sadece sayılar ve + - * / ( ) kullanılabilir. "
                       "Ondalık ayırıcı nokta olmalı.",
        "parameters": {"type": "object", "properties": {
            "expression": {"type": "string", "description": "ör. '(420 - 260) * 22'"}},
            "required": ["expression"]}}},
]
