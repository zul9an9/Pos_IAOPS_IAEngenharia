"""Motor de conformidade: compara o inventário já coletado com o baseline, regra a regra.

Roda inteiramente local e só lê o objeto `Inventario`; nunca toca o host.
Cada tipo de regra tem a sua semântica (design D7) — nada é comparado por
igualdade textual genérica.
"""

import ipaddress
import re
from dataclasses import dataclass

CONFORME = "conforme"
DESVIO = "desvio"
NAO_VERIFICADO = "nao_verificado"

_REDES_INTERNAS = tuple(
    ipaddress.ip_network(rede)
    for rede in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",
                 "169.254.0.0/16", "fe80::/10", "fc00::/7")
)
_RE_VERSAO_COMPLETA = re.compile(r"^[0-9]+(\.[0-9]+)*$")
_RE_VERSAO_PREFIXO = re.compile(r"^[0-9]+(\.[0-9]+)*")


@dataclass(frozen=True)
class Entrada:
    regra: str
    esperado: object
    encontrado: object
    veredito: str
    severidade: str = None
    motivo: str = None

    def como_dict(self):
        """Formato do JSON: `severidade` só em desvio, `motivo` só em nao_verificado."""
        dados = {
            "regra": self.regra,
            "esperado": self.esperado,
            "encontrado": self.encontrado,
            "veredito": self.veredito,
        }
        if self.veredito == DESVIO:
            dados["severidade"] = self.severidade
        if self.veredito == NAO_VERIFICADO:
            dados["motivo"] = self.motivo
        return dados


def _conforme(regra, encontrado):
    return Entrada(regra.id, regra.esperado, encontrado, CONFORME)


def _desvio(regra, encontrado):
    return Entrada(regra.id, regra.esperado, encontrado, DESVIO, severidade=regra.severidade)


def _nao_verificado(regra, motivo):
    return Entrada(regra.id, regra.esperado, None, NAO_VERIFICADO, motivo=motivo)


def _resultado(regra, atende, encontrado):
    return _conforme(regra, encontrado) if atende else _desvio(regra, encontrado)


# ------------------------------------------------------- helpers de valor

def classificar_endereco(endereco):
    """`interno` (loopback, RFC1918, link-local, ULA) ou `publico` (curinga e o resto)."""
    texto = endereco.strip()
    if texto.startswith("[") and texto.endswith("]"):
        texto = texto[1:-1]
    texto = texto.split("%", 1)[0]
    if texto in ("*", ""):
        return "publico"
    try:
        ip = ipaddress.ip_address(texto)
    except ValueError:
        return "publico"  # não reconhecido: tratado como exposto, nunca como interno
    if ip.version == 6 and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    if ip.is_unspecified:
        return "publico"
    if ip.is_loopback:
        return "interno"
    if any(ip in rede for rede in _REDES_INTERNAS if rede.version == ip.version):
        return "interno"
    return "publico"


def parse_versao(texto, aceitar_sufixo=False):
    """Converte '6.10.2' em (6, 10, 2). `aceitar_sufixo` ignora o que vem após o prefixo numérico."""
    if not isinstance(texto, str):
        return None
    texto = texto.strip()
    padrao = _RE_VERSAO_PREFIXO if aceitar_sufixo else _RE_VERSAO_COMPLETA
    m = padrao.match(texto)
    if not m:
        return None
    return tuple(int(parte) for parte in m.group(0).split("."))


def comparar_versoes(a, b):
    """Compara tuplas numéricas completando com zeros: devolve -1, 0 ou 1."""
    tamanho = max(len(a), len(b))
    a = a + (0,) * (tamanho - len(a))
    b = b + (0,) * (tamanho - len(b))
    return (a > b) - (a < b)


def _nome_unidade(nome):
    return nome if nome.endswith((".service", ".socket")) else nome + ".service"


def _rotulo_chave(chave):
    comentario = chave.get("comentario") or ""
    if comentario:
        return comentario
    fp = chave.get("fingerprint") or {}
    if fp.get("read"):
        return fp["value"]
    return f"(chave {chave.get('tipo', '?')} sem identificação)"


# ---------------------------------------------------------- avaliadores

def _avaliar_servicos_ativos(regra, valor):
    ativos = {u["nome"] for u in valor}
    esperados = [_nome_unidade(n) for n in regra.esperado]
    ausentes = sorted(n for n in esperados if n not in ativos)
    encontrado = {"ativos": sorted(n for n in esperados if n in ativos),
                  "ausentes_ou_inativos": ausentes}
    return _resultado(regra, not ausentes, encontrado)


def _avaliar_servicos_proibidos(regra, valor):
    ativos = {u["nome"] for u in valor}
    presentes = sorted(n for n in (_nome_unidade(x) for x in regra.esperado) if n in ativos)
    return _resultado(regra, not presentes, {"proibidos_presentes": presentes})


def _avaliar_distribuicao(regra, valor):
    encontrada = valor["distribuicao"]
    return _resultado(regra, encontrada.lower() == regra.esperado.lower(), encontrada)


def _avaliar_versao_minima(aceitar_sufixo):
    def avaliar(regra, valor):
        bruto = valor["versao"] if isinstance(valor, dict) else valor
        encontrada = parse_versao(bruto, aceitar_sufixo)
        if encontrada is None:
            return _nao_verificado(
                regra, f"a versão reportada pelo host ('{bruto}') não pôde ser interpretada "
                       "como sequência numérica")
        minima = parse_versao(str(regra.esperado))
        return _resultado(regra, comparar_versoes(encontrada, minima) >= 0, bruto)
    return avaliar


def _avaliar_portas_publicas(regra, valor):
    permitidas = set(regra.esperado)
    ofensoras = sorted(
        ({"endereco": p["endereco"], "porta": p["porta"]}
         for p in valor
         if classificar_endereco(p["endereco"]) == "publico" and p["porta"] not in permitidas),
        key=lambda x: (x["porta"], x["endereco"]),
    )
    return _resultado(regra, not ofensoras, {"publicas_nao_permitidas": ofensoras})


def _avaliar_portas_internas(regra, valor):
    encontrado = []
    conforme = True
    for porta in regra.esperado:
        enderecos = sorted({p["endereco"] for p in valor if p["porta"] == porta})
        encontrado.append({"porta": porta, "enderecos": enderecos})
        if not enderecos or any(classificar_endereco(e) == "publico" for e in enderecos):
            conforme = False
    return _resultado(regra, conforme, encontrado)


def _avaliar_swap(regra, valor):
    return _resultado(regra, valor["habilitado"] == regra.esperado, valor["habilitado"])


def _avaliar_ntp(regra, valor):
    return _resultado(regra, valor["ativo"] == regra.esperado, valor["ativo"])


def _avaliar_login_root(regra, valor):
    habilitado = valor != "no"
    encontrado = {"valor_efetivo": valor, "habilitado": habilitado}
    return _resultado(regra, habilitado == regra.esperado, encontrado)


def _avaliar_chaves(regra, valor):
    chaves = valor["chaves"]
    incompativeis = []
    for chave in chaves:
        comentario = chave.get("comentario") or ""
        emissor = comentario.rsplit("@", 1)[1] if "@" in comentario else None
        if emissor != regra.esperado:
            incompativeis.append(_rotulo_chave(chave))
    encontrado = {
        "escopo": f"authorized_keys do usuário que conectou ({valor.get('usuario', '?')})",
        "total": len(chaves),
        "incompativeis": sorted(incompativeis),
    }
    return _resultado(regra, not incompativeis, encontrado)


# regra -> (fato do inventário, avaliador)
REGRAS_CONHECIDAS = {
    "so.distribuicao": ("so", _avaliar_distribuicao),
    "servicos.ativos": ("servicos", _avaliar_servicos_ativos),
    "servicos.proibidos": ("servicos", _avaliar_servicos_proibidos),
    "so.versao_minima": ("so", _avaliar_versao_minima(aceitar_sufixo=False)),
    "kernel.versao_minima": ("kernel", _avaliar_versao_minima(aceitar_sufixo=True)),
    "portas_em_escuta.publicas_permitidas": ("portas", _avaliar_portas_publicas),
    "portas_em_escuta.somente_rede_interna": ("portas", _avaliar_portas_internas),
    "swap.habilitado": ("swap", _avaliar_swap),
    "ssh.login_de_root": ("ssh_login_root", _avaliar_login_root),
    "chaves_ssh.emitidas_por": ("chaves_ssh", _avaliar_chaves),
    "ntp.sincronizado": ("ntp", _avaliar_ntp),
}


def avaliar_regra(regra, inventario):
    conhecida = REGRAS_CONHECIDAS.get(regra.id)
    if conhecida is None:
        return _nao_verificado(
            regra, f"a coleta não produz o fato referenciado pela regra '{regra.id}'")
    nome_fato, avaliador = conhecida
    fato = inventario.fatos.get(nome_fato)
    if fato is None:
        return _nao_verificado(
            regra, f"a coleta não produz o fato '{nome_fato}' referenciado pela regra")
    if not fato.lido:
        return _nao_verificado(regra, f"fato '{nome_fato}' não lido pela coleta: {fato.motivo}")
    return avaliador(regra, fato.valor)


def avaliar(baseline, inventario):
    """Uma entrada por regra do baseline, na ordem em que o baseline as declara."""
    return [avaliar_regra(regra, inventario) for regra in baseline.regras]


def resumo(entradas):
    """Contagem por veredito; `por_severidade` conta apenas os desvios."""
    contagem = {CONFORME: 0, DESVIO: 0, NAO_VERIFICADO: 0}
    por_severidade = {"critico": 0, "alto": 0, "medio": 0}
    for entrada in entradas:
        contagem[entrada.veredito] += 1
        if entrada.veredito == DESVIO:
            por_severidade[entrada.severidade] += 1
    return {**contagem, "por_severidade": por_severidade}
