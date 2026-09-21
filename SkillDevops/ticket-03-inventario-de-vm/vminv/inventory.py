"""Inventário coletado: parsing da resposta JSON única do script remoto."""

import json
from dataclasses import dataclass, field

from .errors import RespostaInvalida

FORMATO_SUPORTADO = 1
FATOS_ESPERADOS = (
    "coletado_em", "hostname", "so", "kernel", "servicos", "swap",
    "portas", "chaves_ssh", "ssh_login_root", "ntp",
)


@dataclass(frozen=True)
class Fato:
    """Um fato do host: lido (com valor) ou não lido (com motivo)."""

    lido: bool
    valor: object = None
    motivo: str = ""

    def como_envelope(self):
        if self.lido:
            return {"read": True, "value": self.valor}
        return {"read": False, "reason": self.motivo}


@dataclass
class Inventario:
    endereco: str
    fatos: dict = field(default_factory=dict)

    def fato(self, nome):
        return self.fatos[nome]

    def como_dict(self):
        dados = {"endereco": self.endereco}
        for nome in FATOS_ESPERADOS:
            dados[nome] = self.fatos[nome].como_envelope()
        return dados


def _fato_de_envelope(nome, bruto):
    if not isinstance(bruto, dict) or not isinstance(bruto.get("read"), bool):
        raise RespostaInvalida(
            f"a resposta do script de coleta é inválida: o fato '{nome}' está malformado"
        )
    if bruto["read"]:
        if "value" not in bruto:
            raise RespostaInvalida(
                f"a resposta do script de coleta é inválida: o fato '{nome}' não traz valor"
            )
        return Fato(lido=True, valor=bruto["value"])
    motivo = bruto.get("reason")
    if not isinstance(motivo, str) or not motivo:
        raise RespostaInvalida(
            f"a resposta do script de coleta é inválida: o fato '{nome}' não lido não traz motivo"
        )
    return Fato(lido=False, motivo=motivo)


def interpretar_resposta(texto, endereco):
    """Converte o JSON do script remoto em um `Inventario`.

    Resposta malformada ou truncada é falha de execução, nunca um resultado parcial.
    """
    try:
        bruto = json.loads(texto)
    except (json.JSONDecodeError, TypeError):
        raise RespostaInvalida(
            "a resposta do script de coleta não é um JSON válido (malformada ou truncada)"
        ) from None
    if not isinstance(bruto, dict) or bruto.get("formato") != FORMATO_SUPORTADO:
        raise RespostaInvalida(
            "a resposta do script de coleta tem formato desconhecido ou incompleto"
        )
    fatos = {}
    for nome in FATOS_ESPERADOS:
        if nome not in bruto:
            raise RespostaInvalida(
                f"a resposta do script de coleta está incompleta: falta o fato '{nome}'"
            )
        fatos[nome] = _fato_de_envelope(nome, bruto[nome])
    return Inventario(endereco=endereco, fatos=fatos)
