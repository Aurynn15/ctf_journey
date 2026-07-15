# Relicshare

An archaeological artifact cataloging platform. Curators can register, create relic entries, and browse the collection. Each relic supports a customizable Jinja2 display theme.

## Source

`service.py` — the complete Flask application source code.

## Interface

REST API on port 8080:
- `POST /api/register` — create a curator account
- `POST /api/login` — authenticate
- `POST /api/relics` — create a new relic entry
- `GET  /api/relics` — list all relics
- `GET  /api/relics/<id>` — view relic detail with rendered theme
- `PUT  /api/relics/<id>` — update relic theme
- `GET  /api/health` — health check
