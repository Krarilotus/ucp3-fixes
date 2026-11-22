# Wegsuche

Ein gemeinsamer Baustein für Module, die verändern, wie Einheiten ihren Weg finden. Für sich allein ändert er nichts im Spiel.

Sowohl Smarter Pathing (Kletterabkürzung für Assassinen) als auch Torhauskorrekturen (Gatehouse Fixes) mit seinen Tor-Routenregeln benötigen die Wegsuche des Spiels für eine Einheit. Dieses Modul sorgt dafür, dass sie zusammenarbeiten: Jedes fügt hier seine Regel hinzu, und jede Regel sieht die richtige Einheit. Andere Module installieren es automatisch, wenn sie es brauchen.
