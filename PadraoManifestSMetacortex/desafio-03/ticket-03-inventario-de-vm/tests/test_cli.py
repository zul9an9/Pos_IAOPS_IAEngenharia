import contextlib
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

from tests.helpers import CONTEUDO_CHAVE, ChaveTemporaria, ExecutorFalso, baseline_texto, resposta_bruta
from vminv import cli

RAIZ = pathlib.Path(__file__).resolve().parent.parent


def baseline_swap(esperado):
    return baseline_texto(("swap.habilitado", esperado, "medio"))


STDERR_AUTH = b"orpheu@10.0.0.5: Permission denied (publickey).\n"
STDERR_TIMEOUT = b"ssh: connect to host 10.0.0.5 port 22: Connection timed out\n"
STDERR_HOST_DESCONHECIDO = b"No ED25519 host key is known.\nHost key verification failed.\n"


def resposta_ok(**kw):
    return json.dumps(resposta_bruta(**kw)).encode("utf-8")


class Ambiente:
    """Diretório temporário com chave sentinela e baseline; roda `cli.main` capturando tudo."""

    def __init__(self, baseline_texto=None):
        self.baseline_texto = baseline_swap("true") if baseline_texto is None else baseline_texto

    def __enter__(self):
        self.chave = ChaveTemporaria().__enter__()
        self.dir = pathlib.Path(self.chave.dir.name)
        self.baseline = self.dir / "baseline.yaml"
        self.baseline.write_text(self.baseline_texto, encoding="utf-8")
        return self

    def __exit__(self, *exc):
        self.chave.__exit__(*exc)

    def args(self, *extras, chave=None, baseline=None):
        return ["--host", "10.0.0.5", "--usuario", "orpheu", "--chave", chave or self.chave.caminho,
                "--baseline", baseline or str(self.baseline), *extras]

    def rodar(self, argv, executor):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            codigo = cli.main(argv, executor=executor)
        return codigo, out.getvalue(), err.getvalue()


class ArgumentosTest(unittest.TestCase):  # 1.1, 1.2
    def test_help_roda_so_com_stdlib_e_sem_requirements(self):
        proc = subprocess.run([sys.executable, "-m", "vminv", "--help"], cwd=RAIZ, capture_output=True,
                              text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("--aceitar-host-novo", proc.stdout)
        self.assertFalse((RAIZ / "requirements.txt").exists())

    def test_layout_do_pacote(self):
        for nome in ("cli.py", "ssh_transport.py", "collector.sh", "baseline.py", "compliance.py", "report.py"):
            self.assertTrue((RAIZ / "vminv" / nome).exists(), nome)

    def rodar_sem_ssh(self, argv):
        out, err = io.StringIO(), io.StringIO()
        ex = ExecutorFalso(stdout=resposta_ok())
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            codigo = cli.main(argv, executor=ex)
        self.assertEqual(ex.chamadas, [], "não deve conectar com uso incorreto")
        return codigo, out.getvalue(), err.getvalue()

    def test_sem_argumentos_sai_com_2_e_mensagem_simples(self):
        codigo, out, err = self.rodar_sem_ssh([])
        self.assertEqual(codigo, 2)
        self.assertEqual(out, "")
        self.assertIn("faltam argumentos obrigatórios", err)
        for flag in ("--host", "--usuario", "--chave", "--baseline"):
            self.assertIn(flag, err)
        self.assertNotIn("Traceback", err)

    def test_argumento_faltando_e_apontado(self):
        codigo, _, err = self.rodar_sem_ssh(["--host", "h", "--usuario", "u", "--chave", "k"])
        self.assertEqual(codigo, 2)
        self.assertIn("--baseline", err)
        self.assertNotIn("--usuario,", err)

    def test_argumento_desconhecido_ou_invalido(self):
        for argv in (["--nao-existe"], ["--formato", "xml"], ["--timeout", "abc"], ["--hosts", "a"],
                     ["--host", "a", "b"]):
            with self.subTest(argv=argv):
                codigo, _, err = self.rodar_sem_ssh(argv)
                self.assertEqual(codigo, 2)
                self.assertIn("argumentos inválidos", err)
                self.assertNotIn("Traceback", err)

    def test_um_unico_host_por_execucao(self):
        # --host é um valor único (nunca uma lista de hosts) e não há como passar vários alvos
        acao = next(a for a in cli.criar_parser()._actions if a.dest == "host")
        self.assertIsNone(acao.nargs)
        self.assertNotIn(type(acao).__name__, ("_AppendAction", "_ExtendAction"))


class DestinoDasSaidasTest(unittest.TestCase):  # 7.3
    def test_padrao_markdown_no_stdout_e_nenhum_arquivo(self):
        with Ambiente() as amb:
            antes = set(os.listdir(amb.dir))
            codigo, out, err = amb.rodar(amb.args(), ExecutorFalso(stdout=resposta_ok()))
            self.assertEqual(set(os.listdir(amb.dir)), antes)
        self.assertEqual(codigo, 0)
        self.assertTrue(out.startswith("# Inventário — host-teste (10.0.0.5)"))
        self.assertEqual(err, "")

    def test_formato_json_deixa_so_json_no_stdout(self):
        with Ambiente() as amb:
            codigo, out, err = amb.rodar(amb.args("--formato", "json"), ExecutorFalso(stdout=resposta_ok()))
        self.assertEqual(codigo, 0)
        self.assertIn("conformidade", json.loads(out))
        self.assertEqual(err, "")

    def test_saidas_em_arquivo_e_os_dois_formatos_numa_execucao(self):
        with Ambiente() as amb:
            j, m = amb.dir / "r.json", amb.dir / "r.md"
            codigo, out, _ = amb.rodar(amb.args("--saida-json", str(j), "--saida-markdown", str(m)),
                                       ExecutorFalso(stdout=resposta_ok()))
            self.assertEqual(codigo, 0)
            self.assertIn("conformidade", json.loads(j.read_text(encoding="utf-8")))
            self.assertEqual(m.read_text(encoding="utf-8"), out)  # stdout padrão = markdown

    def test_arquivo_e_stdout_json_coincidem(self):
        with Ambiente() as amb:
            j = amb.dir / "r.json"
            _, out, _ = amb.rodar(amb.args("--formato", "json", "--saida-json", str(j)),
                                  ExecutorFalso(stdout=resposta_ok()))
            self.assertEqual(j.read_text(encoding="utf-8"), out)

    def test_arquivo_nao_gravavel_sai_com_2(self):
        with Ambiente() as amb:
            destino = str(amb.dir / "nao_existe" / "r.json")
            codigo, out, err = amb.rodar(amb.args("--saida-json", destino), ExecutorFalso(stdout=resposta_ok()))
        self.assertEqual(codigo, 2)
        self.assertEqual(out, "")
        self.assertIn("não foi possível gravar o arquivo de saída", err)

    def test_erros_vao_so_para_o_stderr(self):
        with Ambiente() as amb:
            codigo, out, err = amb.rodar(amb.args(), ExecutorFalso(255, stderr=STDERR_TIMEOUT))
        self.assertEqual((codigo, out), (2, ""))
        self.assertIn("erro:", err)


class CodigosDeSaidaTest(unittest.TestCase):  # 8.1
    def test_zero_sem_desvio(self):
        with Ambiente() as amb:
            codigo, _, _ = amb.rodar(amb.args(), ExecutorFalso(stdout=resposta_ok()))
        self.assertEqual(codigo, 0)

    def test_zero_com_nao_verificado_apenas(self):
        with Ambiente(baseline_texto(("swap.habilitado", "true", "medio"),
                                     ("ssh.login_de_root", "false", "alto"))) as amb:
            codigo, out, _ = amb.rodar(amb.args(), ExecutorFalso(stdout=resposta_ok()))
        self.assertEqual(codigo, 0)
        self.assertIn("## Não verificado", out)
        self.assertIn("`ssh.login_de_root`", out)

    def test_um_com_desvio(self):
        with Ambiente(baseline_swap("false")) as amb:
            codigo, out, _ = amb.rodar(amb.args(), ExecutorFalso(stdout=resposta_ok()))
        self.assertEqual(codigo, 1)
        self.assertIn("| medio | `swap.habilitado` |", out)

    def test_dois_em_toda_falha_de_execucao(self):
        falhas = {
            "inalcançável": ExecutorFalso(255, stderr=STDERR_TIMEOUT),
            "host desconhecido": ExecutorFalso(255, stderr=STDERR_HOST_DESCONHECIDO),
            "autenticação": ExecutorFalso(255, stderr=STDERR_AUTH),
            "resposta truncada": ExecutorFalso(stdout=b'{"formato": 1, "hostn'),
            "resposta vazia": ExecutorFalso(stdout=b""),
        }
        for nome, executor in falhas.items():
            with self.subTest(nome), Ambiente() as amb:
                codigo, out, err = amb.rodar(amb.args(), executor)
                self.assertEqual(codigo, 2)
                self.assertEqual(out, "")  # nunca um relatório "conforme" parcial
                self.assertTrue(err.startswith("erro:"))

    def test_dois_para_baseline_invalido_sem_conectar(self):
        for texto in ("versao: 1\nregras: [", "regras:\n  swap.habilitado:\n    esperado: true\n"
                                              "    severidade: a\n", "a: &x 1\n"):
            with self.subTest(texto=texto[:15]), Ambiente(texto) as amb:
                ex = ExecutorFalso(stdout=resposta_ok())
                codigo, out, err = amb.rodar(amb.args(), ex)
                self.assertEqual(codigo, 2)
                self.assertEqual(ex.chamadas, [], "baseline inválido não deve tocar no host")
                self.assertIn("baseline inválido", err)
                self.assertEqual(out, "")

    def test_dois_para_baseline_inexistente(self):
        with Ambiente() as amb:
            codigo, _, err = amb.rodar(amb.args(baseline=str(amb.dir / "nada.yaml")), ExecutorFalso())
        self.assertEqual(codigo, 2)
        self.assertIn("baseline", err)


class MensagensDeFalhaTest(unittest.TestCase):  # 8.2
    CASOS = {
        "uso incorreto": ([], None, "faltam argumentos"),
        "host inalcançável": (None, ExecutorFalso(255, stderr=STDERR_TIMEOUT), "inalcançável"),
        "host desconhecido": (None, ExecutorFalso(255, stderr=STDERR_HOST_DESCONHECIDO), "desconhecida"),
        "chave rejeitada": (None, ExecutorFalso(255, stderr=STDERR_AUTH), "rejeitou a autenticação"),
        "resposta malformada": (None, ExecutorFalso(stdout=b"{"), "JSON"),
        "outra falha": (None, ExecutorFalso(7), "não classificado"),
        "exceção inesperada": (None, ExecutorFalso(levanta=RuntimeError("SEGREDO-INTERNO")), "inesperada"),
    }

    def test_cada_categoria_diz_o_que_ocorreu_sem_stack_trace_nem_chave(self):
        for nome, (argv, executor, trecho) in self.CASOS.items():
            with self.subTest(nome), Ambiente() as amb:
                codigo, out, err = amb.rodar(argv if argv is not None else amb.args(), executor)
                self.assertEqual(codigo, 2)
                self.assertIn(trecho, err)
                self.assertNotIn("Traceback", err)
                self.assertNotIn('File "', err)
                self.assertNotIn("SEGREDO-INTERNO", err)
                self.assertNotIn(CONTEUDO_CHAVE, err + out)
                self.assertEqual(len(err.strip().splitlines()), 1)

    def test_baseline_invalido(self):
        with Ambiente("versao: 5\nregras:\n  a:\n    esperado: 1\n    severidade: x\n") as amb:
            _, _, err = amb.rodar(amb.args(), ExecutorFalso())
        self.assertIn("baseline inválido", err)
        self.assertIn("futura", err)

    def test_texto_cru_do_ssh_nunca_e_repassado(self):
        stderr = b"debug1: identity file /k/id type -1\nPermission denied (publickey).\nSEGREDO-DO-SSH\n"
        with Ambiente() as amb:
            _, out, err = amb.rodar(amb.args(), ExecutorFalso(255, stderr=stderr))
        self.assertNotIn("SEGREDO-DO-SSH", err + out)
        self.assertNotIn("debug1", err + out)


if __name__ == "__main__":
    unittest.main()
