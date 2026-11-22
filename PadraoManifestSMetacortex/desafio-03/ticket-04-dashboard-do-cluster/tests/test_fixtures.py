"""As fixtures capturadas contêm os casos descritos em proposal.md (tarefa 3.1)."""

from conftest import FIXTURES, carregar, por_nome

TIPOS = ("pods", "deployments", "services", "endpointslices", "events")


def test_nyx_prod_crashloop_oomkilled():
    pods = por_nome(carregar("nyx-prod", "pods"), "nyx-api-")
    assert len(pods) == 2
    for pod in pods:
        assert pod["status"]["phase"] == "Running"
        (status,) = pod["status"]["containerStatuses"]
        assert status["state"]["waiting"]["reason"] == "CrashLoopBackOff"
        assert status["lastState"]["terminated"]["reason"] == "OOMKilled"
        assert status["lastState"]["terminated"]["exitCode"] == 137
        assert status["restartCount"] > 150


def test_nyx_prod_evento_com_count_alto():
    backoff = [e for e in carregar("nyx-prod", "events") if e["reason"] == "BackOff"]
    assert backoff and all(e["count"] > 100 for e in backoff)


def test_orion_stg_deployment_sem_ready_replicas():
    (dep,) = por_nome(carregar("orion-stg", "deployments"), "orion-web")
    assert dep["spec"]["replicas"] == 3
    assert "readyReplicas" not in dep["status"]


def test_nyx_stg_endpointslice_sem_endpoints():
    (slice_,) = [s for s in carregar("nyx-stg", "endpointslices")
                 if s["metadata"]["labels"]["kubernetes.io/service-name"] == "nyx-api"]
    assert slice_.get("endpoints") is None


def test_orion_prod_dois_enderecos_prontos():
    slices = [s for s in carregar("orion-prod", "endpointslices")
              if s["metadata"]["labels"]["kubernetes.io/service-name"] == "orion-fake-shop"]
    enderecos = [e for s in slices for e in s["endpoints"]]
    assert len(enderecos) == 2 and all(e["conditions"]["ready"] for e in enderecos)


def test_nyx_prod_enderecos_nenhum_pronto():
    slices = [s for s in carregar("nyx-prod", "endpointslices")
              if s["metadata"]["labels"]["kubernetes.io/service-name"] == "nyx-api"]
    enderecos = [e for s in slices for e in s["endpoints"]]
    assert len(enderecos) == 2 and not any(e["conditions"]["ready"] for e in enderecos)


def test_kube_public_vazio():
    assert all(carregar("kube-public", tipo) == [] for tipo in TIPOS)


def test_fixtures_sem_senhas_do_laboratorio():
    for arquivo in FIXTURES.rglob("*.json"):
        texto = arquivo.read_text(encoding="utf-8")
        assert "Pg#123" not in texto and "Pg1234" not in texto, arquivo
