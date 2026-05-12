FROM python:3.12-slim AS base-runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd -g 1000 node \
 && useradd -m -u 1000 -g node -s /bin/bash node

COPY pyproject.toml README.md ./
COPY src ./src

RUN python -m pip install --upgrade pip \
 && python -m pip install .

FROM base-runtime

ENV OPENZUES_HOST=127.0.0.1 \
    OPENZUES_PORT=18789 \
    OPENZUES_DATA_DIR=/home/node/.openzues

# Pre-create the default state dir so Docker volumes mounted here inherit
# node ownership instead of root-owned state.
RUN install -d -m 0700 -o node -g node /home/node/.openzues && \
    stat -c '%U:%G %a' /home/node/.openzues | grep -qx 'node:node 700'

EXPOSE 18789

USER node

HEALTHCHECK --interval=3m --timeout=10s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:18789/healthz', timeout=5).close()"

CMD ["openzues", "serve", "--host", "0.0.0.0", "--port", "18789"]
