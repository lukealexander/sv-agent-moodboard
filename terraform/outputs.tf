# outputs.tf — consumed by scripts/deploy.sh to push the image and roll out the
# service. Keep these names in sync with scripts/deploy.sh.

# ── API ──────────────────────────────────────────────────────────────────────
output "ecr_repository_url" {
  description = "ECR repo URL for the API image. deploy.sh builds and pushes here."
  value       = module.api.ecr_repository_url
}

output "cluster_arn" {
  description = "Shared ECS cluster ARN (for `aws ecs update-service --cluster`)."
  value       = module.api.cluster_arn
}

output "ecs_service_name" {
  description = "API ECS service name (for `aws ecs update-service --service`)."
  value       = module.api.ecs_service_name
}

output "task_definition_arn" {
  description = "Current API task-definition ARN. deploy.sh rolls this out explicitly because the service ignores task_definition changes."
  value       = module.api.task_definition_arn
}

output "api_url" {
  description = "Public URL of the API."
  value       = module.api.api_url
}

# ── Frontend ─────────────────────────────────────────────────────────────────
output "amplify_app_id" {
  description = "Amplify app ID (for `aws amplify start-job`)."
  value       = module.frontend.amplify_app_id
}

output "amplify_branch_name" {
  description = "Amplify branch that builds and deploys the SPA."
  value       = module.frontend.amplify_branch_name
}

output "frontend_url" {
  description = "Public URL of the frontend."
  value       = module.frontend.frontend_url
}

# ── Auth ─────────────────────────────────────────────────────────────────────
output "cognito_client_id" {
  description = "This service's Cognito app client id (shared by the frontend and API)."
  value       = module.frontend.cognito_client_id
}

# ── Database (one-shot bootstrap task; consumed by scripts/deploy.sh) ──────────
# deploy.sh reads these to run the bootstrap task with `aws ecs run-task` (and to
# read its exit code / logs) before rolling out the API. When create_database is
# false the db module isn't created, so `one()` makes each output null and
# `terraform output -raw` fails cleanly — deploy.sh treats that as "no database"
# and skips the bootstrap step.
output "db_task_definition_arn" {
  description = "One-shot DB bootstrap task definition ARN (null when create_database = false)."
  value       = one(module.db[*].task_definition_arn)
}

output "db_cluster_arn" {
  description = "Shared ECS cluster ARN to run the bootstrap task on."
  value       = one(module.db[*].cluster_arn)
}

output "db_subnet_ids" {
  description = "Comma-separated private subnet ids to launch the bootstrap task in."
  value       = one(module.db[*].subnet_ids)
}

output "db_security_group_id" {
  description = "ECS tasks security group id to launch the bootstrap task in."
  value       = one(module.db[*].security_group_id)
}

output "db_container_name" {
  description = "Container name inside the bootstrap task (to read its exit code)."
  value       = one(module.db[*].container_name)
}

output "db_log_group_name" {
  description = "CloudWatch log group for the bootstrap task (printed on failure)."
  value       = one(module.db[*].log_group_name)
}

output "db_url_secret_arn" {
  description = "Secrets Manager ARN holding DATABASE_URL (value populated by the bootstrap task; null when create_database = false)."
  value       = one(module.db[*].db_url_secret_arn)
}

output "db_name" {
  description = "Resolved Postgres database name (null when create_database = false). scripts/teardown-db.sh shows this in its confirmation prompt."
  value       = one(module.db[*].db_name)
}

output "db_user" {
  description = "Resolved Postgres login role (null when create_database = false)."
  value       = one(module.db[*].db_user)
}
