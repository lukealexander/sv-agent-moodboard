# Infrastructure & deployment

This service's cloud infrastructure is **thin** Terraform in [terraform/](../terraform)
that composes the shared [`deployment`](https://github.com/Supervenient-AI/deployment)
modules. It does **not** stand up its own VPC, ALB, or cluster — those are part of a
**shared platform** provisioned once by the `infrastructure` repo and published to SSM
Parameter Store. Everything runs in AWS `eu-west-2` (London).

## Three layers

```
infrastructure  (platform)  → VPC, shared ALB, ECS cluster (Fargate), RDS, Cognito, DNS
       │  outputs published to SSM  /<environment>/platform/*
       ▼
deployment      (modules)   → reusable `api` + `frontend` Terraform modules
       │  vendored here as a git submodule at terraform/modules
       ▼
this service    (Layer 3)   → terraform/main.tf composes the modules (api + frontend)
```

The modules read the platform contract from SSM themselves; this repo only supplies
per-service inputs (`service_name`, `github_repo`, the container image, …). See
[terraform/README.md](../terraform/README.md).

## AWS topology

```
  user ──▶ <svc>.labs.supervenient.ai      ──▶  AWS Amplify (builds the SPA on git push)
                                                 Cognito + API config injected as VITE_*

  user ──▶ <svc>.api.labs.supervenient.ai  ──▶  shared ALB  ──▶  ECS service (Fargate)
                                                 (HTTPS listener,   running the API image
                                                  host-based rule)   pulled from ECR
```

| Module (in `terraform/modules/`) | Creates |
|---|---|
| `api` | ECR repo, CloudWatch logs, IAM task role, **Fargate** task definition + ECS service (Service Connect, circuit breaker), ALB target group + host-based listener rule, optional Route 53 record. Validates access tokens at the pool level (no app-client wiring); optional `cognito_allowed_client_ids` allow-list. |
| `frontend` | AWS **Amplify** app + branch (build-on-push), custom-domain association, and this service's **own Cognito app client** in the shared user pool (owns its callback/logout URLs; same client id feeds the API). |

The DB connection URL and other secrets live in **AWS Secrets Manager** and are injected
into the ECS task by ARN (via the `api` module's `secrets` input) — never baked into images.

### One shared ALB

> **Convention:** there is **one** ALB, owned by the platform and shared across all
> services. Each `api` module call adds a host-based **listener rule** (e.g.
> `<svc>.api.labs.supervenient.ai`). Its `alb_listener_rule_priority` is **auto-derived
> from the hostname** — stable across applies and unique per service — so independently
> applied stacks never collide without coordinating. Set `api_listener_rule_priority`
> only to override on a rare hash collision. DNS resolves via the platform's wildcard
> `*.api.<domain_base>` → ALB, so no per-service DNS record is needed by default.

## `terraform/main.tf` at a glance

* Configures the AWS provider (region `eu-west-2`). **No** `us_east_1` alias — Amplify
  manages its own TLS cert (the old S3 + CloudFront design needed one; this doesn't).
* Instantiates `module "api"` and `module "frontend"` from the submodule.
* Injects `DATABASE_URL` (Secrets Manager ARN) into the API only if the service opts
  into a database (`database_url_secret_arn`).
* No `backend` block — `bootstrap-state.sh` writes the real S3 backend into `backend.tf`.

## The deployment modules submodule

`terraform/modules` is a git submodule pinned to the `deployment` repo (currently its
default branch — see the TODO in [.gitmodules](../.gitmodules) to pin a release tag).
After cloning this repo:

```bash
git submodule update --init terraform/modules
```

CI (`actions/checkout`) must set `submodules: recursive`.

## Scripts

### `scripts/bootstrap-state.sh` (once per project)

Creates the **per-service** Terraform remote-state backend and writes
`terraform/backend.tf`:

```bash
SERVICE_NAME=myapp ./scripts/bootstrap-state.sh   # add --dry-run to preview
cd terraform && terraform init
```

It creates `<service>-terraform-state` (versioned, encrypted, public access blocked) and
a `<service>-terraform-lock` DynamoDB table, and is idempotent.

### `scripts/deploy.sh` (every release)

```bash
export TF_VAR_github_access_token=ghp_xxx          # GitHub PAT Amplify uses
SERVICE_NAME=myapp IMAGE_TAG=v1.0.0 ./scripts/deploy.sh
SERVICE_NAME=myapp IMAGE_TAG=v1.0.0 ./scripts/deploy.sh --skip-frontend
```

Steps:

1. **ECR bootstrap** — a *targeted* apply
   (`-target=module.api.aws_ecr_repository.this`) creates the ECR repo first, since the
   image must exist before the ECS service can pull it.
2. **Build & push** the API image with `docker build --platform linux/arm64` (it **must**
   match the `api` module's `cpu_architecture`, which defaults to ARM64/Graviton).
3. **Full `terraform apply`** with `-var container_image=<ecr-url>:<tag>` — registers a
   new task-definition revision and reconciles the ECS service, target group, listener
   rule, and the Amplify app.
3b. **Database provisioning (managed DB only)** — for a service with `create_database =
   true`, the script runs the one-shot Fargate bootstrap task (`aws ecs run-task`) to
   create its Postgres role + database and populate the `DATABASE_URL` secret **only on
   the first deploy** (detected by the secret still being empty). Subsequent deploys skip
   this slow task: the API applies `alembic upgrade head` on startup
   (`apps/api/docker-entrypoint.sh`), so schema changes ship with the normal rollout. A
   failed migration crashes the new task and the circuit breaker rolls the deploy back.
   Re-run the task on demand with `FORCE_DB_BOOTSTRAP=1`; stateless services skip it
   automatically.
4. **Explicit ECS rollout** — the service uses `ignore_changes = [task_definition]`, so
   `apply` won't repoint it and a bare `--force-new-deployment` would redeploy the *old*
   revision. The script runs
   `aws ecs update-service --task-definition <new arn> --force-new-deployment`.
5. **Amplify** builds the frontend **on git push**; the script also triggers a release
   with `aws amplify start-job … --job-type RELEASE` (skip with `--skip-frontend`).

`IMAGE_TAG` defaults to the short git SHA. There is **no** frontend Docker build, S3
sync, or CloudFront invalidation — Amplify owns the frontend build/host.

### Tearing down (`scripts/teardown-db.sh`)

The service's Postgres **role + database live on the shared RDS** and are created by
the bootstrap task with raw SQL — they are *not* in Terraform state. So
`terraform destroy` removes the plumbing (secret, bootstrap role, log group, task
definition) but **leaves the role + database behind**, orphaned on the shared
instance.

For a managed-DB service, run the teardown **before** `terraform destroy`:

```bash
./scripts/teardown-db.sh           # type the database name to confirm
./scripts/teardown-db.sh --yes     # skip the prompt (CI; or FORCE_TEARDOWN=1)
terraform -chdir=terraform destroy
```

It launches a one-shot Fargate task — the bootstrap task definition with its command
overridden to `app.dbteardown` — that connects as the RDS master user and runs
`DROP DATABASE … WITH (FORCE)` then `DROP ROLE`. It's destructive and irreversible,
hence the typed confirmation; stateless services (no db module) are a no-op.

> Skipping teardown doesn't just litter the shared instance — a leftover database
> later blocks a *new* service that derives the same name: the bootstrap task's
> first-provision guard refuses to adopt a pre-existing role/database (it would
> otherwise share data and reset the other owner's password). Choose a unique
> `service_name`, set `db_name`/`db_user` explicitly, or drop the stale objects.

## Local development

`docker-compose.yml` runs the whole stack with auth bypassed (`LOCAL_DEV=true`):

| Service | Port | Notes |
|---|---|---|
| `api` | 8000 | Dockerfile `dev` target, `uvicorn --reload`, source bind-mounted |
| `postgres` | 5432 | `postgres:16-alpine`, healthchecked |
| `frontend` | 5173 | Vite dev server, source bind-mounted |

```bash
cp .env.example .env
docker compose up
```

## Dev container

[.devcontainer/devcontainer.json](../.devcontainer/devcontainer.json) builds from the
API `dev` Dockerfile target and layers in the AWS CLI, Terraform, and Node 22, so the
container doubles as a full deploy environment on macOS and Windows/WSL2. `postCreate`
installs both the API (`uv sync`) and frontend deps.

## Adding a second backend service

1. Create `apps/<service-name>/` with its own `Dockerfile` and FastAPI app.
2. Add a second `module "api"` call in `terraform/main.tf` with a distinct `name` (see the
   commented example there). Its listener-rule priority is derived from the hostname
   automatically — no value to pick. Reuse the shared platform — no new ALB or cluster.
3. Add outputs for its ECR URL / ECS service / task-definition ARN and a build-push-roll
   step for its image in `scripts/deploy.sh`.
4. It becomes available at `https://<service-name>.api.labs.supervenient.ai`.
