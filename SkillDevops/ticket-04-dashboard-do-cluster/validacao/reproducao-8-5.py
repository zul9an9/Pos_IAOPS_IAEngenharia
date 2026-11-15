"""Reprodução OFFLINE do cenário 8.5 (permissão negada para um tipo de recurso).

Não é a captura da tela do laboratório: usa o código do painel e as fixtures
congeladas de tests/fixtures/, com uma camada de acesso falsa em que só a
listagem de eventos devolve 403 (o que a ServiceAccount de
deploy/lab/sem-eventos.yaml recebe do apiserver). Serve para conferir o texto
exato que o painel mostra e as contagens por bloco, sem depender do cluster.

Uso, na raiz do projeto:
    python validacao/reproducao-8-5.py
"""

import html
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tests"))
sys.path.insert(0, str(RAIZ))

from conftest import AcessoFalso, ContextoFalso  # noqa: E402
from painel_cluster import coleta, erros, render  # noqa: E402
from painel_cluster.erros import ErroPainel  # noqa: E402


def texto(trecho_html):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", trecho_html))).strip()


def main():
    # O 403 que a ServiceAccount sem `events` recebe ao listar eventos do namespace.
    acesso = AcessoFalso(falhas={"list_namespaced_event": ErroPainel(erros.SEM_PERMISSAO, recurso="events")})
    relogio = lambda: datetime(2026, 9, 27, 22, 0, tzinfo=timezone.utc)  # noqa: E731
    resultado = coleta.coletar(acesso, ContextoFalso(nome="painel"), "nyx-prod", relogio=relogio)
    pagina = render.pagina(resultado)

    print("Namespace selecionado: nyx-prod | contexto: painel | erro global:", resultado.erro_global)
    print("Estado por bloco:", {n: getattr(resultado, n).estado
                                for n in ("pods", "deployments", "services", "eventos")})
    print("Linhas por bloco:", {n: len(getattr(resultado, n).itens)
                                for n in ("pods", "deployments", "services")})
    print("Aviso de somente leitura na tela:", render.AVISO_SOMENTE_LEITURA in pagina)
    print()
    for secao in re.findall(r"<section[^>]*>.*?</section>", pagina, re.S):
        t = texto(secao)
        if t.startswith(("Pods", "Deployments", "Services")):
            print("--", t.split()[0])
            for linha in re.findall(r"<tr[^>]*data-nome[^>]*>.*?</tr>", secao, re.S):
                print("   ", texto(linha))
        elif t.startswith("Eventos"):
            print("-- Bloco de eventos (texto exato):")
            print("   ", t)


if __name__ == "__main__":
    main()
