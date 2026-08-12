variable "kubeconfig_path" {
  type    = string
  default = ""
}

variable "namespace" {
  type    = string
  default = "enterprise-brain-dev"
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "deploy_mode" {
  type    = string
  default = "saas"
}

variable "otel_enabled" {
  type    = bool
  default = true
}

variable "llm_budget_tokens_per_day" {
  type    = number
  default = 100000
}

variable "slo_search_p95_ms" {
  type    = number
  default = 800
}

variable "slo_chat_p95_ms" {
  type    = number
  default = 2500
}

variable "backup_rpo_hours" {
  type    = number
  default = 24
}

variable "backup_rto_hours" {
  type    = number
  default = 4
}
