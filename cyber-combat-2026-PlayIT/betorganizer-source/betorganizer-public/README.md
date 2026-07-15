# BetOrganizer

BetOrganizer is a sports betting platform where users can register accounts,
claim daily rewards, place bets on football matches, and track their predictions.
Organizers can create matches, set results, and generate match reports.

## Files

- `cmd/server/main.go` - entrypoint
- `internal/handler/` - HTTP request handlers
- `internal/store/` - database layer (SQLite)
- `internal/middleware/` - input validation and rate limiting
- `internal/resolver/` - background match auto-resolver
- `templates/` - HTML templates

## Runtime

- Public port: `8140`
- Flag path: `/flag.txt`
- Proof path: `/proof.txt`

Patch the running service through the platform-provided SSH access. The compiled
binary in the container is located at `/app/betorganizer`.
