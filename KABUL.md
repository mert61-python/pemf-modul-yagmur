# Kabul listesi — kontrol modülü

Bir modül, aşağıdaki maddelerin tamamı ölçülüp geçtiğinde ana uygulamaya (ayrı profil olarak) alınır. Ölçümler kitteki testlerle ve
ana depodaki aynı testlerle yapılır. A ve B maddeleri PLAN §2'deki güvenlik ve "ana uygulamanın akışına dokunmama" kurallarıdır;
C maddeleri Kontrol sekmesi arayüzü içindir.

## A — Güvenlik (pazarlıksız)

| # | kural | nasıl ölçülür |
|---|---|---|
| A1 | ACİL DURDUR, ana yoldan (`emergency_stop`) bağlı **tüm** modüllere paralel gider ve hiçbir koşula bağlı değildir. `acil_durdur` 50 ms içinde döner, kart bobini 100 ms içinde keser. | `test_KABUL_A1…` (kart zaman damgası); sahte sunucuda `test_gercek_surucu…`; ana depoda HTTP ACİL DURDUR uçtan uca |
| A2 | Kart bekçisi: sunucu 500 ms'de bir kalp atışı gönderir; kart `bekci_ms` (en az 1500) içinde kalp atışı duymazsa bobini **kendisi** keser. Kalp atışı akarken bobin yanlışlıkla kesilmez. | `test_KABUL_A2…` |
| A3 | Kart açılışta bobini KAPALI başlatır. Sınırlar hem `modul.json`'da (sunucu reddeder, karta gitmez) hem kartta uygulanır. | `test_KABUL_A3…` + kart formu |
| A4 | Ana sunucu kapanır ya da ölürse sürücü önce `acil_durdur` çağırır, bobin durur. | `test_KABUL_A4…` |
| A5 | ACİL DURDUR mandalı kuruluyken karta **başlat** gitmez; mandal yalnız onaylı "Sıfırla" ile kalkar ve bobin başlatmaz. | sahte sunucu testleri (`test_acil_durdur_mandal…`, `test_mandal_kuruluyken…`) |

## B — Ana uygulamanın akışına dokunmama

| # | kural | nasıl ölçülür |
|---|---|---|
| B4 | Ana PEMF kartına (STM) dokunulmaz: kart yalnız kendi tanımıyla (USB VID / PID / seri no) bulunur, port taranmaz. | denetleyici (beyansız `serial` yok) + kod incelemesi |
| B5 | Ana ağa dokunulmaz: MQTT kullanılıyorsa yalnız `pemf/modul/<kimlik>/…` konuları kullanılır, kalıcı ileti bırakılmaz, keşfe (mDNS) yanıt verilmez, bilgisayarda port dinlenmez. | denetleyici (`mqttKonuAlaniDisi`, `mqttKaliciIleti`, `zeroconf`) |
| B6 | Uygulama yavaşlatılmaz ya da düşürülmez: her çağrı takılmadan döner, sürücü çökse de sunucu ayakta kalır. | `test_KABUL_B6…` + ana depoda takılan sürücü testi |
| B7 | Modül kendi sınırları içinde kalır: ağ yalnız beyan edilen bağlantı için kullanılır, diske yalnız `self.dosya_yolu(...)` ile yazılır, alt süreç başlatılmaz, dinamik kod çalıştırılmaz. | denetleyici |
| B8 | Yeni Python / npm bağımlılığı ancak onayla ve sabit sürümle eklenir. | teslim notu + `package.json` / CI farkı |

## C — Kontrol sekmesi (arayüz)

| # | kural | nasıl ölçülür |
|---|---|---|
| C1 | ACİL DURDUR düğmesi Kontrol sekmesinde her zaman görünür, sekme içeriğinden ÖNCE durur (kaydırmadan erişilir), hiçbir koşula bağlanmaz, gizlenmez. | ekran incelemesi + ana depoda ACİL DURDUR kapıları |
| C2 | Her metin iki dildedir: yeni anahtar `uygulama/src/i18n/tr/` ve `en/` dosyalarının ikisine de eklenir; ekranda düz metin yazılmaz. | `python araclar/i18n_esle.py` |
| C3 | Tip denetimi 0 hata, web derlemesi başarılı. | CI `uygulama` işi (`npm run typecheck`, `npm run export:web`) |
| C4 | Arayüz ana sunucuyla yalnız sahte sunucudaki uçlar ve canlı iletiler üzerinden konuşur. Yeni uç gerekiyorsa koordinatöre bildirilir. | `sunucu/sahte_sunucu.py` ile uçtan uca deneme |
| C5 | Sahte sunucudaki ölçümsüz alanlar ölçüm gibi gösterilmez (ör. `0.00 mT` yerine "—"); alan haritası "Model tahmini, ölçüm değil" etiketiyle gösterilir. | ekran incelemesi |

## Teslim

- `modul.json` ve `KART.md` dolu, tutarlı (kabul testi formdakiyle kartın gerçek davranışını karşılaştırır).
- CI yeşil: `surucu` işi (ruff, denetleyici, kabul + sahte sunucu testleri, sürücü kapsamı %100, TR + EN eşliği) ve `uygulama` işi
  (tip denetimi, web derlemesi).
- Lisans: kart yazılımı, sürücü ve arayüz değişiklikleri ticari kullanıma izin verir.
