
# Justificativa CARE


# Justificativa Claude Opus 4.7 (ou similar com forte performance em IaC).
Tarefas de geração de código Terraform com múltiplos arquivos coerentes entre si se beneficiam de modelos com janela ampla e bom raciocínio estrutural. Temperatura baixa (0–0.3) para reduzir alucinações de atributos do provider AWS.

# Checagem rápida de aderência ao padrão Strickland
Tags obrigatórias (Owner, CostCenter, Environment) consolidadas em local.common_tags e aplicadas via merge(), espelhando o módulo de VPC. Prefixo hvt- presente no padrão hvt-s3-${var.name}-${var.environment}. Bucket S3 com encryption AES256, versioning Enabled, os quatro flags de Block Public Access em true e logging apontando para bucket externo via variável. Todas as variáveis em variables.tf têm description e type. Exemplo de uso entregue em examples/basic/main.tf para que qualquer time consuma o módulo sem precisar adivinhar a interface.
