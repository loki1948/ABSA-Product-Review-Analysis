import { NavLink, Route, Routes } from "react-router-dom";

import ConnectionStatus from "./components/ConnectionStatus";
import Analyzer from "./pages/Analyzer";
import Dashboard from "./pages/Dashboard";
import History from "./pages/History";
import Home from "./pages/Home";

const links = [
  { to: "/", label: "Home" },
  { to: "/analyze", label: "Analyzer" },
  { to: "/history", label: "History" },
  { to: "/dashboard", label: "Dashboard" },
];

export default function App() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <span className="font-semibold">ABSA</span>
          <nav className="flex gap-4 text-sm">
            {links.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.to === "/"}
                className={({ isActive }) =>
                  isActive ? "font-medium text-blue-700" : "text-slate-600 hover:text-slate-900"
                }
              >
                {link.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto">
            <ConnectionStatus />
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-8">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/analyze" element={<Analyzer />} />
          <Route path="/history" element={<History />} />
          <Route path="/dashboard" element={<Dashboard />} />
        </Routes>
      </main>
    </div>
  );
}
