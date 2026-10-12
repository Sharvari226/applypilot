"use client";

import { useEffect, useState } from "react";

type HealthState =
  | { kind: "loading" }
  | { kind: "ok"; database: string }
  | { kind: "error"; message: string };

export default function Home() {
  const [health, setHealth] = useState<HealthState>({ kind: "loading" });

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;

    fetch(`${apiUrl}/health`)
      .then(async (res) => {
        if (!res.ok) throw new Error(`Backend responded with ${res.status}`);
        return res.json();
      })
      .then((data) => setHealth({ kind: "ok", database: data.database }))
      .catch((err: Error) => setHealth({ kind: "error", message: err.message }));
  }, []);

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50">
      <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-2xl font-semibold text-slate-900">ApplyPilot</h1>
        <p className="mt-1 text-sm text-slate-500">System status</p>

        <div className="mt-6 space-y-3 text-sm">
          {health.kind === "loading" && (
            <p className="text-slate-500">Checking backend…</p>
          )}

          {health.kind === "ok" && (
            <>
              <StatusRow label="Backend" value="ok" good />
              <StatusRow label="Database" value={health.database} good />
            </>
          )}

          {health.kind === "error" && (
            <>
              <StatusRow label="Backend" value="unreachable" good={false} />
              <p className="text-red-600">{health.message}</p>
            </>
          )}
        </div>
      </div>
    </main>
  );
}

function StatusRow({
  label,
  value,
  good,
}: {
  label: string;
  value: string;
  good: boolean;
}) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-slate-700">{label}</span>
      <span
        className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
          good ? "bg-emerald-100 text-emerald-700" : "bg-red-100 text-red-700"
        }`}
      >
        {value}
      </span>
    </div>
  );
}