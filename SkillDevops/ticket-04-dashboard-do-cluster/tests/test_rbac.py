"""RBAC de exemplo e de laboratório: só get/list/watch, sem curingas (tarefas 6.1 e 6.2)."""

import re
from pathlib import Path

import pytest
import yaml

RAIZ = Path(__file__).resolve().parent.parent
EXEMPLO = RAIZ / "deploy" / "rbac" / "clusterrole-somente-leitura.yaml"
LAB = sorted((RAIZ / "deploy" / "lab").glob("*.yaml"))
VERBOS_PERMITIDOS = {"get", "list", "watch"}

RECURSOS_DO_PAINEL = {
    ("", "namespaces"), ("", "pods"), ("", "services"), ("", "events"),
    ("apps", "deployments"), ("discovery.k8s.io", "endpointslices"),
}


def papeis(arquivo):
    with open(arquivo, encoding="utf-8") as f:
        return [d for d in yaml.safe_load_all(f) if d and d["kind"] in ("ClusterRole", "Role")]


def recursos(papel):
    return {(g, r) for regra in papel["rules"]
            for g in regra["apiGroups"] for r in regra["resources"]}


@pytest.mark.parametrize("arquivo", [EXEMPLO, *LAB], ids=lambda p: p.name)
def test_somente_get_list_watch_sem_curinga(arquivo):
    encontrados = papeis(arquivo)
    assert encontrados, f"{arquivo} deveria conter um papel"
    for papel in encontrados:
        for regra in papel["rules"]:
            assert set(regra["verbs"]) <= VERBOS_PERMITIDOS, regra
            for campo in ("verbs", "resources", "apiGroups"):
                assert "*" not in regra[campo], (campo, regra)
            assert not regra.get("nonResourceURLs"), regra


def test_exemplo_cobre_exatamente_os_recursos_do_painel():
    (papel,) = papeis(EXEMPLO)
    assert papel["kind"] == "ClusterRole"
    assert recursos(papel) == RECURSOS_DO_PAINEL


def test_exemplo_explica_o_verbo_watch():
    texto = EXEMPLO.read_text(encoding="utf-8")
    assert "watch" in texto and "NÃO abre watch" in texto
    assert "test_somente_leitura.py" in texto


def test_lab_sem_eventos_nega_so_eventos():
    (papel,) = papeis(RAIZ / "deploy" / "lab" / "sem-eventos.yaml")
    assert recursos(papel) == RECURSOS_DO_PAINEL - {("", "events")}


def test_lab_so_um_namespace_nao_lista_namespaces():
    (papel,) = papeis(RAIZ / "deploy" / "lab" / "so-um-namespace.yaml")
    assert papel["kind"] == "Role" and papel["metadata"]["namespace"] == "nyx-prod"
    assert recursos(papel) == RECURSOS_DO_PAINEL - {("", "namespaces")}


def test_nenhum_script_do_projeto_aplica_manifestos():
    scripts = [p for p in RAIZ.rglob("*")
               if p.suffix in (".py", ".sh", ".ps1", ".bat", ".cmd")
               and not any(parte.startswith(".") for parte in p.relative_to(RAIZ).parts)]
    for script in scripts:
        texto = script.read_text(encoding="utf-8", errors="replace")
        assert not re.search(r"kubectl\s+(apply|create|delete|patch|replace|edit)", texto), script
