# SealBroker

SealBroker is a line-based TCP daemon that manages sealed capsules and leases.
Start a session with `AUTH <user> <pass>`; commands return `OK ...` or `ERR ...`
(NEW/WRITE/SEAL/LEASE/SLICE/NOTE/UNLEASE/PATCH/AUDIT/EXPORT/DROP).

Source: `sealbroker` (release binary), `sealbroker.cpp`, `sealbroker.hpp`.

Run it locally with the bundled `Dockerfile` (same base image as the remote
target, so the container ships the exact glibc the service runs against):

    docker build --platform=linux/amd64 -t sealbroker .
    docker run --rm -p 8160:8160 sealbroker

- Port: `8160`
- Flag: `/flag.txt`
- Proof: `/proof.txt`

Patch the service while preserving the normal protocol behavior the checker expects.
