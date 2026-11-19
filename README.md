# PEMF kontrol modülü kiti

> **Bu depo Yağmur'un kontrol modülü içindir.** Bağlantıyla paylaşıldı; herkes okuyabilir. Doğrudan kod göndermek için GitHub
> kullanıcı adınızı koordinatöre iletin, depoya **bakım (maintain)** yetkisiyle eklenirsiniz. O zamana kadar depoyu *fork* edip
> çekme isteği (PR) açabilirsiniz. İlk iş: aşağıdaki **Hızlı başlangıç** adım 1 ile kendi modül kimliğinizi oluşturun.

Bu kit, PEMF uygulamasının **Kontrol** sekmesine kendi kartınızla ve kendi bobininizle bir **modül** eklemeniz için hazırlandı.
Kart, kart yazılımı ve bağlantı (seri, Wi-Fi, BLE, USB) tamamen sizindir. Ana uygulama yalnızca **kuralları** koyar; kurallar bu kitteki
testlerle ve denetleyiciyle ölçülür. Kuralları geçmeyen modül ana uygulamaya birleştirilmez.

## Modül neden oluşur?

| parça | konum | açıklama |
|---|---|---|
| Kart yazılımı | kendi deponuz / klasörünüz | mikroişlemciniz (STM, ESP …); açılışta bobin **kapalı**, kalp atışı bekçisi, kendi sınırları |
| `modul.json` | `moduller/<kimlik>/` | kimlik, görünen ad (adınız, TR + EN), sürüm, bağlantı türü, parametre sınırları, `bekci_ms`, kart bilgisi |
| `KART.md` | `moduller/<kimlik>/` | kart bilgi formu |
| Sürücü | `moduller/<kimlik>/surucu.py` | `class Surucu(BobinSurucusu)`: `baglan` · `kes` · `uygula` · `baslat` · `durdur` · `acil_durdur` · `kalp` · `durum` |
| Panel | `arayuz/Panel.tsx` (+ `arayuz/i18n/tr.json`, `en.json`) | Kontrol sekmesinde modül seçilince açılan ekran; yalnız `useModul()` araç takımını kullanır |

Sürücünüz ana sunucudan **ayrı bir süreçte** çalışır (`backend_service.py --alt-surec modul-surucu <klasör>`). Böylece sürücü takılsa ya da
çökse bile uygulama donmaz. ACİL DURDUR sizin panelinizde değil, Kontrol sekmesindeki büyük düğmededir. Bu düğme her zaman görünür ve
modülünüze de gider.

## Hızlı başlangıç (kartsız)

```bat
python -m pip install pytest==8.3.4 pytest-cov==6.0.0 ruff==0.15.20
python -m pytest testler -q
```

`moduller/sablon/` klasöründe **sahte kartla** (`sahte_kart.py`, bilgisayarda ayrı bir süreç olarak çalışır ve ağ portu dinlemez) uçtan uca
çalışan bir şablon bulunur. Testler bu hâliyle yeşil geçer. Modülünüzü yazmak için:

1. `moduller/sablon` klasörünü kendi kimliğinizle kopyalayın (ör. `moduller/ayse-esp`; küçük harf, rakam ve `-`).
   `modul.json`'daki `kimlik` alanı klasör adıyla aynı olmalıdır.
   Sahte kart testleri için `surucu.py`'deki `PEMF_SABLON_BORU` adını `PEMF_<KİMLİK>_BORU` yapın (`-` yerine `_`, büyük harf).
2. `modul.json` ve `KART.md` dosyalarını doldurun: bağlantı türü, sınırlar ve `bekci_ms` (en az 1500).
3. `surucu.py` içinde `# >>> KENDİ KARTINIZ` ile işaretli yerleri değiştirin. Kartınızı **yalnız kendi tanımınızla** bulun
   (USB VID / PID / seri no); ana PEMF kartının portunu açmayın.
4. Kartlı ölçüm için testlerdeki sahte kart fikstürünü kendi kartınızın durum okumasıyla değiştirin.
5. `arayuz/Panel.tsx` dosyasını ve metinlerini (TR + EN) yazın.
6. `PEMF_KIT_MODUL=<kimlik>` ile testleri çalıştırın; CI (`.github/workflows/ci.yml`) aynı ölçümleri yapar.

## Kurallar

Kuralların tamamı `KABUL.md` dosyasında. En önemlileri:

- **ACİL DURDUR** hiçbir koşula bağlanmaz: `acil_durdur` 50 ms içinde döner, kart bobini 100 ms içinde keser. Bu çağrı, takılı kalmış
  başka bir komutu beklemeden gider; şablonda ayrı bağlantı ve ayrı kilit kullanılır.
- **Kart bekçisi**: sunucu 500 ms'de bir kalp atışı gönderir. Kartınız `bekci_ms` içinde kalp atışı duymazsa bobini **kendisi**
  keser. Kablo çekilse, sürücü takılsa ya da bilgisayar donsa bile bobin böyle durur.
- Ana PEMF kartına, ana MQTT konularına ve cihaz keşfine dokunulmaz. Bilgisayarda port dinlenmez.
- Sürücü ağa yalnız beyan ettiği bağlantı için çıkar. Diske yalnız `self.dosya_yolu(...)` ile kendi klasörüne yazar. Alt süreç başlatmaz.
- Her metin iki dildedir (TR + EN).

## Klasörler

| klasör | içerik |
|---|---|
| `servers/`, `utils/gizli_surec.py` | ana uygulamanın modül çekirdeği: arayüz, alt süreç kabuğu, yönetici, kayıt defteri, denetleyici. **Değiştirmeyin** (`SURUM.md`) |
| `moduller/sablon/` | şablon modül: `modul.json`, `KART.md`, `surucu.py`, `sahte_kart.py` |
| `testler/` | kabul testleri (`test_kabul.py`) + denetleyici testi |
| `arayuz/` | panel şablonu + metinler |
| `araclar/i18n_esle.py` | TR / EN anahtar eşliği denetimi |

Sorularınızı koordinatöre iletin. Depo açma ve davet işlemleri koordinatör üzerinden yapılır.
