// GrantPilot header: a slimmed-down replacement for Mosaic's demo header.
// Keeps the mobile hamburger (toggles the sidebar) and the theme toggle, drops
// the demo search / notifications / help / profile menu (Acme Inc.), and adds a
// live backend status dot and a Source link.

import React, { useEffect, useState } from "react";
import ThemeToggle from "../components/ThemeToggle";
import { api } from "../grantpilot/api";

export default function Header({ sidebarOpen, setSidebarOpen }) {
  return (
    <header className="sticky top-0 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700/60 z-30">
      <div className="px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 -mb-px">
          {/* Left: hamburger (mobile only) */}
          <div className="flex">
            <button
              className="text-gray-500 hover:text-gray-600 dark:hover:text-gray-400 lg:hidden"
              aria-controls="sidebar"
              aria-expanded={sidebarOpen}
              onClick={(e) => {
                e.stopPropagation();
                setSidebarOpen(!sidebarOpen);
              }}
            >
              <span className="sr-only">Open sidebar</span>
              <svg className="w-6 h-6 fill-current" viewBox="0 0 24 24">
                <rect x="4" y="5" width="16" height="2" />
                <rect x="4" y="11" width="16" height="2" />
                <rect x="4" y="17" width="16" height="2" />
              </svg>
            </button>
          </div>

          {/* Right: backend status, theme toggle */}
          <div className="flex items-center gap-3">
            <BackendStatus />
            <div className="w-px h-6 bg-gray-200 dark:bg-gray-700/60" aria-hidden="true" />
            <ThemeToggle />
          </div>
        </div>
      </div>
    </header>
  );
}

// Pings /health once on mount and shows a colored status dot. The Promise.resolve
// wrapper means a synchronous throw (e.g. api.health missing) still lands in
// .catch and shows "offline" rather than crashing the header.
function BackendStatus() {
  const [state, setState] = useState("checking"); // checking | online | offline

  useEffect(() => {
    let alive = true;
    Promise.resolve()
      .then(() => api.health())
      .then(() => alive && setState("online"))
      .catch(() => alive && setState("offline"));
    return () => {
      alive = false;
    };
  }, []);

  const dot =
    state === "online" ? "bg-green-500"
    : state === "offline" ? "bg-red-500"
    : "bg-gray-400 animate-pulse";
  const label =
    state === "online" ? "API online"
    : state === "offline" ? "API offline"
    : "checking...";

  return (
    <span className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
      <span className={`w-2 h-2 rounded-full ${dot}`} />
      <span className="hidden sm:inline">{label}</span>
    </span>
  );
}
