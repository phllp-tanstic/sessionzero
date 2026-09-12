"use client";

import { useEffect, useState } from "react";

type Capability = {
  capability: string;
  status: "AVAILABLE" | "GATED" | "UNAVAILABLE" | "UNKNOWN";
  reason: string;
};

type CapabilityResponse = {
  source: string;
  capabilities: Capability[];
};

export default function Home() {
  const [data, setData] = useState<CapabilityResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/capabilities", { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error(`API returned HTTP ${response.status}`);
        return response.json() as Promise<CapabilityResponse>;
      })
      .then(setData)
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        setError(reason instanceof Error ? reason.message : "API unavailable");
      });
    return () => controller.abort();
  }, []);

  return (
    <main>
      <section className="hero">
        <p className="eyebrow">PHASE 0 · READ-ONLY FOUNDATION</p>
        <h1>SessionZero</h1>
        <p className="thesis">
          Price discovery for the market session that did not exist before 24/7 equities.
        </p>
      </section>

      <section aria-labelledby="capability-heading" className="panel">
        <div className="panel-heading">
          <h2 id="capability-heading">Provider capabilities</h2>
          <span>{data?.source ?? "bitget_uta_v3"}</span>
        </div>
        {error ? <p className="error">DATA UNAVAILABLE · {error}</p> : null}
        {!data && !error ? <p className="muted">Checking API…</p> : null}
        {data ? (
          <ul>
            {data.capabilities.map((item) => (
              <li key={item.capability}>
                <div>
                  <strong>{item.capability.replaceAll("_", " ")}</strong>
                  <small>{item.reason}</small>
                </div>
                <span className={`status status-${item.status.toLowerCase()}`}>
                  {item.status}
                </span>
              </li>
            ))}
          </ul>
        ) : null}
      </section>

      <p className="boundary">
        No fair value, market-state, conviction, or trading decision is produced in Phase 0.
      </p>
    </main>
  );
}
