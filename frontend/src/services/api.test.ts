import { analyzeReview, ApiError, deleteReview, getReviews } from "./api";

function respond(status: number, body?: unknown): Response {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const fetchMock = vi.fn<typeof fetch>();

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => vi.unstubAllGlobals());

describe("api client", () => {
  it("posts the review as JSON to /api/analyze", async () => {
    fetchMock.mockResolvedValue(respond(200, { id: 1 }));
    await analyzeReview("Great screen", false);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/analyze");
    expect(init?.method).toBe("POST");
    expect(JSON.parse(init?.body as string)).toEqual({ review: "Great screen", save: false });
  });

  it("builds the query string and leaves out undefined options", async () => {
    fetchMock.mockResolvedValue(respond(200, { total: 0, limit: 10, offset: 20, items: [] }));
    await getReviews({ limit: 10, offset: 20, sentiment: undefined });
    expect(fetchMock.mock.calls[0][0]).toBe("/api/reviews?limit=10&offset=20");
  });

  it("resolves a 204 without a body", async () => {
    fetchMock.mockResolvedValue(respond(204));
    await expect(deleteReview(3)).resolves.toBeUndefined();
  });

  it("uses the backend's detail string as the error message", async () => {
    fetchMock.mockResolvedValue(respond(404, { detail: "Review not found." }));
    await expect(deleteReview(3)).rejects.toMatchObject({ message: "Review not found.", status: 404 });
  });

  it("joins the messages of a validation error", async () => {
    fetchMock.mockResolvedValue(
      respond(422, { detail: [{ msg: "review must not be blank" }, { msg: "too long" }] }),
    );
    await expect(analyzeReview(" ")).rejects.toMatchObject({
      message: "review must not be blank; too long",
      status: 422,
    });
  });

  it("reports an unreachable backend as status 0", async () => {
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));
    const error = await analyzeReview("x").catch((reason: unknown) => reason);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(0);
  });

  it("survives an error response that is not JSON", async () => {
    fetchMock.mockResolvedValue(new Response("<html>Bad gateway</html>", { status: 502 }));
    await expect(analyzeReview("x")).rejects.toMatchObject({ status: 502 });
  });
});
