# Supervenient skeleton

This is a template for Supervenient's microservice / tool experiments.

This is the original spec, preserved to show the intent of the tool.  Please don't use it as a readme - we have README.md for that.

- Start a new repo in GitHub using this as a template
- Rapidly build a frontend and backend(s) using the FastAPI (+Alembic) and React (Vite) stubs that are already in place
- Deploy to our labs.supervenient.ai setup using Terraform
- The front end will be deployed behind AWS Cognito so auth flows will already be set up
- Front end should provide a token from Cognito to the API (deployed on AWS but not behind Cognito, so we can have public end points) when calling it - the API should explicitly declare public endpoints, all others should be behind auth; auth tokens should be validated vs Cognito
- Tests should be baked into the setup (e.g. Pytest for the FastApi element, Playwright for e2e)
- Sensible defaults throughout - we want an opinionated, sensible development configuration
- We should be able to deploy and redeploy from the command line easily (e.g. bash script that stands up to AWS via terraform)
- Deployment will be to a AWS ECR which then triggers a new ECS task description and ECS service creation via an ELB
- By default we won't use a database but the basic structure should be there for us to easily do so (e.g. seeding and migrations via Alembic)
- I should be able to run a local docker compose to get a local version up and running easily
- I should be able to uset the backend container as a dev container (on both Mac and Windows/WSL2 using Docker backend)

