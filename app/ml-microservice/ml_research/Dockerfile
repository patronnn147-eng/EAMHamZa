# ML Research environment — tensorflow + umap-learn + mlflow + jupyter
# NOT production — dev/research only
FROM python:3.11-slim

WORKDIR /workspace

# Upgrade OS packages, install runtime deps, then remove linux-libc-dev
# (kernel headers — never needed at runtime, but pulled in by python:3.11-slim base).
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    curl git build-essential \
    && apt-get purge -y --auto-remove linux-libc-dev \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 appuser

COPY app/ml-microservice/ml_research/requirements-notebooks.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install "pip>=26.1.2" && \
    pip install -r requirements-notebooks.txt && \
    pip install --upgrade "jaraco.context>=6.1.0" "wheel>=0.46.2" && \
    chown -R appuser:appuser /workspace
USER appuser

# Jupyter config — ip must stay 0.0.0.0 for docker-compose's port mapping to reach it
# (binding to 127.0.0.1 inside the container is unreachable via `docker run -p`/compose
# port publishing). Token/password are intentionally NOT overridden here — Jupyter
# auto-generates a random token per run (printed to `docker compose logs notebooks`),
# so the notebook server still requires authentication even though it's reachable.
RUN jupyter notebook --generate-config && \
    echo "c.NotebookApp.ip = '0.0.0.0'" >> /home/appuser/.jupyter/jupyter_notebook_config.py && \
    echo "c.NotebookApp.open_browser = False" >> /home/appuser/.jupyter/jupyter_notebook_config.py

EXPOSE 8888

CMD ["jupyter", "notebook", "--notebook-dir=/workspace/app/ml-microservice/ml_research"]
