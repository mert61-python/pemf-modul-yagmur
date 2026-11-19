// Author: mertaygn, cglrgrkn
/**
 * GELİŞTİRİCİ KİTİ: ana uygulamanın cihaz keşfi (kayıtlı adres, mDNS, alt ağ taraması, bulut cihaz kayıt defteri) kitte YOKTUR.
 * Sahte sunucu, sayfayı sunan adreste (web) ya da `EXPO_PUBLIC_PEMF_API_BASE_URL` / `EXPO_PUBLIC_PEMF_WS_URL` ile verilen adreste
 * çalışır (`services/config.ts`). İmza ana uygulamadakiyle aynıdır; keşif her zaman "bulunamadı" döner ve geçerli adres kullanılır.
 */
export type DiscoverySource = "current" | "saved" | "mdns" | "subnet" | "remote" | "none";
export type KesifKipi = "tam" | "hafif" | "kayitliHemen";
export interface DiscoveryResult {
  address: string;
  source: DiscoverySource;
}

export async function discoverBackend(_kip: KesifKipi = "tam"): Promise<DiscoveryResult | null> {
  return null;
}
