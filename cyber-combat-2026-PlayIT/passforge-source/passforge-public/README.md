# PassForge

PassForge is a password-manager web service (HTTP/JSON): account register and
login, a user directory, vault entries, and CSV import/export, plus an admin
workspace with a spreadsheet smart-import and settings.

- Public port: `8120`
- Flag: `/flag.txt`
- Proof: `/proof.txt`
- State: `/opt/ad/state`

Source: `service.py`, `workspace.py`. Patch the running service through the
platform SSH access; the source in the container is under `/app`.
