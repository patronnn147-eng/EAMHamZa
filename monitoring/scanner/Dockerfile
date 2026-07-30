# Continuous Trivy scanner image
# Base: python:3.11-alpine (has Python for metrics push)
# Adds: trivy binary + docker CLI (to access local Docker daemon)
#
# Build context is ./monitoring/ so both scanner/ and scripts/ are accessible.

FROM python:3.11-alpine

ARG TRIVY_VERSION=0.72.0
ARG TARGETARCH

# Trivy release assets use Linux-64bit for amd64, Linux-ARM64 for arm64 —
# not $TARGETARCH's own naming. Map it so this stage cross-builds correctly
# instead of downloading and executing a wrong-arch binary (build-time
# `trivy --version` would fail with ENOEXEC on a mismatched arch).
RUN apk add --no-cache \
        curl \
        bash \
        docker-cli \
    && case "${TARGETARCH}" in \
        amd64) TRIVY_ARCH=64bit ;; \
        arm64) TRIVY_ARCH=ARM64 ;; \
        *) echo "unsupported TARGETARCH: ${TARGETARCH}" >&2; exit 1 ;; \
       esac \
    && curl -sfL \
        "https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_Linux-${TRIVY_ARCH}.tar.gz" \
        | tar -xz -C /usr/local/bin trivy \
    && trivy --version

# Copy the shared push script, loop script, and ignore list
COPY scripts/trivy_push_metrics.py /scripts/trivy_push_metrics.py
COPY scanner/scanner_loop.sh       /scripts/scanner_loop.sh
COPY scanner/.trivyignore          /etc/trivy/.trivyignore
RUN chmod +x /scripts/scanner_loop.sh

ENTRYPOINT ["/scripts/scanner_loop.sh"]
