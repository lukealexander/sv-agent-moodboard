const COGNITO_DOMAIN = import.meta.env.VITE_COGNITO_DOMAIN as string;
const CLIENT_ID = import.meta.env.VITE_COGNITO_CLIENT_ID as string;
const REDIRECT_URI = import.meta.env.VITE_COGNITO_REDIRECT_URI as string;

const CODE_VERIFIER_KEY = "pkce_code_verifier";

function base64url(buffer: ArrayBuffer | Uint8Array): string {
  const bytes = buffer instanceof Uint8Array ? buffer : new Uint8Array(buffer);
  return btoa(String.fromCharCode(...bytes))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=/g, "");
}

async function generatePKCE(): Promise<{ verifier: string; challenge: string }> {
  const verifier = base64url(crypto.getRandomValues(new Uint8Array(32)));
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier));
  return { verifier, challenge: base64url(digest) };
}

export async function redirectToLogin(): Promise<void> {
  const { verifier, challenge } = await generatePKCE();
  sessionStorage.setItem(CODE_VERIFIER_KEY, verifier);

  const params = new URLSearchParams({
    response_type: "code",
    client_id: CLIENT_ID,
    redirect_uri: REDIRECT_URI,
    scope: "openid email profile",
    code_challenge_method: "S256",
    code_challenge: challenge,
  });

  window.location.replace(`https://${COGNITO_DOMAIN}/oauth2/authorize?${params}`);
}

export interface TokenSet {
  access_token: string;
  id_token: string;
  refresh_token: string;
  expires_in: number;
}

export async function exchangeCodeForTokens(code: string): Promise<TokenSet> {
  const verifier = sessionStorage.getItem(CODE_VERIFIER_KEY);
  if (!verifier) throw new Error("Missing PKCE code verifier");
  sessionStorage.removeItem(CODE_VERIFIER_KEY);

  const body = new URLSearchParams({
    grant_type: "authorization_code",
    client_id: CLIENT_ID,
    redirect_uri: REDIRECT_URI,
    code,
    code_verifier: verifier,
  });

  const response = await fetch(`https://${COGNITO_DOMAIN}/oauth2/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });

  if (!response.ok) {
    throw new Error(`Token exchange failed: ${response.statusText}`);
  }

  return response.json() as Promise<TokenSet>;
}

export async function refreshAccessToken(refreshToken: string): Promise<TokenSet> {
  const body = new URLSearchParams({
    grant_type: "refresh_token",
    client_id: CLIENT_ID,
    refresh_token: refreshToken,
  });

  const response = await fetch(`https://${COGNITO_DOMAIN}/oauth2/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });

  if (!response.ok) {
    throw new Error(`Token refresh failed: ${response.statusText}`);
  }

  return response.json() as Promise<TokenSet>;
}

export function logoutUrl(): string {
  const params = new URLSearchParams({
    client_id: CLIENT_ID,
    logout_uri: window.location.origin,
  });
  return `https://${COGNITO_DOMAIN}/logout?${params}`;
}
