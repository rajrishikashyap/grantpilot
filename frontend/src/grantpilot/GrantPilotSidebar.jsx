// A clean, GrantPilot-branded sidebar that replaces Mosaic's demo nav.
// Matches Mosaic's dark panel styling and responsive behaviour (slides in on
// mobile, static on large screens) but carries only GrantPilot-relevant links.

import React from "react";
import { NavLink } from "react-router-dom";

export default function GrantPilotSidebar({ sidebarOpen, setSidebarOpen }) {
  return (
    <>
      {/* Mobile backdrop */}
      <div
        className={`fixed inset-0 bg-gray-900/30 z-40 lg:hidden transition-opacity duration-200 ${
          sidebarOpen ? "opacity-100" : "opacity-0 pointer-events-none"
        }`}
        onClick={() => setSidebarOpen(false)}
        aria-hidden="true"
      />

      <aside
        className={`flex flex-col absolute z-40 left-0 top-0 lg:static h-screen overflow-y-auto no-scrollbar w-64 shrink-0 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700/60 p-4 transition-transform duration-200 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-64"
        } lg:translate-x-0`}
      >
        {/* Brand */}
        <div className="flex items-center gap-2 mb-8 px-2 pt-1">
          <div className="w-8 h-8 rounded-lg bg-violet-500 flex items-center justify-center text-white font-bold">
            G
          </div>
          <span className="text-lg font-semibold text-gray-800 dark:text-gray-100">
            GrantPilot
          </span>
        </div>

        <nav className="space-y-1">
          <div className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wide px-3 mb-2">
            Workspace
          </div>

          <Item to="/" end label="Assess" icon={icons.assess} />
          <Item to="/analytics" label="Mosaic demo" icon={icons.chart} />

          <a
            href="https://github.com/rajrishikashyap/grantpilot"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700/50"
          >
            {icons.git}
            <span>Source</span>
          </a>
        </nav>

        <div className="mt-auto pt-6 px-3 text-xs text-gray-400 dark:text-gray-500 leading-relaxed">
          35,104 EU-funded projects
          <br />
          local Qwen 2.5 · scikit-learn · ChromaDB
        </div>
      </aside>
    </>
  );
}

function Item({ to, label, icon, end }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
          isActive
            ? "bg-violet-500/10 text-violet-600 dark:text-violet-400 font-medium"
            : "text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700/50"
        }`
      }
    >
      {icon}
      <span>{label}</span>
    </NavLink>
  );
}

// Minimal inline icons (stroke, currentColor), so there are no asset deps.
const icons = {
  assess: (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M9 11l3 3L22 4" />
      <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
    </svg>
  ),
  chart: (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M3 3v18h18" />
      <rect x="7" y="11" width="3" height="6" />
      <rect x="12" y="7" width="3" height="10" />
      <rect x="17" y="13" width="3" height="4" />
    </svg>
  ),
  git: (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 .5a12 12 0 0 0-3.8 23.4c.6.1.8-.3.8-.6v-2c-3.3.7-4-1.6-4-1.6-.6-1.4-1.3-1.8-1.3-1.8-1-.7.1-.7.1-.7 1.2.1 1.8 1.2 1.8 1.2 1 .1.7 1.8 2.6 1.3.1-.8.4-1.3.7-1.6-2.7-.3-5.5-1.3-5.5-5.9 0-1.3.5-2.4 1.2-3.2-.1-.3-.5-1.5.1-3.1 0 0 1-.3 3.3 1.2a11.5 11.5 0 0 1 6 0C17 5.3 18 5.6 18 5.6c.6 1.6.2 2.8.1 3.1.8.8 1.2 1.9 1.2 3.2 0 4.6-2.8 5.6-5.5 5.9.4.4.8 1.1.8 2.2v3.3c0 .3.2.7.8.6A12 12 0 0 0 12 .5Z" />
    </svg>
  ),
};