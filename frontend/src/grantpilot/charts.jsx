// Hand-built SVG/CSS charts for the analytics dashboard. No charting library:
// the marks are plain divs and SVG, animated with Motion, themed with Tailwind.
// This keeps the bundle small, works identically in light and dark, and matches
// the RiskBars aesthetic already used on the assess page.
//
// Colors follow a validated palette: a single violet accent for single-series
// bars (identity is carried by each bar's own label, so no legend is needed),
// amber to flag an outlier, and a CVD-checked green/blue/red triplet for the
// status donut (every slice is also labelled, so meaning is never colour-alone).

import React from "react";
import { motion } from "motion/react";

// ----- formatting helpers -----

export function formatInt(v) {
  return Number(v).toLocaleString();
}

export function formatEur(v) {
  const n = Number(v);
  if (n >= 1e6) return `€${(n / 1e6).toFixed(2)}M`;
  if (n >= 1e3) return `€${Math.round(n / 1e3)}K`;
  return `€${Math.round(n)}`;
}

export function formatPct(v) {
  return `${(Number(v) * 100).toFixed(1)}%`;
}

function Empty() {
  return <p className="text-sm text-gray-400 dark:text-gray-500">No data.</p>;
}

// ----- horizontal bars (magnitude, one series) -----
// data: [{ label, value, n? }]. `format` renders the value, `highlight(d)`
// flags a bar amber (used for the MSCA-IF outlier).

export function HBars({ data, format = formatInt, highlight }) {
  if (!data || data.length === 0) return <Empty />;
  const max = Math.max(...data.map((d) => d.value), 0.0001);
  return (
    <div className="space-y-2.5">
      {data.map((d, i) => {
        const hi = highlight && highlight(d);
        return (
          <div key={d.label} className="flex items-center text-xs gap-3">
            <span className="w-24 shrink-0 truncate text-right text-gray-600 dark:text-gray-400">
              {d.label}
            </span>
            <div className="flex-1 h-3 rounded bg-gray-100 dark:bg-gray-700/50 overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${(d.value / max) * 100}%` }}
                transition={{ duration: 0.5, delay: i * 0.04, ease: "easeOut" }}
                className={`h-full rounded ${hi ? "bg-amber-500" : "bg-violet-500"}`}
                title={`${d.label}: ${format(d.value)}${d.n ? ` (n=${d.n})` : ""}`}
              />
            </div>
            <span className="w-20 shrink-0 text-right tabular-nums text-gray-500 dark:text-gray-400">
              {format(d.value)}
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ----- donut (a part-to-whole split) -----
// data: [{ label, value, strokeClass, dotClass }]. strokeClass/dotClass are full
// Tailwind arbitrary-colour classes so JIT picks them up from source.

export function Donut({ data, centerValue, centerLabel }) {
  if (!data || data.length === 0) return <Empty />;
  const total = data.reduce((s, d) => s + d.value, 0) || 1;
  const r = 60;
  const sw = 22;
  const gap = 0.012; // fractional gap between slices (the 2px surface break)
  let acc = 0;

  return (
    <div className="flex items-center gap-6 flex-wrap">
      <div className="relative shrink-0" style={{ width: 160, height: 160 }}>
        <motion.svg
          width="160"
          height="160"
          viewBox="0 0 160 160"
          initial={{ opacity: 0, scale: 0.92 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.4, ease: "easeOut" }}
        >
          <g transform="rotate(-90 80 80)">
            {data.map((d) => {
              const frac = d.value / total;
              const dash = Math.max(frac - gap, 0.001);
              const circle = (
                <circle
                  key={d.label}
                  cx={80}
                  cy={80}
                  r={r}
                  fill="none"
                  strokeWidth={sw}
                  pathLength="1"
                  strokeDasharray={`${dash} ${1 - dash}`}
                  strokeDashoffset={-acc}
                  strokeLinecap="butt"
                  className={d.strokeClass}
                />
              );
              acc += frac;
              return circle;
            })}
          </g>
        </motion.svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <div className="text-xl font-bold text-gray-800 dark:text-gray-100 tabular-nums">
            {centerValue}
          </div>
          <div className="text-[10px] uppercase tracking-wide text-gray-400 dark:text-gray-500">
            {centerLabel}
          </div>
        </div>
      </div>

      <ul className="space-y-2 text-sm">
        {data.map((d) => {
          const pct = ((d.value / total) * 100).toFixed(1);
          return (
            <li key={d.label} className="flex items-center gap-2">
              <span className={`w-3 h-3 rounded-sm ${d.dotClass}`} />
              <span className="w-24 text-gray-700 dark:text-gray-300">{d.label}</span>
              <span className="tabular-nums text-gray-500 dark:text-gray-400">
                {d.value.toLocaleString()} ({pct}%)
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

// ----- histogram (a distribution) -----
// counts: bar heights. edges: log10(EUR) bin edges, length counts.length + 1.
// X ticks sit at integer powers of ten within the range.

export function Histogram({ counts, edges }) {
  if (!counts || !edges || counts.length === 0) return <Empty />;
  const maxC = Math.max(...counts, 1);
  const min = edges[0];
  const max = edges[edges.length - 1];

  const ticks = [];
  for (let k = Math.ceil(min); k <= Math.floor(max); k++) {
    ticks.push({ k, left: ((k - min) / (max - min)) * 100 });
  }

  return (
    <div>
      <div className="flex items-end gap-[2px] h-40">
        {counts.map((c, i) => (
          <motion.div
            key={i}
            initial={{ height: 0 }}
            animate={{ height: `${(c / maxC) * 100}%` }}
            transition={{ duration: 0.5, delay: i * 0.02, ease: "easeOut" }}
            className="flex-1 rounded-t bg-violet-500/80 hover:bg-violet-500"
            title={`${c.toLocaleString()} projects`}
          />
        ))}
      </div>
      <div className="relative h-5 mt-1 text-[10px] text-gray-400 dark:text-gray-500">
        {ticks.map((t) => (
          <span
            key={t.k}
            className="absolute -translate-x-1/2 tabular-nums"
            style={{ left: `${t.left}%` }}
          >
            {eurPow(t.k)}
          </span>
        ))}
      </div>
    </div>
  );
}

function eurPow(k) {
  const v = Math.pow(10, k);
  if (v >= 1e6) return `€${v / 1e6}M`;
  if (v >= 1e3) return `€${v / 1e3}K`;
  return `€${v}`;
}
