
# Justificativa do framework CARE
Justificativa — como C, A, R, E aparecem no prompt
Context aparece no bloco inicial: estabelece o papel do modelo (engenheiro de plataforma sênior), o ambiente organizacional (padrão Strickland, Segurança & Compliance) e as regras de negócio que não são negociáveis (tags, prefixo, requisitos do S3, formato do variables.tf). Sem esse contexto, o modelo geraria um bucket S3 genérico sem aderência ao padrão interno.
Action isola o que deve ser feito de forma imperativa e enumerada: gerar quatro arquivos específicos (main.tf, variables.tf, outputs.tf, examples/basic/main.tf). A ação é objetiva e mensurável — dá pra checar se o output contém os quatro artefatos.
Result define o formato e os critérios de aceite do entregável: versões mínimas de provider, uso de locals.common_tags, padrão de nomenclatura hvt-s3-..., uso de merge() para tags, ausência de variáveis extras e formato da resposta (apenas blocos de código). É o "definition of done" do prompt.
Example ancora o estilo no módulo de VPC já existente. Esse é o elemento mais poderoso do CARE neste caso: em vez de descrever em palavras como deve ser o estilo, mostra concretamente como locals, merge e o prefixo hvt- se combinam. O modelo replica o padrão visual e estrutural com muito mais fidelidade quando vê o exemplo do que quando apenas lê a regra.

# Justificativa Claude Opus 4.7 (ou similar com forte performance em IaC).
Tarefas de geração de código Terraform com múltiplos arquivos coerentes entre si se beneficiam de modelos com janela ampla e bom raciocínio estrutural. Temperatura baixa (0–0.3) para reduzir alucinações de atributos do provider AWS.

# Checagem rápida de aderência ao padrão Strickland
Tags obrigatórias (Owner, CostCenter, Environment) consolidadas em local.common_tags e aplicadas via merge(), espelhando o módulo de VPC. Prefixo hvt- presente no padrão hvt-s3-${var.name}-${var.environment}. Bucket S3 com encryption AES256, versioning Enabled, os quatro flags de Block Public Access em true e logging apontando para bucket externo via variável. Todas as variáveis em variables.tf têm description e type. Exemplo de uso entregue em examples/basic/main.tf para que qualquer time consuma o módulo sem precisar adivinhar a interface.
