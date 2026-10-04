"""Renderização HTML. Único lugar do projeto que monta HTML.

Todo texto externo (API, kubeconfig, entrada de quem opera) passa por `e()`,
que é `html.escape(..., quote=True)`, e por isso é seguro tanto no corpo
quanto em valores de atributo. Nenhum texto externo entra em <script>.
"""

import base64
import hashlib
import html
from urllib.parse import quote

from . import erros

AVISO_SOMENTE_LEITURA = ("Somente leitura: este painel só lê o cluster e não altera nada nele.")
NOTA_EVENTOS = ("A API retém eventos por tempo limitado (padrão do Kubernetes: 1 hora); "
                "eventos mais antigos não aparecem aqui.")

RECURSOS = {"namespaces": "namespaces", "pods": "pods", "deployments": "deployments",
            "services": "services", "endpointslices": "endpointslices", "events": "eventos"}

TIPOS_KUBECONFIG = {erros.INEXISTENTE: "inexistente", erros.ILEGIVEL: "ilegível",
                    erros.MALFORMADO: "malformado"}


def e(valor):
    return html.escape("" if valor is None else str(valor), quote=True)


def _frase(texto):
    """Primeira letra maiúscula e ponto final, sem mexer no resto (ex.: YAML)."""
    texto = (texto or "").strip()
    return texto[:1].upper() + texto[1:] + "." if texto else ""


def formatar_carimbo(carimbo):
    return carimbo.strftime("%d/%m/%Y %H:%M:%S (UTC%z)")


# Script estático de busca: filtra as linhas já coletadas, sem nova consulta.
SCRIPT_BUSCA = """
(function () {
  var seletor = document.querySelector('select[name=ns]');
  if (seletor) {
    seletor.addEventListener('change', function () { seletor.form.submit(); });
  }
  var busca = document.getElementById('busca');
  if (!busca) { return; }
  busca.addEventListener('input', function () {
    var termo = busca.value.trim().toLowerCase();
    document.querySelectorAll('tr[data-nome]').forEach(function (tr) {
      tr.hidden = termo !== '' && tr.getAttribute('data-nome').indexOf(termo) === -1;
    });
    document.querySelectorAll('section.bloco').forEach(function (secao) {
      var contagem = secao.querySelector('.contagem');
      if (!contagem) { return; }
      var total = secao.querySelectorAll('tr[data-nome]').length;
      var visiveis = secao.querySelectorAll('tr[data-nome]:not([hidden])').length;
      contagem.textContent = termo === '' ? String(total) : visiveis + ' de ' + total;
    });
  });
})();
"""
HASH_SCRIPT = base64.b64encode(hashlib.sha256(SCRIPT_BUSCA.encode("utf-8")).digest()).decode()
CSP = ("default-src 'none'; style-src 'unsafe-inline'; "
       f"script-src 'sha256-{HASH_SCRIPT}'; form-action 'self'; base-uri 'none'; "
       "frame-ancestors 'none'")

ESTILO = """
:root { --fundo:#f7f7f5; --superficie:#ffffff; --texto:#1d1d1b; --suave:#5f5f5a;
  --borda:#d9d9d4; --destaque:#1f4e79; --aviso-fundo:#fff4d6; --aviso-borda:#c99a1a;
  --erro-fundo:#fbe4e1; --erro-borda:#b3412e; --vazio-fundo:#eeeeea; }
@media (prefers-color-scheme: dark) { :root { --fundo:#161614; --superficie:#1f1f1c;
  --texto:#ecece8; --suave:#a3a39c; --borda:#3a3a35; --destaque:#8cb8e0;
  --aviso-fundo:#3a3014; --aviso-borda:#c99a1a; --erro-fundo:#3d1d18;
  --erro-borda:#e07a66; --vazio-fundo:#2a2a26; } }
* { box-sizing:border-box; }
body { margin:0; background:var(--fundo); color:var(--texto);
  font:14px/1.45 system-ui, -apple-system, "Segoe UI", sans-serif; }
header { background:var(--superficie); border-bottom:1px solid var(--borda); padding:12px 16px; }
h1 { font-size:18px; margin:0 0 6px; }
.somente-leitura { display:inline-block; background:var(--aviso-fundo);
  border:1px solid var(--aviso-borda); border-radius:4px; padding:4px 8px; font-weight:600; }
.meta { color:var(--suave); margin-top:6px; overflow-wrap:anywhere; }
.meta strong { color:var(--texto); }
main { padding:16px; max-width:1400px; margin:0 auto; }
.controles { display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin-bottom:16px; }
.controles form { display:flex; flex-wrap:wrap; gap:8px; align-items:center; }
select, input, button { font:inherit; padding:5px 8px; border:1px solid var(--borda);
  border-radius:4px; background:var(--superficie); color:var(--texto); }
button { cursor:pointer; background:var(--destaque); color:var(--superficie); border-color:var(--destaque); }
.bloco { background:var(--superficie); border:1px solid var(--borda); border-radius:6px;
  padding:12px; margin-bottom:16px; overflow-x:auto; }
.bloco h2 { font-size:15px; margin:0 0 8px; }
.contagem { color:var(--suave); font-weight:normal; }
table { border-collapse:collapse; width:100%; }
th, td { text-align:left; padding:4px 8px; border-top:1px solid var(--borda); vertical-align:top; }
th { color:var(--suave); font-weight:600; border-top:none; }
td.num { text-align:right; font-variant-numeric:tabular-nums; }
.estado { padding:8px 10px; border-radius:4px; border:1px solid var(--borda); }
.vazio { background:var(--vazio-fundo); font-style:italic; }
.aviso, .sem-permissao { background:var(--aviso-fundo); border-color:var(--aviso-borda); }
.erro { background:var(--erro-fundo); border-color:var(--erro-borda); }
.nota { color:var(--suave); font-size:12px; margin-top:8px; }
.falha-global { background:var(--superficie); border:1px solid var(--erro-borda);
  border-left:6px solid var(--erro-borda); border-radius:6px; padding:12px 16px; }
.falha-global h2 { margin-top:0; font-size:16px; }
ul.namespaces { list-style:none; padding:0; margin:0; display:flex; flex-wrap:wrap; gap:6px; }
ul.namespaces a { color:var(--destaque); }
code { overflow-wrap:anywhere; }
"""


# --------------------------------------------------------------------------
# estrutura comum
# --------------------------------------------------------------------------

def _documento(cabecalho, corpo):
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Painel do cluster</title>
<style>{ESTILO}</style>
</head>
<body>
{cabecalho}
<main>
{corpo}
</main>
<script>{SCRIPT_BUSCA}</script>
</body>
</html>
"""


def _cabecalho(contexto, carimbo, rotulo_carimbo="Coleta"):
    linhas = []
    if contexto is not None:
        linhas.append(f'<div class="meta">Contexto <strong>{e(contexto.nome)}</strong> · '
                      f'servidor <code>{e(contexto.servidor)}</code></div>')
    linhas.append(f'<div class="meta">{e(rotulo_carimbo)}: <strong id="carimbo">'
                  f'{e(formatar_carimbo(carimbo))}</strong></div>')
    return f"""<header>
<h1>Painel do cluster</h1>
<div class="somente-leitura" id="aviso-somente-leitura">{e(AVISO_SOMENTE_LEITURA)}</div>
{"".join(linhas)}
</header>"""


def _controles(namespaces=None, selecionado=None, negados=False, valor_digitado=None):
    """Seletor de namespace (gatilho de coleta) e busca por nome (sem coleta)."""
    if negados or namespaces is None:
        valor = valor_digitado if valor_digitado is not None else (selecionado or "")
        aviso = ('<span class="estado sem-permissao">sem permissão para listar namespaces</span>'
                 if negados else "")
        seletor = (f'{aviso}<label>Namespace <input type="text" name="ns" value="{e(valor)}" '
                   'placeholder="nome do namespace" maxlength="63" autocomplete="off"></label>')
    else:
        opcoes = ['<option value="">todos os namespaces</option>']
        for nome in namespaces:
            marcado = " selected" if nome == selecionado else ""
            opcoes.append(f'<option value="{e(nome)}"{marcado}>{e(nome)}</option>')
        seletor = ('<label>Namespace <select name="ns">'
                   f'{"".join(opcoes)}</select></label>')
    return f"""<div class="controles">
<form method="get" action="/">{seletor}<button type="submit">Atualizar</button></form>
<label>Buscar por nome <input type="search" id="busca" placeholder="filtra a coleta exibida" autocomplete="off"></label>
</div>"""


def _falha_global(titulo, paragrafos):
    corpo = "".join(f"<p>{p}</p>" for p in paragrafos)
    return f'<section class="falha-global" role="alert"><h2>{e(titulo)}</h2>{corpo}</section>'


# --------------------------------------------------------------------------
# blocos
# --------------------------------------------------------------------------

def _estado_bloco(bloco, rotulo, namespace):
    if bloco.estado == "aviso":
        return f'<p class="estado aviso">{e(bloco.aviso)}</p>'
    if bloco.estado == "vazio":
        onde = "neste namespace" if namespace else "no cluster"
        return f'<p class="estado vazio">Nenhum item de {e(rotulo)} {onde}.</p>'
    erro = bloco.erro
    recurso = RECURSOS.get(erro.recurso, erro.recurso or rotulo)
    if erro.categoria == erros.SEM_PERMISSAO:
        return f'<p class="estado sem-permissao">sem permissão para listar {e(recurso)}</p>'
    if erro.categoria == erros.NAO_RESPONDEU:
        texto = f"O cluster não respondeu ao listar {recurso}."
    elif erro.categoria == erros.CREDENCIAL:
        texto = f"A credencial foi recusada ao listar {recurso}."
    else:
        texto = (f"Erro inesperado ao listar {recurso}. "
                 "O detalhe técnico foi registrado no log local do painel.")
    return f'<p class="estado erro">{e(texto)}</p>'


def _tabela(colunas, linhas, chave_busca):
    cabecalho = "".join(f"<th>{e(titulo)}</th>" for titulo, _, _ in colunas)
    corpo = []
    for linha in linhas:
        celulas = "".join(
            f'<td{" class=num" if numerica else ""}>{e(linha[chave])}</td>'
            for _, chave, numerica in colunas)
        corpo.append(f'<tr data-nome="{e(str(linha[chave_busca]).lower())}">{celulas}</tr>')
    return f"<table><thead><tr>{cabecalho}</tr></thead><tbody>{''.join(corpo)}</tbody></table>"


def _bloco(identificador, titulo, bloco, namespace, colunas, chave_busca="nome", nota=None):
    if bloco.estado == "dados":
        conteudo = _tabela(colunas, bloco.itens, chave_busca)
        contagem = f' <span class="contagem">{len(bloco.itens)}</span>'
    else:
        conteudo = _estado_bloco(bloco, identificador, namespace)
        contagem = ""
    extra = f'<p class="nota">{e(nota)}</p>' if nota else ""
    return (f'<section class="bloco" id="{identificador}"><h2>{e(titulo)}{contagem}</h2>'
            f"{conteudo}{extra}</section>")


def _bloco_namespaces(coleta):
    bloco = coleta.namespaces
    if bloco.estado == "dados":
        itens = "".join(f'<li><a href="/?ns={e(quote(nome))}">{e(nome)}</a></li>'
                        for nome in bloco.itens)
        conteudo = f'<ul class="namespaces">{itens}</ul>'
        contagem = f' <span class="contagem-ns">{len(bloco.itens)}</span>'
    else:
        conteudo, contagem = _estado_bloco(bloco, "namespaces", None), ""
    return f'<section class="bloco" id="namespaces"><h2>Namespaces{contagem}</h2>{conteudo}</section>'


COLUNAS_PODS = [("Namespace", "namespace", False), ("Nome", "nome", False),
                ("Fase", "fase", False), ("Prontos", "prontos", False),
                ("Reinícios", "reinicios", True), ("Motivo", "motivo", False)]
COLUNAS_DEPLOYMENTS = [("Namespace", "namespace", False), ("Nome", "nome", False),
                       ("Prontas/desejadas", "prontas", False)]
COLUNAS_SERVICES = [("Namespace", "namespace", False), ("Nome", "nome", False),
                    ("Tipo", "tipo", False), ("Cluster IP", "cluster_ip", False),
                    ("Portas", "portas", False), ("Endpoint", "endpoint", False)]
COLUNAS_EVENTOS = [("Última", "ultima", False), ("Primeira", "primeira", False),
                   ("Contagem", "contagem", True), ("Tipo", "tipo", False),
                   ("Razão", "razao", False), ("Objeto", "objeto_tipo", False),
                   ("Nome do objeto", "objeto_nome", False), ("Mensagem", "mensagem", False)]


# --------------------------------------------------------------------------
# páginas
# --------------------------------------------------------------------------

def pagina(coleta):
    """Página de uma coleta, inclusive quando ela terminou em erro global."""
    contexto = coleta.contexto
    if coleta.erro_global is not None:
        return _documento(_cabecalho(contexto, coleta.carimbo, "Tentativa"),
                          _controles(None, coleta.namespace) +
                          corpo_erro_global(coleta.erro_global, contexto, coleta.carimbo))
    ns = coleta.namespace
    namespaces = None if coleta.namespaces.estado == "erro" else coleta.namespaces.itens
    corpo = [
        _controles(namespaces, ns, coleta.namespaces_negados),
        _bloco_namespaces(coleta),
        _bloco("pods", "Pods", coleta.pods, ns, COLUNAS_PODS),
        _bloco("deployments", "Deployments", coleta.deployments, ns, COLUNAS_DEPLOYMENTS),
        _bloco("services", "Services", coleta.services, ns, COLUNAS_SERVICES),
        _bloco("eventos", f"Eventos{' de ' + ns if ns else ''}", coleta.eventos, ns,
               COLUNAS_EVENTOS, chave_busca="objeto_nome", nota=NOTA_EVENTOS),
    ]
    return _documento(_cabecalho(contexto, coleta.carimbo), "\n".join(corpo))


def corpo_erro_global(erro, contexto, carimbo):
    quando = e(formatar_carimbo(carimbo))
    if erro.categoria == erros.NAO_RESPONDEU:
        return _falha_global("O cluster não respondeu", [
            f"O servidor <code>{e(contexto.servidor)}</code> do contexto "
            f"<strong>{e(contexto.nome)}</strong> não respondeu (conexão recusada, sem rota "
            f"ou tempo esgotado). Tentativa em {quando}.",
            "Verifique se o cluster está no ar e acessível desta máquina e clique em Atualizar.",
        ])
    if erro.categoria == erros.CREDENCIAL:
        return _falha_global("Credencial recusada ou expirada", [
            f"O servidor <code>{e(contexto.servidor)}</code> respondeu, mas recusou a "
            f"credencial do contexto <strong>{e(contexto.nome)}</strong>: ela expirou, é "
            f"inválida ou não pôde ser obtida (por exemplo, falha no plugin de credencial). "
            f"Tentativa em {quando}.",
            "Renove a credencial (novo login no provedor, novo token ou certificado) e "
            "clique em Atualizar.",
        ])
    return _falha_global("Erro inesperado", [
        "Não foi possível concluir a coleta. O detalhe técnico foi registrado no log local "
        "do painel.",
    ])


def pagina_kubeconfig(erro, carimbo):
    """kubeconfig-invalido ou sem-contexto: nenhuma chamada ao cluster foi feita."""
    if erro.categoria == erros.SEM_CONTEXTO:
        corpo = _falha_global("Nenhum contexto corrente no kubeconfig", [
            f"O kubeconfig em <code>{e(erro.caminho)}</code> não define "
            "<code>current-context</code>, então o painel não sabe qual cluster ler. "
            "Nenhuma chamada ao cluster foi feita.",
            "Defina um contexto com <code>kubectl config use-context &lt;nome&gt;</code> "
            "e clique em Atualizar.",
        ])
    else:
        tipo = TIPOS_KUBECONFIG.get(erro.tipo, erro.tipo)
        corpo = _falha_global("Não foi possível carregar o kubeconfig", [
            f"Caminho tentado: <code>{e(erro.caminho)}</code>",
            f"Problema: arquivo {e(tipo)}. {e(_frase(erro.motivo))}",
            "Nenhuma chamada ao cluster foi feita. Corrija o arquivo ou a variável "
            "<code>KUBECONFIG</code> e clique em Atualizar.",
        ])
    return _documento(_cabecalho(None, carimbo, "Tentativa"),
                      '<div class="controles"><form method="get" action="/">'
                      '<button type="submit">Atualizar</button></form></div>' + corpo)


def pagina_namespace_invalido(contexto, nome, carimbo):
    corpo = _controles(None, None, valor_digitado=nome) + _falha_global(
        "Nome de namespace inválido", [
            f"“{e(nome)}” não é um nome de namespace válido: use letras minúsculas, dígitos "
            "e hífen, começando e terminando com letra ou dígito, até 63 caracteres.",
            "Nenhuma chamada ao cluster foi feita.",
        ])
    return _documento(_cabecalho(contexto, carimbo, "Tentativa"), corpo)


def pagina_inesperada(carimbo):
    return _documento(_cabecalho(None, carimbo, "Tentativa"), _falha_global("Erro inesperado", [
        "O painel encontrou um erro que não soube tratar. O detalhe técnico foi registrado "
        "no log local do painel.",
    ]))


def pagina_simples(carimbo, titulo, texto):
    return _documento(_cabecalho(None, carimbo, "Horário"), _falha_global(titulo, [e(texto)]))
