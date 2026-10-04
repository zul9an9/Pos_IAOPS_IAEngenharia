"""Páginas: aviso, escape, mensagens, busca e ausência de juízo de saúde.

Tarefas 2.1 e 2.3 (parte de tela), 3.6, 5.2, 5.3 e 5.4.
"""

import re
from datetime import datetime, timezone

import pytest
from conftest import AcessoFalso, ContextoFalso

from painel_cluster import coleta, erros, render, traducao
from painel_cluster.coleta import Bloco, Coleta
from painel_cluster.erros import ErroPainel

AGORA = datetime(2026, 9, 27, 22, 0, tzinfo=timezone.utc)
NAMESPACES = ("nyx-prod", "nyx-stg", "orion-prod", "orion-stg", "kube-public")


def pagina_de(namespace=None, falhas=None, contexto=None):
    resultado = coleta.coletar(AcessoFalso(falhas), contexto or ContextoFalso(), namespace,
                               relogio=lambda: AGORA)
    return render.pagina(resultado)


def coleta_global(categoria):
    return Coleta(contexto=ContextoFalso(), carimbo=AGORA, erro_global=ErroPainel(categoria))


def todas_as_paginas():
    paginas = {f"coleta-{ns}": pagina_de(ns) for ns in NAMESPACES}
    paginas["coleta-todos"] = pagina_de()
    paginas["nao-respondeu"] = render.pagina(coleta_global(erros.NAO_RESPONDEU))
    paginas["credencial"] = render.pagina(coleta_global(erros.CREDENCIAL))
    paginas["sem-contexto"] = render.pagina_kubeconfig(
        ErroPainel(erros.SEM_CONTEXTO, caminho="C:/kube/config"), AGORA)
    for tipo in (erros.INEXISTENTE, erros.ILEGIVEL, erros.MALFORMADO):
        paginas[f"kubeconfig-{tipo}"] = render.pagina_kubeconfig(
            ErroPainel(erros.KUBECONFIG_INVALIDO, caminho="C:/kube/config", tipo=tipo,
                       motivo="o arquivo não é YAML válido"), AGORA)
    paginas["namespace-invalido"] = render.pagina_namespace_invalido(
        ContextoFalso(), "Nyx_Prod", AGORA)
    paginas["inesperada"] = render.pagina_inesperada(AGORA)
    paginas["405"] = render.pagina_simples(AGORA, "Método não permitido", "Só GET.")
    paginas["eventos-negados"] = pagina_de(
        "nyx-prod", {"list_namespaced_event": ErroPainel(erros.SEM_PERMISSAO, recurso="events")})
    return paginas


PAGINAS = todas_as_paginas()


# --- 5.2 aviso e estrutura ------------------------------------------------------

@pytest.mark.parametrize("nome", sorted(PAGINAS))
def test_aviso_de_somente_leitura_em_toda_tela(nome):
    assert 'id="aviso-somente-leitura"' in PAGINAS[nome]
    assert render.e(render.AVISO_SOMENTE_LEITURA) in PAGINAS[nome]


@pytest.mark.parametrize("nome", sorted(PAGINAS))
def test_nenhuma_tela_mostra_stack_trace(nome):
    pagina = PAGINAS[nome]
    for proibido in ("Traceback", "Exception", "ErroPainel", "ApiException", 'File "'):
        assert proibido not in pagina, (nome, proibido)


def test_cabecalho_com_contexto_servidor_e_carimbo():
    pagina = PAGINAS["coleta-nyx-prod"]
    assert "kind-metacortex-lab" in pagina and "https://127.0.0.1:6443" in pagina
    assert render.formatar_carimbo(AGORA.astimezone()) in pagina  # fuso local


# --- 2.1 sem seletor de contexto --------------------------------------------------

def test_nao_existe_seletor_de_contexto():
    pagina = PAGINAS["coleta-todos"]
    assert pagina.count("<select") == 1 and '<select name="ns">' in pagina
    assert not re.search(r'name="(context|contexto|cluster)"', pagina)


# --- 5.2 escape ----------------------------------------------------------------

def test_mensagem_de_evento_com_script_sai_escapada():
    maliciosa = "<script>alert(1)</script>"
    evento = {"metadata": {"name": "e"}, "type": "Warning", "reason": "Teste",
              "message": maliciosa, "count": 1,
              "involvedObject": {"kind": "Pod", "name": "p"}}
    resultado = Coleta(contexto=ContextoFalso(), carimbo=AGORA, namespace="x",
                       namespaces=Bloco(itens=["x"]),
                       eventos=Bloco(itens=traducao.eventos([evento])))
    pagina = render.pagina(resultado)
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in pagina
    assert maliciosa not in pagina
    # único <script> da página é o script estático de busca
    assert pagina.count("<script>") == 1


def test_aspas_em_atributo_nao_encerram_o_atributo():
    nome = 'x" onmouseover="alert(1)'
    pod = {"metadata": {"name": nome, "namespace": "ns'q"}, "status": {"phase": "Running"}}
    resultado = Coleta(contexto=ContextoFalso(nome='ctx"<b>'), carimbo=AGORA,
                       namespaces=Bloco(itens=[nome]),
                       pods=Bloco(itens=[traducao.pod(pod)]))
    pagina = render.pagina(resultado)
    assert 'onmouseover="alert(1)' not in pagina
    assert "x&quot; onmouseover=&quot;alert(1)" in pagina
    assert "ns&#x27;q" in pagina
    assert "ctx&quot;&lt;b&gt;" in pagina


def test_namespace_digitado_e_escapado_ao_reapresentar():
    pagina = render.pagina_namespace_invalido(ContextoFalso(), '"><script>x</script>', AGORA)
    assert "<script>x</script>" not in pagina
    assert "&quot;&gt;&lt;script&gt;" in pagina


# --- 5.3 filtro e busca ---------------------------------------------------------

def test_busca_filtra_no_navegador_sem_nova_coleta():
    pagina = PAGINAS["coleta-todos"]
    busca = re.search(r"<input[^>]*id=\"busca\"[^>]*>", pagina).group(0)
    assert "name=" not in busca, "a busca não pode ser enviada ao servidor"
    formulario = re.search(r"<form.*?</form>", pagina, re.S).group(0)
    assert 'id="busca"' not in formulario
    for proibido in ("fetch", "XMLHttpRequest", "location", "setInterval", "setTimeout"):
        assert proibido not in render.SCRIPT_BUSCA


def test_linhas_tem_nome_para_busca():
    pagina = PAGINAS["coleta-nyx-prod"]
    assert 'data-nome="nyx-postgres' in pagina
    assert pagina.count("data-nome=") > 5


def test_filtro_reduz_a_lista():
    todos = PAGINAS["coleta-todos"].count("<tr data-nome=")
    um = PAGINAS["coleta-nyx-prod"].count("<tr data-nome=")
    assert 0 < um < todos + 10  # nyx-prod inclui eventos, ausentes em "todos"
    pods_todos = pagina_de().split('id="pods"')[1].split("</section>")[0].count("<tr data-nome=")
    pods_um = pagina_de("nyx-prod").split('id="pods"')[1].split("</section>")[0] \
        .count("<tr data-nome=")
    assert 0 < pods_um < pods_todos


# --- 5.4 mensagens por categoria --------------------------------------------------

def test_nao_respondeu_e_credencial_tem_textos_distintos():
    assert "O cluster não respondeu" in PAGINAS["nao-respondeu"]
    assert "Credencial recusada ou expirada" in PAGINAS["credencial"]
    assert "Credencial recusada" not in PAGINAS["nao-respondeu"]
    assert "não respondeu" not in PAGINAS["credencial"]
    assert "https://127.0.0.1:6443" in PAGINAS["nao-respondeu"]
    assert "27/09/2026 22:00:00" in PAGINAS["nao-respondeu"]


def test_sem_contexto_e_kubeconfig_invalido_tem_textos_distintos():
    sem = PAGINAS["sem-contexto"]
    assert "Nenhum contexto corrente no kubeconfig" in sem
    assert "Não foi possível carregar o kubeconfig" not in sem
    for tipo, rotulo in (("inexistente", "inexistente"), ("ilegível", "ilegível"),
                         ("malformado", "malformado")):
        pagina = PAGINAS[f"kubeconfig-{tipo}"]
        assert "Não foi possível carregar o kubeconfig" in pagina
        assert f"arquivo {rotulo}" in pagina and "C:/kube/config" in pagina
        assert "O arquivo não é YAML válido." in pagina
        assert "Nenhum contexto corrente" not in pagina


def test_sem_permissao_so_no_bloco_negado():
    pagina = PAGINAS["eventos-negados"]
    eventos = pagina.split('id="eventos"')[1].split("</section>")[0]
    assert "sem permissão para listar eventos" in eventos
    for bloco in ("pods", "deployments", "services"):
        trecho = pagina.split(f'id="{bloco}"')[1].split("</section>")[0]
        assert "<table>" in trecho and "sem permissão" not in trecho


def test_vazio_e_visualmente_distinto_de_erro():
    pagina = PAGINAS["coleta-kube-public"]
    for bloco in ("pods", "deployments", "services", "eventos"):
        trecho = pagina.split(f'id="{bloco}"')[1].split("</section>")[0]
        assert 'class="estado vazio"' in trecho
        assert "estado erro" not in trecho and "sem-permissao" not in trecho


def test_namespaces_negados_mostram_campo_de_digitacao():
    contexto = ContextoFalso(namespace="nyx-prod")
    pagina = pagina_de(None, {"list_namespace": ErroPainel(erros.SEM_PERMISSAO,
                                                           recurso="namespaces")}, contexto)
    assert "sem permissão para listar namespaces" in pagina
    assert '<input type="text" name="ns" value="nyx-prod"' in pagina
    pods = pagina.split('id="pods"')[1].split("</section>")[0]
    assert "<table>" in pods


def test_nota_de_retencao_de_eventos():
    assert render.e(render.NOTA_EVENTOS) in PAGINAS["coleta-nyx-prod"]


# --- 3.6 sem juízo de saúde ------------------------------------------------------

@pytest.mark.parametrize("nome", sorted(PAGINAS))
def test_nenhum_termo_de_juizo_de_saude(nome):
    pagina = PAGINAS[nome]
    texto = re.sub(r"<style>.*?</style>|<script>.*?</script>", "", pagina, flags=re.S)
    assert not re.search(r"saudáve(l|is)|healthy|unhealthy|✓|✔|\bOK\b", texto, re.I), nome
