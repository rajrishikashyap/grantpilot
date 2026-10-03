// Small presentational components for GrantPilot, styled to match Mosaic's
// cards and animated with Motion (motion.dev). No business logic here; the
// page owns state and passes data in.

import { motion } from "motion/react";

// A Mosaic-style card with an optional title and a Motion fade-up on mount.
export function Card({ title, children, span = "xl:col-span-4", className = "", delay = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut", delay }}
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

// A stacked list of precedent-search hits as compact cards. `results` is the
// array from POST /search (id, acronym, title, scheme, status, similarity,
// objective). Each card staggers in.
export function GrantResults({ results }) {
  if (!results || results.length === 0)
    return <p className="text-sm text-gray-400 dark:text-gray-500">No matches.</p>;
  return (
    <div className="space-y-3">
      {results.map((g, i) => (
        <motion.div
          key={`${g.id}-${i}`}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, delay: i * 0.05, ease: "easeOut" }}
          className="rounded-lg border border-gray-200 dark:border-gray-700/60 p-4 hover:border-violet-300 dark:hover:border-violet-500/40 transition-colors"
        >
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-semibold text-gray-800 dark:text-gray-100 truncate">
                  {g.acronym || g.id}
                </span>
                <SchemeTag scheme={g.scheme} />
                <StatusTag status={g.status} />
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-300 mt-0.5 line-clamp-1">
                {g.title}
              </p>
            </div>
            <SimBadge value={g.similarity} />
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-2 leading-relaxed line-clamp-2">
            {g.objective}
          </p>
        </motion.div>
      ))}
    </div>
  );
}

function SchemeTag({ scheme }) {
  if (!scheme) return null;
  return (
    <span className="shrink-0 rounded px-1.5 py-0.5 text-xs font-medium bg-violet-500/10 text-violet-600 dark:text-violet-400">
      {scheme}
    </span>
  );
}

const STATUS_COLORS = {
  CLOSED: "bg-gray-500/10 text-gray-500 dark:text-gray-400",
  SIGNED: "bg-blue-500/10 text-blue-600 dark:text-blue-400",
  TERMINATED: "bg-red-500/10 text-red-600 dark:text-red-400",
};
function StatusTag({ status }) {
  if (!status) return null;
  const cls = STATUS_COLORS[status] || "bg-gray-500/10 text-gray-500 dark:text-gray-400";
  return (
    <span className={`shrink-0 rounded px-1.5 py-0.5 text-xs font-medium ${cls}`}>
      {status}
    </span>
  );
}

// Cosine similarity in [0,1]. Shown as a raw number, not a percentage, to stay
// honest: it is a distance-derived score, not a probability of relevance.
function SimBadge({ value }) {
  return (
    <div className="shrink-0 text-right">
      <div className="text-sm font-semibold text-gray-700 dark:text-gray-200">
        {Number(value).toFixed(2)}
      </div>
      <div className="text-xs text-gray-400 dark:text-gray-500">similarity</div>
    </div>
  );
}

// A shimmering placeholder line.
export function SkeletonLine({ w = "w-full" }) {
  return <div className={`h-3 rounded bg-gray-200 dark:bg-gray-700/60 animate-pulse ${w}`} />;
}

// Placeholder for the precedent-search list while a query is in flight.
export function SearchSkeleton() {
  return (
    <div className="space-y-3">
      {[0, 1, 2].map((i) => (
        <div key={i} className="rounded-lg border border-gray-200 dark:border-gray-700/60 p-4 space-y-2">
          <SkeletonLine w="w-1/3" />
          <SkeletonLine w="w-2/3" />
          <SkeletonLine w="w-full" />
        </div>
      ))}
    </div>
  );
}

// A small inline spinner.
export function Spinner({ className = "w-4 h-4" }) {
  return (
    <svg className={`animate-spin ${className}`} viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 1 8-8v4a4 4 0 0 0-4 4H4z" />
    </svg>
  );
}

// Skeleton panels shown while the full assessment runs (the LLM step is slow).
// Mirrors the three real result cards so the layout does not jump when data lands.
export function AssessmentSkeleton() {
  return (
    <>
      <Card title="Quality review" span="xl:col-span-4">
        <div className="space-y-3">
          <SkeletonLine w="w-1/2" />
          <SkeletonLine w="w-5/6" />
          <SkeletonLine w="w-4/6" />
          <SkeletonLine w="w-3/6" />
        </div>
      </Card>

      <Card title="Post-award risk (advisory)" span="xl:col-span-4">
        <div className="space-y-3">
          <SkeletonLine w="w-1/3" />
          <SkeletonLine w="w-full" />
          <SkeletonLine w="w-5/6" />
          <SkeletonLine w="w-4/6" />
        </div>
      </Card>

      <Card title="Drafted section" span="xl:col-span-8" className="col-span-full">
        <div className="space-y-3">
          <SkeletonLine w="w-full" />
          <SkeletonLine w="w-full" />
          <SkeletonLine w="w-11/12" />
          <SkeletonLine w="w-10/12" />
          <SkeletonLine w="w-full" />
          <SkeletonLine w="w-9/12" />
        </div>
      </Card>
    </>
  );
}

// Renders a drafted proposal section with real typography instead of a <pre>.
// The draft has a light structure (short "Header:" lines, numbered objectives,
// paragraphs); we style each kind rather than dumping monospace text.
export function DraftView({ text }) {
  if (!text) return null;
  const lines = text.split("\n");
  const blocks = [];
  let list = null;

  const flushList = () => {
    if (list) { blocks.push({ type: "list", ...list }); list = null; }
  };

  for (const raw of lines) {
    const line = raw.trim();
    if (!line) { flushList(); continue; }

    const isHeader = /^[A-Za-z][A-Za-z /&-]{0,28}:$/.test(line);
    const listMatch = line.match(/^(\d+[.)]|[-*•])\s+(.*)$/);

    if (isHeader) {
      flushList();
      blocks.push({ type: "header", text: line.replace(/:$/, "") });
    } else if (listMatch) {
      const ordered = /\d/.test(listMatch[1]);
      if (!list) list = { ordered, items: [] };
      list.items.push(listMatch[2]);
    } else {
      flushList();
      blocks.push({ type: "para", text: line });
    }
  }
  flushList();

  return (
    <div className="space-y-4 text-sm leading-relaxed text-gray-700 dark:text-gray-300">
      {blocks.map((b, i) => {
        if (b.type === "header")
          return (
            <h3 key={i} className="text-xs font-semibold uppercase tracking-wide text-violet-600 dark:text-violet-400">
              {b.text}
            </h3>
          );
        if (b.type === "list") {
          const List = b.ordered ? "ol" : "ul";
          return (
            <List
              key={i}
              className={`space-y-2 ${b.ordered ? "list-decimal" : "list-disc"} list-inside marker:text-gray-400 dark:marker:text-gray-500`}
            >
              {b.items.map((it, j) => (
                <li key={j} className="pl-1">{it}</li>
              ))}
            </List>
          );
        }
        return <p key={i}>{b.text}</p>;
      })}
    </div>
  );
}
