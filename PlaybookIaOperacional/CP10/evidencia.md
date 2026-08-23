# CP10 — Evidência de execução do gate

Todas as execuções abaixo foram rodadas de verdade (promptfoo `0.122.0`, Node `v22.22.2`).
Para não gastar token nem depender de chave, o **provider é `echo`** no smoke local — o que
está sendo provado aqui é o **mecanismo do gate** (assert → exit code → build), idêntico ao que
roda em CI trocando `echo` pelos providers reais.

## 1. Gate determinístico — verde e vermelho (arquivos reais da entrega)

Mesmo `prompts/postmortem/prompt.txt` da biblioteca, decidido pelo `.github/scripts/gate.mjs` da entrega.

```text
    ### RUN 1 — baseline (prompt saudável) — espera-se APROVAR
    Gate Aegis :: threshold-juiz=0.75  min-runs=1
      asserts determinísticos reprovados: 0
      casos de juiz abaixo da mediana:     0
    
    ✅ GATE APROVADO.
    exit-code-do-gate=0
    
    ### RUN 2 — regressão: 'melhoria' remove a seção AÇÕES CORRETIVAS — espera-se REPROVAR
    -- diff aplicado no prompt --
    7d6
    < 4. AÇÕES CORRETIVAS
    Gate Aegis :: threshold-juiz=0.75  min-runs=1
      asserts determinísticos reprovados: 1
      casos de juiz abaixo da mediana:     0
      [DET-FAIL] contains="AÇÕES CORRETIVAS" :: Expected output to contain "AÇÕES CORRETIVAS"
    
    ❌ GATE REPROVADO — regressão detectada.
    exit-code-do-gate=1   (não-zero => build REPROVADO no CI)
    
    ### prompt restaurado; biblioteca de volta ao estado saudável
```

**Leitura:** o baseline aprova com `exit 0`. Ao introduzir a regressão (uma "melhoria"
descuidada que apaga a seção `AÇÕES CORRETIVAS`), o assert `contains` falha e o gate sai com
`exit 1` — que é exatamente o que **reprova o build** no GitHub Actions. Regressão barrada.

## 2. Gate do juiz — mediana-de-N absorve flutuação

JSON sintético (sem chamar modelo) exercitando `gate.mjs` com `--min-judge-runs=3`:

```text
    ### Teste da lógica do juiz (mediana-de-N) — sem gastar token, JSON sintético
    
    CASO A: scores [0.90, 0.55(outlier), 0.85] -> mediana 0.85 >= 0.75 -> APROVA
    Gate Aegis :: threshold-juiz=0.75  min-runs=3
      asserts determinísticos reprovados: 0
      casos de juiz abaixo da mediana:     0
    
    ✅ GATE APROVADO.
    exit=0
    
    CASO B: scores [0.40, 0.50, 0.72] -> mediana 0.50 < 0.75 -> REPROVA
    Gate Aegis :: threshold-juiz=0.75  min-runs=3
      asserts determinísticos reprovados: 0
      casos de juiz abaixo da mediana:     1
      [JUIZ-FAIL] mediana=0.500 scores=["0.40","0.50","0.72"] 
    
    ❌ GATE REPROVADO — regressão detectada.
    exit=1
```

**Leitura:** no Caso A um run isolado devolveu 0.55 (abaixo do threshold), mas a **mediana** dos 3
runs é 0.85 — o gate **não** reprova por flutuação de um único julgamento. No Caso B a mediana em si
é 0.50, sinal de regressão real e persistente, e o gate reprova. É essa a diferença entre "o juiz
tremeu uma vez" e "o prompt piorou de verdade".

## 3. Evidência que só o CI produz

O comentário *before/after* no PR (camada 1) e os artefatos `promptfoo-results` só existem numa
execução real do workflow no GitHub, com os secrets configurados. Para gerá-la: abra um PR que
edite um `prompts/<nome>/prompt.txt`, confirme o comentário da action e o check verde; depois
faça um commit que regrida o prompt (ex.: remova uma seção obrigatória) e confirme o check
**vermelho**. Anexe os dois screenshots aqui.
