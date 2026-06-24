# variables.tf — per-service inputs. The platform (VPC, ALB, ECS cluster,
# Cognito, RDS, DNS) is discovered from SSM by the modules, so this root only
# needs service-specific values.

# ── Required ─────────────────────────────────────────────────────────────────

variable "service_name" {
  type        = string
  description = "Service slug. Drives ECR/ECS/target-group/log/Amplify naming and the API/frontend subdomains. Unique within an environment."
  # Example: "funapp1". scripts/init-project.sh pre-fills this in terraform.tfvars.
}

variable "github_repo" {
  type        = string
  description = "GitHub repo (org/repo) Amplify builds the frontend from."
  # Example: "Supervenient-AI/svc-funapp1"
}

# ── Optional with defaults ───────────────────────────────────────────────────

variable "environment" {
  type        = string
  default     = "development"
  description = "Platform environment; selects the /<environment>/platform/* SSM namespace."

  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "environment must be one of: development, staging, production."
  }
}

variable "aws_region" {
  type        = string
  default     = "eu-west-2"
  description = "AWS region. Must match the shared platform's region."
}

variable "domain_base" {
  type        = string
  default     = "labs.supervenient.ai"
  description = "Base domain for this environment. Must match the platform's `domain-base` SSM value (labs.supervenient.ai for development, staging.supervenient.ai for staging, app.supervenient.ai for production)."
}

variable "container_image" {
  type        = string
  default     = ""
  description = "Full ECR image URI incl. tag for the API. Set by scripts/deploy.sh (-var container_image=<ecr-url>:<tag>) after the image is built; left empty for the initial ECR-only bootstrap apply."
}

variable "github_access_token" {
  type        = string
  default     = ""
  sensitive   = true
  description = "GitHub PAT for Amplify repo access. Provide via the environment (export TF_VAR_github_access_token=...) — never commit it. Required for the frontend; may be empty for an API-only/bootstrap apply."
}

variable "github_branch" {
  type        = string
  default     = "main"
  description = "Git branch Amplify builds and deploys (and that deploy.sh triggers a release for)."
}

variable "api_listener_rule_priority" {
  type        = number
  default     = null
  description = "Override this API's priority on the shared ALB listener. Leave null (default) to let the module auto-derive a stable, unique priority from the hostname — services no longer need to coordinate. Set an explicit 1–50000 value only to resolve a rare hash collision."
}

variable "create_database" {
  type        = bool
  default     = false
  description = "Opt this service into a managed Postgres database on the shared RDS instance. When true, Terraform creates the db module's plumbing (DATABASE_URL secret, bootstrap IAM role, one-shot task definition); scripts/deploy.sh runs the bootstrap task to create the role+database only on first deploy (when the secret is empty) or when FORCE_DB_BOOTSTRAP=1, and the API applies migrations on startup. When false (default), nothing DB-related is created and the API is stateless — unless var.database_url_secret_arn points at a bring-your-own database."
}

variable "database_url_secret_arn" {
  type        = string
  default     = ""
  description = "Bring-your-own database: a Secrets Manager ARN holding the API's DATABASE_URL. When set it takes precedence over var.create_database (the API uses this secret and no db module is provisioned). Leave empty to either use the managed db module (create_database = true) or run a stateless API."
  # Example: "arn:aws:secretsmanager:eu-west-2:123456789012:secret:funapp1-db-AbCdEf"
}