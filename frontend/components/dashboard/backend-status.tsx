"use client";

import { useEffect, useState } from "react";

import { getHealth } from "@/lib/api";

type ConnectionState = "checking" | "ok" | "error";

export function BackendStatus() {
  const [state, setState] = useState<ConnectionState>("checking");
  const [detail, setDetail] = useState("Checking connection...");

  useEffect(() => {
    let cancelled = false;

    getHealth()
      .then((health) => {
        if (cancelled) return;
        setState("ok");
        setDetail(`Backend reachable (status: ${health.status})`);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setState("error");
        setDetail(error instanceof Error ? error.message : "Unknown error");
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const badgeColor =
    state === "ok"
      ? "bg-emerald-100 text-emerald-700"
      : state === "error"
        ? "bg-red-100 text-red-700"
        : "bg-slate-100 text-slate-600";

  return (
    <section className="rounded-md border border-line bg-white p-5">
      <p className="text-sm font-medium text-muted">Backend Connectivity</p>
      <span className={`mt-3 inline-block rounded-full px-3 py-1 text-sm font-semibold ${badgeColor}`}>
        {state === "checking" ? "Checking..." : state === "ok" ? "Connected" : "Failed"}
      </span>
      <p className="mt-2 text-sm text-slate-500">{detail}</p>
    </section>
  );
}
