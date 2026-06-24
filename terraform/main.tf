# main.tf — composes the shared `deployment` modules into this service's
# full stack: one API (apps/api) + one frontend (apps/frontend) on the shared
# Supervenient AI platform.
#
# The modules discover platform resources (VPC, ALB, ECS cluster, Cognito, RDS,
# DNS) from SSM under /<environment>/platform/* — this root only supplies
# per-service inputs. The modules are vendored as a git submodule at ./modules
# (see ../.gitmodules) and referenced by local path.

# Shared Cognito Hosted UI domain (same value the frontend gets as
# VITE_COGNITO_DOMAIN). The API calls its /oauth2/userInfo endpoint to enrich
# access-token claims with the caller's email/profile, which Cognito access
# tokens omit by design.
data "aws_ssm_parameter" "cognito_domain" {
  name = "/${var.environment}/platform/cognito-domain"
}

# Allows the API task to call Bedrock's Converse API for dataset generation.
# Scoped to cover both direct foundation-model ARNs and cross-region inference
# profile ARNs, since either form is valid depending on which model id the
# deploying account has been granted access to.
resource "aws_iam_policy" "bedrock_invoke" {
  name        = "${var.service_name}-bedrock-invoke"
  description = "Allows the API task to call Bedrock for dataset generation."

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:Converse",
        ]
        Resource = [
          "arn:aws:bedrock:*::foundation-model/*",
          "arn:aws:bedrock:*:*:inference-profile/*",
        ]
      }
    ]
  })
}

# ── Backend API (apps/api) ───────────────────────────────────────────────────
# Creates ECR repo, log group, task role, Fargate task definition + service,
# ALB target group + host-based listener rule. Served at
# https://<service_name>.api.<domain_base>.
module "api" {
  source = "./modules/api"

  name            = var.service_name
  environment     = var.environment
  domain_base     = var.domain_base
  container_image = var.container_image

  # COGNITO_DOMAIN enables /whoami (and any route using require_user) to resolve
  # the caller's email via the userInfo endpoint. Merged over the module's
  # injected platform env vars; the api module itself stays Cognito-agnostic.
  environment_variables = {
    COGNITO_DOMAIN   = data.aws_ssm_parameter.cognito_domain.value
  }

  # No Cognito wiring needed: the API validates access tokens at the POOL level
  # (issuer + signature + token_use), so it accepts tokens from any service's
  # client in the shared pool. The frontend module still creates this service's
  # login client. To restrict callers, set cognito_allowed_client_ids.

  # cpu_architecture is left at the module default (ARM64 / Graviton). The image
  # built by scripts/deploy.sh (docker build --platform linux/arm64) MUST match.

  # Priority on the shared ALB HTTPS listener. Left null, the module derives a
  # stable, unique priority from the hostname, so services (and additional api
  # module calls) never collide without anyone tracking a registry. Set
  # api_listener_rule_priority only to override on a rare hash collision.
  alb_listener_rule_priority = var.api_listener_rule_priority

  # DATABASE_URL wiring, in precedence order:
  #   1. var.database_url_secret_arn set  -> bring-your-own DB (use that secret).
  #   2. var.create_database = true       -> use the managed db module's secret.
  #   3. otherwise                        -> stateless API, no DATABASE_URL.
  # The secret's VALUE is written by the one-shot bootstrap task, not Terraform.
  secrets = var.database_url_secret_arn != "" ? {
    DATABASE_URL = var.database_url_secret_arn
    } : var.create_database ? {
    DATABASE_URL = module.db[0].db_url_secret_arn
  } : {}

  additional_task_role_policies = {
    bedrock_invoke = aws_iam_policy.bedrock_invoke.arn
  }

  # cpu / memory / desired_count have module defaults (256 / 512 / 1); add them
  # here to size the task.
}

# ── Frontend SPA (apps/frontend) ─────────────────────────────────────────────
# AWS Amplify connects to the GitHub repo and rebuilds on every push to
# github_branch; Cognito + API config are injected as VITE_* at build time.
# Served at https://<service_name>.<domain_base>.
module "frontend" {
  source = "./modules/frontend"

  name                = var.service_name
  environment         = var.environment
  domain_base         = var.domain_base
  github_repo         = var.github_repo
  github_branch       = var.github_branch
  github_access_token = var.github_access_token
}

# ── Database (apps/api on the shared RDS) ─────────────────────────────────────
# Gated by var.create_database (default false). When enabled it provisions this
# service's Postgres role + database on the shared RDS instance and an (empty)
# Secrets Manager secret for DATABASE_URL, whose ARN the api module references
# above. Flip create_database = false (the default) in terraform.tfvars to skip
# the database entirely — count drops the module and the API runs stateless.
#
# IMPORTANT: `terraform apply` only creates the PLUMBING — the secret, a scoped
# bootstrap IAM role, and a one-shot Fargate task DEFINITION. The actual
# CREATE ROLE / CREATE DATABASE runs inside that task, which scripts/deploy.sh
# launches with `aws ecs run-task` only for first-time provisioning (when the
# DATABASE_URL secret is still empty) or on demand via FORCE_DB_BOOTSTRAP=1.
# Apply alone will NOT create the database. Routine schema migrations run on API
# startup (apps/api/docker-entrypoint.sh), not here.
module "db" {
  source = "./modules/db"
  count  = var.create_database ? 1 : 0

  name            = var.service_name
  environment     = var.environment
  container_image = var.container_image

  # bootstrap_command defaults to `uv run python -m app.dbtask` — the entrypoint
  # at apps/api/app/dbtask.py that provisions the role+db, writes the secret,
  # and migrates. cpu/memory/db_name/db_user have module defaults.
}

# ─────────────────────────────────────────────────────────────────────────────
# Adding a second backend
# ─────────────────────────────────────────────────────────────────────────────
# Call the `api` module again with a distinct `name`. It gets its own ECR repo +
# ECS service, is served at https://<name>.api.<domain_base>, and auto-derives a
# unique listener-rule priority from that hostname — no priority bookkeeping
# needed. Add matching outputs (ECR URL, service name, task-definition ARN) and a
# build/push/rollout step in scripts/deploy.sh for its image.
#
# module "api_admin" {
#   source = "./modules/api"
#
#   name                 = "${var.service_name}-admin"
#   environment          = var.environment
#   domain_base          = var.domain_base
#   container_image      = var.admin_container_image # add this variable
#   cors_allowed_origins = "https://${var.service_name}.${var.domain_base}"
# }
