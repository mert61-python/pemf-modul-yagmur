// Author: mertaygn, cglrgrkn
// PEMF GELİŞTİRİCİ KABUĞU — kök düzen. Dil katmanı İLK içe aktarılır (ana uygulamadaki gibi: ilk karede metin hazır).
import "@/i18n";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { ToastProvider } from "@/components/ui/ToastProvider";
import { OnayPenceresiSaglayici } from "@/components/ui/OnayPenceresiSaglayici";

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <ToastProvider>
        <OnayPenceresiSaglayici>
          <StatusBar style="light" />
          <Stack screenOptions={{ headerShown: false }} />
        </OnayPenceresiSaglayici>
      </ToastProvider>
    </SafeAreaProvider>
  );
}
