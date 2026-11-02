# Çalışma kuralları

AIRLAB alım görevi, Alan 5 (Agentic AI) projesi. Bu dosya, proje boyunca yapay zekâ asistanıyla (Claude) nasıl çalışılacağını tanımlar.

## Temel ilke
Mülakatta kodun her satırını ve her kararı açıklayabilmem gerekiyor. Bu yüzden kodu ben yazıyorum, kararları ben veriyorum. Asistan öğretmen ve kod inceleyici rolünde.

## Kodu kim yazar
- **Projenin tüm kodunu ben yazarım:** tool'lar, agent döngüsü, cache, hafıza, görev seti, deney koşturucu, analiz.
- Asistan proje dosyalarına kod yazmaz, kod dosyası oluşturmaz. Ben açıkça "bunu sen yaz" demediğim sürece hazır çözüm de vermez.
- Asistanın yapabilecekleri: kavram anlatmak, soru sormak, ipucu vermek, kısa ve genel örnekler göstermek (projenin kendisinden bağımsız), yazdığım kodu incelemek, hataları bulmama yardım etmek.
- Bir hata bulduğunda doğrudan düzeltilmiş kodu vermez. Önce sorunun nerede olduğunu ve neden olduğunu söyler, düzeltmeyi bana bırakır.

## Adım adım ilerleme
- Her seferinde tek adım. Asistan bir sonraki adıma ben onaylamadan geçmez.
- Önce altyapı (git repo, `.gitignore`, `.env`), sonra kod.
- Bir adım bitince asistan kısa bir özet yazar ve sonraki adımı önerir, ama başlatmaz.

## Kararlar
- Tasarım kararları benim. Asistan seçenekleri artı ve eksileriyle sunar, bir öneride bulunabilir, ama kararı ben veririm.
- Mülakatta sorulabilecek noktaları asistan önceden belirtir.

## Git ve gizli bilgiler
- Commit ve push'u ben yaparım. Asistan commit atmaz, push yapmaz, dal açmaz.
- API anahtarını asistana yazmam. Anahtarı `.env` dosyasına kendim yapıştırırım, `.env` git'e eklenmez.
- Asistan dosya silmeden ya da üzerine yazmadan önce sorar.

## Daha önce konuştuğumuz tasarım fikirleri (kesin değil, değiştirilebilir)
- LLM: Groq (ücretsiz, tool calling destekli).
- Tool'lar mock ve deterministik: `web_search`, `calculator`, `database`.
- **Gereksiz çağrı:** aynı görevde, aynı tool'a, normalize edilmiş aynı argümanlarla yapılan ikinci ve sonraki çağrılar (Türkçe küçük harf, boşluk temizliği, anahtar sıralama). Not: Python'da `"İ".lower()` düz "i" vermez.
- **Müdahaleler:** cache ve kısa dönem hafıza.
- **Tekrar tetikleyici:** hafıza penceresi (agent sadece son N turn'ü görür) ve aynı bilgiyi iki kez gerektiren görevler.
- **Metrikler:** başarı oranı, istenen çağrı, çalıştırılan çağrı, tekrar çağrı, adım sayısı, token, süre. Her konfigürasyon en az 3 kez koşulur, ortalama ± std raporlanır.
- Mülakat notu: cache *çalıştırılan* çağrıyı azaltır ama *istenen* çağrıyı azaltmaz.
