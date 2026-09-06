# Yapay zekâ: AIV birlik davranışı

Kargıcıların ve her iki kılıçlı türünün eksik AIV konumlarını geri getirir. İsteğe bağlı ayarlar 15 birlik türünün başlangıç görevini ve savunma hareketini yönetir.

Her birlik türü için her çiftten en fazla bir seçenek seçin. Savun: AIV konumlarına git; Kaz: başlangıç birliklerini hendek kazmaya ata. Bekle: savunma noktasında kal; Devriye: yapay zekânın AIC devriye ayarlarına göre savunma noktaları arasında dolaş. Çifti temizleyip oyunun varsayılan davranışını kullanmak için seçili kutuya tekrar tıklayın.

Her yapay zekâ için: `AIVTroops_InitialRole_<Troop>` (`"defend"` / `"dig"`) ve `AIVTroops_Movement_<Troop>` (`"hold"` / `"patrol"`). Birlik son eki olmadan ayar yapay zekânın tamamına uygulanır; ortak görev yalnızca `"defend"` kabul eder. Etkin AIC ayarları önceliklidir; atlanan alanlar devralır.

Örnek: `AIVTroops_InitialRole_Slave: "dig"` köleleri kazmaya atar. Birlik adları ve ayrıntılar için [AIC alanları rehberine](https://github.com/UnofficialCrusaderPatch/UCP-Wiki/blob/docs/extension-aic-fields/docs/Stronghold-Crusader-Wiki/AI-Lords/AI-Character-Parameters.md#aiv-troop-behaviour) bakın.

Birlik ayarları başlangıçta kapalıdır. Değişiklikten sonra oyunu yeniden başlatıp yeni bir oyun açın.
