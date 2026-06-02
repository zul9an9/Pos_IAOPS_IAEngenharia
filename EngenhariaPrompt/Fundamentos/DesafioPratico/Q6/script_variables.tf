variable "name" {
  description = "Nome lógico do bucket (sufixo após hvt-s3-)"
  type        = string
}

variable "environment" {
  description = "Nome do ambiente (dev, staging, production)"
  type        = string
}

variable "owner" {
  description = "Time ou pessoa responsável pelo recurso"
  type        = string
}

variable "cost_center" {
  description = "Centro de custo para billing"
  type        = string
}

variable "logging_target_bucket" {
  description = "Nome do bucket S3 destino dos access logs"
  type        = string
}
