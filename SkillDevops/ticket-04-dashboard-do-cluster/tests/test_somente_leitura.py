"""Garantia de só leitura, camadas 1 e 2 (design.md, D5).

Varre com `ast` todos os .py do projeto (inclusive a camada de acesso e os
demais testes), exceto este arquivo, e falha com arquivo:linha ao encontrar
identificador de escrita, execução, watch, `kubectl` como subprocesso ou
import do cliente `kubernetes` fora da camada de acesso.

Diretórios ignorados: os que começam com "." (.venv, .claude, .git, caches)
e __pycache__. Nenhum deles contém código do painel.
"""

import ast
import textwrap
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
ESTE_ARQUIVO = Path(__file__).resolve()
CAMADA_DE_ACESSO = RAIZ / "painel_cluster" / "acesso.py"

PREFIXOS_PROIBIDOS = ("create_", "patch_", "replace_", "delete_", "connect_")
METODOS_DE_ESCRITA = {"POST", "PUT", "PATCH", "DELETE"}
FUNCOES_DE_PROCESSO = {"run", "Popen", "call", "check_call", "check_output",
                       "system", "popen", "getoutput", "getstatusoutput"}


def _nome(func):
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return ""


def _textos(no):
    return [n.value for n in ast.walk(no)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)]


def _modulo_kubernetes(nome):
    return nome == "kubernetes" or nome.startswith("kubernetes.")


def _proibido_em_kubernetes(nome):
    return nome.startswith(("kubernetes.stream", "kubernetes.watch"))


def varrer(arquivo, camada_de_acesso=CAMADA_DE_ACESSO):
    """Devolve [(arquivo, linha, motivo)] para cada violação."""
    arvore = ast.parse(Path(arquivo).read_text(encoding="utf-8"), filename=str(arquivo))
    e_camada = Path(arquivo).resolve() == Path(camada_de_acesso).resolve()
    violacoes = []

    def violou(no, motivo):
        violacoes.append((str(arquivo), no.lineno, motivo))

    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            for alias in no.names:
                if _proibido_em_kubernetes(alias.name):
                    violou(no, f"import de {alias.name}")
                elif _modulo_kubernetes(alias.name) and not e_camada:
                    violou(no, "import do cliente kubernetes fora da camada de acesso")
        elif isinstance(no, ast.ImportFrom) and no.module:
            if _proibido_em_kubernetes(no.module):
                violou(no, f"import de {no.module}")
            elif no.module == "kubernetes" and {a.name for a in no.names} & {"stream", "watch"}:
                violou(no, "import de kubernetes.stream/kubernetes.watch")
            elif _modulo_kubernetes(no.module) and not e_camada:
                violou(no, "import do cliente kubernetes fora da camada de acesso")
        elif isinstance(no, ast.Attribute):
            if no.attr == "Watch" and _nome(no.value) == "watch":
                violou(no, "uso de watch.Watch")
            if no.attr in ("stream", "watch") and _nome(no.value) == "kubernetes":
                violou(no, f"uso de kubernetes.{no.attr}")
        elif isinstance(no, ast.Call):
            nome = _nome(no.func)
            if nome.startswith(PREFIXOS_PROIBIDOS):
                violou(no, f"chamada de escrita/execução {nome}")
            for kw in no.keywords:
                if kw.arg == "watch" and isinstance(kw.value, ast.Constant) \
                        and kw.value.value is True:
                    violou(no, "argumento watch=True")
            if nome in ("call_api", "request"):
                if any(t.upper() in METODOS_DE_ESCRITA for t in _textos(no)):
                    violou(no, f"{nome} com método de escrita")
            if nome in FUNCOES_DE_PROCESSO or _nome(getattr(no.func, "value", None)) == "subprocess":
                if any("kubectl" in t for t in _textos(no)):
                    violou(no, "kubectl executado como subprocesso")
    return violacoes


def arquivos_do_projeto(raiz=RAIZ):
    for caminho in sorted(raiz.rglob("*.py")):
        relativo = caminho.relative_to(raiz)
        if any(p.startswith(".") or p == "__pycache__" for p in relativo.parts[:-1]):
            continue
        if caminho.resolve() == ESTE_ARQUIVO:
            continue
        yield caminho


def test_projeto_nao_tem_escrita_nem_watch():
    arquivos = list(arquivos_do_projeto())
    assert CAMADA_DE_ACESSO in arquivos, "a camada de acesso precisa ser varrida"
    violacoes = [v for arq in arquivos for v in varrer(arq)]
    assert not violacoes, "\n".join(f"{a}:{l}: {m}" for a, l, m in violacoes)


PLANTADOS = {
    "delete_namespaced_pod": """
        def limpar(api):
            api.delete_namespaced_pod("x", "default")
    """,
    "watch.Watch": """
        from painel_cluster import acesso as watch
        def observar():
            return watch.Watch()
    """,
    "watch=True": """
        def listar(api):
            return api.list_namespaced_pod("default", watch=True)
    """,
    "kubectl": """
        import subprocess
        subprocess.run(["kubectl", "delete", "pod", "x"])
    """,
    "call_api": """
        def cru(api):
            return api.call_api("/api/v1/namespaces", "POST")
    """,
    "import": """
        from kubernetes import client
    """,
}


@pytest.mark.parametrize("caso", sorted(PLANTADOS))
def test_varredura_detecta_arquivo_plantado(tmp_path, caso):
    plantado = tmp_path / f"plantado_{caso.replace('.', '_').replace('=', '_')}.py"
    plantado.write_text(textwrap.dedent(PLANTADOS[caso]), encoding="utf-8")
    violacoes = varrer(plantado)
    assert violacoes, f"a varredura deveria detectar {caso}"
    arquivo, linha, _ = violacoes[0]
    assert arquivo == str(plantado) and linha >= 1


def test_camada_de_acesso_exporta_so_listagens():
    from painel_cluster import acesso

    publicos = {nome for nome in dir(acesso.AcessoLeitura)
                if not nome.startswith("_") and callable(getattr(acesso.AcessoLeitura, nome))}
    assert publicos == set(acesso.OPERACOES_PERMITIDAS)
    assert all(nome.startswith("list_") for nome in acesso.OPERACOES_PERMITIDAS)
