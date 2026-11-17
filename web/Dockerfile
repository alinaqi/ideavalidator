# ideavalidator-web: Rust shell (axum/tokio) + hosted MCP that drives the Python pipeline engine.
# Build context is the REPO ROOT (see render.yaml dockerContext / `docker build -f web/Dockerfile .`),
# because the runtime stage copies pipeline/ and worker/ alongside the release binary.

# ---- stage 1: build the release binary ------------------------------------------------------------
# sqlx runtime queries (no query! macros) mean this compiles with no DATABASE_URL and no offline cache.
FROM rust:1.99-slim-bookworm AS builder

# Native build deps for the rustls/ring/aws-lc-rs TLS stack used by reqwest + sqlx.
RUN apt-get update \
    && apt-get install -y --no-install-recommends pkg-config build-essential cmake perl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
# The crate (incl. migrations/ embedded via include_str!) and its lockfile.
COPY web/ ./web/
WORKDIR /build/web
RUN cargo build --release --locked --bin ideavalidator-web

# ---- stage 2: slim runtime with the Python engine -------------------------------------------------
FROM python:3.12-slim

# ca-certificates for outbound HTTPS to Palgu/Gemini from the Python worker.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Pipeline runtime deps only (the worker never imports the server/ or xlsx extras).
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# The engine the worker drives, plus the NDJSON worker entrypoint. The binary spawns
# `python3 -m worker.run_job` from this workdir, so both packages must sit at /app.
COPY pipeline/ ./pipeline/
COPY worker/ ./worker/

# The release binary. Schema migrations are embedded in it (include_str! of web/migrations),
# so the binary applies them on startup — no migrations/ copy needed at runtime.
COPY --from=builder /build/web/target/release/ideavalidator-web /usr/local/bin/ideavalidator-web

# PYTHON_BIN points at the system python (NOT a .venv, which does not exist in this image).
ENV PYTHON_BIN=python3 \
    PORT=8000 \
    IV_STORE=/data

EXPOSE 8000
CMD ["ideavalidator-web"]
