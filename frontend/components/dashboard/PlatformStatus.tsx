import { PanelCard } from "@/components/ui/PanelCard";
import { StatusRow } from "@/components/ui/StatusRow";
import { fetchHealth } from "@/lib/api/health";

const foundationModules = [
  {
    score: "01",
    title: "Monorepo layout",
    subtitle: "Backend, frontend, Docker, docs, scripts, and tests are in place.",
    active: true,
  },
  {
    score: "02",
    title: "FastAPI foundation",
    subtitle: "Versioned API, structured logging, health checks, and OpenAPI docs.",
    active: true,
  },
  {
    score: "03",
    title: "Data layer",
    subtitle: "PostgreSQL pooling, Alembic migrations, and Redis cache conventions.",
    active: true,
  },
  {
    score: "04",
    title: "Dashboard shell",
    subtitle: "Next.js App Router with a dark, card-based intelligence UI.",
    active: true,
  },
] as const;

function statusScore(status: string): number {
  if (status === "ok") {
    return 96;
  }
  if (status === "degraded") {
    return 72;
  }
  return 41;
}

export async function PlatformStatus() {
  let health = null;
  let healthError: string | null = null;

  try {
    health = await fetchHealth({ server: true });
  } catch {
    healthError = "API unavailable. Start the backend or run docker compose up.";
  }

  return (
    <>
      <PanelCard
        eyebrow="Platform status"
        title="Foundation services"
        description="Live health from the versioned API. Database and Redis checks run on every request."
      >
        {healthError ? (
          <p className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
            {healthError}
          </p>
        ) : health ? (
          <div className="space-y-3">
            <StatusRow
              score={statusScore(health.status)}
              title={`API ${health.status}`}
              subtitle={`${health.service} · v${health.version} · ${health.environment}`}
              active
            />
            <StatusRow
              score={statusScore(health.checks.database)}
              title="PostgreSQL"
              subtitle={`Connection check: ${health.checks.database}`}
              active={health.checks.database === "ok"}
            />
            <StatusRow
              score={statusScore(health.checks.redis)}
              title="Redis cache"
              subtitle={`Connection check: ${health.checks.redis}`}
              active={health.checks.redis === "ok"}
            />
          </div>
        ) : null}
      </PanelCard>

      <PanelCard
        eyebrow="Phase 0"
        title="Repository foundation"
        description="The first milestone is a trusted shell for validator intelligence work."
      >
        <div className="space-y-3">
          {foundationModules.map((module) => (
            <StatusRow
              key={module.title}
              score={module.score}
              title={module.title}
              subtitle={module.subtitle}
              active={module.active}
            />
          ))}
        </div>
      </PanelCard>
    </>
  );
}
