# KI: AIV-Truppenverhalten

Stellt fehlende AIV-Positionen für Pikeniere und beide Schwertkämpfertypen wieder her. Optionale Einstellungen steuern Startrollen und Verteidigerbewegungen aller 15 Truppentypen.

Pro Truppentyp höchstens eine Option je Paar wählen. Wache: AIV-Positionen beziehen; Graben: Starttruppen dem Ausheben von Burggräben zuweisen. Halten: am Verteidigungsplatz bleiben; Patrouille: gemäß den AIC-Patrouilleneinstellungen der KI zwischen Verteidigungsplätzen wechseln. Ein gewähltes Kästchen erneut anklicken, um das Paar abzuwählen und das Spielverhalten zu verwenden.

Für einzelne KIs: `AIVTroops_InitialRole_<Troop>` (`"defend"` / `"dig"`) und `AIVTroops_Movement_<Troop>` (`"hold"` / `"patrol"`). Ohne Truppensuffix gilt die Einstellung für die ganze KI; die gemeinsame Rolle erlaubt nur `"defend"`. Aktivierte AIC-Überschreibungen haben Vorrang; fehlende Felder erben.

Beispiel: `AIVTroops_InitialRole_Slave: "dig"` weist Sklaven dem Graben zu. Truppennamen und Details stehen in der [AIC-Feldreferenz](https://github.com/UnofficialCrusaderPatch/UCP-Wiki/blob/docs/extension-aic-fields/docs/Stronghold-Crusader-Wiki/AI-Lords/AI-Character-Parameters.md#aiv-troop-behaviour).

Truppeneinstellungen sind anfangs deaktiviert. Nach Änderungen das Spiel neu starten und eine neue Partie beginnen.
