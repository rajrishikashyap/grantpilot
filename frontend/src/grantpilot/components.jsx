// Small presentational components for GrantPilot, styled to match Mosaic's
// cards and animated with Motion (motion.dev). No business logic here; the
// page owns state and passes data in.

import { motion } from "motion/react";

// A Mosaic-style card with an optional title and a Motion fade-up on mount.
export function Card({ title, children, span = "xl:col-span-4", className = "" }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className={`flex flex-col col-span-full sm:col-span-6 ${span} bg-white dark:bg-gray-800 shadow-xs rounded-xl ${className}`}
    >
      {title && (
        <header className="px-5 py-4 border-b border-gray-100 dark:border-gray-700/60">
          <h2 className="font-semibold text-gray-800 dark:text-gray-100">{title}</h2>
        </header>
      )}
      <div className="p-5 grow">{children}</div>
    </motion.div>
  );
}

// A colored verdict pill. Handles the eligibility, budget and risk vocabularies.
export function Verdict({ value }) {
  const map = {
    "ELIGIBLE": "bg-green-500/15 text-green-600 dark:text-green-400",
    "NOT ELIGIBLE": "bg-red-500/15 text-red-600 dark:text-red-400",
    "UNDETERMINED": "bg-amber-500/15 text-amber-600 dark:text-amber-500",
    "normal": "bg-green-500/15 text-green-600 dark:text-green-400",
    "ANOMALOUS": "bg-red-500/15 text-red-600 dark:text-red-400",
    "LOW": "bg-green-500/15 text-green-600 dark:text-green-400",
    "MODERATE": "bg-amber-500/15 text-amber-600 dark:text-amber-500",
    "HIGH": "bg-red-500/15 text-red-600 dark:text-red-400",
  };
  const cls = map[value] || "bg-gray-500/15 text-gray-600 dark:text-gray-300";
  return (
    <span className={`inline-flex rounded-full text-sm font-medium px-2.5 py-1 ${cls}`}>
      {value}
    </span>
  );
}

// A pass/fail/unchecked checklist for eligibility rules or quality checks.
// Each item is [label, passed, detail] where passed is true, false, or null.
export function Checklist({ checks }) {
  const mark = (p) =>
    p === true ? ["✓", "text-green-500"]
    : p === false ? ["✕", "text-red-500"]
    : ["–", "text-amber-500"];
  return (
    <ul className="space-y-2">
      {checks.map(([label, passed, detail], i) => {
        const [sym, color] = mark(passed);
        return (
          <li key={i} className="flex items-start text-sm">
            <span className={`mt-0.5 mr-2 font-semibold ${color}`}>{sym}</span>
            <span className="text-gray-700 dark:text-gray-300">
              {label}{" "}
              {detail && <span className="text-gray-400 dark:text-gray-500">({detail})</span>}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

// Horizontal SHAP-style bars for the risk-driving words. `words` is
// [[word, value], ...]; bars are scaled to the largest magnitude and animate in.
export function RiskBars({ words, color = "violet" }) {
  if (!words || words.length === 0)
    return <p className="text-sm text-gray-400">No drivers.</p>;
  const max = Math.max(...words.map(([, v]) => Math.abs(v)), 0.001);
  const bar = color === "green" ? "bg-green-500" : "bg-violet-500";
  return (
    <div className="space-y-2">
      {words.map(([word, val], i) => (
        <div key={i} className="flex items-center text-xs">
          <span className="w-28 shrink-0 truncate text-gray-600 dark:text-gray-400">{word}</span>
          <div className="flex-1 h-2.5 overflow-hidden rounded bg-gray-100 dark:bg-gray-700/50">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${(Math.abs(val) / max) * 100}%` }}
              transition={{ duration: 0.5, delay: i * 0.05, ease: "easeOut" }}
              className={`h-full rounded ${bar}`}
            />
          </div>
          <span className="w-12 text-right text-gray-500 dark:text-gray-400">
            {val.toFixed(2)}
          </span>
        </div>
      ))}
    </div>
  );
}

// A big number with a label, for the risk percentage etc.
export function Stat({ value, label, sub }) {
  return (
    <div>
      <div className="text-3xl font-bold text-gray-800 dark:text-gray-100">{value}</div>
      <div className="text-sm text-gray-500 dark:text-gray-400">{label}</div>
      {sub && <div className="text-xs text-gray-400 dark:text-gray-500 mt-1">{sub}</div>}
    </div>
  );
}
