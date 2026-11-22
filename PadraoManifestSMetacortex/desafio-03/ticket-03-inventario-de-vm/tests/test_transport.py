import ast
import pathlib
import subprocess
import sys
import unittest

from tests.helpers import CONTEUDO_CHAVE, ChaveTemporaria, ExecutorFalso
from vminv import ssh_transport
from vminv.errors import FalhaDeConexao, FalhaDeExecucao
from vminv.ssh_transport import Resultado, classificar, coletar, montar_argv

PACOTE = pathlib.Path(__file__).resolve().parent.parent / "vminv"
BIBLIOTECAS_SSH = {"paramiko", "asyncssh", "fabric", "pexpect", "ssh2", "netmiko", "cryptography"}

STDERR_HOST_DESCONHECIDO = (
    b"No ED25519 host key is known for 10.0.0.5 and you have requested strict checking.\n"
    b"Host key verification failed.\n")
STDERR_HOST_ALTERADO = (
    b"@@@ WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED! @@@\n"
    b"Offending ED25519 key in /home/x/.ssh/known_hosts:5\nHost key verification failed.\n")
STDERR_AUTH = b"orpheu@10.0.0.5: Permission denied (publickey).\n"
STDERR_TIMEOUT = b"ssh: connect to host 10.0.0.5 port 22: Connection timed out\n"


class ArgvTest(unittest.TestCase):  # 2.1
    def argv(self, **kw):
        return montar_argv("10.0.0.5", "orpheu", "/k/id", **kw)

    def test_opcoes_obrigatorias(self):
        argv = self.argv(timeout=7)
        self.assertEqual(argv[0], "ssh")
        self.assertEqual(argv[argv.index("-i") + 1], "/k/id")
        self.assertIn("BatchMode=yes", argv)
        self.assertIn("IdentitiesOnly=yes", argv)  # só a chave de -i é oferecida (D8)
        self.assertIn("ConnectTimeout=7", argv)
        self.assertIn("StrictHostKeyChecking=yes", argv)
        self.assertEqual(argv[-3:], ["orpheu@10.0.0.5", "sh", "-s"])

    def test_chave_so_como_caminho_e_sem_flags_proibidas(self):
        argv = self.argv()
        self.assertEqual(argv.count("/k/id"), 1)
        self.assertNotIn("-v", argv)
        self.assertNotIn("-vv", argv)
        juntos = " ".join(argv)
        self.assertNotIn("StrictHostKeyChecking=no", juntos)
        self.assertNotIn("UserKnownHostsFile", juntos)

    def test_nenhuma_biblioteca_ssh_importada_pelo_pacote(self):
        stdlib = sys.stdlib_module_names
        for arquivo in PACOTE.glob("*.py"):
            arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
            for no in ast.walk(arvore):
                if isinstance(no, ast.Import):
                    nomes = [a.name.split(".")[0] for a in no.names]
                elif isinstance(no, ast.ImportFrom) and no.level == 0:
                    nomes = [no.module.split(".")[0]]
                else:
                    continue
                for nome in nomes:
                    self.assertNotIn(nome, BIBLIOTECAS_SSH, f"{arquivo.name} importa {nome}")
                    self.assertIn(nome, stdlib, f"{arquivo.name} importa fora da stdlib: {nome}")

    def test_coleta_usa_subprocesso_com_script_por_stdin(self):
        with ChaveTemporaria() as k:
            ex = ExecutorFalso(stdout=b"{}")
            coletar("10.0.0.5", "orpheu", k.caminho, executor=ex, ssh_bin="ssh")
        argv, kwargs = ex.chamadas[0]
        self.assertEqual(argv[-2:], ["sh", "-s"])
        self.assertEqual(kwargs["input"], ssh_transport.ler_coletor())
        self.assertNotIn(CONTEUDO_CHAVE.encode(), kwargs["input"])


class ClassificacaoTest(unittest.TestCase):  # 2.2
    def test_categorias(self):
        casos = [
            (0, "", Resultado.SUCESSO),
            (255, STDERR_TIMEOUT.decode(), Resultado.INALCANCAVEL),
            (255, "ssh: connect to host x port 22: Connection refused", Resultado.INALCANCAVEL),
            (255, "ssh: Could not resolve hostname x", Resultado.INALCANCAVEL),
            (255, "texto que ninguém reconhece", Resultado.INALCANCAVEL),   # fallback de conexão
            (255, "", Resultado.INALCANCAVEL),
            (255, STDERR_HOST_DESCONHECIDO.decode(), Resultado.HOST_DESCONHECIDO),
            (255, STDERR_HOST_ALTERADO.decode(), Resultado.HOST_ALTERADO),
            (255, STDERR_AUTH.decode(), Resultado.AUTENTICACAO),
            (1, "", Resultado.OUTRA),
            (127, "sh: ...", Resultado.OUTRA),
        ]
        for codigo, texto, esperado in casos:
            with self.subTest(codigo=codigo, texto=texto[:30]):
                self.assertEqual(classificar(codigo, texto), esperado)

    def test_status_de_saida_vem_antes_do_texto(self):
        # texto de "permission denied" com status 0 ou 1 não vira falha de autenticação
        self.assertEqual(classificar(0, "Permission denied"), Resultado.SUCESSO)
        self.assertEqual(classificar(1, "Permission denied"), Resultado.OUTRA)


class FalhasEDoublesTest(unittest.TestCase):  # 2.4
    def falha(self, executor, **kw):
        with ChaveTemporaria() as k:
            with self.assertRaises(FalhaDeExecucao) as cm:
                coletar("10.0.0.5", "orpheu", k.caminho, executor=executor, ssh_bin="ssh", **kw)
        return cm.exception

    def test_host_inalcancavel(self):
        f = self.falha(ExecutorFalso(255, stderr=STDERR_TIMEOUT))
        self.assertIsInstance(f, FalhaDeConexao)
        self.assertIn("inalcançável", f.mensagem)

    def test_autenticacao_rejeitada(self):
        f = self.falha(ExecutorFalso(255, stderr=STDERR_AUTH))
        self.assertIsInstance(f, FalhaDeConexao)
        self.assertIn("rejeitou a autenticação", f.mensagem)

    def test_timeout_da_sessao(self):
        f = self.falha(ExecutorFalso(levanta=subprocess.TimeoutExpired("ssh", 120)))
        self.assertIsInstance(f, FalhaDeConexao)
        self.assertIn("tempo máximo", f.mensagem)

    def test_outra_falha(self):
        f = self.falha(ExecutorFalso(3))
        self.assertIn("não classificado", f.mensagem)

    def test_ssh_ausente(self):
        f = self.falha(ExecutorFalso(levanta=FileNotFoundError()))
        self.assertIn("cliente ssh", f.mensagem)

    def test_chave_inexistente_cita_o_caminho_e_nao_conecta(self):
        ex = ExecutorFalso()
        with self.assertRaises(FalhaDeExecucao) as cm:
            coletar("10.0.0.5", "orpheu", "/nao/existe/id", executor=ex, ssh_bin="ssh")
        self.assertIn("/nao/existe/id", cm.exception.mensagem)
        self.assertEqual(ex.chamadas, [])


class HostKeyTest(unittest.TestCase):  # 2.5
    def test_padrao_e_strict_yes(self):
        with ChaveTemporaria() as k:
            ex = ExecutorFalso(stdout=b"{}")
            coletar("10.0.0.5", "orpheu", k.caminho, executor=ex, ssh_bin="ssh")
        self.assertIn("StrictHostKeyChecking=yes", ex.chamadas[0][0])

    def test_host_desconhecido_recusado_por_padrao(self):
        with ChaveTemporaria() as k, self.assertRaises(FalhaDeConexao) as cm:
            coletar("10.0.0.5", "orpheu", k.caminho, ssh_bin="ssh",
                    executor=ExecutorFalso(255, stderr=STDERR_HOST_DESCONHECIDO))
        self.assertIn("desconhecida", cm.exception.mensagem)
        self.assertIn("--aceitar-host-novo", cm.exception.mensagem)

    def test_flag_usa_accept_new_e_nunca_no(self):
        with ChaveTemporaria() as k:
            ex = ExecutorFalso(stdout=b"{}")
            coletar("10.0.0.5", "orpheu", k.caminho, aceitar_host_novo=True, executor=ex, ssh_bin="ssh")
        argv = ex.chamadas[0][0]
        self.assertIn("StrictHostKeyChecking=accept-new", argv)
        self.assertNotIn("StrictHostKeyChecking=yes", argv)
        self.assertNotIn("StrictHostKeyChecking=no", " ".join(argv))

    def test_host_alterado_recusado_mesmo_com_a_flag(self):
        with ChaveTemporaria() as k, self.assertRaises(FalhaDeConexao) as cm:
            coletar("10.0.0.5", "orpheu", k.caminho, aceitar_host_novo=True, ssh_bin="ssh",
                    executor=ExecutorFalso(255, stderr=STDERR_HOST_ALTERADO))
        self.assertIn("alterada", cm.exception.mensagem)


if __name__ == "__main__":
    unittest.main()
