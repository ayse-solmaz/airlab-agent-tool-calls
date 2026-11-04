# Senaryo: Kuzey Kitabevi (kurgusal)

Kuzey Kitabevi, 5 şubesi olan kurgusal bir kitabevi zinciri. Buradaki bütün isimler, fiyatlar ve sayılar uydurmadır. Bilerek kurgusal seçildi: model bu verileri ezberinden bilemez, cevap bulmak için tool çağırmak **zorundadır**.

Agent bu zincirin bir çalışanına yardım eden asistan rolündedir.

---

## 1. `database`: mağazanın kendi verisi (sadece okuma)

### `subeler`
| sube_id | ad | sehir | acilis_yili | calisan_sayisi |
| --- | --- | --- | --- | --- |
| 1 | Kadıköy | İstanbul | 2016 | 12 |
| 2 | Beşiktaş | İstanbul | 2019 | 8 |
| 3 | Çankaya | Ankara | 2018 | 9 |
| 4 | Alsancak | İzmir | 2020 | 7 |
| 5 | Nilüfer | Bursa | 2022 | 5 |

### `urunler`
| urun_id | ad | kategori | alis_fiyati_tl | satis_fiyati_tl | tedarikci |
| --- | --- | --- | --- | --- | --- |
| 101 | Sessiz Liman | roman | 140 | 240 | Mavi Yayın |
| 102 | Yıldız Atlası | bilim | 210 | 350 | Pusula Dağıtım |
| 103 | Kodla Düşün | bilgisayar | 260 | 420 | Pusula Dağıtım |
| 104 | Küçük Fener | çocuk | 90 | 165 | Mavi Yayın |
| 105 | Akdeniz Mutfağı | yemek | 180 | 310 | Lale Basım |
| 106 | Unutulan Harita | roman | 120 | 225 | Lale Basım |

### `satislar` (adet)
| sube_id | urun_id | ay | adet |
| --- | --- | --- | --- |
| 1 | 101 | 2026-09 | 38 |
| 1 | 101 | 2026-10 | 45 |
| 1 | 103 | 2026-10 | 22 |
| 1 | 106 | 2026-10 | 30 |
| 2 | 102 | 2026-10 | 17 |
| 2 | 103 | 2026-09 | 25 |
| 2 | 103 | 2026-10 | 31 |
| 3 | 101 | 2026-10 | 27 |
| 3 | 104 | 2026-10 | 40 |
| 3 | 105 | 2026-10 | 12 |
| 4 | 104 | 2026-09 | 18 |
| 4 | 104 | 2026-10 | 24 |
| 4 | 106 | 2026-10 | 15 |
| 5 | 102 | 2026-10 | 9 |
| 5 | 105 | 2026-10 | 14 |

### `stok` (şubede kalan adet)
| sube_id | urun_id | adet |
| --- | --- | --- |
| 1 | 101 | 12 |
| 1 | 103 | 4 |
| 2 | 103 | 0 |
| 3 | 104 | 25 |
| 4 | 104 | 6 |
| 5 | 105 | 9 |

---

## 2. `web_search`: mağazanın DIŞINDAKİ bilgi

Sabit bir metin listesi. Arama her zaman aynı sorguya aynı sonucu döndürür.

1. Kuzey Kitabevi muhasebesinin Ekim 2026 için kullandığı sabit kur: 1 ABD doları = 42,00 TL.
2. Kuzey Kitabevi muhasebesinin Ekim 2026 için kullandığı sabit kur: 1 euro = 48,50 TL.
3. Pusula Dağıtım, Kasım 2026'dan itibaren tüm ürünlerinin alış fiyatına %8 zam yapacağını duyurdu.
4. Mavi Yayın, Kasım 2026'da tüm ürünlerinin alış fiyatında %5 indirim uygulayacak.
5. Lale Basım'ın sipariş teslim süresi 12 iş günüdür.
6. Rakip zincir Okyanus Kitap, "Kodla Düşün" kitabını 399 TL'ye satıyor.
7. Rakip zincir Okyanus Kitap, "Sessiz Liman" kitabını 255 TL'ye satıyor.
8. Anlaşmalı kargo firması Hızlı Kargo'nun şubeler arası transfer ücreti paket başına 45 TL'dir.

---

## 3. `calculator`: aritmetik

Sadece sayılar ve `+ - * / ( )`. `ast` ile güvenli şekilde hesaplanır.

---

## Bu veriyle hangi görev tipleri kurulabilir (görevleri sen yazacaksın)
- **Tek tool:** sadece veritabanı ya da sadece arama.
- **Zincir:** veritabanı → arama → hesap (ör. bir tutarı dolara çevirmek, zam sonrası fiyat).
- **Karşılaştırma:** iki şubeyi ya da iki ayı kıyaslamak.
- **Aynı bilgiye iki kez ihtiyaç (tekrar tetikleyici):** görevin başında kullanılan bir değer sonda tekrar lazım olur (ör. aynı kur iki farklı tutar için, aynı ürünün fiyatı iki ayrı hesapta).
- **Cevabı olmayan soru:** veride bulunmayan bir şube ya da ürün. Agent "bilmiyorum" diyebiliyor mu?
