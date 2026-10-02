// The proposal input form. Holds its own field state and hands a clean payload
// up to the page via onQuickCheck (fast endpoints) and onAssess (full pipeline).

import React, { useState } from "react";
import { Card } from "./components";

const SCHEMES = ["RIA", "IA", "CSA", "ERC-STG", "ERC-COG", "ERC-ADG", "MSCA-IF"];

export default function ProposalForm({ onQuickCheck, onAssess, loadingQuick, loadingAssess }) {
  const [f, setF] = useState({
    id: "DEMO-1",
    idea:
      "A platform using machine learning on low-cost drone imagery to detect " +
      "early-stage crop disease in smallholder farms, with an offline mobile app.",
    scheme: "RIA",
    ec_contribution: 5000000,
    total_cost: 6200000,
    consortium_size: 9,
    num_countries: 6,
  });

  const upd = (k, v) => setF((s) => ({ ...s, [k]: v }));
  const num = (v) => (v === "" || v === null ? null : Number(v));
  const payload = () => ({
    ...f,
    ec_contribution: num(f.ec_contribution),
    total_cost: num(f.total_cost),
    consortium_size: num(f.consortium_size),
    num_countries: num(f.num_countries),
  });

  const input =
    "w-full rounded-lg bg-white dark:bg-gray-800 border border-gray-200 " +
    "dark:border-gray-700/60 text-sm px-3 py-2 text-gray-800 dark:text-gray-100 " +
    "focus:ring-violet-500 focus:border-violet-500";
  const label = "block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1";

  return (
    <Card title="Proposal" span="xl:col-span-4" className="col-span-full">
      <div className="space-y-4">
        <div>
          <label className={label}>Research idea</label>
          <textarea
            className={input}
            rows={4}
            value={f.idea}
            onChange={(e) => upd("idea", e.target.value)}
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className={label}>Funding scheme</label>
            <select
              className={input}
              value={f.scheme}
              onChange={(e) => upd("scheme", e.target.value)}
            >
              {SCHEMES.map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </div>
          <div>
            <label className={label}>EC contribution (EUR)</label>
            <input
              className={input}
              type="number"
              value={f.ec_contribution}
              onChange={(e) => upd("ec_contribution", e.target.value)}
            />
          </div>
          <div>
            <label className={label}>Total cost (EUR)</label>
            <input
              className={input}
              type="number"
              value={f.total_cost}
              onChange={(e) => upd("total_cost", e.target.value)}
            />
          </div>
          <div>
            <label className={label}>Consortium size</label>
            <input
              className={input}
              type="number"
              value={f.consortium_size}
              onChange={(e) => upd("consortium_size", e.target.value)}
            />
          </div>
          <div>
            <label className={label}>Countries</label>
            <input
              className={input}
              type="number"
              value={f.num_countries}
              onChange={(e) => upd("num_countries", e.target.value)}
            />
          </div>
        </div>

        <div className="flex flex-wrap gap-2 pt-1">
          <button
            onClick={() => onQuickCheck(payload())}
            disabled={loadingQuick}
            className="btn border-gray-200 dark:border-gray-700/60 text-gray-600 dark:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600 disabled:opacity-50"
          >
            {loadingQuick ? "Checking..." : "Quick check"}
          </button>
          <button
            onClick={() => onAssess(payload())}
            disabled={loadingAssess}
            className="btn bg-violet-500 hover:bg-violet-600 text-white disabled:opacity-50"
          >
            {loadingAssess ? "Assessing..." : "Run full assessment"}
          </button>
        </div>
        <p className="text-xs text-gray-400 dark:text-gray-500">
          Quick check runs eligibility and budget instantly. Full assessment also
          drafts and reviews the proposal (uses the local LLM, takes a moment).
        </p>
      </div>
    </Card>
  );
}
