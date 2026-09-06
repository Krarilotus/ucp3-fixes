# MI: AIV-csapatviselkedés

Helyreállítja a pikások és mindkét kardforgatótípus hiányzó AIV-pozícióit. Opcionális beállítások szabályozzák mind a 15 egységtípus kezdőszerepét és védelmi mozgását.

Egységtípusonként mindkét párból legfeljebb egy lehetőséget válassz. Védelem: az AIV-helyek elfoglalása; Ásás: a kezdőcsapatok várárokásásra kijelölése. Tartás: maradás a védelmi helyen; Járőr: mozgás a védelmi helyek között az MI AIC-járőrbeállításai szerint. A kijelölt négyzetre újra kattintva törölheted a pár kijelölését, így a játék eredeti viselkedése érvényesül.

MI-nként: `AIVTroops_InitialRole_<Troop>` (`"defend"` / `"dig"`) és `AIVTroops_Movement_<Troop>` (`"hold"` / `"patrol"`). Egységutótag nélkül a beállítás közös az MI számára; a közös szerep csak `"defend"` lehet. Az engedélyezett AIC-felülírások elsőbbséget élveznek; a kihagyott mezők örökölnek.

Példa: `AIVTroops_InitialRole_Slave: "dig"` ásásra osztja be a rabszolgákat. Az egységnevek és részletek az [AIC-mezők leírásában](https://github.com/UnofficialCrusaderPatch/UCP-Wiki/blob/docs/extension-aic-fields/docs/Stronghold-Crusader-Wiki/AI-Lords/AI-Character-Parameters.md#aiv-troop-behaviour) találhatók.

Az egységbeállítások kezdetben ki vannak kapcsolva. Módosítás után indítsd újra a játékot és kezdj új meccset.
