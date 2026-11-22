"""Utilitários de teste: inventário sintético, test double do subprocesso e chave sentinela."""

import json
import os
import subprocess
import tempfile

from vminv import inventory

# Conteúdo sentinela: nenhum texto capturado pode conter esta string (a "chave" de teste).
CONTEUDO_CHAVE = "SENTINELA-CHAVE-PRIVADA-b3JnLXRlc3RlLTEyMzQ1Njc4OTA"


def ok(valor):
    return {"read": True, "value": valor}


def nao_lido(motivo="sem privilégio"):
    return {"read": False, "reason": motivo}


def resposta_bruta(**sobrescritas):
    """Resposta JSON do script remoto para um host saudável e conforme."""
    dados = {
        "formato": 1,
        "coletado_em": ok("2026-01-01T00:00:00Z"),
        "hostname": ok("host-teste"),
        "so": ok({"distribuicao": "ubuntu", "versao": "24.04"}),
        "kernel": ok("5.15.0-101-generic"),
        "servicos": ok([
            {"nome": "ssh.service", "tipo": "service", "estado": "active"},
            {"nome": "cron.service", "tipo": "service", "estado": "active"},
            {"nome": "ssh.socket", "tipo": "socket", "estado": "active"},
        ]),
        "swap": ok({"habilitado": True, "tamanho_kib": 2048}),
        "portas": ok([
            {"endereco": "0.0.0.0", "porta": 22, "processo": ok("sshd")},
            {"endereco": "10.0.0.5", "porta": 9100, "processo": nao_lido("outro usuário")},
        ]),
        "chaves_ssh": ok({
            "escopo": "usuario_conectado", "usuario": "orpheu", "arquivo": ".ssh/authorized_keys",
            "chaves": [{"tipo": "ssh-ed25519", "comentario": "platform@metacortex-platform",
                        "fingerprint": ok("SHA256:abc")}],
        }),
        "ssh_login_root": nao_lido("sshd -T falhou"),
        "ntp": ok({"mecanismo": "chrony", "ativo": True}),
    }
    dados.update(sobrescritas)
    return dados


def inventario(**sobrescritas):
    return inventory.interpretar_resposta(json.dumps(resposta_bruta(**sobrescritas)), "10.0.0.5")


class ExecutorFalso:
    """Test double de `subprocess.run`: registra argv/input e devolve um resultado fixo."""

    def __init__(self, returncode=0, stdout=b"", stderr=b"", levanta=None):
        self.returncode, self.stdout, self.stderr, self.levanta = returncode, stdout, stderr, levanta
        self.chamadas = []

    def __call__(self, argv, **kwargs):
        self.chamadas.append((argv, kwargs))
        if self.levanta:
            raise self.levanta
        return subprocess.CompletedProcess(argv, self.returncode, self.stdout, self.stderr)


class ChaveTemporaria:
    """Arquivo de chave com conteúdo sentinela, em diretório temporário."""

    def __enter__(self):
        self.dir = tempfile.TemporaryDirectory(prefix="vminv-teste-")
        self.caminho = os.path.join(self.dir.name, "id_chave_teste")
        with open(self.caminho, "w", encoding="utf-8") as f:
            f.write(f"-----BEGIN OPENSSH PRIVATE KEY-----\n{CONTEUDO_CHAVE}\n-----END OPENSSH PRIVATE KEY-----\n")
        return self

    def __exit__(self, *exc):
        self.dir.cleanup()


def baseline_texto(*regras, versao="1", aplica_a="vms-do-parque"):
    """Baseline no layout oficial. Cada regra: (id pontilhado, valor em YAML de uma linha, severidade)."""
    grupos = {}
    niveis = {"critico": [], "alto": [], "medio": []}
    for regra_id, valor, severidade in regras:
        grupo, nome = regra_id.split(".", 1)
        grupos.setdefault(grupo, []).append(f"{nome}: {valor}")
        niveis[severidade].append(regra_id)
    esperado = "\n".join(f"  {g}: {{{', '.join(itens)}}}" for g, itens in grupos.items())
    severidade = "\n".join(f"  {n}: [{', '.join(ids)}]" for n, ids in niveis.items() if ids)
    return (f"versao: {versao}\naplica_a: {aplica_a}\nesperado:\n{esperado}\n"
            f"severidade:\n{severidade}\n")

