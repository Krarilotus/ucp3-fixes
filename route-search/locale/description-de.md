# Wegsuche

Ein gemeinsamer Baustein für Module, die verändern, wie Einheiten ihren Weg finden. Für sich allein ändert er nichts im Spiel.

Sowohl Smarter Pathing (Kletterabkürzung für Assassinen) als auch das Modul Torhauskorrekturen (Gatehouse Fixes) mit seinen Tor-Routenregeln ändern die Wegsuche, die das Spiel ausführt, wenn eine Einheit ein neues Ziel erhält. Die Wegsuche sorgt dafür, dass sie zusammenarbeiten – jedes Modul fügt hier seine Regel hinzu, und jede Regel sieht die richtige Einheit. Nur Versionen dieser beiden Module, die „Wegsuche“ als Abhängigkeit voraussetzen, nutzen sie und installieren sie automatisch.
