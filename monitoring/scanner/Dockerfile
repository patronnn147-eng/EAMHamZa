# Continuous Trivy scanner image
# Base: python:3.11-alpine (has Python for metrics push)
# Adds: trivy binary + docker CLI (to access local Docker daemon)
#
# Build context is ./monitoring/ so both scanner/ and scripts/ are accessible.

FROM python:3.11-alpine

ARG TRIVY_VERSION=0.72.0

RUN apk add --no-cache \
        curl \
        bash \
        docker-cli \
    && curl -sfL \
        "https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz" \
        | tar -xz -C /usr/local/bin trivy \
    && trivy --version

# Copy the shared push script and the loop script
COPY scripts/trivy_push_metrics.py /scripts/trivy_push_metrics.py
COPY scanner/scanner_loop.sh       /scripts/scanner_loop.sh
RUN chmod +x /scripts/scanner_loop.sh

ENTRYPOINT ["/scripts/scanner_loop.sh"]
