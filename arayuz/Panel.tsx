// Author: mertaygn, cglrgrkn
/**
 * ŞABLON PANEL — kendi kartınızın paneli. YALNIZ modül araç takımını (`@/moduller/arac` → `useModul`) ve ortak arayüz parçalarını
 * (`@/theme/tokens`, `@/services/moduller` hata metni) kullanır; ana uygulamanın başka iç dosyalarını içe aktarmaz.
 * Metinler `arayuz/i18n/{tr,en}.json` — birleştirmede `modul<Kimlik>` ad alanı olarak eklenir; her metin iki dilde.
 * ACİL DURDUR panelde OLMAZ: Kontrol sekmesindeki büyük düğme her zaman görünür ve modüle de gider.
 */
import { useState } from "react";
import { StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";
import { useTranslation } from "react-i18next";
import { useModul } from "@/moduller/arac";
import { modulHataMetni } from "@/services/moduller";
import { colors, rf, rs, spacing, touch } from "@/theme/tokens";

const ALANLAR: { ad: "frekans_hz" | "duty_yuzde" | "sure_dk"; varsayilan: string }[] = [
  { ad: "frekans_hz", varsayilan: "100" },
  { ad: "duty_yuzde", varsayilan: "25" },
  { ad: "sure_dk", varsayilan: "10" },
];

export default function SablonPanel() {
  const { t } = useTranslation();
  const m = useModul();
  const [deger, setDeger] = useState<Record<string, string>>(Object.fromEntries(ALANLAR.map((a) => [a.ad, a.varsayilan])));
  const etiket = (ad: string) =>
    ad === "frekans_hz" ? t("modulSablon.frekans") : ad === "duty_yuzde" ? t("modulSablon.duty") : t("modulSablon.sure");
  const bobin = m.durum?.bobin === true;
  return (
    <View style={styles.kutu} testID="modul-sablon-panel">
      <Text style={styles.baslik}>{t("modulSablon.baslik")}</Text>
      <View style={styles.satir}>
        {ALANLAR.map((a) => (
          <View key={a.ad} style={styles.alan}>
            <Text style={styles.etiket}>{etiket(a.ad)}</Text>
            <TextInput
              style={styles.giris}
              value={deger[a.ad]}
              onChangeText={(v) => setDeger((d) => ({ ...d, [a.ad]: v }))}
              keyboardType="numeric"
              testID={`modul-sablon-${a.ad}`}
            />
          </View>
        ))}
      </View>
      <View style={styles.satir}>
        <TouchableOpacity
          style={styles.dugme}
          disabled={m.mesgul}
          onPress={() => void m.uygula(Object.fromEntries(ALANLAR.map((a) => [a.ad, Number(deger[a.ad])])))}
          testID="modul-sablon-uygula"
          accessibilityRole="button"
        >
          <Text style={styles.dugmeMetin}>{t("modulSablon.uygula")}</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.dugme} disabled={m.mesgul} onPress={() => void m.baslat()} testID="modul-sablon-baslat" accessibilityRole="button">
          <Text style={styles.dugmeMetin}>{t("modulSablon.baslat")}</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.dugme, styles.durdur]} onPress={() => void m.durdur()} testID="modul-sablon-durdur" accessibilityRole="button">
          <Text style={styles.dugmeMetin}>{t("modulSablon.durdur")}</Text>
        </TouchableOpacity>
      </View>
      <Text style={styles.durum} testID="modul-sablon-durum">
        {m.durum === null ? t("modulSablon.durumYok") : bobin ? t("modulSablon.bobinAcik") : t("modulSablon.bobinKapali")}
      </Text>
      {m.hata && (
        <Text style={styles.hata} testID="modul-sablon-hata">
          {modulHataMetni(t, m.hata)}
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  kutu: { gap: spacing.sm },
  baslik: { color: colors.text, fontSize: rf(14), fontWeight: "700" },
  satir: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
  alan: { flexGrow: 1, minWidth: rs(110), gap: rs(4) },
  etiket: { color: colors.textMuted, fontSize: rf(12) },
  giris: {
    minHeight: touch.min,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: rs(8),
    color: colors.text,
    paddingHorizontal: rs(10),
  },
  dugme: {
    minHeight: touch.min,
    flexGrow: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: colors.primary,
    borderRadius: rs(10),
    paddingHorizontal: rs(12),
  },
  durdur: { backgroundColor: colors.danger },
  dugmeMetin: { color: colors.white, fontSize: rf(13), fontWeight: "700" },
  durum: { color: colors.text, fontSize: rf(12) },
  hata: { color: colors.warning, fontSize: rf(12), fontWeight: "700" },
});
