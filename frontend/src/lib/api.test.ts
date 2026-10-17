import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, apiUrl, request } from "./api";

/** Minimal fetch Response stand-in so the tests do not depend on undici. */
function mockResponse(
  body: string,
  { status = 200 }: { status?: number } = {},
): {
  ok: boolean;
  status: number;
  text: () => Promise<string>;
} {
  return {
    ok: status >= 200 && status < 300,
    status,
    text: () => Promise.resolve(body),
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
  document.cookie = "ba_csrf=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
});

describe("request", () => {
  it("parses a JSON response and sends session cookies", async () => {
    const fetchMock = vi.fn().mockResolvedValue(mockResponse(JSON.stringify({ ok: true })));
    vi.stubGlobal("fetch", fetchMock);

    const result = await request<{ ok: boolean }>("/api/v1/ping");

    expect(result).toEqual({ ok: true });
    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe(apiUrl("/api/v1/ping"));
    expect(init.credentials).toBe("include");
    expect((init.headers as Record<string, string>).Accept).toBe("application/json");
    // GET requests never carry a CSRF token.
    expect((init.headers as Record<string, string>)["X-CSRF-Token"]).toBeUndefined();
  });

  it("adds the CSRF header from the cookie on mutations and JSON-encodes the body", async () => {
    document.cookie = "ba_csrf=token-123; path=/";
    const fetchMock = vi.fn().mockResolvedValue(mockResponse(JSON.stringify({ id: "1" })));
    vi.stubGlobal("fetch", fetchMock);

    await request("/api/v1/things", { method: "POST", body: { name: "demo" } });

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const headers = init.headers as Record<string, string>;
    expect(headers["X-CSRF-Token"]).toBe("token-123");
    expect(headers["Content-Type"]).toBe("application/json");
    expect(init.body).toBe(JSON.stringify({ name: "demo" }));
  });

  it("normalizes the backend error envelope into ApiError", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      mockResponse(
        JSON.stringify({
          error: {
            code: "challenge_not_found",
            message: "No such challenge.",
            details: [{ field: "slug" }],
          },
        }),
        { status: 404 },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const failure = await request("/api/v1/challenges/nope").catch((error: unknown) => error);

    expect(failure).toBeInstanceOf(ApiError);
    const error = failure as ApiError;
    expect(error.status).toBe(404);
    expect(error.code).toBe("challenge_not_found");
    expect(error.message).toBe("No such challenge.");
    expect(error.isNotFound).toBe(true);
    expect(error.fieldErrors).toEqual({ slug: "No such challenge." });
  });

  it("falls back to a generic message for non-JSON failures", async () => {
    const fetchMock = vi.fn().mockResolvedValue(mockResponse("<html>oops</html>", { status: 500 }));
    vi.stubGlobal("fetch", fetchMock);

    const error = (await request("/api/v1/boom").catch((cause: unknown) => cause)) as ApiError;

    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(500);
    expect(error.code).toBe("http_500");
    expect(error.message).toMatch(/status 500/);
  });

  it("reports network failures as ApiError with status 0", async () => {
    const fetchMock = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));
    vi.stubGlobal("fetch", fetchMock);

    const error = (await request("/api/v1/ping").catch((cause: unknown) => cause)) as ApiError;

    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(0);
    expect(error.code).toBe("network_error");
  });

  it("treats an empty 204 body as null", async () => {
    const fetchMock = vi.fn().mockResolvedValue(mockResponse("", { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(request("/api/v1/things/1", { method: "DELETE" })).resolves.toBeNull();
  });
});
