# Stadtbibliothek API

Eine reine Backend-REST-API für die Ausleihe einer kleinen Stadtbibliothek. Sie
verwaltet Bücher und Mitglieder, legt Ausleihen an und gibt sie zurück, erzwingt
Ausleihregeln (höchstens drei offene Ausleihen je Mitglied, Ausleihe nur bei
freiem Exemplar, Fälligkeit 14 Tage nach der Ausleihe), bietet eine
Buchsuche mit Paginierung, schützt alle schreibenden Endpunkte mit einem
API-Key und liefert alle Fehler in einem einheitlichen JSON-Format.

## Tech Stack

- **Python 3.13** mit **FastAPI**
- **Pydantic v2** und **pydantic-settings** für Validierung und Konfiguration
- **SQLAlchemy 2.0** (ORM, `Mapped`/`select`-Stil) mit **SQLite**
- **Uvicorn** als ASGI-Server
- **pytest** und **httpx** (über `TestClient`) für die Testsuite

## Installation

```bash
python -m pip install -r requirements.txt
```

## Starten (Entwicklung)

```bash
python -m uvicorn app.main:app --port 8000
```

Die API läuft danach unter `http://localhost:8000`. Die interaktive
Dokumentation ist unter `/docs` erreichbar, das maschinenlesbare Schema unter
`/openapi.json`. Beim Start wird das Datenbankschema automatisch angelegt
(`Base.metadata.create_all`), es ist keine Migration von Hand nötig.

## Build (Produktion)

Es gibt keinen separaten Build-Schritt. Für den produktiven Betrieb wird die API
mit Uvicorn gestartet, ohne `--reload`:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Umgebungsvariablen

| Variable | Pflicht | Beschreibung |
| --- | --- | --- |
| `API_KEY` | nein | Erwarteter Wert des Headers `X-API-Key`. Ist er nicht gesetzt, antworten alle schreibenden Endpunkte mit `401`. |
| `DATABASE_URL` | nein | SQLAlchemy-Datenbank-URL. Standard: `sqlite:///./library.db` (SQLite-Datei statt In-Memory, damit Daten einen Neustart überleben). |

Beide Variablen werden zur Laufzeit gelesen; ein fehlender API-Key führt nicht
zum Absturz, sondern wertet jeden Schreibzugriff als nicht autorisiert.

## Verwendung (API)

Alle Antworten sind JSON. Fehler haben immer denselben Körper:

```json
{"error": {"code": "unauthorized", "message": "...", "details": [{"field": "...", "message": "..."}]}}
```

Schreibende Aufrufe (`POST`, `PUT`, `PATCH`, `DELETE`) benötigen den Header
`X-API-Key` mit dem Wert aus `API_KEY`; lesende Aufrufe (`GET`) brauchen ihn
nicht.

### Endpunkte

| Methode & Pfad | Beschreibung | Erfolg | Fehler |
| --- | --- | --- | --- |
| `GET /health` | Liveness-Check | `200 {"status":"ok"}` | – |
| `GET /books?q=&limit=20&offset=0` | Büchersuche mit Paginierung (`q` sucht case-insensitiv in Titel oder Autor) | `200 Page[BookRead]` | 422 |
| `POST /books` | Buch anlegen | `201 BookRead` | 401, 409, 422 |
| `GET /books/{book_id}` | Ein Buch lesen | `200 BookRead` | 404 |
| `PUT /books/{book_id}` | Buch ersetzen | `200 BookRead` | 401, 404, 409, 422 |
| `PATCH /books/{book_id}` | Buch teilweise ändern | `200 BookRead` | 401, 404, 409, 422 |
| `DELETE /books/{book_id}` | Buch löschen | `204` | 401, 404, 409 |
| `GET /members?limit=20&offset=0` | Mitglieder auflisten | `200 Page[MemberRead]` | 422 |
| `POST /members` | Mitglied anlegen | `201 MemberRead` | 401, 409, 422 |
| `GET /members/{member_id}` | Ein Mitglied lesen | `200 MemberRead` | 404 |
| `PUT /members/{member_id}` | Mitglied ersetzen | `200 MemberRead` | 401, 404, 409, 422 |
| `PATCH /members/{member_id}` | Mitglied teilweise ändern | `200 MemberRead` | 401, 404, 409, 422 |
| `DELETE /members/{member_id}` | Mitglied löschen | `204` | 401, 404 |
| `POST /loans` | Ausleihe anlegen | `201 LoanRead` | 401, 404, 409, 422 |
| `POST /loans/{loan_id}/return` | Ausleihe zurückgeben | `200 LoanRead` | 401, 404, 409 |
| `GET /loans/overdue?limit=20&offset=0` | Überfällige Ausleihen | `200 Page[OverdueLoanRead]` | 422 |

### Schemata

- `Page[T] = {items: [T], total, limit, offset}` (limit höchstens 100)
- `BookCreate = {titel, autor, isbn, erscheinungsjahr, exemplare=1}`
- `BookRead = {id, titel, autor, isbn, erscheinungsjahr, exemplare, verfuegbar}`
- `MemberCreate = {name, email, mitglied_seit=heute}`
- `MemberRead = {id, name, email, mitglied_seit, offene_ausleihen}`
- `LoanCreate = {book_id, member_id}`
- `LoanRead = {id, book_id, member_id, ausgeliehen_am, faellig_am, zurueckgegeben_am}`
- `OverdueLoanRead = {loan_id, book, member, ausgeliehen_am, faellig_am, tage_ueberfaellig}`

Daten werden als ISO-Strings im Format `YYYY-MM-DD` übertragen.

### Beispiel

```bash
curl -X POST http://localhost:8000/books \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"titel":"Der Steppenwolf","autor":"Hermann Hesse","isbn":"978-3-16-148410-0","exemplare":2}'

curl "http://localhost:8000/books?q=stein&limit=20&offset=0"
```

## Tests

Die Testsuite läuft mit einem einzigen Kommando gegen eine separate
Test-Datenbank in einem temporären Verzeichnis und schreibt nie in die
Produktionsdatenbank:

```bash
PYTHONPATH=. python -m pytest
```

## Fehlercodes

`unauthorized`, `not_found`, `validation_error`, `internal_error`,
`duplicate_isbn`, `duplicate_email`, `loan_limit_reached`, `no_copy_available`,
`already_returned`, `book_has_open_loans`.

## Funktionsumfang

- CRUD für Bücher und Mitglieder
- Buchsuche mit Paginierung
- Ausleihe und Rückgabe mit Ausleihregeln (max. 3 offene Ausleihen, nur bei
  freiem Exemplar, Fälligkeit 14 Tage)
- Überfälligkeitsbericht
- API-Key-Schutz für schreibende Endpunkte
- Einheitliches Fehlerformat
