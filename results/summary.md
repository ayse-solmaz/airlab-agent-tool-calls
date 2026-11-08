# Sonuç tabloları

`analyze.py` ile üretildi. Değerler 2 seed üzerinden ortalama ± örneklem std'sidir.

## Başarı (bütün koşular)

API hatası başarısız sayılır.

| Mod | Başarı oranı (%) | Başarılı koşu | Adım sınırına takılan | API hatası |
|---|---|---|---|---|
| baseline | 80,0 ± 14,1 | 16 / 20 | 3 | 0 |
| cache | 80,0 ± 0,0 | 16 / 20 | 2 | 0 |
| memory | 95,0 ± 7,1 | 19 / 20 | 0 | 0 |

## Görev başına ortalamalar (eşleştirilmiş koşular)

API hatası olmadı, hiçbir koşu çıkarılmadı: her modda 20 koşu var. Süre, seed içi medyandır.

| Mod | İstenen çağrı | Çalışan çağrı | Tekrar çağrı | Adım | Token | Süre medyanı (sn) |
|---|---|---|---|---|---|---|
| baseline | 5,15 ± 0,49 | 5,15 ± 0,49 | 1,45 ± 0,49 | 6,00 ± 0,42 | 5486 ± 331 | 3,68 ± 1,62 |
| cache | 4,35 ± 0,35 | 3,20 ± 0,00 | 1,15 ± 0,35 | 5,25 ± 0,35 | 4810 ± 416 | 3,08 ± 0,44 |
| memory | 3,50 ± 0,28 | 3,50 ± 0,28 | 0,10 ± 0,14 | 4,50 ± 0,28 | 4763 ± 551 | 3,73 ± 0,82 |

## Baseline'a göre değişim (%)

| Mod | İstenen çağrı | Çalışan çağrı | Tekrar çağrı | Adım | Token | Süre medyanı (sn) |
|---|---|---|---|---|---|---|
| cache | -15,5 | -37,9 | -20,7 | -12,5 | -12,3 | -16,3 |
| memory | -32,0 | -32,0 | -93,1 | -25,0 | -13,2 | +1,4 |

## Sadece tekrar tetikleyen görevler (eşleştirilmiş)

| Mod | İstenen çağrı | Çalışan çağrı | Tekrar çağrı | Adım | Token | Süre medyanı (sn) |
|---|---|---|---|---|---|---|
| baseline | 13,00 ± 2,83 | 13,00 ± 2,83 | 5,50 ± 2,83 | 13,25 ± 2,47 | 13564 ± 1694 | 12,88 ± 2,79 |
| cache | 12,25 ± 1,77 | 6,50 ± 0,00 | 5,75 ± 1,77 | 12,75 ± 1,77 | 12394 ± 1734 | 16,75 ± 6,05 |
| memory | 8,00 ± 2,12 | 8,00 ± 2,12 | 0,50 ± 0,71 | 9,00 ± 2,12 | 11278 ± 2767 | 12,15 ± 2,13 |

## Diğer görevler (eşleştirilmiş)

| Mod | İstenen çağrı | Çalışan çağrı | Tekrar çağrı | Adım | Token | Süre medyanı (sn) |
|---|---|---|---|---|---|---|
| baseline | 3,19 ± 0,09 | 3,19 ± 0,09 | 0,44 ± 0,09 | 4,19 ± 0,09 | 3467 ± 10 | 2,95 ± 1,14 |
| cache | 2,38 ± 0,00 | 2,38 ± 0,00 | 0,00 ± 0,00 | 3,38 ± 0,00 | 2914 ± 87 | 2,64 ± 0,56 |
| memory | 2,38 ± 0,18 | 2,38 ± 0,18 | 0,00 ± 0,00 | 3,38 ± 0,18 | 3134 ± 3 | 3,32 ± 0,63 |

## Görev bazında sonuçlar (bütün koşular)

Tekrar sütunları bütün seed'lerin toplamıdır. Yıldız: API hatası veren koşu toplamda yok.

| Görev | Tekrar tetikler | baseline başarı | cache başarı | memory başarı | baseline tekrar | cache tekrar | memory tekrar |
|---|---|---|---|---|---|---|---|
| 1 | hayır | 2 / 2 | 2 / 2 | 2 / 2 | 0 | 0 | 0 |
| 2 | hayır | 2 / 2 | 2 / 2 | 2 / 2 | 0 | 0 | 0 |
| 3 | hayır | 2 / 2 | 2 / 2 | 2 / 2 | 0 | 0 | 0 |
| 4 | hayır | 2 / 2 | 2 / 2 | 2 / 2 | 7 | 0 | 0 |
| 5 | hayır | 2 / 2 | 2 / 2 | 2 / 2 | 0 | 0 | 0 |
| 6 | hayır | 2 / 2 | 2 / 2 | 2 / 2 | 0 | 0 | 0 |
| 7 | hayır | 1 / 2 | 0 / 2 | 1 / 2 | 0 | 0 | 0 |
| 8 | evet | 0 / 2 | 0 / 2 | 2 / 2 | 12 | 15 | 1 |
| 9 | evet | 1 / 2 | 2 / 2 | 2 / 2 | 10 | 8 | 1 |
| 10 | hayır | 2 / 2 | 2 / 2 | 2 / 2 | 0 | 0 | 0 |
