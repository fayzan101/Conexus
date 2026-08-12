terraform {
  required_version = ">= 1.5.0"
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.32"
    }
  }
}

provider "kubernetes" {
  config_path = var.kubeconfig_path
}

resource "kubernetes_namespace" "eb" {
  metadata {
    name = var.namespace
    labels = {
      "app.kubernetes.io/name" = "enterprise-brain"
      environment              = var.environment
      deploy_mode              = var.deploy_mode
    }
  }
}

resource "kubernetes_config_map" "eb_runtime" {
  metadata {
    name      = "enterprise-brain-runtime"
    namespace = kubernetes_namespace.eb.metadata[0].name
  }
  data = {
    ENVIRONMENT              = var.environment
    DEPLOY_MODE              = var.deploy_mode
    PROMETHEUS_ENABLED       = "true"
    OTEL_ENABLED             = tostring(var.otel_enabled)
    LLM_CACHE_ENABLED        = "true"
    LLM_BUDGET_TOKENS_PER_DAY = tostring(var.llm_budget_tokens_per_day)
    SLO_SEARCH_P95_MS        = tostring(var.slo_search_p95_ms)
    SLO_CHAT_P95_MS          = tostring(var.slo_chat_p95_ms)
    BACKUP_RPO_HOURS         = tostring(var.backup_rpo_hours)
    BACKUP_RTO_HOURS         = tostring(var.backup_rto_hours)
  }
}

output "namespace" {
  value = kubernetes_namespace.eb.metadata[0].name
}

output "promote_hint" {
  value = "helm upgrade --install eb ./deploy/helm/enterprise-brain -n ${var.namespace} -f deploy/helm/enterprise-brain/values-${var.environment}.yaml"
}
