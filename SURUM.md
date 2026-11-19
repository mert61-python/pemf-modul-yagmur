# Kit sürümü

- Kit sürümü: **0.2.0** (19-11-2026) — ana uygulamanın gerçek Kontrol + Simülasyon sekmeleri (`uygulama/`) ve sahte sunucu
  (`sunucu/`) eklendi; eski panel şablonu (`arayuz/`) kaldırıldı. 0.1.0: modül çekirdeği + şablon sürücü + sahte kart + kabul testleri.
- Kaynak: ana depo dal `ozellik/canli-alan-moduller` @ `e64c3f0b`.
  - `servers/modul_*.py`, `servers/alt_surec.py`, `utils/gizli_surec.py` **BİREBİR** kopyadır; değiştirmeyin (birleştirmede ana
    depodaki sürüm kullanılır). Değişiklik gerekiyorsa koordinatöre bildirin.
  - `uygulama/src/` ana depodaki `apps/ui/src/`'nin Kontrol + Simülasyon sekmelerinin kullandığı dosyalardır (birebir). Kitte
    değişenler yalnız şunlardır:
    - `screens/ControlScreen.tsx`: ana uygulamaya özgü parçalar çıkarıldı (hasta seçimi, AI Pro sekmesi, operatör, oturum, seans
      sonu gözlem notu, geliştirici modülü seçici).
    - `services/discovery.ts`: cihaz keşfi (mDNS, alt ağ taraması, bulut kayıt defteri) yerine boş taslak.
    - `GelistiriciUygulamasi.tsx` + `app/`: ana kabuk (menü, profiller, oturum açma) yerine iki sekmeli yalın çerçeve.
    - `package.json` / `package-lock.json`: ana uygulamanın kilidinden yalnız bu sekmelerin bağımlılıkları (sürümler aynı).
- `utils/path_utils.py` ve `backend_service.py` kit için yalın sürümlerdir (ana depodakiler değildir).
