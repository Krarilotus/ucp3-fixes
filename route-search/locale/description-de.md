# Wegsuche

Ein gemeinsamer Baustein für Module, die verändern, wie Einheiten ihren Weg finden. Für sich allein ändert er nichts im Spiel.

Smarter Pathing (Abkürzung für Assassinen) und Torhauskorrekturen (Gatehouse Fixes, Regeln für Wege durch Tore) ändern beide, wie das Spiel einen Weg sucht, wenn eine Einheit ein neues Ziel erhält. Mit „Wegsuche“ können beide Module zusammenarbeiten. Jedes fügt der Wegsuche seine eigene Regel hinzu, und jede Regel berücksichtigt die Einheit, für die der Weg gesucht wird. Nur die Versionen dieser Module, die „Wegsuche“ als Abhängigkeit angeben, nutzen das Modul und installieren es automatisch.
