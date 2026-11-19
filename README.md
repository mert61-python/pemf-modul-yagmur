# PEMF kontrol modülü kiti

> **Bu depo Yağmur'un kontrol modülü içindir.** Bağlantıyla paylaşıldı; herkes okuyabilir. Doğrudan kod göndermek için GitHub
> kullanıcı adınızı koordinatöre iletin, depoya **bakım (maintain)** yetkisiyle eklenirsiniz. O zamana kadar depoyu *fork* edip
> çekme isteği (PR) açabilirsiniz. İlk iş: aşağıdaki **Kurulum** ve **Çalıştırma** adımlarıyla Kontrol sekmesini sahte kartla
> açın, sonra **Kendi modülünüz** adım 1 ile modül kimliğinizi oluşturun.

Bu kit, PEMF uygulamasının **Kontrol** sekmesini kendi kartınız ve kendi bobininizle çalıştırmanız için hazırlandı. İçinde ana
uygulamanın **gerçek Kontrol ve Simülasyon sekmeleri** var. Ana PEMF sunucusunun yerine de bir **sahte sunucu** konuldu. Kart, kart
yazılımı ve bağlantı (seri, Wi-Fi, BLE, USB) tamamen sizindir. Ana uygulama yalnızca **kuralları** koyar. Kurallar bu kitteki testlerle
ve denetleyiciyle ölçülür; kuralları geçmeyen çalışma ana uygulamaya alınmaz.

## Ne yapacaksınız?

| parça | konum | açıklama |
|---|---|---|
| Kontrol sekmesi (arayüz) | `uygulama/src/screens/ControlScreen.tsx` ve kullandığı bileşenler | Ana uygulamanın **gerçek** Kontrol sekmesi. Tasarımı kendi kartınıza göre değiştirebilirsiniz (KABUL C). |
| Arka uç = kart sürücünüz | `moduller/<kimlik>/surucu.py` | `class Surucu(BobinSurucusu)`: `baglan` · `kes` · `uygula` · `baslat` · `durdur` · `acil_durdur` · `kalp` · `durum` |
| Kart yazılımı | kendi deponuz / klasörünüz | mikroişlemciniz (STM, ESP …): açılışta bobin **kapalı**, kalp atışı bekçisi, kendi sınırları |
| `modul.json` + `KART.md` | `moduller/<kimlik>/` | kimlik, görünen ad (TR + EN), sürüm, bağlantı türü, parametre sınırları, `bekci_ms`, kart bilgisi |

**Entegrasyonda:** Kontrol sekmeniz ana uygulamaya **ayrı bir profil** olarak eklenir; arka uç olarak sürücünüz ana sunucunun modül
yöneticisi altında çalışır. Arayüzünüzün konuştuğu uçlar, sahte sunucudaki uçlarla aynıdır (aşağıda). Yeni bir uca ihtiyaç duyarsanız
koordinatöre bildirin; uç entegrasyonda ana sunucuya eklenir.

## Nasıl çalışır?

```
tarayıcı  ──►  uygulama/  (gerçek Kontrol + Simülasyon sekmeleri)
                  │  HTTP /api/... + canlı veri /ws  (ana sunucuyla AYNI biçim)
                  ▼
           sunucu/sahte_sunucu.py  (ana PEMF sunucusunun yerine)
                  │  bobin komutları  →  uygula + baslat / durdur / acil_durdur
                  ▼
           moduller/<kimlik>/surucu.py   (AYRI süreçte, 500 ms kalp atışı)  →  sizin kartınız
```

- Sahte sunucu 7 bobinli PEMF cihazını yazılımda canlandırır: seans, kalan süre, sürüş kipi ve ACİL DURDUR mandalı. **Ölçüm
  üretmez:** bobin kartlarındaki ölçüm alanları boş kalır.
- `--modul <kimlik>` ile çalıştırıldığında ilk bobin başlayınca sürücünüze `uygula` + `baslat`, son bobin durunca `durdur`,
  ACİL DURDUR'da `acil_durdur` gider. Sürücü çağrıları ayrı bir iş parçacığında yapılır; takılan bir sürücü ne arayüzü ne de ACİL
  DURDUR'u bekletir. ACİL DURDUR mandalı kuruluyken kartınıza **başlat** gitmez.
- Canlı alan haritası (Kontrol sekmesindeki "Alan haritası" kartı) **sentetik** dipollerden üretilir; ana uygulamanın kalibre alan
  modeli kitte yoktur. Kalibrasyon kimliği "sentetik-kit" olarak görünür.

## Kurulum

Gerekenler: Python 3.10 ve Node.js 22.

```bat
python -m pip install pytest==8.3.4 pytest-cov==6.0.0 ruff==0.15.20 fastapi==0.136.3 uvicorn==0.48.0 httpx==0.28.1
cd uygulama
npm ci --legacy-peer-deps
npm run export:web
cd ..
```

## Çalıştırma (kartsız)

```bat
python sunucu/sahte_sunucu.py --modul sablon --sahte-kart
```

Tarayıcıda `http://127.0.0.1:8765` adresini açın. Kontrol sekmesinde bobin seçip **Başlat**'a basın; sahte kart bobini açar.
**TÜM BOBİNLERİ ACİL DURDUR** kartı hemen keser ve mandalı kurar. Mandal kuruluyken üstteki bant görünür; **Sıfırla** onay ister
ve bobin başlatmaz. Simülasyon sekmesini adresle açmak için: `http://127.0.0.1:8765/?sekme=simulasyon` (dijital ikiz klasörü
`--ikiz <klasör>` ile verilir).

**Arayüzü değiştirirken (anında yenileme):** sahte sunucu açıkken ikinci bir pencerede:

```bat
cd uygulama
set EXPO_PUBLIC_PEMF_API_BASE_URL=http://127.0.0.1:8765/api
set EXPO_PUBLIC_PEMF_WS_URL=ws://127.0.0.1:8765/ws
npm run web
```

## Kendi modülünüz

1. `moduller/sablon` klasörünü kendi kimliğinizle kopyalayın (ör. `moduller/ayse-esp`; küçük harf, rakam ve `-`).
   `modul.json`'daki `kimlik` alanı klasör adıyla aynı olmalıdır. CI dosyasındaki `PEMF_KIT_MODUL` değerini de değiştirin.
2. `modul.json` ve `KART.md` dosyalarını doldurun: bağlantı türü, sınırlar ve `bekci_ms` (en az 1500).
3. `surucu.py` içinde `# >>> KENDİ KARTINIZ` ile işaretli yerleri değiştirin. Kartınızı **yalnız kendi tanımınızla** bulun
   (USB VID / PID / seri no); ana PEMF kartının portunu açmayın.
4. Kartlı ölçüm için testlerdeki sahte kart fikstürünü kendi kartınızın durum okumasıyla değiştirin.
5. Kartınızı arayüzden sürmek için: `python sunucu/sahte_sunucu.py --modul <kimlik>` (sahte kart olmadan).
6. Kontrol sekmesinin tasarımını kartınıza göre değiştirin (örneğin bobin sayısı). Her yeni metni hem `uygulama/src/i18n/tr/` hem
   `en/` dosyasına ekleyin.
7. `python -m pytest testler -q` ve `cd uygulama && npm run typecheck` komutlarını çalıştırın; CI (`.github/workflows/ci.yml`) aynı
   ölçümleri yapar.

## Kurallar

Kuralların tamamı `KABUL.md` dosyasında. En önemlileri:

- **ACİL DURDUR** hiçbir koşula bağlanmaz: `acil_durdur` 50 ms içinde döner, kart bobini 100 ms içinde keser. Bu çağrı, takılı kalmış
  başka bir komutu beklemeden gider; şablonda ayrı bağlantı ve ayrı kilit kullanılır. Kontrol sekmesindeki ACİL DURDUR düğmesi
  kaldırılmaz, gizlenmez, kaydırma gerektiren bir yere taşınmaz.
- **Kart bekçisi:** sunucu 500 ms'de bir kalp atışı gönderir. Kartınız `bekci_ms` içinde kalp atışı duymazsa bobini **kendisi**
  keser. Kablo çekilse, sürücü takılsa ya da bilgisayar donsa bile bobin böyle durur.
- Ana PEMF kartına, ana MQTT konularına ve cihaz keşfine dokunulmaz. Bilgisayarda port dinlenmez (sahte sunucu yalnız geliştirme içindir).
- Sürücü ağa yalnız beyan ettiği bağlantı için çıkar. Diske yalnız `self.dosya_yolu(...)` ile kendi klasörüne yazar. Alt süreç başlatmaz.
- Her metin iki dildedir (TR + EN).

## Klasörler

| klasör | içerik |
|---|---|
| `uygulama/` | ana uygulamanın gerçek Kontrol + Simülasyon sekmeleri (Expo / React Native, web'de de çalışır); `src/GelistiriciUygulamasi.tsx` kitin iki sekmeli çerçevesi |
| `sunucu/sahte_sunucu.py` | ana PEMF sunucusunun yerine geçen sahte sunucu |
| `servers/`, `utils/gizli_surec.py` | ana uygulamanın modül çekirdeği: arayüz, alt süreç kabuğu, yönetici, kayıt defteri, denetleyici. **Değiştirmeyin** (`SURUM.md`) |
| `moduller/sablon/` | şablon modül: `modul.json`, `KART.md`, `surucu.py`, `sahte_kart.py` |
| `testler/` | kabul testleri (`test_kabul.py`), sahte sunucu testleri, denetleyici testi |
| `araclar/i18n_esle.py` | arayüz metinleri TR / EN eşliği denetimi |

Sorularınızı koordinatöre iletin.
