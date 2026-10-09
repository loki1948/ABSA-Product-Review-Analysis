import { Link, NavLink, Route, Routes } from "react-router-dom";

import ConnectionStatus from "./components/ConnectionStatus";
import Analyzer from "./pages/Analyzer";
import Batch from "./pages/Batch";
import Dashboard from "./pages/Dashboard";
import History from "./pages/History";
import Home from "./pages/Home";

const links = [
  { to: "/", label: "Home" },
  { to: "/analyze", label: "Analyzer" },
  { to: "/batch", label: "Batch" },
  { to: "/history", label: "History" },
  { to: "/dashboard", label: "Dashboard" },
];

function NotFound() {
  return (
    <section className="space-y-3">
      <h1 className="text-2xl font-semibold">Page not found</h1>
      <p className="text-sm text-slate-600">There is nothing at this address.</p>
      <Link to="/" className="text-sm text-blue-700 hover:underline">
        Back to the home page
      </Link>
    </section>
  );
}

export default function App() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <span className="font-semibold">ABSA</span>
          <nav aria-label="Main" className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
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
          <Route path="/batch" element={<Batch />} />
          <Route path="/history" element={<History />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
    </div>
  );
}
