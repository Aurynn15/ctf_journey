# Local deploy for SealBroker. Same base image as the live target, so the glibc
# in this container is byte-for-byte the one the remote service runs against —
# pull /lib/x86_64-linux-gnu/libc.so.6 out of it instead of guessing the version.
#
#   docker build --platform=linux/amd64 -t sealbroker .
#   docker run --rm -p 8160:8160 sealbroker
#   # grab the exact libc for your exploit:
#   docker create --name sb sealbroker && docker cp sb:/lib/x86_64-linux-gnu/libc.so.6 . && docker rm sb
#
# socat owns the listening socket and forks one stdin/stdout-wired sealbroker
# worker per connection, matching how the service is deployed remotely.
FROM --platform=linux/amd64 ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
  && apt-get install -y --no-install-recommends socat \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY sealbroker /app/sealbroker

RUN chmod 755 /app/sealbroker \
  && printf 'PLAYIT{local_test_flag}\n' > /flag.txt \
  && printf 'local-test-proof\n' > /proof.txt \
  && chmod 0644 /flag.txt /proof.txt

EXPOSE 8160

CMD ["socat", "TCP-LISTEN:8160,reuseaddr,fork", "EXEC:/app/sealbroker"]
