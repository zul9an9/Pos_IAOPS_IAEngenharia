"""Verificações contra o host de laboratório real (tarefas 2.5c, 3.6, 3.9 e 3.10).

Só rodam com VMINV_LAB_HOST, VMINV_LAB_USER e VMINV_LAB_KEY definidos; caso contrário
são ignoradas. Nenhum comando aqui altera o host: as capturas de estado usam apenas
leitura, feitas em sessões SSH separadas da do coletor (para a verificação não ser circular).
"""

import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

from vminv import inventory, ssh_transport

HOST = os.environ.get("VMINV_LAB_HOST")
USUARIO = os.environ.get("VMINV_LAB_USER")
CHAVE = os.environ.get("VMINV_LAB_KEY")
LAB = bool(HOST and USUARIO and CHAVE)

# O estado comparado antes/depois da coleta (tarefa 3.9). A linha de log da sessão SSH
# (sshd/journal/wtmp) é rastro esperado da própria conexão e NÃO faz parte deste conjunto.
SNAPSHOT = r"""
echo '== systemctl list-units (service,socket ativos) =='
systemctl list-units --type=service,socket --state=active --no-legend --plain --no-pager | awk '{print $1, $3, $4}' | sort
echo '== /proc/swaps =='
cat /proc/swaps
echo '== ss -ltn =='
ss -ltn | sort
echo '== authorized_keys (sha256 + mtime) =='
sha256sum "$HOME/.ssh/authorized_keys"
stat -c '%Y' "$HOME/.ssh/authorized_keys"
"""


def ssh_snapshot():
    argv = ssh_transport.montar_argv(HOST, USUARIO, CHAVE)[:-2] + ["sh", "-s"]
    proc = subprocess.run(argv, input=SNAPSHOT.encode(), capture_output=True, timeout=120)
    if proc.returncode != 0:
        raise AssertionError("não foi possível capturar o estado do host")
    return proc.stdout.decode("utf-8", errors="replace")


def coletar():
    return inventory.interpretar_resposta(ssh_transport.coletar(HOST, USUARIO, CHAVE), HOST)


@unittest.skipUnless(LAB, "defina VMINV_LAB_HOST, VMINV_LAB_USER e VMINV_LAB_KEY")
class LaboratorioTest(unittest.TestCase):
    def test_somente_leitura_estado_do_host_igual_antes_e_depois(self):  # 3.9
        antes = ssh_snapshot()
        coletar()
        depois = ssh_snapshot()
        self.assertEqual(antes, depois, "o estado do host mudou após a coleta")

    def test_coleta_repetida_e_idempotente(self):  # 3.10
        a, b = coletar().como_dict(), coletar().como_dict()
        a.pop("coletado_em")
        b.pop("coletado_em")
        self.assertEqual(a, b)

    @unittest.skipUnless(shutil.which("ssh-keygen"), "ssh-keygen indisponível")
    def test_chave_errada_e_rejeitada_mesmo_com_chave_padrao_do_operador(self):  # D8: IdentitiesOnly
        from vminv.errors import FalhaDeConexao
        with tempfile.TemporaryDirectory() as tmp:
            errada = os.path.join(tmp, "chave_errada")
            subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", errada], check=True,
                           capture_output=True)
            with self.assertRaises(FalhaDeConexao) as cm:
                ssh_transport.coletar(HOST, USUARIO, errada)
        self.assertIn("rejeitou a autenticação", cm.exception.mensagem)

    def test_login_de_root_sem_privilegio_e_nao_lido(self):  # 3.6 (ramo sem privilégio)
        fato = coletar().fato("ssh_login_root")
        self.assertFalse(fato.lido)
        self.assertTrue(fato.motivo)


@unittest.skipUnless(LAB and shutil.which("ssh"), "defina VMINV_LAB_* e tenha o ssh no PATH")
class HostKeyRealTest(unittest.TestCase):  # 2.5 — com o ssh real e um known_hosts isolado
    """Isola o known_hosts trocando HOME/USERPROFILE; só vale se o ssh respeitar a variável."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        global BASELINE
        BASELINE = pathlib.Path(cls.tmp.name, "baseline.yaml")
        BASELINE.write_text(
            "versao: 1\naplica_a: vms-do-parque\nesperado:\n  swap: {habilitado: true}\n"
            "severidade:\n  medio: [swap.habilitado]\n",
            encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def executar(self, *extras, home):
        env = {**os.environ, "HOME": home, "USERPROFILE": home}
        return subprocess.run(
            [os.sys.executable, "-m", "vminv", "--host", HOST, "--usuario", USUARIO, "--chave", CHAVE,
             "--baseline", str(BASELINE), *extras],
            capture_output=True, text=True, encoding="utf-8", env=env,
            cwd=str(pathlib.Path(__file__).resolve().parent.parent), timeout=180)

    def test_desconhecido_recusado_aceitar_novo_prossegue_e_alterado_e_recusado(self):
        with tempfile.TemporaryDirectory() as home:
            os.makedirs(os.path.join(home, ".ssh"))
            # (a) known_hosts vazio: host desconhecido é recusado por padrão
            proc = self.executar(home=home)
            if "inalcançável" in proc.stderr or "não foi possível" in proc.stderr:
                self.skipTest("o ssh do sistema não respeitou o HOME isolado")
            self.assertEqual(proc.returncode, 2, proc.stderr)
            self.assertIn("desconhecida", proc.stderr)
            self.assertEqual(proc.stdout, "")
            # (b) com --aceitar-host-novo a conexão prossegue e o host passa a constar
            proc = self.executar("--aceitar-host-novo", home=home)
            self.assertIn(proc.returncode, (0, 1), proc.stderr)
            known = pathlib.Path(home, ".ssh", "known_hosts")
            self.assertTrue(known.exists() and HOST in known.read_text())
            # (c) chave do host adulterada no known_hosts: recusada MESMO com a flag
            linhas = known.read_text().splitlines()
            adulteradas = []
            for linha in linhas:
                partes = linha.split(" ")
                blob = partes[2]
                partes[2] = blob[:-6] + ("AAAAAA" if not blob.endswith("AAAAAA") else "BBBBBB")
                adulteradas.append(" ".join(partes))
            known.write_text("\n".join(adulteradas) + "\n")
            proc = self.executar("--aceitar-host-novo", home=home)
            self.assertEqual(proc.returncode, 2, proc.stderr)
            self.assertIn("alterada", proc.stderr)


if __name__ == "__main__":
    unittest.main()
