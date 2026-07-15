FROM --platform=linux/amd64 golang:1.22-bookworm AS build

WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY *.go ./
COPY templates ./templates
COPY static ./static
RUN CGO_ENABLED=1 GOOS=linux GOARCH=amd64 go build -trimpath -ldflags "-s -w" -o /out/archivedesk .

FROM --platform=linux/amd64 debian:bookworm-slim

RUN apt-get update \
  && apt-get install -y --no-install-recommends ca-certificates libxml2-utils openssh-server vim nano \
  && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/sh archivedesk \
  && mkdir -p /run/sshd /opt/ad/state /app \
  && chown -R archivedesk:archivedesk /opt/ad/state

WORKDIR /app
COPY --from=build /out/archivedesk /app/archivedesk
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod 755 /app/entrypoint.sh /app/archivedesk

ENTRYPOINT ["/app/entrypoint.sh"]
