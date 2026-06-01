# =============================================================================
# Stage 1: builder
# =============================================================================
FROM python:3.12-slim AS builder

# Evita bytecode desnecessário e bufferização de stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# Copia apenas o manifesto de dependências antes do código-fonte
# para aproveitar o cache de camadas do Docker
COPY requirements.txt .

# Instala as dependências em um diretório isolado (--prefix) sem
# sujar o sistema e sem cache local do pip
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt


# =============================================================================
# Stage 2: runtime
# =============================================================================
FROM python:3.12-slim AS runtime

# ── Metadados OCI ─────────────────────────────────────────────────────────────
LABEL org.opencontainers.image.title="lift" \
      org.opencontainers.image.description="Lift – Hill Valley Tech beta service" \
      org.opencontainers.image.vendor="Hill Valley Tech"

# ── Variáveis de ambiente de runtime ─────────────────────────────────────────
# Valores intencionalmente AUSENTES: devem ser injetados pelo Kubernetes
# via Secret/ConfigMap. A presença das variáveis é validada pelo próprio app.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Documentação explícita das variáveis obrigatórias (sem valores padrão)
# DATABASE_URL e API_KEY DEVEM ser fornecidas em runtime
ENV DATABASE_URL="" \
    API_KEY=""

# ── Usuário não-root ──────────────────────────────────────────────────────────
RUN groupadd --gid 1001 appgroup \
    && useradd --uid 1001 --gid appgroup --no-create-home --shell /sbin/nologin appuser

# ── Dependências copiadas do stage builder ───────────────────────────────────
COPY --from=builder /install /usr/local

# ── Código da aplicação ───────────────────────────────────────────────────────
WORKDIR /app

COPY --chown=appuser:appgroup app.py         ./app.py
COPY --chown=appuser:appgroup requirements.txt ./requirements.txt
COPY --chown=appuser:appgroup lib/            ./lib/

# ── Sistema de arquivos somente-leitura (hardening) ───────────────────────────
# O diretório /tmp permanece gravável para necessidades de runtime temporárias
RUN chmod -R 550 /app

# ── Troca para usuário sem privilégios ───────────────────────────────────────
USER appuser

# ── Porta exposta ─────────────────────────────────────────────────────────────
EXPOSE 8080

# ── Healthcheck ───────────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" \
    || exit 1

# ── Entrypoint ────────────────────────────────────────────────────────────────
ENTRYPOINT ["gunicorn"]
CMD ["--bind", "0.0.0.0:8080", "--workers", "4", "app:app"]


