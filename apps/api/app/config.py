from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    local_dev: bool = False

    # Cognito — required in production, ignored when local_dev=True.
    # Tokens are validated at the POOL level (issuer + signature + token_use),
    # not against a single app client, so cross-service / api-to-api calls work.
    # The per-service app client id is only needed by the frontend (for login).
    cognito_user_pool_id: str = ""
    cognito_region: str = "eu-west-2"

    # Cognito Hosted UI domain (bare host, e.g. "myapp.auth.eu-west-2.amazoncognito.com").
    # Used to call the OIDC userInfo endpoint to enrich access-token claims with the
    # caller's profile (email, name, ...), which Cognito access tokens omit by design.
    # Empty disables enrichment — the API still authenticates, it just can't surface email.
    cognito_domain: str = ""

    # Optional defense-in-depth: comma-separated allow-list of app client ids
    # permitted to call this API. Empty = accept any client in the pool.
    cognito_allowed_client_ids: str = ""

    # Optional — set to enable DB layer
    database_url: str = ""

    # Optional — name of the Secrets Manager secret holding runtime secrets
    aws_secrets_manager_secret_name: str = ""

    # CORS — required when local_dev=False; comma-separated list of allowed origins
    cors_allowed_origins: str = ""

    @model_validator(mode="after")
    def _validate_cors(self) -> "Settings":
        if not self.local_dev and not self.cors_allowed_origins:
            raise ValueError(
                "CORS_ALLOWED_ORIGINS must be set when LOCAL_DEV=false"
            )
        return self

    @property
    def cors_origins(self) -> list[str]:
        if not self.cors_allowed_origins:
            return ["*"]
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @property
    def cognito_issuer(self) -> str:
        return f"https://cognito-idp.{self.cognito_region}.amazonaws.com/{self.cognito_user_pool_id}"

    @property
    def cognito_jwks_url(self) -> str:
        return f"{self.cognito_issuer}/.well-known/jwks.json"

    @property
    def cognito_userinfo_url(self) -> str:
        return f"https://{self.cognito_domain}/oauth2/userInfo"

    @property
    def cognito_allowed_client_id_list(self) -> list[str]:
        return [c.strip() for c in self.cognito_allowed_client_ids.split(",") if c.strip()]


settings = Settings()
