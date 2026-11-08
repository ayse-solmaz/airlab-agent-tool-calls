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

## 8. Hafıza penceresi: 4 turn, adım sınırı: 15
**Karar:** Agent son 4 turn'ü görür ve en fazla 15 adım atar. Sıcaklık 0.6.
**Neden:** Değerler görev 8 ve 9 üzerinde yapılan pilotlarla seçildi (`results/pilot.jsonl`, `results/pilot_w4.jsonl`). Pencere 2 ile 6 koşunun hepsi 10 adım sınırına takıldı: hesap için üç bilgi aynı anda gerekiyor ama model son ikisini görüyor, bu yüzden aynı çağrıları döngü hâlinde yineledi. Bu, görevi imkânsız kılan bir baseline olurdu. Pencere 4 ile 6 koşunun 2'si başarılı oldu, görev 8 ise en az 7-8 çağrı gerektirdiği için 10 adıma sığmadı.
**Sınırlama:** Pencere ve adım sınırı sonuçlara bakılarak seçildi, yani bağımsız bir ayar değildir.

## 9. Başarı kontrolü
**Karar:** Görevin beklediği bütün sayılar son cevapta geçiyorsa görev başarılıdır (`evaluate.py`). Türkçe ve İngilizce sayı biçimleri kabul edilir, yuvarlama payı var. Cevabı olmayan görevde agent bilginin bulunmadığını söylemeli ve uydurma sayı yazmamalıdır.
**Neden:** Otomatik kontrol, bütün koşuları aynı kuralla puanlar.
**Sınırlama:** Kontrol sayıların doğru bağlamda olup olmadığına bakmaz.

## 10. Ana sonuç dosyası: `results/results_v2.jsonl`
**Karar:** Deney son kodla baştan koşuldu. Raporun ana sonucu bu koşudur. Bu seçim yeni sonuçlar görülmeden, koşu başlarken yapıldı.
**Neden:** İlk koşuda (`results/results.jsonl`) düzeltmeler deney ortasında yapılmıştı: görev 7 için arama kelimeleri eklendi, puanlama düzeltildi, bağlantı kopmalarına tekrar deneme eklendi. Ayrıca birkaç koşunun süresi agent dışı bir duraklamayla şişti (en uzunu 4 adımda 56.445 sn). Yeni koşuda bütün satırlar aynı kodla üretilir ve başarısız denemenin süresi agent'ın süresine yazılmaz.
**Sınırlama:** Model aynı seed'le birebir aynı cevabı vermediği için iki koşunun sayıları farklı olabilir. İlk koşu silinmedi, karşılaştırma olarak raporda kalır.

## 11. Yeni koşuda 2 seed
**Karar:** Yeni koşu 3 yerine 2 seed ile (0 ve 1, toplam 60 koşu) durduruldu.
**Neden:** Groq'un günlük 200.000 token limiti koşuyu yavaşlattı ve 90 koşunun ne zaman biteceği belirsizleşti. Görev her konfigürasyon için 2-3 tekrar istiyor, 2 seed bunu karşılıyor. Koşular seed sırasıyla ilerlediği için her modda eşit sayıda koşu var. Karar 49. koşuda, seed 1'in görev 8 ve 9 sonuçları gelmeden verildi.
**Sınırlama:** Seed 0 sonuçları karar verilirken görülmüştü. Ayrıca iki değerden hesaplanan std zayıf bir ölçüdür.

## 12. Ana sonuç dosyası: `results/results_v3.jsonl`
**Karar:** İkinci koşu 52 / 60'ta durduktan sonra kaldığı yerden devam edilmedi, aynı 60 koşu baştan başlatıldı. Raporun ana sonucu bu üçüncü koşudur. Bu seçim üçüncü koşunun sonuçları görülmeden yapıldı. Bölüm 10 ve 11'deki `results_v2.jsonl` kararının yerine geçer, 2 seed kararı aynen geçerlidir.
**Neden:** İkinci koşu önce bilgisayarın bekleme moduyla uzun süre durdu, sonra Wi-Fi yaklaşık 3 dakikadan uzun kopunca tamamen durdu. Yeni koşudan önce iki düzeltme yapıldı: bağlantı kopunca yaklaşık 1 saat denemeye devam eder, bekleme sırasında geçen gerçek süre ölçümden çıkarılır.
**Sınırlama:** İkinci koşunun 52 satırı karar verilirken görülmüştü. Bu yüzden `results_v2.jsonl` silinmedi, raporda karşılaştırma olarak kalır.
