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
- die Schriftart "OpenSan" technisch festgelegt werden kann
- Vorlagen konsistent bleiben
- Bilder optional als separater Schritt behandelt werden

## Aktueller MVP-Stand

Ein erster HTML-Renderer ist vorhanden:

- `scripts/render_worksheets.py`
- liest ein Arbeitsblatt-JSON ein
- prueft die benoetigten Felder
- erzeugt drei druckbare HTML-Seiten
- orientiert sich an den beiden PDF-Vorlagen in `templates/`
- nutzt vorhandene Piktogramme aus `pictogramme/`
- enthaelt jetzt auch einen lokalen Generator-Server mit Formular und Vorschau

## Lokaler Generator-Workflow

### 1. API-Schluessel setzen

Der echte Modellaufruf nutzt die OpenAI Responses API.

```bash
export OPENAI_API_KEY="dein_api_key"
```

Optional kannst du ein Modell vorgeben. Standard ist aktuell `gpt-5.4-mini`.

```bash
export OPENAI_MODEL="gpt-5.4-mini"
```

### 2. Lokale App starten

```bash
/Users/rolfyhientz/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  scripts/run_local_app.py
```

Danach ist die App unter `http://127.0.0.1:8123` erreichbar.

### 3. Arbeitsblaetter erzeugen

- Thema eintragen
- Lernziel eintragen
- optional Fokus, Wortschatz und Vorlagenvariante setzen
- `Arbeitsblaetter erzeugen` klicken
- oder `Demo laden` fuer einen lokalen Test ohne API-Aufruf

Die Ergebnisse landen unter `out/generated/` als:

- JSON-Datei der Modellantwort
- HTML-Vorschau mit drei Niveaustufen
- PDF-Datei fuer den Druck oder direkten Export

### Renderer starten

Beispiel mit der Vorlage `AB-Vorlage-mit-Arbeitsanweisungen.pdf`:

```bash
/Users/rolfyhientz/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  scripts/render_worksheets.py \
  --input examples/output-example.json \
  --output out/arbeitsblaetter-vorschau.html \
  --template instructions
```

Alternative mit der blanken Vorlage:

```bash
/Users/rolfyhientz/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  scripts/render_worksheets.py \
  --template blank
```

## Was noch fehlt

- Einbindung der echten Schriftdatei `OpenSan`, falls du sie lokal bereitstellst
- optional Bildgenerierung als zweiter Schritt
- feinere Feldvalidierung direkt gegen das volle JSON-Schema

## Empfohlener naechster Schritt

1. Schriftdatei `OpenSan` in `templates/` oder einen Font-Unterordner legen.
2. Ein erstes echtes Themenbeispiel ueber die lokale App generieren.
3. Danach optional Bildgenerierung pro Blatt anbinden.
4. Anschliessend Feinschliff bei Layout und Feldvalidierung machen.
