# AB-Agent

AB-Agent ist die Grundstruktur fuer eine Assistentin, die Arbeitsblaetter fuer den Foerderschulbereich erzeugt.

## Ziel

Die Assistentin soll:

- Themen und Lernziele entgegennehmen
- drei Niveaustufen erzeugen:
  - sehr leicht
  - mittel
  - etwas schwerer
- kreative, kindgerechte Aufgaben entwickeln
- bei Bedarf Bildideen oder Bildprompts liefern
- Inhalte in eine feste Vorlage einsetzen
- spaeter als PDF oder DOCX ausgeben

## Projektstruktur

- `prompts/`
  - System-Prompts fuer die Assistentin
- `schemas/`
  - JSON-Schemas fuer strukturierte Modellantworten
- `examples/`
  - Beispiel-Eingaben und Beispiel-Ausgaben
- `templates/`
  - Platz fuer echte Arbeitsblatt-Vorlagen
- `docs/`
  - Konzept, MVP-Plan und fachliche Notizen
- `app/`
  - kleines Frontend-Grundgeruest fuer Eingabe und Vorschau

## Empfohlene Architektur

Das Projekt trennt Inhalt und Layout:

1. Das Modell erzeugt nur die paedagogischen Inhalte.
2. Ein Renderer setzt diese Inhalte in eine feste Vorlage ein.
3. Die Ausgabe wird als PDF oder DOCX exportiert.

Das ist stabiler als ein reiner Chat-Workflow, weil:

- die drei Niveaustufen besser kontrollierbar sind
- die Schriftart "Stimme" technisch festgelegt werden kann
- Vorlagen konsistent bleiben
- Bilder optional als separater Schritt behandelt werden

## Empfohlener naechster Schritt

1. Eine echte Vorlage in `templates/` ablegen.
2. Entscheiden, ob zuerst `DOCX` oder `HTML -> PDF` gebaut werden soll.
3. Den Prompt mit dem JSON-Schema gegen erste Beispielthemen testen.
4. Danach den eigentlichen Generator implementieren.
