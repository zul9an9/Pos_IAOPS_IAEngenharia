"""Testes do script remoto de coleta (tarefas 3.1–3.8 e revisão estática de 3.9)."""

import json
import re
import shutil
import pathlib
import subprocess
import tempfile
import unittest

from vminv import inventory, ssh_transport

SCRIPT = ssh_transport.ler_coletor().decode("utf-8")
FATOS = inventory.FATOS_ESPERADOS


def sem_comentarios(texto):
    return "\n".join(l for l in texto.splitlines() if not l.lstrip().startswith("#"))


def sem_aspas(texto):
    """Remove trechos entre aspas simples/duplas (programas awk/sed, mensagens, JSON)."""
    texto = re.sub(r"'[^']*'", "''", texto)
    return re.sub(r'"(?:\\.|[^"\\])*"', '""', texto)


def executar_sh(comando, script=SCRIPT):
    return subprocess.run(comando, input=script.encode("utf-8"), capture_output=True, timeout=120)


def coletar_local():
    if not shutil.which("sh"):
        raise unittest.SkipTest("sh não disponível nesta máquina")
    proc = executar_sh(["sh", "-s"])
    return proc


def coletar_wsl():
    if not shutil.which("wsl"):
        raise unittest.SkipTest("wsl não disponível")
    try:
        proc = executar_sh(["wsl", "-d", "Ubuntu", "-e", "sh", "-s"])
    except (OSError, subprocess.TimeoutExpired):
        raise unittest.SkipTest("WSL Ubuntu indisponível")
    if proc.returncode != 0 or not proc.stdout.strip().startswith(b"{"):
        raise unittest.SkipTest("WSL Ubuntu indisponível")
    return json.loads(proc.stdout.decode("utf-8"))


class PosixTest(unittest.TestCase):  # 3.1 — sh POSIX, sem bashismos
    def test_sem_bashismos(self):
        codigo = sem_aspas(sem_comentarios(SCRIPT))
        proibidos = [r"\[\[", r"<\(", r">\(", r"\$\{[^}]*(,,|\^\^)", r"\bfunction\b", r"(?m)^\s*local\s",
                     r"\bdeclare\b", r"\bsource\b", r"&>", r"<<<", r"\$\(\(", r"\bmapfile\b",
                     r"\bselect\b", r"==", r"\$'", r"\$\{!"]
        for padrao in proibidos:
            self.assertIsNone(re.search(padrao, codigo), f"bashismo: {padrao}")

    def test_nenhum_shebang_de_bash(self):
        self.assertNotIn("bash", sem_comentarios(SCRIPT))

    def test_sintaxe_sob_sh_local(self):
        if not shutil.which("sh"):
            self.skipTest("sh não disponível")
        proc = executar_sh(["sh", "-n"])
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_sintaxe_e_execucao_sob_dash(self):
        if not shutil.which("wsl"):
            self.skipTest("wsl não disponível")
        try:
            proc = executar_sh(["wsl", "-d", "Ubuntu", "-e", "dash", "-n"])
        except (OSError, subprocess.TimeoutExpired):
            self.skipTest("WSL Ubuntu indisponível")
        if proc.returncode != 0 and b"not found" in proc.stderr.lower():
            self.skipTest("dash indisponível")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(coletar_wsl())  # executa de fato sob o /bin/sh (dash) do host


class RevisaoEstaticaSomenteLeituraTest(unittest.TestCase):  # 3.9 — checklist estática
    CODIGO = sem_aspas(sem_comentarios(SCRIPT))

    def test_nenhum_comando_mutante(self):
        proibidos = ["rm", "rmdir", "mv", "cp", "touch", "mkdir", "mkfifo", "mktemp", "tee", "chmod",
                     "chown", "chgrp", "ln", "dd", "truncate", "install", "apt", "apt-get", "dpkg",
                     "yum", "dnf", "rpm", "pip", "npm", "useradd", "usermod", "passwd", "kill", "pkill",
                     "reboot", "shutdown", "sudo", "su", "curl", "wget", "nc", "scp", "sftp", "crontab"]
        for palavra in proibidos:
            self.assertIsNone(re.search(rf"(?<![\w./-]){re.escape(palavra)}(?![\w-])", self.CODIGO),
                              f"comando proibido no script: {palavra}")

    def test_sed_sem_edicao_in_place(self):
        self.assertIsNone(re.search(r"\bsed\b[^|\n]*\s-[a-zA-Z]*i", self.CODIGO))

    def test_unico_redirecionamento_de_saida_e_para_dev_null(self):
        for m in re.finditer(r">", self.CODIGO):
            depois = self.CODIGO[m.end():m.end() + 9]
            self.assertTrue(depois.startswith(("/dev/null", "&1")), f"redirecionamento suspeito: {depois!r}")

    def test_systemctl_somente_consulta(self):
        subcomandos = set(re.findall(r"systemctl\s+([a-z][a-z-]*)", self.CODIGO))
        self.assertLessEqual(subcomandos, {"list-units", "is-active"})

    def test_sshd_so_em_modo_de_teste(self):
        codigo = sem_comentarios(SCRIPT)
        execucoes = re.findall(r'\$\("\$sshd_bin"([^)]*)\)', codigo)
        self.assertEqual(len(execucoes), 1)
        self.assertTrue(execucoes[0].lstrip().startswith("-T "), execucoes)

    def test_ss_e_ssh_keygen_somente_leitura(self):
        self.assertEqual(set(re.findall(r"\bss\s+(-\w+)", self.CODIGO)), {"-ltnp"})
        self.assertEqual(set(re.findall(r"ssh-keygen\s+(-\w+)", self.CODIGO)), {"-lf"})

    def test_stdin_do_script_protegido(self):
        self.assertTrue(SCRIPT.rstrip().endswith("exit 0"))
        self.assertIn("main </dev/null", SCRIPT)


class SaidaLocalTest(unittest.TestCase):  # 3.1, 3.3 (swap desabilitado), 3.8
    def test_json_valido_com_todos_os_fatos_em_envelope(self):
        proc = coletar_local()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        dados = json.loads(proc.stdout.decode("utf-8"))
        self.assertEqual(dados["formato"], 1)
        for nome in FATOS:
            self.assertIn(nome, dados)
        inv = inventory.interpretar_resposta(proc.stdout.decode("utf-8"), "local")
        self.assertTrue(inv.fato("hostname").lido)
        self.assertTrue(inv.fato("coletado_em").lido)
        self.assertTrue(inv.fato("kernel").lido)


class SaidaWslTest(unittest.TestCase):  # 3.1–3.5, 3.7 contra um host Linux real
    @classmethod
    def setUpClass(cls):
        cls.dados = coletar_wsl()

    def valor(self, nome):
        fato = self.dados[nome]
        self.assertTrue(fato["read"], f"{nome} não lido: {fato.get('reason')}")
        return fato["value"]

    def test_identificacao_so_e_kernel(self):  # 3.1
        self.assertTrue(self.valor("hostname"))
        self.assertRegex(self.valor("coletado_em"), r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        so = self.valor("so")
        self.assertRegex(so["distribuicao"], r"^[a-z0-9._-]+$")  # ID do os-release, em minúsculas
        self.assertTrue(so["versao"])
        self.assertTrue(self.valor("kernel"))

    def test_servicos_distinguem_service_de_socket(self):  # 3.2
        unidades = self.valor("servicos")
        tipos = {u["tipo"] for u in unidades}
        self.assertEqual(tipos, {"service", "socket"})
        for u in unidades:
            self.assertTrue(u["nome"].endswith("." + u["tipo"]))
            self.assertEqual(u["estado"], "active")

    def test_swap(self):  # 3.3 (ramo habilitado; o desabilitado é testado localmente/unitariamente)
        swap = self.valor("swap")
        self.assertIsInstance(swap["habilitado"], bool)
        self.assertGreaterEqual(swap["tamanho_kib"], 0)
        self.assertEqual(swap["habilitado"], swap["tamanho_kib"] > 0)

    def test_portas_com_endereco_e_dono(self):  # 3.4
        portas = self.valor("portas")
        self.assertTrue(portas)
        for p in portas:
            self.assertIsInstance(p["porta"], int)
            self.assertTrue(p["endereco"])
            self.assertIn("read", p["processo"])

    def test_chaves_ssh_sem_material_da_chave(self):  # 3.5
        v = self.valor("chaves_ssh")
        self.assertEqual(v["escopo"], "usuario_conectado")
        for chave in v["chaves"]:
            self.assertTrue(chave["tipo"].startswith(("ssh-", "ecdsa-", "sk-")))
            for campo in chave.values():
                self.assertNotRegex(str(campo), r"AAAA[A-Za-z0-9+/]{20,}")

    def test_login_root_sem_privilegio_e_nao_lido_com_motivo(self):  # 3.6 (ramo sem privilégio)
        fato = self.dados["ssh_login_root"]
        if fato["read"]:
            self.skipTest("o usuário da coleta tem privilégio neste host")
        self.assertTrue(fato["reason"])

    def test_ntp(self):  # 3.7
        ntp = self.valor("ntp")
        self.assertIn("mecanismo", ntp)
        self.assertEqual(ntp["ativo"], ntp["mecanismo"] != "nenhum")


class SentinelaTest(unittest.TestCase):  # 3.8
    VAZIOS_LIDOS = [[], "", 0, False, None, {}, {"habilitado": False, "tamanho_kib": 0}]

    def test_sentinela_difere_de_todo_vazio_lido(self):
        nao_lido = {"read": False, "reason": "sem privilégio"}
        for vazio in self.VAZIOS_LIDOS:
            lido = {"read": True, "value": vazio}
            self.assertNotEqual(nao_lido, lido)
            self.assertNotEqual(nao_lido["read"], lido["read"])
            self.assertNotIn("value", nao_lido)
            self.assertNotIn("reason", lido)

    def test_saida_do_coletor_respeita_o_formato_da_sentinela(self):
        for proc in (coletar_local(),):
            dados = json.loads(proc.stdout.decode("utf-8"))
            self._checar(dados)
        self._checar(coletar_wsl())

    def _checar(self, dados):
        def percorrer(no):
            if isinstance(no, dict):
                if "read" in no:
                    self.assertIsInstance(no["read"], bool)
                    if no["read"]:
                        self.assertIn("value", no)
                        self.assertNotIn("reason", no)
                    else:
                        self.assertEqual(set(no), {"read", "reason"})
                        self.assertTrue(no["reason"])
                for v in no.values():
                    percorrer(v)
            elif isinstance(no, list):
                for v in no:
                    percorrer(v)
        for nome in FATOS:
            self.assertIn("read", dados[nome], nome)
        percorrer(dados)

    def test_swap_desabilitado_e_lido_e_diferente_de_nao_lido(self):
        dados = coletar_local()
        swap = json.loads(dados.stdout.decode("utf-8"))["swap"]
        if not swap["read"]:
            self.skipTest("sem /proc/swaps nesta máquina")
        if swap["value"]["habilitado"]:
            self.skipTest("swap habilitado nesta máquina")
        self.assertEqual(swap["value"], {"habilitado": False, "tamanho_kib": 0})


class SwapComFixtureTest(unittest.TestCase):  # 3.3 — ramos habilitado/desabilitado/ilegível
    CABECALHO = "Filename\t\t\t\tType\t\tSize\t\tUsed\t\tPriority\n"

    def swap_com(self, conteudo):
        """Roda o coletor real trocando só o caminho de /proc/swaps por um arquivo de fixture."""
        if not shutil.which("sh"):
            self.skipTest("sh não disponível")
        with tempfile.TemporaryDirectory() as tmp:
            alvo = pathlib.Path(tmp, "swaps")
            if conteudo is not None:
                alvo.write_text(conteudo, encoding="utf-8")
            script = SCRIPT.replace("/proc/swaps", alvo.as_posix())
            proc = executar_sh(["sh", "-s"], script)
        return json.loads(proc.stdout.decode("utf-8"))["swap"]

    def test_desabilitado_e_lido_como_falso_e_zero(self):
        self.assertEqual(self.swap_com(self.CABECALHO),
                         {"read": True, "value": {"habilitado": False, "tamanho_kib": 0}})

    def test_habilitado_soma_os_tamanhos(self):
        conteudo = (self.CABECALHO + "/swapfile\t\t\tfile\t\t2097152\t\t0\t\t-2\n"
                    "/dev/sdb1\t\t\tpartition\t1024\t\t0\t\t-3\n")
        self.assertEqual(self.swap_com(conteudo),
                         {"read": True, "value": {"habilitado": True, "tamanho_kib": 2098176}})

    def test_arquivo_ilegivel_e_nao_lido_e_nao_falso(self):
        fato = self.swap_com(None)
        self.assertFalse(fato["read"])
        self.assertNotIn("value", fato)


class LoginRootComPrivilegioTest(unittest.TestCase):  # 3.6 — ramo COM privilégio (root no WSL, só leitura)
    def test_valor_efetivo_e_devolvido(self):
        if not shutil.which("wsl"):
            self.skipTest("wsl não disponível")
        try:
            proc = executar_sh(["wsl", "-d", "Ubuntu", "-u", "root", "-e", "sh", "-s"])
        except (OSError, subprocess.TimeoutExpired):
            self.skipTest("WSL Ubuntu indisponível")
        if proc.returncode != 0 or not proc.stdout.strip().startswith(b"{"):
            self.skipTest("WSL como root indisponível")
        fato = json.loads(proc.stdout.decode("utf-8"))["ssh_login_root"]
        if not fato["read"]:
            self.skipTest("sshd -T indisponível no WSL: " + fato["reason"])
        self.assertIn(fato["value"], {"yes", "no", "prohibit-password", "without-password",
                                      "forced-commands-only"})


if __name__ == "__main__":
    unittest.main()
