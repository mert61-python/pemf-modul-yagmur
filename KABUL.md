# Kabul listesi — kontrol modülü

Bir modül, aşağıdaki maddelerin tamamı ölçülüp geçtiğinde birleştirilir. Ölçümler kitteki testlerle ve ana depodaki aynı testlerle yapılır.
Her madde PLAN §2'deki A (güvenlik) ve B (ana uygulamanın akışına dokunmama) kurallarına karşılık gelir.

## A — Güvenlik (pazarlıksız)

| # | kural | nasıl ölçülür |
|---|---|---|
| A1 | ACİL DURDUR, ana yoldan (`emergency_stop`) bağlı **tüm** modüllere paralel gider ve hiçbir koşula bağlı değildir. `acil_durdur` 50 ms içinde döner, kart bobini 100 ms içinde keser. | `test_KABUL_A1…` (kart zaman damgası); ana depoda HTTP ACİL DURDUR uçtan uca |
| A2 | Kart bekçisi: sunucu 500 ms'de bir kalp atışı gönderir; kart `bekci_ms` (en az 1500) içinde kalp atışı duymazsa bobini **kendisi** keser. Kalp atışı akarken bobin yanlışlıkla kesilmez. | `test_KABUL_A2…` |
| A3 | Kart açılışta bobini KAPALI başlatır. Sınırlar hem `modul.json`'da (sunucu reddeder, karta gitmez) hem kartta uygulanır. | `test_KABUL_A3…` + kart formu |
| A4 | Ana sunucu kapanır ya da ölürse sürücü önce `acil_durdur` çağırır, bobin durur. | `test_KABUL_A4…` |

## B — Ana uygulamanın akışına dokunmama

| # | kural | nasıl ölçülür |
|---|---|---|
| B4 | Ana PEMF kartına (STM) dokunulmaz: kart yalnız kendi tanımıyla (USB VID / PID / seri no) bulunur, port taranmaz. | denetleyici (beyansız `serial` yok) + kod incelemesi |
| B5 | Ana ağa dokunulmaz: MQTT kullanılıyorsa yalnız `pemf/modul/<kimlik>/…` konuları kullanılır, kalıcı ileti bırakılmaz, keşfe (mDNS) yanıt verilmez, bilgisayarda port dinlenmez. | denetleyici (`mqttKonuAlaniDisi`, `mqttKaliciIleti`, `zeroconf`) |
| B6 | Uygulama yavaşlatılmaz ya da düşürülmez: modül yalnız seçildiğinde yüklenir, her çağrı takılmadan döner, sürücü çökse de sunucu ayakta kalır. | `test_KABUL_B6…` + ana depoda takılan sürücü testi |
| B7 | Modül kendi sınırları içinde kalır: ağ yalnız beyan edilen bağlantı için kullanılır, diske yalnız `self.dosya_yolu(...)` ile yazılır, alt süreç başlatılmaz, dinamik kod çalıştırılmaz. Panel yalnız modül araç takımını kullanır. | denetleyici + panel içe aktarma incelemesi |
| B8 | Yeni Python / npm bağımlılığı ancak onayla ve sabit sürümle eklenir. | teslim notu |

## Teslim

- `modul.json` ve `KART.md` dolu, tutarlı (kabul testi formdakiyle kartın gerçek davranışını karşılaştırır).
- CI yeşil: ruff, denetleyici, kabul testleri, sürücü kapsamı %100, panel metinleri TR + EN eşleşik.
- Lisans: kart yazılımı + sürücü + panel ticari kullanıma izin verir.
