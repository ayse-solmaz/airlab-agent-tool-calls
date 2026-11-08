"""10 görevlik test seti. Veriler SENARYO.md'de.

beklenen: son cevapta bulunması gereken sayılar. None ise doğru cevap "bu bilgi yok" demektir.
tekrar:   True ise görev aynı bilgiye iki kez ihtiyaç duyar (tekrar tetikleyici).
"""

TASKS = [
    {"id": 1, "tip": "tek bilgi (database)", "tekrar": False,
     "soru": "Alsancak şubesinde kaç kişi çalışıyor?",
     "beklenen": [7]},
    {"id": 2, "tip": "tek bilgi (web_search)", "tekrar": False,
     "soru": "Lale Basım'ın sipariş teslim süresi kaç iş günü?",
     "beklenen": [12]},
    {"id": 3, "tip": "iki kaynağı bağlama (hesapsız)", "tekrar": False,
     "soru": "Nilüfer şubesinde Ekim 2026'da en çok satan kitabın tedarikçisi siparişi kaç iş gününde teslim ediyor?",
     "beklenen": [12]},
    {"id": 4, "tip": "kur çevirme", "tekrar": False,
     "soru": "Çankaya şubesi Ekim 2026'da Küçük Fener kitabından kaç euroluk satış yaptı?",
     "beklenen": [136.08]},
    {"id": 5, "tip": "zam hesabı", "tekrar": False,
     "soru": "Kasım 2026'daki tedarikçi zammından sonra Kodla Düşün'ün alış fiyatı kaç TL olacak?",
     "beklenen": [280.8]},
    {"id": 6, "tip": "stok (sıfır değeri)", "tekrar": False,
     "soru": "Beşiktaş şubesinde Kodla Düşün'den kaç adet stok kaldı?",
     "beklenen": [0]},
    {"id": 7, "tip": "arama + hesap", "tekrar": False,
     "soru": "Kadıköy'den Beşiktaş'a 4 paket transfer etmek kaç TL tutar?",
     "beklenen": [180]},
    {"id": 8, "tip": "aynı bilgi iki kez", "tekrar": True,
     "soru": "Kadıköy şubesinin Ekim 2026'daki Kodla Düşün satışını dolar olarak hesapla. "
             "Sonra aynısını Beşiktaş şubesi için yap. En son ikisi arasındaki farkı dolar olarak yaz.",
     "beklenen": [220, 310, 90]},
    {"id": 9, "tip": "aynı bilgi iki kez", "tekrar": True,
     "soru": "Sessiz Liman kitabının adet başına kârı kaç TL? Sonra bu kitabın Ekim 2026'da "
             "Kadıköy şubesinden ve Çankaya şubesinden getirdiği toplam kârı ayrı ayrı hesapla.",
     "beklenen": [100, 4500, 2700]},
    {"id": 10, "tip": "cevabı olmayan soru", "tekrar": False,
     "soru": "Karşıyaka şubesi Ekim 2026'da kaç kitap sattı?",
     "beklenen": None},
]
