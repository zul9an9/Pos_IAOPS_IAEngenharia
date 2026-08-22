
[CONTEXT]
Você é um engenheiro de plataforma sênior especializado em Terraform e AWS, 
trabalhando em uma empresa que possui um padrão interno de IaC publicado pela 
área de Segurança & Compliance (liderada por Strickland). Toda a infraestrutura 
da empresa segue as regras abaixo, sem exceção:

- Tags obrigatórias em TODO recurso: Owner, CostCenter, Environment.
- Prefixo "hvt-" no Name de todos os recursos.
- Buckets S3 devem ter:
    * Server-side encryption habilitada (no mínimo SSE-S3 / AES256).
    * Versioning ativo.
    * Block Public Access TOTAL (os 4 flags = true).
    * Access logging configurado (apontando para outro bucket informado por variável).
- Arquivo variables.tf com TODAS as variáveis tendo "description" e "type" obrigatórios.
- O módulo será consumido por todos os times da empresa, portanto precisa ser 
  reutilizável e acompanhado de exemplo de uso.

[ACTION]
Gere um módulo Terraform reutilizável chamado "s3-bucket" que crie um bucket S3 
aderente ao padrão acima. Entregue os arquivos separados e nomeados:

1. main.tf       → recursos (bucket, versioning, encryption, public access block, logging)
2. variables.tf  → todas as variáveis com description e type
3. outputs.tf    → bucket id, arn e domain_name
4. examples/basic/main.tf → exemplo mínimo de uso do módulo

[RESULT]
- Código Terraform válido (terraform >= 1.5, provider aws >= 5.0).
- Use locals.common_tags para consolidar as tags obrigatórias.
- Nome do bucket no padrão: hvt-s3-${var.name}-${var.environment}.
- Use merge(local.common_tags, { Name = "..." }) em cada recurso.
- Não invente variáveis fora do padrão; mantenha o mínimo necessário.
- Comente apenas o estritamente necessário; código limpo.
- Resposta APENAS com os blocos de código de cada arquivo, separados por título.

[EXAMPLE]
Siga EXATAMENTE este estilo (módulo de VPC já existente na empresa), 
replicando o mesmo padrão de locals, merge de tags e nomenclatura:

variable "environment" {
  description = "Nome do ambiente (dev, staging, production)"
  type        = string
}

locals {
  common_tags = {
    Owner       = var.owner
    CostCenter  = var.cost_center
    Environment = var.environment
  }
}

resource "aws_vpc" "this" {
  cidr_block = var.cidr_block
  tags = merge(local.common_tags, {
    Name = "hvt-vpc-${var.environment}"
  })
}
