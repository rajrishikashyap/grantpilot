// The GrantPilot page: the multi-panel assessment dashboard.
//
// Mirrors Mosaic's Dashboard layout (Sidebar + Header + a 12-col card grid) and
// owns all the result state. The form hands up a payload; this page calls the
// API and fills the panels. Fast endpoints (Quick check) populate eligibility
// and budget instantly; the full assessment adds the quality review, the draft,
// and the advisory risk.

import React, { useState } from "react";
import { motion, AnimatePresence } from "motion/react";

import GrantPilotSidebar from "../grantpilot/GrantPilotSidebar";
import Header from "../partials/Header";

import ProposalForm from "../grantpilot/ProposalForm";
import { api } from "../grantpilot/api";
import { Card, Verdict, Checklist, RiskBars, Stat, GrantResults, SearchSkeleton, AssessmentSkeleton, Spinner, DraftView } from "../grantpilot/components";

export default function GrantPilot() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const [elig, setElig] = useState(null);
  const [budget, setBudget] = useState(null);
  const [report, setReport] = useState(null);
  const [loadingQuick, setLoadingQuick] = useState(false);
  const [loadingAssess, setLoadingAssess] = useState(false);
  const [error, setError] = useState(null);

  const [searchQuery, setSearchQuery] = useState("drone crop disease detection");
  const [searchOut, setSearchOut] = useState({ results: null, loading: false, error: null });

  const quickCheck = async (p) => {
    setError(null);
    setLoadingQuick(true);
    try {
      const [e, b] = await Promise.all([
        api.eligibility({
          scheme: p.scheme,
          ec_contribution: p.ec_contribution,
          consortium_size: p.consortium_size,
          num_countries: p.num_countries,
        }),
        api.budget({ scheme: p.scheme, ec_contribution: p.ec_contribution }),
      ]);
      setElig(e);
      setBudget(b);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingQuick(false);
    }
  };

  const runAssess = async (p) => {
    setError(null);
    setLoadingAssess(true);
    setReport(null);
    try {
      const r = await api.assess(p);
      setReport(r);
      setElig(r.eligibility);
      setBudget(r.budget);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingAssess(false);
    }
  };

  const doSearch = async () => {
    setSearchOut({ results: null, loading: true, error: null });
    try {
      const r = await api.search({ query: searchQuery, k: 5 });
      setSearchOut({ results: r.results, loading: false, error: null });
    } catch (err) {
      setSearchOut({ results: null, loading: false, error: err.message });
    }
  };

  return (
    <div className="flex h-screen overflow-hidden">
      <GrantPilotSidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />

      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />

        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-9xl mx-auto">
            <div className="mb-8">
              <h1 className="text-2xl md:text-3xl text-gray-800 dark:text-gray-100 font-bold">
                GrantPilot
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Multi-agent grant assessment over 35,000 EU-funded projects
              </p>
            </div>

            <AnimatePresence>
              {error && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="mb-6 rounded-lg bg-red-500/10 border border-red-500/30 text-red-600 dark:text-red-400 px-4 py-3 text-sm"
                >
                  {error}
                </motion.div>
              )}
            </AnimatePresence>

            <AnimatePresence>
              {loadingAssess && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="mb-6 rounded-lg bg-violet-500/10 border border-violet-500/20 text-violet-600 dark:text-violet-400 px-4 py-3 text-sm flex items-center gap-2"
                >
                  <Spinner /> Drafting and reviewing with the local model. This takes a moment.
                </motion.div>
              )}
            </AnimatePresence>

            <div className="grid grid-cols-12 gap-6">
              {/* Input */}
              <ProposalForm
                onQuickCheck={quickCheck}
                onAssess={runAssess}
                loadingQuick={loadingQuick}
                loadingAssess={loadingAssess}
              />

              {/* Eligibility */}
              <Card title="Eligibility" span="xl:col-span-4" delay={0.05}>
                {elig ? (
                  <div className="space-y-3">
                    <Verdict value={elig.verdict} />
                    {elig.checks && elig.checks.length > 0 && (
                      <Checklist checks={elig.checks} />
                    )}
                  </div>
                ) : (
                  <Placeholder text="Run a check to see eligibility." />
                )}
              </Card>

              {/* Budget */}
              <Card title="Budget" span="xl:col-span-4" delay={0.1}>
                {budget ? (
                  budget.scored ? (
                    <div className="space-y-3">
                      <Verdict value={budget.is_anomaly ? "ANOMALOUS" : "normal"} />
                      <Stat
                        value={`z = ${budget.robust_z}`}
                        label={`requested ${fmtEur(budget.budget_eur)}`}
                        sub={`scheme median ${fmtEur(budget.scheme_median_eur)}`}
                      />
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        {budget.explanation}
                      </p>
                    </div>
                  ) : (
                    <Placeholder text={budget.reason || "Could not score."} />
                  )
                ) : (
                  <Placeholder text="Run a check to see the budget anomaly." />
                )}
              </Card>

              {/* Skeleton panels while the assessment is running */}
              {loadingAssess && <AssessmentSkeleton />}

              {/* Assessment panels appear after a full assessment */}
              {report && !report.gated && (
                <>
                  {/* Quality */}
                  <Card title="Quality review" span="xl:col-span-4" delay={0}>
                    <div className="mb-3 text-sm text-gray-500 dark:text-gray-400">
                      {report.quality.passed}/{report.quality.total} checks passed
                    </div>
                    <Checklist checks={report.quality.checks} />
                  </Card>

                  {/* Advisory risk */}
                  <Card title="Post-award risk (advisory)" span="xl:col-span-4" delay={0.08}>
                    <div className="space-y-4">
                      <div className="flex items-center gap-3">
                        <Verdict value={report.advisory_risk.band} />
                        <span className="text-sm text-gray-500 dark:text-gray-400">
                          {(report.advisory_risk.risk * 100).toFixed(1)}% (
                          {report.advisory_risk.relative_to_base.toFixed(2)}x base)
                        </span>
                      </div>
                      <div>
                        <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">
                          Top risk-raising words (SHAP)
                        </div>
                        <RiskBars words={report.advisory_risk.risk_words} />
                      </div>
                      <p className="text-xs text-gray-400 dark:text-gray-500">
                        Advisory only. Model A risk is scheme-dominated, so this is
                        context, not an optimisation target.
                      </p>
                    </div>
                  </Card>

                  {/* Draft */}
                  <Card title="Drafted section" span="xl:col-span-8" className="col-span-full" delay={0.16}>
                    <DraftView text={report.quality.final_draft} />
                  </Card>
                </>
              )}

              {report && report.gated && (
                <Card title="Assessment" span="xl:col-span-8" className="col-span-full">
                  <Placeholder text="Proposal is NOT ELIGIBLE, so drafting was skipped." />
                </Card>
              )}

              {/* Precedent search (independent) */}
              <Card title="Precedent search" span="xl:col-span-4" className="col-span-full" delay={0.05}>
                <div className="flex gap-2 mb-4">
                  <input
                    className="flex-1 rounded-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700/60 text-sm px-3 py-2 text-gray-800 dark:text-gray-100 focus:ring-violet-500 focus:border-violet-500"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && doSearch()}
                    placeholder="Search 35k funded projects..."
                  />
                  <button
                    onClick={doSearch}
                    disabled={searchOut.loading}
                    className="btn bg-violet-500 hover:bg-violet-600 text-white disabled:opacity-50"
                  >
                    {searchOut.loading ? "..." : "Search"}
                  </button>
                </div>
                {searchOut.loading && <SearchSkeleton />}
                {searchOut.error && (
                  <p className="text-sm text-red-500">{searchOut.error}</p>
                )}
                {searchOut.results && <GrantResults results={searchOut.results} />}
              </Card>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

function Placeholder({ text }) {
  return <p className="text-sm text-gray-400 dark:text-gray-500">{text}</p>;
}

function fmtEur(n) {
  if (n === null || n === undefined) return "n/a";
  return "€" + Number(n).toLocaleString();
}
