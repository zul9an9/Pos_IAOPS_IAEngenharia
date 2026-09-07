# Resultados esperados por fixture

O oráculo mora aqui, fora dos manifestos. Fixture que carrega dentro de si a resposta certa
deixa de ser teste — e o validador pode acabar acertando por ler o comentário.

| Arquivo | Exercita | Exit code esperado |
|---|---|---|
| `01-conforme.yaml` | linha de base: nada deve disparar | 0 |
| `02-obrigatorio.yaml` | 10 regras obrigatórias violadas | 1 |
| `03-proibido.yaml` | 3 regras proibidas + exceção indevida | 1 |
| `04-recomendado.yaml` | 5 recomendações violadas, nenhuma obrigatória | **0** |
| `05-nao-avaliado.yaml` | cascata de não-avaliado, exceções, heurísticas | 1 |

---

## 01-conforme.yaml

Quatro objetos, todos aprovados. Se qualquer regra reprovar aqui, é falso positivo do validador
— este arquivo é a régua.

Ponto de atenção: os quatro rótulos aparecem *idênticos* em `matchLabels`, no `selector` do Service
e no template do pod. Foi de propósito. A regra 1.4 diz "idênticos, caractere por caractere", mas
na prática um seletor costuma ser subconjunto dos rótulos do pod. Com os conjuntos iguais, a fixture
passa sob as duas leituras e não vira armadilha para o validador.

---

## 02-obrigatorio.yaml

| Regra | O que está errado |
|---|---|
| 1.1 | `OrionWorker` — camelCase |
| 1.3 | só o rótulo curto `app:`, faltam os quatro |
| 1.4 | `matchLabels: app: orion-worker` contra rótulo do pod `app: orionworker` |
| 2.1 | contêiner sem `resources` |
| 2.2 | nenhuma sonda |
| 2.3 | `replicas: 1` em namespace de prod |
| 2.4 | sem bloco `strategy` |
| 3.2 | sem `securityContext` |
| 3.4 | `automountServiceAccountToken` nem declarado |
| 3.7 | imagem em `docker.io` |

O Service herda 1.3 e 1.4. A imagem tem tag imutável de propósito: viola 3.7 sem tocar em 3.1,
para que as duas regras não fiquem acopladas no teste.

**O `apiVersion` e o `kind` estão corretos** e o namespace é válido — sem isso, as regras 2.3 e 2.4
cairiam em não-avaliado e o arquivo perderia metade do propósito.

---

## 03-proibido.yaml

| Regra | O que está errado |
|---|---|
| 3.1 | `:latest` |
| 3.3 | `DATABASE_URL` e `ADMIN_TOKEN` em `env.value`, e `SMTP_PASSWORD` no ConfigMap |
| 3.6 | `hostNetwork: true`, `hostPID: true`, `privileged: true` |

A anotação `metacortex.io/exception: "3.6:2027-01-31"` tem data futura e formato correto. Ainda assim
não pode suprimir nada: a seção "Exceções" do padrão diz que não existe exceção a regra proibida em
carga de trabalho de cliente. O comportamento certo é reportar a violação **e** sinalizar a tentativa
de exceção indevida. Validador que aceita a anotação aqui está com o mecanismo de exceção largo demais.

O `SMTP_PASSWORD` no ConfigMap é o caso que a heurística mais erra: o nome da chave entrega, o valor
não tem forma de URI. Serve para calibrar se a detecção olha só o valor ou também o nome do campo.

---

## 04-recomendado.yaml

| Regra | O que está errado |
|---|---|
| 1.5 | sem `metacortex.io/owner` |
| 1.6 | contêiner chamado `app` |
| 2.5 | prod com 2 réplicas e nenhum PDB no diretório |
| 2.6 | sem `terminationGracePeriodSeconds` |
| 3.5 | `serviceAccountName: default` |

Este é o teste mais importante do conjunto, e o mais fácil de errar na implementação: **cinco avisos
e exit code 0**. Validador que soma severidades num contador único reprova aqui, e o time perde a
confiança na ferramenta na primeira semana.

A 2.5 só é avaliável porque o escopo é diretório: falta um PDB que casaria com estes rótulos. Se o
validador for rodado neste arquivo isolado, 2.5 vira não-avaliado, e isso também está correto.

A imagem por digest exercita o caminho alternativo da 3.1 — sem tag, e mesmo assim conforme.

---

## 05-nao-avaliado.yaml

**A cascata.** O namespace `producao` está fora do formato `<cliente>-<ambiente>` (viola 1.2). Como
o ambiente é derivado do sufixo do namespace, ele fica indeterminado, e três regras condicionais
não podem ser decididas:

- 2.3 — `replicas: 1` só é violação se for prod. Não se sabe. → **não-avaliado**
- 2.4 — `strategy` ausente só é violação se for prod. → **não-avaliado**
- 2.5 — PDB ausente idem. → **não-avaliado**

Aprovar qualquer uma das três aqui é o defeito central que o exercício persegue.

**As exceções.** A anotação traz duas, na mesma string:

- `3.2:2027-03-01` — dentro da validade. O `securityContext` está ausente, e a violação deve ser
  suprimida, aparecendo como exceção ativa no relatório e não como aprovação.
- `3.7:2026-01-15` — vencida. A imagem em `ghcr.io` viola a regra e a violação **reaparece**. Se o
  validador aceita a exceção sem olhar a data, o mecanismo inteiro é decorativo.

**A heurística da 2.2.** As duas sondas apontam para `/health`. Presença: aprovado. Mas é exatamente
a armadilha que o texto da regra descreve, e vale aviso — marcado como heurístico, porque o validador
não sabe o que aquele endpoint verifica.

**Os falsos positivos plantados da 3.3.** `TRACE_SAMPLE_KEY` parece base64 e não é segredo;
`PARTITION_SEED` é hexadecimal de alta entropia e também não é. Nenhum dos dois deveria reprovar.
Se reprovarem, a heurística está agressiva demais e vai gerar exceção de rotina — que é como uma
regra vira ruído.

**Fora da cascata**, ainda deve reprovar: 1.2 (namespace) e 3.4 (`automountServiceAccountToken: true`
com o campo declarado — o padrão exige `false` quando a aplicação não fala com a API, e essa condição
não é decidível pelo YAML; aqui o validador pode, no máximo, avisar que o valor `true` precisa de
justificativa). Vale conferir como o script gerado resolve esse caso: é a regra mais ambígua do padrão.

**Consumo em regime.** `requests: 1Gi` contra `limits: 8Gi` é razão 8x, muito acima da regra de bolso
de 1,5x–2x. Mas a regra fala do consumo *observado*, não do request — e consumo observado não está
no manifesto. A fração continua não-avaliável, e um validador que reprova aqui inventou uma regra
que o padrão não escreveu.
