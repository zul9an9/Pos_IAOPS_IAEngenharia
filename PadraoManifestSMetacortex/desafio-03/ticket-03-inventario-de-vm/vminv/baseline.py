"""Parser YAML mínimo e carga do `baseline.yaml`.

Layout oficial do baseline (subconjunto de YAML):

    versao: 1
    aplica_a: vms-do-parque
    esperado:
      so: {distribuicao: ubuntu, versao_minima: "22.04"}
      swap: {habilitado: false}
    severidade:
      critico: [swap.habilitado]
      alto: [so.distribuicao, so.versao_minima]

O id da regra é o caminho pontilhado dentro de `esperado`; a severidade vem das
listas invertidas de `severidade` (conjunto fechado: critico, alto, medio).

O parser aceita apenas: mapeamentos em bloco, listas em bloco de escalares,
flow style de uma linha (`[a, b]` e `{chave: valor, outra: [x, y]}`), escalares
(planos, 'aspas simples', "aspas duplas"), comentários e um único `---` inicial.
Todo o resto é recusado com um erro que nomeia a construção e a linha; nada é
interpretado por palpite. Booleanos são somente `true`/`false`.
"""

import re
from dataclasses import dataclass

from .errors import BaselineInvalido

VERSOES_SUPORTADAS = (1,)

_AMBIGUOS = {"yes", "no", "on", "off", "y", "n", "null", "~"}
_INICIOS_PROIBIDOS = {
    "&": "âncora (&)",
    "*": "alias (*)",
    "!": "tag (!)",
    "|": "bloco literal (|)",
    ">": "bloco dobrado (>)",
    "%": "diretiva (%)",
    "@": "indicador reservado (@)",
    "`": "indicador reservado (`)",
    "{": "mapeamento em linha ({...})",
    "}": "mapeamento em linha ({...})",
}
_RE_INT = re.compile(r"^-?(0|[1-9][0-9]*)$")
_RE_INT_ZERO_A_ESQUERDA = re.compile(r"^-?0[0-9]+$")


def _erro(numero, mensagem):
    return BaselineInvalido(f"baseline inválido (linha {numero}): {mensagem}")


# ---------------------------------------------------------------- escalares

def _remover_comentario(linha):
    """Remove `# comentário` respeitando aspas."""
    aspas = None
    i = 0
    while i < len(linha):
        c = linha[i]
        if aspas == '"':
            if c == "\\":
                i += 2
                continue
            if c == '"':
                aspas = None
        elif aspas == "'":
            if c == "'":
                aspas = None
        else:
            if c in "\"'" and (i == 0 or linha[i - 1] in " \t[,:"):
                aspas = c
            elif c == "#" and (i == 0 or linha[i - 1] in " \t"):
                return linha[:i]
        i += 1
    return linha


def _entre_aspas(texto, numero):
    q = texto[0]
    i = 1
    saida = []
    while i < len(texto):
        c = texto[i]
        if q == '"' and c == "\\":
            if i + 1 >= len(texto) or texto[i + 1] not in '"\\':
                raise _erro(numero, "sequência de escape não suportada em string com aspas duplas")
            saida.append(texto[i + 1])
            i += 2
            continue
        if q == "'" and c == "'" and texto[i + 1:i + 2] == "'":
            saida.append("'")
            i += 2
            continue
        if c == q:
            if texto[i + 1:].strip():
                raise _erro(numero, "conteúdo após o fechamento das aspas")
            return "".join(saida)
        saida.append(c)
        i += 1
    raise _erro(numero, "string com aspas não fechada")


def _escalar_plano(texto, numero):
    if texto[0] in _INICIOS_PROIBIDOS:
        raise _erro(numero, f"construção não suportada: {_INICIOS_PROIBIDOS[texto[0]]}")
    if texto.startswith("? ") or texto == "?":
        raise _erro(numero, "construção não suportada: chave complexa (?)")
    if ": " in texto or texto.endswith(":"):
        raise _erro(numero, "construção não suportada: mapeamento dentro de um valor")
    if texto in ("true", "false"):
        return texto == "true"
    if texto.lower() in _AMBIGUOS or texto.lower() in ("true", "false"):
        raise _erro(
            numero,
            f"valor ambíguo '{texto}': use somente os literais true/false para booleanos "
            "(ou coloque entre aspas se for texto)",
        )
    if _RE_INT_ZERO_A_ESQUERDA.match(texto):
        raise _erro(numero, f"inteiro com zero à esquerda '{texto}' é ambíguo (octal?); use aspas")
    if _RE_INT.match(texto):
        return int(texto)
    return texto


def _fim_das_aspas(texto, inicio, numero):
    """Índice logo após a string com aspas que começa em `inicio`."""
    q = texto[inicio]
    i = inicio + 1
    while i < len(texto):
        c = texto[i]
        if q == '"' and c == "\\":
            i += 2
            continue
        if c == q:
            if q == "'" and texto[i + 1:i + 2] == "'":
                i += 2
                continue
            return i + 1
        i += 1
    raise _erro(numero, "string com aspas não fechada")


class _Fluxo:
    """Flow style de uma linha: `[a, b]` ou `{chave: valor, outra: [x, y]}`.

    Um mapeamento em linha só aceita valores escalares ou listas de escalares; uma
    lista em linha só aceita escalares. Qualquer aninhamento além disso é recusado.
    """

    def __init__(self, texto, numero):
        self.t = texto
        self.i = 0
        self.n = numero

    def _espaco(self):
        while self.i < len(self.t) and self.t[self.i] == " ":
            self.i += 1

    def _atual(self):
        self._espaco()
        if self.i >= len(self.t):
            raise _erro(self.n, "flow style não fechado (ou multilinha, não suportado)")
        return self.t[self.i]

    def _escalar(self, delimitadores):
        c = self._atual()
        if c in "\"'":
            fim = _fim_das_aspas(self.t, self.i, self.n)
            valor = _entre_aspas(self.t[self.i:fim], self.n)
            self.i = fim
            return valor
        inicio = self.i
        while self.i < len(self.t) and self.t[self.i] not in delimitadores:
            if self.t[self.i] in "[]{}":
                raise _erro(self.n, "construção não suportada: flow style aninhado")
            self.i += 1
        token = self.t[inicio:self.i].strip()
        if not token:
            raise _erro(self.n, "item vazio em flow style")
        return _escalar_plano(token, self.n)

    def raiz(self):
        c = self._atual()
        valor = self._lista() if c == "[" else self._mapeamento()
        self._espaco()
        if self.i != len(self.t):
            raise _erro(self.n, "conteúdo após o fechamento do flow style")
        return valor

    def _lista(self):
        self.i += 1  # [
        itens = []
        if self._atual() == "]":
            self.i += 1
            return itens
        while True:
            if self._atual() in "[{":
                raise _erro(self.n, "construção não suportada: lista aninhada ou mapeamento dentro de lista em linha")
            itens.append(self._escalar(",]"))
            c = self._atual()
            self.i += 1
            if c == "]":
                return itens
            if c != ",":
                raise _erro(self.n, "esperado ',' ou ']' na lista em linha")

    def _mapeamento(self):
        self.i += 1  # {
        mapa = {}
        while True:
            c = self._atual()
            if c in "\"'":
                fim = _fim_das_aspas(self.t, self.i, self.n)
                chave = _entre_aspas(self.t[self.i:fim], self.n)
                self.i = fim
            else:
                inicio = self.i
                while self.i < len(self.t) and self.t[self.i] not in ":,{}[]":
                    self.i += 1
                chave = self.t[inicio:self.i].strip()
            if not chave or self._atual() != ":":
                raise _erro(self.n, "esperado 'chave: valor' no mapeamento em linha")
            self.i += 1
            if chave in mapa:
                raise _erro(self.n, f"chave duplicada '{chave}'")
            c = self._atual()
            if c == "{":
                raise _erro(self.n, "construção não suportada: mapeamento em linha aninhado")
            mapa[chave] = self._lista() if c == "[" else self._escalar(",}")
            c = self._atual()
            self.i += 1
            if c == "}":
                return mapa
            if c != ",":
                raise _erro(self.n, "esperado ',' ou '}' no mapeamento em linha")


def _valor_em_linha(texto, numero):
    texto = texto.strip()
    if texto[0] in "\"'":
        return _entre_aspas(texto, numero)
    if texto[0] in "[{":
        return _Fluxo(texto, numero).raiz()
    return _escalar_plano(texto, numero)


# ------------------------------------------------------------ estrutura

def _separar_chave(texto, numero):
    """Divide `chave: resto`. Devolve (chave, resto)."""
    if texto[0] in "\"'":
        q = texto[0]
        fim = texto.find(q, 1)
        if fim == -1:
            raise _erro(numero, "chave com aspas não fechada")
        chave = texto[1:fim]
        resto = texto[fim + 1:]
        if not resto.startswith(":"):
            raise _erro(numero, "esperado ':' após a chave")
        return chave, resto[1:].strip()
    if texto[0] in _INICIOS_PROIBIDOS:
        raise _erro(numero, f"construção não suportada: {_INICIOS_PROIBIDOS[texto[0]]}")
    m = re.match(r"^([^\s:][^:]*?)\s*:(?:\s+(.*)|$)", texto)
    if not m:
        raise _erro(numero, "linha não é um par 'chave: valor' nem um item de lista")
    return m.group(1), (m.group(2) or "").strip()


class _Parser:
    def __init__(self, texto):
        self.linhas = []
        documento_iniciado = False
        for numero, bruta in enumerate(texto.splitlines(), 1):
            sem_comentario = _remover_comentario(bruta).rstrip()
            if not sem_comentario.strip():
                continue
            indentacao = len(sem_comentario) - len(sem_comentario.lstrip(" \t"))
            if "\t" in sem_comentario[:indentacao]:
                raise _erro(numero, "tabulação na indentação não é suportada; use espaços")
            corpo = sem_comentario.strip()
            if corpo == "---":
                if documento_iniciado:
                    raise _erro(numero, "construção não suportada: múltiplos documentos (---)")
                documento_iniciado = True
                continue
            if corpo == "...":
                raise _erro(numero, "construção não suportada: marcador de fim de documento (...)")
            documento_iniciado = True
            self.linhas.append((numero, indentacao, corpo))
        self.i = 0

    def documento(self):
        if not self.linhas:
            raise BaselineInvalido("baseline inválido: o arquivo está vazio")
        numero, indentacao, _ = self.linhas[0]
        if indentacao != 0:
            raise _erro(numero, "o documento deve começar na coluna 0")
        valor = self._bloco(0)
        if self.i < len(self.linhas):
            raise _erro(self.linhas[self.i][0], "indentação inesperada")
        return valor

    def _bloco(self, indentacao):
        _, _, corpo = self.linhas[self.i]
        if corpo == "-" or corpo.startswith("- "):
            return self._lista(indentacao)
        return self._mapeamento(indentacao)

    def _mapeamento(self, indentacao):
        resultado = {}
        while self.i < len(self.linhas):
            numero, ind, corpo = self.linhas[self.i]
            if ind < indentacao:
                break
            if ind > indentacao:
                raise _erro(numero, "indentação inesperada")
            if corpo == "-" or corpo.startswith("- "):
                raise _erro(numero, "item de lista onde era esperada uma chave")
            chave, resto = _separar_chave(corpo, numero)
            if chave in resultado:
                raise _erro(numero, f"chave duplicada '{chave}'")
            self.i += 1
            if resto:
                valor = _valor_em_linha(resto, numero)
                if self.i < len(self.linhas) and self.linhas[self.i][1] > indentacao:
                    raise _erro(self.linhas[self.i][0], "indentação inesperada após um valor em linha")
                resultado[chave] = valor
                continue
            if self.i >= len(self.linhas):
                raise _erro(numero, f"a chave '{chave}' não tem valor")
            prox_num, prox_ind, prox_corpo = self.linhas[self.i]
            eh_lista = prox_corpo == "-" or prox_corpo.startswith("- ")
            if prox_ind > indentacao:
                resultado[chave] = self._bloco(prox_ind)
            elif prox_ind == indentacao and eh_lista:
                resultado[chave] = self._lista(indentacao)
            else:
                raise _erro(numero, f"a chave '{chave}' não tem valor")
        return resultado

    def _lista(self, indentacao):
        itens = []
        while self.i < len(self.linhas):
            numero, ind, corpo = self.linhas[self.i]
            if ind != indentacao or not (corpo == "-" or corpo.startswith("- ")):
                break
            resto = corpo[1:].strip()
            if not resto:
                raise _erro(numero, "construção não suportada: item de lista aninhado ou vazio")
            if re.match(r"^[^\s\"'\[{][^:]*:(\s|$)", resto):
                raise _erro(numero, "construção não suportada: mapeamento dentro de uma lista")
            itens.append(_valor_em_linha(resto, numero))
            self.i += 1
        return itens


def parse_yaml(texto):
    """Interpreta o subconjunto de YAML suportado; recusa todo o resto."""
    return _Parser(texto).documento()


# ------------------------------------------------------------ baseline

@dataclass(frozen=True)
class Regra:
    id: str
    esperado: object
    severidade: str


@dataclass(frozen=True)
class Baseline:
    versao: int
    aplica_a: str
    regras: tuple


RE_VERSAO_NUMERICA = re.compile(r"^[0-9]+(\.[0-9]+)*$")
SEVERIDADES = ("critico", "alto", "medio")
CHAVES_DA_RAIZ = ("versao", "aplica_a", "esperado", "severidade")


def _lista_de_textos(regra_id, esperado):
    if not isinstance(esperado, list) or not all(isinstance(x, str) and x for x in esperado):
        raise BaselineInvalido(
            f"baseline inválido: o 'esperado' da regra '{regra_id}' deve ser uma lista de nomes"
        )
    return list(esperado)


def _lista_de_portas(regra_id, esperado):
    if (not isinstance(esperado, list)
            or not all(isinstance(x, int) and not isinstance(x, bool) and 0 < x < 65536
                       for x in esperado)):
        raise BaselineInvalido(
            f"baseline inválido: o 'esperado' da regra '{regra_id}' deve ser uma lista de portas (1-65535)"
        )
    return list(esperado)


def _versao_minima(regra_id, esperado):
    if isinstance(esperado, int) and not isinstance(esperado, bool):
        esperado = str(esperado)
    if not isinstance(esperado, str) or not RE_VERSAO_NUMERICA.match(esperado):
        raise BaselineInvalido(
            f"baseline inválido: o 'esperado' da regra '{regra_id}' deve ser uma versão numérica "
            "(ex.: 22.04 ou 5.15.0)"
        )
    return esperado


def _booleano(regra_id, esperado):
    if not isinstance(esperado, bool):
        raise BaselineInvalido(
            f"baseline inválido: o 'esperado' da regra '{regra_id}' deve ser true ou false"
        )
    return esperado


def _texto(regra_id, esperado):
    if not isinstance(esperado, str) or not esperado:
        raise BaselineInvalido(
            f"baseline inválido: o 'esperado' da regra '{regra_id}' deve ser um texto não vazio"
        )
    return esperado


VALIDADORES_ESPERADO = {
    "so.distribuicao": _texto,
    "so.versao_minima": _versao_minima,
    "kernel.versao_minima": _versao_minima,
    "servicos.ativos": _lista_de_textos,
    "servicos.proibidos": _lista_de_textos,
    "swap.habilitado": _booleano,
    "portas_em_escuta.publicas_permitidas": _lista_de_portas,
    "portas_em_escuta.somente_rede_interna": _lista_de_portas,
    "chaves_ssh.emitidas_por": _texto,
    "ssh.login_de_root": _booleano,
    "ntp.sincronizado": _booleano,
}


def validar_versao(documento):
    """Valida `versao` ANTES de interpretar qualquer regra (design D5)."""
    if "versao" not in documento:
        raise BaselineInvalido(
            "baseline inválido: o campo 'versao' está ausente; declare a versão do formato "
            f"(suportadas: {', '.join(map(str, VERSOES_SUPORTADAS))})"
        )
    versao = documento["versao"]
    if isinstance(versao, bool) or not isinstance(versao, int) or versao < 1:
        raise BaselineInvalido(
            f"baseline inválido: a 'versao' do baseline é desconhecida (suportadas: "
            f"{', '.join(map(str, VERSOES_SUPORTADAS))})"
        )
    if versao > max(VERSOES_SUPORTADAS):
        raise BaselineInvalido(
            f"baseline inválido: a 'versao' {versao} é futura; este baseline foi escrito para "
            f"uma versão mais nova da ferramenta (suportadas: "
            f"{', '.join(map(str, VERSOES_SUPORTADAS))})"
        )
    if versao not in VERSOES_SUPORTADAS:
        raise BaselineInvalido(
            f"baseline inválido: a 'versao' {versao} do baseline é desconhecida (suportadas: "
            f"{', '.join(map(str, VERSOES_SUPORTADAS))})"
        )
    return versao


def _severidades_por_regra(severidade, ids_de_regras):
    """Inverte as listas de `severidade` (nível -> ids) em id -> nível, validando o conjunto fechado."""
    if not isinstance(severidade, dict):
        raise BaselineInvalido(
            "baseline inválido: 'severidade' deve ser um mapeamento de nível (critico, alto, medio) "
            "para a lista de ids das regras"
        )
    por_regra = {}
    for nivel, ids in severidade.items():
        if nivel not in SEVERIDADES:
            raise BaselineInvalido(
                f"baseline inválido: severidade desconhecida '{nivel}' "
                f"(permitidas: {', '.join(SEVERIDADES)})"
            )
        if not isinstance(ids, list) or not all(isinstance(i, str) and i for i in ids):
            raise BaselineInvalido(
                f"baseline inválido: a severidade '{nivel}' deve ser uma lista de ids de regras"
            )
        for regra_id in ids:
            if regra_id not in ids_de_regras:
                raise BaselineInvalido(
                    f"baseline inválido: a severidade '{nivel}' lista '{regra_id}', "
                    "que não existe em 'esperado'"
                )
            if regra_id in por_regra:
                raise BaselineInvalido(
                    f"baseline inválido: a regra '{regra_id}' está em mais de um nível de severidade"
                )
            por_regra[regra_id] = nivel
    for regra_id in ids_de_regras:
        if regra_id not in por_regra:
            raise BaselineInvalido(
                f"baseline inválido: a regra '{regra_id}' não tem severidade declarada"
            )
    return por_regra


def carregar_baseline(texto):
    """Parseia e valida o baseline (layout oficial). Qualquer problema é `BaselineInvalido` (exit 2)."""
    documento = parse_yaml(texto)
    if not isinstance(documento, dict):
        raise BaselineInvalido("baseline inválido: o documento deve ser um mapeamento na raiz")
    versao = validar_versao(documento)
    desconhecidas = [k for k in documento if k not in CHAVES_DA_RAIZ]
    if desconhecidas:
        raise BaselineInvalido(
            f"baseline inválido: chave desconhecida na raiz: '{desconhecidas[0]}' "
            f"(esperadas: {', '.join(CHAVES_DA_RAIZ)})"
        )
    for chave in ("aplica_a", "esperado", "severidade"):
        if chave not in documento:
            raise BaselineInvalido(f"baseline inválido: a chave '{chave}' está ausente")
    aplica_a = documento["aplica_a"]
    if not isinstance(aplica_a, str) or not aplica_a:
        raise BaselineInvalido("baseline inválido: 'aplica_a' deve ser um texto não vazio")
    esperado = documento["esperado"]
    if not isinstance(esperado, dict) or not esperado:
        raise BaselineInvalido(
            "baseline inválido: 'esperado' deve ser um mapeamento não vazio de grupos de regras"
        )
    valores = {}
    for grupo, regras_do_grupo in esperado.items():
        if not isinstance(regras_do_grupo, dict) or not regras_do_grupo:
            raise BaselineInvalido(
                f"baseline inválido: o grupo '{grupo}' de 'esperado' deve ser um mapeamento "
                "não vazio de regras"
            )
        for nome, valor in regras_do_grupo.items():
            regra_id = f"{grupo}.{nome}"
            validador = VALIDADORES_ESPERADO.get(regra_id)
            valores[regra_id] = validador(regra_id, valor) if validador else valor
    severidades = _severidades_por_regra(documento["severidade"], valores)
    regras = tuple(Regra(id=i, esperado=v, severidade=severidades[i]) for i, v in valores.items())
    return Baseline(versao=versao, aplica_a=aplica_a, regras=regras)
