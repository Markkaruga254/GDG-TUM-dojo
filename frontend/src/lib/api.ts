/**
 * Minimal typed API client for the Build Arena backend.
 *
 * - Sends cookies (`credentials: "include"`) for the session.
 * - Mirrors the backend's double-submit CSRF scheme: mutating requests carry
 *   the `ba_csrf` cookie value in the `X-CSRF-Token` header.
 * - Normalizes every failure into an `ApiError` with the server's error code.
 */

export interface ApiErrorDetail {
  code: string;
  message: string;
  details?: unknown[] | null;
}

interface ApiErrorEnvelope {
  error?: ApiErrorDetail;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: unknown[] | null;

  constructor(status: number, code: string, message: string, details: unknown[] | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }

  get isUnauthorized(): boolean {
    return this.status === 401;
  }

  get isForbidden(): boolean {
    return this.status === 403;
  }

  get isNotFound(): boolean {
    return this.status === 404;
  }

  /** Details shaped as `[{ field, ... }]`, e.g. validation errors. */
  get fieldErrors(): Record<string, string> {
    const result: Record<string, string> = {};
    for (const detail of this.details ?? []) {
      if (detail && typeof detail === "object" && "field" in detail) {
        const field = (detail as { field?: unknown }).field;
        if (typeof field === "string") result[field] = this.message;
      }
    }
    return result;
  }
}

export const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/+$/, "");

/** Build an absolute URL for the API, honoring the optional base URL. */
export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

function readCookie(name: string): string | null {
  const prefix = `${name}=`;
  for (const part of document.cookie.split(";")) {
    const cookie = part.trim();
    if (cookie.startsWith(prefix)) {
      return decodeURIComponent(cookie.slice(prefix.length));
    }
  }
  return null;
}

const CSRF_COOKIE = "ba_csrf";
const CSRF_HEADER = "X-CSRF-Token";

export interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  signal?: AbortSignal;
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const method = options.method ?? "GET";
  const headers: Record<string, string> = { Accept: "application/json" };

  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  if (method !== "GET") {
    const csrf = readCookie(CSRF_COOKIE);
    if (csrf) headers[CSRF_HEADER] = csrf;
  }

  let response: Response;
  try {
    response = await fetch(apiUrl(path), {
      method,
      headers,
      credentials: "include",
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
      signal: options.signal,
    });
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === "AbortError") throw cause;
    throw new ApiError(
      0,
      "network_error",
      "Unable to reach the Build Arena API. Check that the backend is running.",
    );
  }

  const text = await response.text();
  let payload: unknown = null;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = null;
    }
  }

  if (!response.ok) {
    const envelope = payload as ApiErrorEnvelope | null;
    const detail = envelope?.error;
    throw new ApiError(
      response.status,
      detail?.code ?? `http_${response.status}`,
      detail?.message ?? `Request failed with status ${response.status}.`,
      detail?.details ?? null,
    );
  }

  return payload as T;
}
