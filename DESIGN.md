# Tasarım kararları

Her kararın yanında **neden** öyle seçildiği yazıyor. Bu dosya ileride README'nin "Tasarım kararları" bölümüne dönüşecek.

## Problem
Tool kullanan bir agent aynı tool'u aynı argümanlarla gereksiz yere tekrar çağırıyor. Bu da adım sayısını, süreyi ve maliyeti artırıyor. Amaç bu tekrarları ölçmek ve görev başarısını düşürmeden azaltmak.

## 1. Senaryo: kurgusal kitabevi
**Karar:** Kurgusal "Kuzey Kitabevi" zinciri (detaylar [SENARYO.md](SENARYO.md)'de). Kurlar da kurgusal.
**Neden:** Gerçek veri (ör. şehir nüfusu, gerçek döviz kuru) kullanılsaydı model cevabı ezberinden verebilirdi. Kurgusal veride cevabı bilemez, tool çağırmak zorunda kalır. Böylece ölçtüğümüz şey gerçekten tool kullanımı olur.

## 2. Tool'lar deterministik
**Karar:** Üç tool (`web_search`, `database`, `calculator`) da aynı girdiye her zaman aynı çıktıyı verir.
**Neden:** Tool deterministikse, aynı argümanlarla yapılan ikinci çağrının yeni bilgi getirmediğinden emin olabiliriz. Bu yüzden o çağrıyı kesin olarak "gereksiz" sayabiliriz. Tool değişken olsaydı tekrar çağrı yeni bir sonuç getirebilirdi ve gereksiz olduğunu iddia edemezdik. Yan faydası: koşular arasındaki farkın tek kaynağı modelin rastgeleliği olur.

## 3. Database: sadece okuma
**Karar:** Agent veritabanını okuyabilir, değiştiremez.
**Neden:**
- Görevlerin hepsi bilgi sorgusu, yazmaya ihtiyaç yok.
- Yazma determinizmi bozar: bir güncellemeden sonra aynı sorgu farklı sonuç döndürür.
- Yazma "gereksiz çağrı" tanımını karmaşıklaştırır: aynı kaydı iki kez eklemek gereksiz değil, hatalıdır.
- Güvenlik: model tabloyu silemez ya da bozamaz.

**Kapsam dışı:** Yazma işlemleri (sipariş verme, stok güncelleme) gelecek çalışma olarak bırakıldı.

## 4. Database arayüzü: yapılandırılmış, sadece "eşittir" filtresi
**Karar:** Model SQL yazmaz. Tablo adını ve isteğe bağlı bir eşitlik filtresini gönderir:
`{"tablo": "satislar", "filtre": {"sube_id": 1, "ay": "2026-10"}}`
Filtre verilmezse tablonun tamamı döner. Sıralama ve limit yok.

**Neden:**
- **Ölçümün güvenilirliği (asıl sebep):** Serbest SQL'de aynı bilgi farklı yazılmış sorgularla istenebilir (koşulların sırası, boşluklar, `SUM` ile satır satır okuma). Bu çağrılar tekrar olarak yakalanamaz ve metrik eksik sayar. Yapılandırılmış argümanlar küçük ve düzenli olduğu için normalizasyon iyi çalışır.
- Model SQL söz dizimi hatası yapamaz, hatalı sorguların yeniden denenmesi deneye gürültü katmaz.
- Güvenlik: model hiç SQL yazmadığı için tehlikeli sorgu riski yok.
- **Sıralama/limit yok:** Bunlar argüman çeşitliliğini artırır (`limit: 1` ile `limit: 3`), bu da tekrar tespitini zorlaştırır. Veri küçük olduğu için (en büyük tablo 15 satır) model satırları kendisi karşılaştırabilir.
- **Filtresiz çağrı serbest:** `satislar` tablosunda şube adı yok, sadece `sube_id` var. Model "Kadıköy"ün id'sini bulmak için `subeler` tablosuna bakabilmeli. Tablolar küçük olduğu için tamamını döndürmek token açısından sorun değil.

**Bedeli:** Toplama ve birleştirme için daha fazla çağrı gerekir (ör. toplam satış için `calculator`). Model satırları kendi karşılaştırırken hata yapabilir.

**Hata durumları:** Olmayan bir tablo ya da sütun istenirse program çökmez, modele var olan tabloları ve sütunları söyleyen bir hata metni döner.

## 5. Calculator: `ast` ile güvenli hesaplama
**Karar:** İfade `eval()` ile değil, `ast` ile ağaca çevrilip hesaplanır. Sadece sayılara ve `+ - * / ( )` işlemlerine izin verilir.
**Neden:** `eval()` metni Python kodu olarak çalıştırır. Calculator'a giden metni model ürettiği için, yanlış ya da kötü niyetli bir ifade bilgisayarda kod çalıştırabilir. `ast` ile sadece izin verilen işlemler hesaplanır, gerisi reddedilir. Hazır kütüphane yerine kısa bir `ast` değerlendirici tercih edildi, çünkü her satırı açıklanabilir ve ek paket gerektirmez. `**` bilerek yok: `2 ** 99999999` gibi bir ifade programı kilitleyebilir.

## 6. Normalizasyon
**Karar:** Bir değeri karşılaştırılabilir hâle getiren **tek** bir kural var:
1. metne çevir (`1` → `"1"`)
2. baştaki ve sondaki boşlukları sil
3. aradaki fazla boşlukları teke indir
4. Türkçe'ye uygun küçük harfe çevir (`"İ"` → `"i"`, `"I"` → `"ı"`)

Sözlüklerde anahtarlar sıralanır. Kural iç içe sözlüklere de uygulanır (`filtre` argümanının içi de normalize edilir). Boş değerler (`None`, `{}`) atılır: `{"tablo": "subeler"}` ile `{"tablo": "subeler", "filtre": {}}` aynı sonucu verdiği için aynı çağrı sayılır.

**Nerede kullanılıyor:**
- **Tekrar tespiti ve cache:** aynı tool + aynı normalize argümanlar = aynı çağrı.
- **Database filtresi:** satırdaki değer ile filtredeki değer normalize edilip karşılaştırılır.

**Neden tek kural:** Tekrar tespiti ile filtreleme farklı eşitlik tanımları kullanırsa, "aynı" sayılan iki çağrı farklı sonuç döndürebilir (biri satır bulur, diğeri boş döner). O zaman "tekrar çağrı yeni bilgi getirmez" iddiası çöker.

**Neden Türkçe'ye özel küçük harf:** Python'da `"İ".lower()` düz `"i"` vermez, `"i̇"` (i + birleşik nokta) verir. Düzeltilmezse `"İstanbul"` ile `"istanbul"` farklı sayılır.

**Tool'a özel istisna:** `calculator` ifadelerinde **tüm** boşluklar silinir (`"2 * 3"` = `"2*3"`). Matematik ifadesinde boşluk anlam taşımaz. Arama ve database'de silinmez, çünkü orada boşluk kelimeleri ayırır (`"sessiz liman"` ≠ `"sessizliman"`).

**Bilerek yapılmayanlar:**
| Durum | Aynı sayılır mı? | Neden |
| --- | --- | --- |
| `1` ile `1.0` | Hayır | Modelin tamsayı id için ondalık göndermesi nadir. Kural sayısı az kalır. Gerçekleşirse raporda not edilecek. |
| `"Kadıköy"` ile `"Kadikoy"` | Hayır | Türkçe harfleri düzleştirmek farklı kelimeleri yanlışlıkla birleştirebilir (ör. "kar" ile "kâr"). |
| `"Pusula zam"` ile `"Pusula Dağıtım zammı"` | Hayır | Anlamsal eşleşme kapsam dışı (eşik seçimi tartışmalı ve karmaşık). |

**Normalizasyon neyi değiştirmez:** Veriyi değiştirmez, sadece karşılaştırmada kullanılır. Modele dönen sonuç orijinal hâliyle gider. Anahtar adları (`sube_id`) normalize edilmez.

**Sınırlama:** Anlamca aynı ama farklı yazılmış çağrılar yakalanmadığı için ölçülen tekrar sayısı bir **alt sınırdır**.

## 7. Model: `openai/gpt-oss-120b` (Groq)
**Karar:** Deneyler Groq üzerinde `openai/gpt-oss-120b` ile koşulur.
**Neden:** Hesapta açık olan tool calling adayları (`gpt-oss-120b`, `gpt-oss-20b`, `qwen3.8-27b`) aynı görevle denendi, üçü de doğru cevabı verdi. `gpt-oss-120b` hesabı `calculator` ile yaptı ve filtreyi dar tuttu; `gpt-oss-20b` `calculator`'ı atladı, `qwen3.8-27b` tüm tabloyu çekti.
**Sınırlama:** Bu seçim her model için tek koşuya dayanıyor, kesin bir karşılaştırma değil. `llama-3.3-70b-versatile` hesapta bulunmadığı için denenemedi.

## 8. Henüz kararlaştırılmadı
- Hafıza penceresi boyutu ve sıcaklık ayarı (kodda şimdilik varsayılan: 2 turn, 0.6)
- 10 görev ve başarı kontrolü
