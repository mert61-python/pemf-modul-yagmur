// Author: mertaygn, cglrgrkn
/**
 * PEMF GELİŞTİRİCİ KABUĞU — ana uygulamanın GERÇEK Kontrol ve Simülasyon sekmeleri, tek başına.
 *
 * Ekranlar (`screens/ControlScreen.tsx`, `screens/DemaSimulatorScreen.tsx`) ve kullandıkları bileşenler ana uygulamadan kopyalandı.
 * Arka uç olarak ana PEMF sunucusu YERİNE kitteki sahte sunucuya (`sunucu/sahte_sunucu.py`) bağlanır; adres ana uygulamadaki
 * kuralla bulunur (web'de sayfayı sunan adres, ya da `EXPO_PUBLIC_PEMF_API_BASE_URL` / `EXPO_PUBLIC_PEMF_WS_URL`).
 * Bu dosya yalnız kittedir: ana uygulamadaki kabuk (menü, profiller, oturum açma) yerine iki sekmeli yalın bir çerçeve.
 */
import { useState } from "react";
import { ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import i18n from "i18next";
import { useTranslation } from "react-i18next";
import { dilSec } from "@/i18n";
import { LiveDataProvider, useLiveData } from "@/context/LiveDataContext";
import { ControlScreen } from "@/screens/ControlScreen";
import { DemaSimulatorScreen } from "@/screens/DemaSimulatorScreen";
import { EstopMandalBandi } from "@/components/ui/EstopMandalBandi";
import { colors, layoutMax, rf, rs, spacing, touch } from "@/theme/tokens";

const METIN = {
  tr: {
    baslik: "PEMF geliştirici kabuğu",
    kontrol: "Kontrol",
    simulasyon: "Simülasyon",
    bagli: "Sunucuya bağlı",
    bagliDegil: "Sunucuya bağlı değil — sahte sunucuyu başlatın (README)",
    dil: "English",
    sonBildirim: "Son bildirim: ",
  },
  en: {
    baslik: "PEMF developer shell",
    kontrol: "Control",
    simulasyon: "Simulation",
    bagli: "Connected to server",
    bagliDegil: "Not connected — start the fake server (README)",
    dil: "Türkçe",
    sonBildirim: "Latest notification: ",
  },
} as const;

type Sekme = "kontrol" | "simulasyon";

/** Web'de adresle açılış sekmesi: `?sekme=simulasyon` (ör. ikizi doğrudan denemek için). Mobilde adres yok → Kontrol. */
function ilkSekme(): Sekme {
  const arama = typeof window !== "undefined" ? window.location?.search ?? "" : "";
  return new URLSearchParams(arama).get("sekme") === "simulasyon" ? "simulasyon" : "kontrol";
}

function Ust({ sekme, onSekme }: { sekme: Sekme; onSekme: (s: Sekme) => void }) {
  useTranslation(); // dil değişince yeniden çiz
  const dil = i18n.language === "en" ? "en" : "tr";
  const m = METIN[dil];
  const { wsConnected, snapshot } = useLiveData();
  // Sahte sunucunun bildirimleri (ör. sürücü hatası) — ana uygulamadaki bildirim zili kitte yok; en sonuncusu burada görünür.
  const son = (snapshot.notifications ?? [])[0];
  const sonMetin = son ? (son.mesajlar?.[dil] ?? son.message) : "";
  return (
    <View>
      <View style={styles.ust}>
        <Text style={styles.baslik} numberOfLines={1}>{m.baslik}</Text>
        <TouchableOpacity
          style={styles.dilDugmesi}
          onPress={() => void dilSec(dil === "tr" ? "en" : "tr")}
          accessibilityRole="button"
          accessibilityLabel={m.dil}
        >
          <Text style={styles.dilYazi}>{m.dil}</Text>
        </TouchableOpacity>
      </View>
      <Text style={[styles.rozet, wsConnected ? styles.rozetBagli : styles.rozetKopuk]}>
        {wsConnected ? m.bagli : m.bagliDegil}
      </Text>
      {sonMetin ? <Text style={styles.bildirim}>{m.sonBildirim + sonMetin}</Text> : null}
      {/* Ana uygulamanın kabuğundaki ACİL DURDUR mandalı bandı (kuruluysa görünür; "Sıfırla" onay ister, bobin BAŞLATMAZ). */}
      <EstopMandalBandi />
      <View style={styles.sekmeler}>
        {(["kontrol", "simulasyon"] as const).map((s) => (
          <TouchableOpacity
            key={s}
            style={[styles.sekme, sekme === s && styles.sekmeEtkin]}
            onPress={() => onSekme(s)}
            accessibilityRole="tab"
            accessibilityState={{ selected: sekme === s }}
          >
            <Text style={[styles.sekmeYazi, sekme === s && styles.sekmeYaziEtkin]}>{m[s]}</Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );
}

export function GelistiriciUygulamasi() {
  const [sekme, setSekme] = useState<Sekme>(ilkSekme);
  return (
    <LiveDataProvider>
      <View style={styles.kok}>
        <ScrollView contentContainerStyle={styles.icerik} keyboardShouldPersistTaps="handled">
          <Ust sekme={sekme} onSekme={setSekme} />
          {sekme === "kontrol" ? <ControlScreen /> : <DemaSimulatorScreen />}
        </ScrollView>
      </View>
    </LiveDataProvider>
  );
}

const styles = StyleSheet.create({
  kok: { flex: 1, backgroundColor: colors.bg },
  icerik: { padding: spacing.md, gap: spacing.md, width: "100%", maxWidth: layoutMax.icerik, alignSelf: "center" },
  ust: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: spacing.md },
  baslik: { color: colors.text, fontSize: rf(20), fontWeight: "700", flexShrink: 1 },
  dilDugmesi: { minHeight: touch.min, paddingHorizontal: spacing.md, justifyContent: "center", borderRadius: rs(8), borderWidth: 1, borderColor: colors.border },
  dilYazi: { color: colors.text, fontSize: rf(14) },
  rozet: { marginTop: spacing.sm, fontSize: rf(13), fontWeight: "600" },
  rozetBagli: { color: colors.success },
  rozetKopuk: { color: colors.warning },
  bildirim: { marginTop: spacing.xs, color: colors.textMuted, fontSize: rf(13) },
  sekmeler: { flexDirection: "row", gap: spacing.sm, marginTop: spacing.md },
  sekme: { flex: 1, minHeight: touch.min, alignItems: "center", justifyContent: "center", borderRadius: rs(10), borderWidth: 1, borderColor: colors.border },
  sekmeEtkin: { backgroundColor: colors.primary, borderColor: colors.primary },
  sekmeYazi: { color: colors.textMuted, fontSize: rf(15), fontWeight: "600" },
  sekmeYaziEtkin: { color: colors.text },
});
