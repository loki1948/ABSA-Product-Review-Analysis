import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import App from "./App";
import { getHealth } from "./services/api";

vi.mock("./services/api", async (original) => ({
  ...(await original<typeof import("./services/api")>()),
  getHealth: vi.fn(),
}));

beforeEach(() => {
  vi.mocked(getHealth).mockResolvedValue({ status: "ok", models_loaded: true, database: true, detail: null });
});

function renderApp(path = "/") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

describe("App shell", () => {
  it("links to every page", () => {
    renderApp();
    const nav = screen.getByRole("navigation", { name: /main/i });
    expect(within(nav).getAllByRole("link").map((link) => link.textContent)).toEqual([
      "Home",
      "Analyzer",
      "Batch",
      "History",
      "Dashboard",
    ]);
  });

  it("shows whether the backend is connected", async () => {
    renderApp();
    expect(await screen.findByText("Backend connected")).toBeInTheDocument();
  });

  it("opens the batch page from the navigation", async () => {
    renderApp();
    await userEvent.click(screen.getByRole("link", { name: "Batch" }));
    expect(screen.getByRole("heading", { name: /batch analysis/i })).toBeInTheDocument();
  });

  it("explains an unknown address instead of showing a blank page", () => {
    renderApp("/nowhere");
    expect(screen.getByRole("heading", { name: /page not found/i })).toBeInTheDocument();
  });
});

describe("Home page", () => {
  it("explains the idea with a worked example that needs no backend", () => {
    renderApp();
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(/aspect-based sentiment analysis/i);
    expect(screen.getByText("battery life", { selector: "mark" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /traditional/i })).toBeInTheDocument();
  });

  it("leads to the analyzer", async () => {
    renderApp();
    await userEvent.click(screen.getByRole("link", { name: /analyze a review/i }));
    expect(screen.getByRole("heading", { name: /review analyzer/i })).toBeInTheDocument();
  });
});

describe("connection indicator", () => {
  it("says the backend is unreachable when a proxy answers for it", async () => {
    const { ApiError } = await import("./services/api");
    vi.mocked(getHealth).mockRejectedValue(new ApiError("Request failed (HTTP 502).", 502));
    renderApp();
    expect(await screen.findByText("Cannot reach the backend")).toBeInTheDocument();
  });
});
