// The Analytics page: a live dashboard over the CORDIS corpus.
//
// Reads precomputed aggregates from GET /stats (built by src/data/compute_stats.py)
// and renders five charts plus a KPI row. Everything here is read-only context:
// it is the dataset GrantPilot reasons over, shown honestly.

import React, { useEffect, useState } from "react";

import GrantPilotSidebar from "../grantpilot/GrantPilotSidebar";
import Header from "../partials/Header";
import { api } from "../grantpilot/api";
import { Card, Stat, SkeletonLine } from "../grantpilot/components";
import { HBars, Donut, Histogram, formatEur, formatInt, formatPct } from "../grantpilot/charts";

export default function Analytics() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let alive = true;
    api
      .stats()
      .then((s) => alive && setStats(s))
      .catch((e) => alive && setError(e.message));
    return () => {
      alive = false;
    };
  }, []);

  return (
    <div className="flex h-screen overflow-hidden">
      <GrantPilotSidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />

      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />

        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-9xl mx-auto">
            <div className="mb-8">
              <h1 className="text-2xl md:text-3xl text-gray-800 dark:text-gray-100 font-bold">
                Analytics
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                The corpus GrantPilot reasons over: 35,104 Horizon 2020 projects
              </p>
            </div>

            {error && (
              <div className="mb-6 rounded-lg bg-red-500/10 border border-red-500/30 text-red-600 dark:text-red-400 px-4 py-3 text-sm">
                {error}. Is the backend running, and has{" "}
                <code>python -m src.data.compute_stats</code> been run?
              </div>
            )}

            {!stats && !error && <LoadingGrid />}
            {stats && <Dashboard stats={stats} />}
          </div>
        </main>
      </div>
    </div>
  );
}

function Dashboard({ stats }) {
  const st = stats.status || {};
  const closed = st.CLOSED || 0;
  const signed = st.SIGNED || 0;
  const term = st.TERMINATED || 0;
  const decided = closed + term;
  const termRate = decided ? term / decided : 0;

  const bySch = (stats.by_scheme || []).map((d) => ({ label: d.scheme, value: d.count }));
  const termBars = (stats.failure_rate_by_scheme || []).map((d) => ({
    label: d.scheme,
    value: d.rate,
    n: d.n,
  }));
  const medBars = (stats.median_budget_by_scheme || []).map((d) => ({
    label: d.scheme,
    value: d.median_eur,
    n: d.n,
  }));

  const donut = [
    { label: "Closed", value: closed, strokeClass: "stroke-[#0ca30c]", dotClass: "bg-[#0ca30c]" },
    {
      label: "Signed",
      value: signed,
      strokeClass: "stroke-[#2a78d6] dark:stroke-[#3987e5]",
      dotClass: "bg-[#2a78d6] dark:bg-[#3987e5]",
    },
    { label: "Terminated", value: term, strokeClass: "stroke-[#d03b3b]", dotClass: "bg-[#d03b3b]" },
  ];

  return (
    <div className="grid grid-cols-12 gap-6">
      {/* KPI row */}
      <Kpi label="Total projects" value={formatInt(stats.total)} />
      <Kpi
        label="Termination rate"
        value={formatPct(termRate)}
        sub="of decided projects · equals Model A base rate"
      />
      <Kpi label="Completed (closed)" value={formatInt(closed)} />
      <Kpi label="Ongoing (signed)" value={formatInt(signed)} />

      {/* Projects by scheme */}
      <Card title="Projects by scheme" span="xl:col-span-6" delay={0}>
        <HBars data={bySch} format={formatInt} />
      </Card>

      {/* Status split */}
      <Card title="Status split" span="xl:col-span-6" delay={0.05}>
        <Donut data={donut} centerValue={formatInt(stats.total)} centerLabel="projects" />
      </Card>

      {/* Termination rate by scheme */}
      <Card title="Termination rate by scheme" span="xl:col-span-6" delay={0.1}>
        <HBars
          data={termBars}
          format={formatPct}
          highlight={(d) => d.label === "MSCA-IF"}
        />
        <p className="mt-4 text-xs text-gray-400 dark:text-gray-500 leading-relaxed">
          MSCA-IF (highlighted) is an individual-fellowship scheme: most of its
          terminations are administrative (fellow declines or moves on), not
          project failure. This is why Model A treats funding scheme as a strong
          risk signal.
        </p>
      </Card>

      {/* Median budget by scheme */}
      <Card title="Median EC contribution by scheme" span="xl:col-span-6" delay={0.15}>
        <HBars data={medBars} format={formatEur} />
      </Card>

      {/* Budget distribution */}
      <Card title="Budget distribution" span="xl:col-span-6" className="col-span-full" delay={0.2}>
        <Histogram
          counts={stats.budget_histogram?.counts}
          edges={stats.budget_histogram?.bin_edges_log10}
        />
        <p className="mt-3 text-xs text-gray-400 dark:text-gray-500">
          EC contribution per project, log scale. Each bar is a bucket of projects;
          the axis marks powers of ten in euros.
        </p>
      </Card>
    </div>
  );
}

function Kpi({ label, value, sub }) {
  return (
    <Card span="xl:col-span-3">
      <Stat value={value} label={label} sub={sub} />
    </Card>
  );
}

function LoadingGrid() {
  return (
    <div className="grid grid-cols-12 gap-6">
      {[0, 1].map((i) => (
        <Card key={i} title=" " span="xl:col-span-6">
          <div className="space-y-3">
            <SkeletonLine w="w-2/3" />
            <SkeletonLine w="w-5/6" />
            <SkeletonLine w="w-1/2" />
            <SkeletonLine w="w-3/4" />
          </div>
        </Card>
      ))}
    </div>
  );
}
