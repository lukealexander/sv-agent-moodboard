import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "../auth/AuthContext";
import { API_BASE, fetchWithAuth } from "../api/client";
import { Modal } from "../components/Modal";
import styles from "./Home.module.css";

const LOCAL_DEV = import.meta.env.VITE_LOCAL_DEV === "true";
const COGNITO_DOMAIN = import.meta.env.VITE_COGNITO_DOMAIN as string | undefined;
const MODE = import.meta.env.MODE;

type Status = "ok" | "down" | "pending";
type ModalKey = "heartbeat" | "database" | "auth" | "identity" | "items";

interface Item {
  id: number;
  name: string;
  description: string | null;
}

interface WhoAmI {
  sub: string | null;
  email: string | null;
  claims: Record<string, unknown>;
}

interface Heartbeat {
  status: string;
  latencyMs: number;
}

interface DbHealth {
  status: "ok" | "error" | "disabled";
  detail?: string;
  latencyMs: number;
}

/** Pings the API's /health endpoint and measures round-trip latency. */
async function checkHeartbeat(): Promise<Heartbeat> {
  const start = performance.now();
  const response = await fetch(`${API_BASE}/health`);
  const latencyMs = Math.round(performance.now() - start);
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status}`);
  }
  const data = (await response.json()) as { status: string };
  return { status: data.status, latencyMs };
}

/**
 * Asks the API whether it can reach the database (`GET /health/db`).
 *
 * The body is read on every response — including the 503 the API returns when the
 * DB is configured but unreachable — so the row can distinguish "down" from
 * "disabled". Only a transport failure (API itself unreachable) rejects, which the
 * query surfaces as an error.
 */
async function checkDbHealth(): Promise<DbHealth> {
  const start = performance.now();
  const response = await fetch(`${API_BASE}/health/db`);
  const latencyMs = Math.round(performance.now() - start);
  const data = (await response.json()) as { status?: string; detail?: string };
  const status: DbHealth["status"] =
    data.status === "ok" || data.status === "disabled" ? data.status : "error";
  return { status, detail: data.detail, latencyMs };
}

/** Decodes a JWT payload without verifying it. Returns null if not a JWT. */
function decodeJwt(token: string): Record<string, unknown> | null {
  const parts = token.split(".");
  if (parts.length !== 3) return null;
  try {
    const json = atob(parts[1].replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(json) as Record<string, unknown>;
  } catch {
    return null;
  }
}

function formatClaim(key: string, value: unknown): string {
  if (
    typeof value === "number" &&
    ["exp", "iat", "auth_time", "nbf"].includes(key)
  ) {
    return new Date(value * 1000).toLocaleString();
  }
  return typeof value === "string" ? value : JSON.stringify(value);
}

function StatusRow({
  status,
  label,
  detail,
  onClick,
}: {
  status: Status;
  label: string;
  detail: string;
  onClick: () => void;
}) {
  return (
    <button type="button" className={styles.row} onClick={onClick}>
      <span className={`${styles.dot} ${styles[status]}`} aria-hidden="true" />
      <div className={styles.rowText}>
        <span className={styles.rowLabel}>{label}</span>
        <span className={styles.rowDetail}>{detail}</span>
      </div>
      <span className={`${styles.badge} ${styles[status]}`}>
        {status === "ok" ? "OK" : status === "down" ? "Down" : "Checking"}
      </span>
      <span className={styles.chevron} aria-hidden="true">
        ›
      </span>
    </button>
  );
}

function EnvItem({ label, value }: { label: string; value: string }) {
  return (
    <div className={styles.envItem}>
      <span className={styles.envLabel}>{label}</span>
      <span className={styles.envValue}>{value}</span>
    </div>
  );
}

function DetailList({ rows }: { rows: [string, string][] }) {
  return (
    <dl className={styles.detailList}>
      {rows.map(([k, v]) => (
        <div key={k} className={styles.detailRow}>
          <dt className={styles.detailKey}>{k}</dt>
          <dd className={styles.detailValue}>{v}</dd>
        </div>
      ))}
    </dl>
  );
}

function CodeBlock({ children }: { children: string }) {
  return <pre className={styles.codeBlock}>{children}</pre>;
}

export function Home() {
  const { accessToken, isAuthenticated, logout } = useAuth();
  const [openModal, setOpenModal] = useState<ModalKey | null>(null);

  const heartbeat = useQuery({
    queryKey: ["heartbeat"],
    queryFn: checkHeartbeat,
    refetchInterval: 10_000,
    retry: false,
  });

  const dbHealth = useQuery({
    queryKey: ["db-health"],
    queryFn: checkDbHealth,
    refetchInterval: 30_000,
    retry: false,
  });

  const whoami = useQuery({
    queryKey: ["whoami"],
    queryFn: () => fetchWithAuth<WhoAmI>("/whoami", accessToken),
    enabled: isAuthenticated,
    retry: false,
  });

  const items = useQuery({
    queryKey: ["items"],
    queryFn: () => fetchWithAuth<Item[]>("/items", accessToken),
    enabled: isAuthenticated,
    retry: false,
  });

  const heartbeatStatus: Status = heartbeat.isPending
    ? "pending"
    : heartbeat.isError
      ? "down"
      : "ok";

  const heartbeatDetail = heartbeat.isPending
    ? "Pinging /health…"
    : heartbeat.isError
      ? "No response from the API"
      : `Responded in ${heartbeat.data.latencyMs} ms`;

  const dbStatus: Status = dbHealth.isPending
    ? "pending"
    : dbHealth.isError || dbHealth.data.status !== "ok"
      ? "down"
      : "ok";

  const dbDetail = dbHealth.isPending
    ? "Checking /health/db…"
    : dbHealth.isError
      ? "No response from the API"
      : dbHealth.data.status === "ok"
        ? `Connected in ${dbHealth.data.latencyMs} ms`
        : dbHealth.data.status === "disabled"
          ? "No database configured (DATABASE_URL unset)"
          : "Configured but unreachable";

  const authStatus: Status = isAuthenticated ? "ok" : "down";
  const authDetail = !isAuthenticated
    ? "Not signed in"
    : LOCAL_DEV
      ? "Local dev session (auth bypassed)"
      : "Signed in via Cognito";

  const identityStatus: Status = !isAuthenticated
    ? "pending"
    : whoami.isPending
      ? "pending"
      : whoami.isError
        ? "down"
        : "ok";

  const identityName = whoami.data?.email ?? whoami.data?.sub ?? null;
  const identityDetail = !isAuthenticated
    ? "Sign in to resolve your identity"
    : whoami.isPending
      ? "Resolving /whoami…"
      : whoami.isError
        ? "Request failed — token rejected or API down"
        : identityName
          ? `Resolved as ${identityName}`
          : "Token validated — no identity claims returned";

  const itemsStatus: Status = !isAuthenticated
    ? "pending"
    : items.isPending
      ? "pending"
      : items.isError
        ? "down"
        : "ok";

  const itemsDetail = !isAuthenticated
    ? "Sign in to query protected routes"
    : items.isPending
      ? "Fetching /items…"
      : items.isError
        ? "Request failed — token rejected or API down"
        : `Authorized — ${items.data.length} item${items.data.length === 1 ? "" : "s"} returned`;

  const healthUrl = `${API_BASE || "(same origin)"}/health`;
  const dbHealthUrl = `${API_BASE || "(same origin)"}/health/db`;
  const claims = accessToken ? decodeJwt(accessToken) : null;

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div>
          <h1>sv-skeleton</h1>
          <p className={styles.subtitle}>Service status &amp; developer dashboard</p>
        </div>
        <button onClick={logout}>Sign out</button>
      </header>

      <main className={styles.main}>
        <section className={styles.card}>
          <h2 className={styles.cardTitle}>System status</h2>
          <p className={styles.hint}>Select a check for details.</p>
          <div className={styles.rows}>
            <StatusRow
              status={heartbeatStatus}
              label="API heartbeat"
              detail={heartbeatDetail}
              onClick={() => setOpenModal("heartbeat")}
            />
            <StatusRow
              status={dbStatus}
              label="Database connection"
              detail={dbDetail}
              onClick={() => setOpenModal("database")}
            />
            <StatusRow
              status={authStatus}
              label="Authentication"
              detail={authDetail}
              onClick={() => setOpenModal("auth")}
            />
            <StatusRow
              status={identityStatus}
              label="Identity (/whoami)"
              detail={identityDetail}
              onClick={() => setOpenModal("identity")}
            />
            <StatusRow
              status={itemsStatus}
              label="Protected API access"
              detail={itemsDetail}
              onClick={() => setOpenModal("items")}
            />
          </div>
        </section>

        <section className={styles.card}>
          <h2 className={styles.cardTitle}>Environment</h2>
          <div className={styles.envGrid}>
            <EnvItem label="Local dev mode" value={LOCAL_DEV ? "On" : "Off"} />
            <EnvItem label="Build mode" value={MODE} />
            <EnvItem label="API base URL" value={API_BASE || "(same origin)"} />
            <EnvItem
              label="Cognito domain"
              value={COGNITO_DOMAIN ? COGNITO_DOMAIN : "Not configured"}
            />
          </div>
        </section>
      </main>

      {openModal === "heartbeat" && (
        <Modal title="API heartbeat" onClose={() => setOpenModal(null)}>
          <DetailList
            rows={[
              ["Endpoint", `GET ${healthUrl}`],
              ["Poll interval", "10 s"],
              ["Status", heartbeat.isError ? "Unreachable" : heartbeat.isPending ? "Checking…" : "Operational"],
              ["Latency", heartbeat.data ? `${heartbeat.data.latencyMs} ms` : "—"],
              [
                "Last checked",
                heartbeat.dataUpdatedAt || heartbeat.errorUpdatedAt
                  ? new Date(
                      Math.max(heartbeat.dataUpdatedAt, heartbeat.errorUpdatedAt),
                    ).toLocaleTimeString()
                  : "—",
              ],
            ]}
          />
          {heartbeat.isError ? (
            <>
              <h3 className={styles.modalSubhead}>Error</h3>
              <CodeBlock>{(heartbeat.error as Error).message}</CodeBlock>
            </>
          ) : heartbeat.data ? (
            <>
              <h3 className={styles.modalSubhead}>Response body</h3>
              <CodeBlock>{JSON.stringify({ status: heartbeat.data.status }, null, 2)}</CodeBlock>
            </>
          ) : null}
        </Modal>
      )}

      {openModal === "database" && (
        <Modal title="Database connection" onClose={() => setOpenModal(null)}>
          <DetailList
            rows={[
              ["Endpoint", `GET ${dbHealthUrl}`],
              ["Probe", "SELECT 1 on the API's connection pool"],
              ["Poll interval", "30 s"],
              [
                "Status",
                dbHealth.isError
                  ? "Unreachable"
                  : dbHealth.isPending
                    ? "Checking…"
                    : dbHealth.data.status === "ok"
                      ? "Connected"
                      : dbHealth.data.status === "disabled"
                        ? "Not configured"
                        : "Unreachable",
              ],
              ["Latency", dbHealth.data ? `${dbHealth.data.latencyMs} ms` : "—"],
              [
                "Last checked",
                dbHealth.dataUpdatedAt || dbHealth.errorUpdatedAt
                  ? new Date(
                      Math.max(dbHealth.dataUpdatedAt, dbHealth.errorUpdatedAt),
                    ).toLocaleTimeString()
                  : "—",
              ],
            ]}
          />
          <p className={styles.note}>
            This is a readiness probe, separate from the API heartbeat: the API can be
            up while the database is unreachable. It never affects the load-balancer
            health check, so a database blip won't cycle the API tasks.
          </p>
          {dbHealth.isError ? (
            <>
              <h3 className={styles.modalSubhead}>Error</h3>
              <CodeBlock>{(dbHealth.error as Error).message}</CodeBlock>
            </>
          ) : dbHealth.data?.status === "error" ? (
            <>
              <h3 className={styles.modalSubhead}>Error</h3>
              <CodeBlock>
                {dbHealth.data.detail ?? "Database is configured but unreachable."}
              </CodeBlock>
            </>
          ) : dbHealth.data?.status === "disabled" ? (
            <p className={styles.note}>
              No DATABASE_URL is set, so the API's database layer is dormant.
              Configure it to enable persistence.
            </p>
          ) : null}
        </Modal>
      )}

      {openModal === "auth" && (
        <Modal title="Authentication" onClose={() => setOpenModal(null)}>
          <DetailList
            rows={[
              ["Method", LOCAL_DEV ? "Local dev (auth bypassed)" : "AWS Cognito (OAuth2 + PKCE)"],
              ["Authenticated", isAuthenticated ? "Yes" : "No"],
              ["Cognito domain", COGNITO_DOMAIN ?? "Not configured"],
            ]}
          />
          {LOCAL_DEV && (
            <p className={styles.note}>
              Running in local dev mode — a stub token is used and the access token is
              not a real JWT.
            </p>
          )}
          {claims ? (
            <>
              <h3 className={styles.modalSubhead}>Access token claims</h3>
              <DetailList
                rows={Object.entries(claims).map(([k, v]) => [k, formatClaim(k, v)])}
              />
            </>
          ) : accessToken ? (
            <p className={styles.note}>Access token is not a decodable JWT.</p>
          ) : (
            <p className={styles.note}>No access token present.</p>
          )}
          {accessToken && (
            <>
              <h3 className={styles.modalSubhead}>Raw access token</h3>
              <CodeBlock>{accessToken}</CodeBlock>
            </>
          )}
        </Modal>
      )}

      {openModal === "identity" && (
        <Modal title="Identity (/whoami)" onClose={() => setOpenModal(null)}>
          <DetailList
            rows={[
              ["Endpoint", `GET ${API_BASE || "(same origin)"}/whoami`],
              ["Auth", "Bearer token required"],
              [
                "Status",
                !isAuthenticated
                  ? "Not signed in"
                  : whoami.isError
                    ? "Request failed"
                    : whoami.isPending
                      ? "Loading…"
                      : "Resolved",
              ],
              ["Subject (sub)", whoami.data?.sub ?? "—"],
              ["Email", whoami.data?.email ?? "—"],
            ]}
          />
          <p className={styles.note}>
            Unlike the Authentication panel (which decodes the JWT in the browser),
            this calls the API — so a success proves the backend validated the token
            and resolved your identity server-side.
          </p>
          {!isAuthenticated ? (
            <p className={styles.note}>Sign in to call this protected endpoint.</p>
          ) : whoami.isError ? (
            <>
              <h3 className={styles.modalSubhead}>Error</h3>
              <CodeBlock>{(whoami.error as Error).message}</CodeBlock>
            </>
          ) : whoami.isPending ? (
            <p className={styles.note}>Calling /whoami…</p>
          ) : (
            <>
              <h3 className={styles.modalSubhead}>Claims (server-side)</h3>
              <CodeBlock>{JSON.stringify(whoami.data.claims, null, 2)}</CodeBlock>
            </>
          )}
        </Modal>
      )}

      {openModal === "items" && (
        <Modal title="Protected API access" onClose={() => setOpenModal(null)}>
          <DetailList
            rows={[
              ["Endpoint", `GET ${API_BASE || "(same origin)"}/items`],
              ["Auth", "Bearer token required"],
              [
                "Status",
                !isAuthenticated
                  ? "Not signed in"
                  : items.isError
                    ? "Request failed"
                    : items.isPending
                      ? "Loading…"
                      : "Authorized",
              ],
              ["Items returned", items.data ? String(items.data.length) : "—"],
            ]}
          />
          {!isAuthenticated ? (
            <p className={styles.note}>Sign in to query protected routes.</p>
          ) : items.isError ? (
            <>
              <h3 className={styles.modalSubhead}>Error</h3>
              <CodeBlock>{(items.error as Error).message}</CodeBlock>
            </>
          ) : items.isPending ? (
            <p className={styles.note}>Fetching items…</p>
          ) : items.data.length === 0 ? (
            <p className={styles.note}>The endpoint responded with an empty list.</p>
          ) : (
            <>
              <h3 className={styles.modalSubhead}>Items</h3>
              <ul className={styles.itemList}>
                {items.data.map((item) => (
                  <li key={item.id} className={styles.item}>
                    <span className={styles.itemName}>
                      <span className={styles.itemId}>#{item.id}</span> {item.name}
                    </span>
                    {item.description && (
                      <span className={styles.itemDesc}>{item.description}</span>
                    )}
                  </li>
                ))}
              </ul>
            </>
          )}
        </Modal>
      )}
    </div>
  );
}
