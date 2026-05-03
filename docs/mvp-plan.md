# MVP-Plan

## Ziel

Ein erster funktionierender Prototyp soll:

- Thema und Lernziel entgegennehmen
- drei Niveaustufen erzeugen
- die Antwort gegen das Schema validieren
- Inhalte in eine feste Vorlage einsetzen
- spaeter PDF oder DOCX ausgeben

## Minimaler Ablauf

1. Eingabeformular fuellen
2. Modell mit System-Prompt aufrufen
3. JSON validieren
4. Vorlage befuellen
5. Optional Bilder ergaenzen
6. Exportieren

## Erste technische Entscheidung

Es gibt zwei gute Startwege:

- `DOCX`, wenn du Blaetter nachtraeglich in Word anpassen willst
- `HTML -> PDF`, wenn das Layout besonders stabil und reproduzierbar sein soll

## Empfehlung

Sobald eine echte Vorlage vorliegt, sollte zuerst der Renderer gebaut werden. Danach lohnt sich der eigentliche Modellaufruf.
