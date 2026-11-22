"""Tradução API → tela com fixtures reais e casos sintéticos (tarefas 3.2 a 3.5)."""

from conftest import carregar, por_nome

from painel_cluster import traducao


# --- 3.2 pods --------------------------------------------------------------

def test_pod_crashloop_nyx_prod():
    for item in por_nome(carregar("nyx-prod", "pods"), "nyx-api-"):
        esperado = item["status"]["containerStatuses"][0]["restartCount"]
        linha = traducao.pod(item)
        assert linha["fase"] == "Running"
        assert linha["prontos"] == "0/1"
        assert linha["reinicios"] == esperado and esperado > 150
        assert linha["motivo"] == "CrashLoopBackOff; última terminação: OOMKilled (exit 137)"


def test_pod_imagepullbackoff_orion_stg():
    for item in por_nome(carregar("orion-stg", "pods"), "orion-web-"):
        linha = traducao.pod(item)
        assert linha["motivo"] == "ImagePullBackOff"
        assert linha["reinicios"] == 0
        assert linha["prontos"] == "0/1"


def test_pod_pronto_sem_motivo():
    (item,) = por_nome(carregar("orion-prod", "pods"), "orion-fake-shop-db-")
    linha = traducao.pod(item)
    assert (linha["fase"], linha["prontos"], linha["motivo"]) == ("Running", "1/1", "")


def test_pod_sem_container_statuses():
    item = {"metadata": {"name": "pendente", "namespace": "x"},
            "spec": {"containers": [{"name": "app"}]},
            "status": {"phase": "Pending"}}
    linha = traducao.pod(item)
    assert (linha["fase"], linha["reinicios"], linha["prontos"], linha["motivo"]) == \
        ("Pending", 0, "0/1", "")


def test_pod_sem_status_nenhum():
    linha = traducao.pod({"metadata": {"name": "p", "namespace": "x"}})
    assert (linha["fase"], linha["reinicios"], linha["prontos"]) == ("—", 0, "0/0")


def test_falha_em_init_container_e_reinicios_somados():
    item = {
        "metadata": {"name": "p", "namespace": "orion-prod"},
        "spec": {"containers": [{"name": "app"}]},
        "status": {
            "phase": "Pending",
            "initContainerStatuses": [{
                "name": "db-migrate", "restartCount": 4, "ready": False,
                "state": {"waiting": {"reason": "CrashLoopBackOff"}},
                "lastState": {"terminated": {"reason": "Error", "exitCode": 1}},
            }],
            "containerStatuses": [{
                "name": "app", "restartCount": 0, "ready": False,
                "state": {"waiting": {"reason": "PodInitializing"}},
            }],
        },
    }
    linha = traducao.pod(item)
    assert linha["reinicios"] == 4
    assert linha["motivo"].startswith(
        "init container db-migrate: CrashLoopBackOff; última terminação: Error (exit 1)")


# --- 3.3 deployments --------------------------------------------------------

def test_deployment_sem_ready_replicas_orion_stg():
    (item,) = por_nome(carregar("orion-stg", "deployments"), "orion-web")
    assert traducao.deployment(item)["prontas"] == "0/3"


def test_deployment_pronto_orion_prod():
    (item,) = por_nome(carregar("orion-prod", "deployments"), "orion-fake-shop")
    assert traducao.deployment(item)["prontas"] == "2/2"


def test_deployment_sem_spec_replicas_nem_ready():
    linha = traducao.deployment({"metadata": {"name": "d", "namespace": "x"},
                                 "spec": {}, "status": {}})
    assert linha["prontas"] == "0/1"
    assert "None" not in linha["prontas"]


# --- 3.4 endpoints ----------------------------------------------------------

def _endpoint(ns, nome):
    linhas = traducao.services(carregar(ns, "services"), carregar(ns, "endpointslices"))
    return {l["nome"]: l["endpoint"] for l in linhas}[nome]


def test_service_sem_endpoint_nyx_stg():
    assert _endpoint("nyx-stg", "nyx-api") == "sem endpoint"


def test_service_com_enderecos_prontos_orion_prod():
    assert _endpoint("orion-prod", "orion-fake-shop") == "2 endereços, 2 prontos"


def test_service_com_enderecos_nenhum_pronto_nyx_prod():
    assert _endpoint("nyx-prod", "nyx-api") == "2 endereços, 0 prontos"


def _slice(nome, service, enderecos):
    return {"metadata": {"name": nome, "namespace": "x",
                         "labels": {"kubernetes.io/service-name": service}},
            "endpoints": [{"addresses": [ip], "conditions": {"ready": pronto}}
                          for ip, pronto in enderecos]}


def test_enderecos_em_varios_slices_sem_duplicar():
    service = {"metadata": {"name": "web", "namespace": "x"}, "spec": {"type": "ClusterIP"}}
    slices = [_slice("web-a", "web", [("10.0.0.1", True), ("10.0.0.2", False)]),
              _slice("web-b", "web", [("10.0.0.2", False), ("10.0.0.3", True)]),
              _slice("outro-a", "outro", [("10.0.0.9", True)])]
    assert traducao.services([service], slices)[0]["endpoint"] == "3 endereços, 2 prontos"


def test_service_sem_slice_algum():
    service = {"metadata": {"name": "web", "namespace": "x"}, "spec": {}}
    assert traducao.services([service], [])[0]["endpoint"] == "sem endpoint"


def test_service_external_name():
    service = {"metadata": {"name": "ext", "namespace": "x"},
               "spec": {"type": "ExternalName", "externalName": "db.example.com"}}
    assert traducao.services([service], [])[0]["endpoint"] == "ExternalName (db.example.com)"


def test_ready_ausente_conta_como_pronto_conforme_a_api():
    slice_ = {"metadata": {"name": "a", "namespace": "x",
                           "labels": {"kubernetes.io/service-name": "web"}},
              "endpoints": [{"addresses": ["10.0.0.1"], "conditions": {}}]}
    service = {"metadata": {"name": "web", "namespace": "x"}, "spec": {}}
    assert traducao.services([service], [slice_])[0]["endpoint"] == "1 endereço, 1 pronto"


# --- 3.5 eventos ------------------------------------------------------------

def test_evento_repetido_e_uma_linha():
    itens = carregar("nyx-prod", "events")
    linhas = traducao.eventos(itens)
    assert len(linhas) == len(itens)
    backoff = [l for l in linhas if l["razao"] == "BackOff"]
    originais = sorted(e["count"] for e in itens if e["reason"] == "BackOff")
    assert sorted(l["contagem"] for l in backoff) == originais
    assert all(l["contagem"] > 100 for l in backoff)
    assert all(l["objeto_tipo"] == "Pod" and l["objeto_nome"].startswith("nyx-api-")
               for l in backoff)


def test_eventos_do_mais_recente_para_o_mais_antigo():
    ultimas = [l["ultima"] for l in traducao.eventos(carregar("nyx-prod", "events"))]
    assert ultimas == sorted(ultimas, reverse=True)


def test_evento_sem_count_e_sem_carimbos_legados():
    item = {"metadata": {"name": "e"}, "reason": "Scheduled", "type": "Normal",
            "involvedObject": {"kind": "Pod", "name": "p"},
            "eventTime": "2026-09-27T20:00:00.000000Z"}
    linha = traducao.evento(item)
    assert linha["contagem"] == 1
    assert linha["primeira"] == linha["ultima"] == "2026-09-27T20:00:00.000000Z"


def test_evento_com_series():
    item = {"metadata": {"name": "e"}, "eventTime": "2026-09-27T20:00:00.000000Z",
            "series": {"count": 21, "lastObservedTime": "2026-09-27T20:10:00.000000Z"}}
    linha = traducao.evento(item)
    assert (linha["contagem"], linha["ultima"]) == (21, "2026-09-27T20:10:00.000000Z")


def test_evento_sem_carimbo_nenhum():
    linha = traducao.evento({"metadata": {"name": "e"}})
    assert (linha["primeira"], linha["ultima"], linha["contagem"]) == ("—", "—", 1)


# --- namespace ---------------------------------------------------------------

def test_validacao_de_nome_de_namespace():
    assert traducao.namespace_valido("nyx-prod")
    for invalido in ("Nyx_Prod", "<script>", "", "-a", "a-", "a" * 64, None):
        assert not traducao.namespace_valido(invalido)
