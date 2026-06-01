Justificativa técnica — Dockerfile do serviço Lift
Hill Valley Tech · Migração VM → Kubernetes

1. Multi-stage build (builder + runtime)
FROM python:3.12-slim AS builder
...
FROM python:3.12-slim AS runtime
Por quê? O stage builder instala todas as ferramentas de compilação (gcc, headers do sistema, pip) necessárias para montar as dependências nativas (e.g. psycopg2-binary). O stage runtime copia apenas o artefato final (/install) e o código da aplicação, descartando compiladores, caches e pacotes intermediários.

Resultado prático: imagem final enxuta, superfície de ataque reduzida e ausência de ferramentas que poderiam ser exploradas em caso de comprometimento do container.

2. Imagem base python:3.12-slim
FROM python:3.12-slim AS builder
Por quê?

slim inclui apenas o mínimo do sistema Debian necessário para rodar Python — sem gerenciadores de pacotes extras, editores ou utilitários desnecessários.
Alternativas como alpine exigem compilação extra para pacotes C (psycopg2) e podem introduzir incompatibilidades de libc; slim oferece o melhor equilíbrio entre tamanho e compatibilidade.
Python 3.12 é a versão estável mais recente com suporte ativo (LTS-equivalente).
3. Variáveis de ambiente de build
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
Variável	Efeito
PYTHONDONTWRITEBYTECODE=1	Impede geração de arquivos .pyc, reduzindo camadas e superfície de ataque
PYTHONUNBUFFERED=1	Saída de stdout/stderr fluida — essencial para que o Beacon (stack de observabilidade) capture logs em tempo real sem buffer
4. Cache de camadas com COPY seletivo
COPY requirements.txt .
RUN pip install ...
Por quê? Copiar requirements.txt antes do código-fonte garante que o Docker reutilize a camada de pip install enquanto apenas o código mudar. Isso reduz drasticamente o tempo de build em pipelines de CI/CD (Chronos pipeline, por exemplo).

5. Instalação de dependências isolada
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt
--no-cache-dir: não armazena cache do pip na imagem, mantendo-a menor.
--prefix=/install: instala em diretório separado para facilitar o COPY --from=builder, sem misturar com o Python do sistema.
--upgrade pip: garante que vulnerabilidades conhecidas no pip em si sejam corrigidas antes da instalação.
6. Labels OCI
LABEL org.opencontainers.image.title="lift" \
      org.opencontainers.image.description="..." \
      org.opencontainers.image.vendor="Hill Valley Tech"
Por quê? Labels OCI padronizados permitem que ferramentas de inventário (Harbor, Trivy, Beacon) identifiquem e cataloguem a imagem automaticamente. Obrigatório para rastreabilidade em ambientes Kubernetes com múltiplos serviços (Chronos, Ledger, Reactor, Beacon, Lift).

7. Variáveis de ambiente sensíveis sem valores padrão
ENV DATABASE_URL="" \
    API_KEY=""
Por quê? As variáveis são declaradas sem valor para documentar explicitamente que são obrigatórias em runtime, mas jamais embutidas na imagem. Os valores reais devem ser injetados pelo Kubernetes via Secret (para API_KEY) e ConfigMap ou Secret (para DATABASE_URL).

Regra de segurança: nenhuma credencial ou string de conexão pode residir em uma imagem Docker — ela seria visível em qualquer registry e em docker inspect.

8. Usuário não-root
RUN groupadd --gid 1001 appgroup \
    && useradd --uid 1001 --gid appgroup --no-create-home --shell /sbin/nologin appuser
...
USER appuser
Por quê? Rodar como root dentro do container é uma vulnerabilidade crítica: se um atacante escapar do isolamento, terá privilégios de root no host. Boas práticas de CIS Kubernetes Benchmark e PSP/PSA exigem runAsNonRoot: true.

--no-create-home: não cria home directory desnecessário.
--shell /sbin/nologin: impede login interativo mesmo se o usuário for comprometido.
UID/GID fixos (1001): necessários para que o manifest Kubernetes possa declarar runAsUser: 1001 no securityContext.
9. Separação de responsabilidades no COPY
COPY --chown=appuser:appgroup app.py         ./app.py
COPY --chown=appuser:appgroup requirements.txt ./requirements.txt
COPY --chown=appuser:appgroup lib/            ./lib/
Por quê?

O diretório tests/ é excluído intencionalmente: código de teste não pertence a imagens de produção — aumenta superfície, tamanho e pode expor fixtures com dados sensíveis.
--chown garante que os arquivos já pertençam ao appuser ao serem copiados, sem a necessidade de um RUN chown extra (que criaria uma camada adicional).
10. Permissões restritivas no filesystem
RUN chmod -R 550 /app
Por quê? 550 = dono pode ler/executar, grupo pode ler/executar, outros não têm acesso. O container não precisa escrever em /app durante a execução — qualquer escrita inesperada pode indicar uma tentativa de comprometimento ou erro de configuração. Alinha-se com o princípio do menor privilégio.

11. HEALTHCHECK nativo
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" \
    || exit 1
Por quê? O Kubernetes usa seu próprio livenessProbe/readinessProbe, mas o HEALTHCHECK do Docker serve como fallback em execuções locais e em ambientes Docker Compose (útil para o time do Lift durante desenvolvimento). Parâmetros escolhidos:

Parâmetro	Valor	Razão
--interval	30s	Frequência razoável sem sobrecarregar o processo
--timeout	5s	Falha rápida em caso de deadlock
--start-period	10s	Tempo para o gunicorn iniciar todos os workers antes de checar
--retries	3	Tolerância a falhas transitórias antes de marcar como unhealthy
Usa urllib.request da stdlib para evitar dependência de curl ou wget (não presentes no slim).

12. ENTRYPOINT + CMD separados
ENTRYPOINT ["gunicorn"]
CMD ["--bind", "0.0.0.0:8080", "--workers", "4", "app:app"]
Por quê?

ENTRYPOINT define o processo principal imutável (gunicorn).
CMD fornece os argumentos padrão, que podem ser sobrescritos em tempo de execução (e.g. docker run lift --workers 2 app:app ou via args: no manifest Kubernetes) sem precisar alterar a imagem.
Formato exec (["..."]) em vez de shell ("...") garante que o processo receba os sinais do SO (SIGTERM, SIGINT) diretamente — fundamental para graceful shutdown no Kubernetes.
Resumo das práticas de segurança aplicadas
Prática	Implementada?
Multi-stage (sem ferramentas de build no runtime)	✅
Imagem base slim (superfície mínima)	✅
Usuário não-root com UID fixo	✅
Nenhuma credencial na imagem	✅
Arquivos de teste excluídos	✅
Filesystem com permissões mínimas	✅
Processo com recepção direta de sinais (exec form)	✅
Cache de pip desabilitado	✅
Labels OCI para rastreabilidade	✅
Healthcheck documentado	✅
 
