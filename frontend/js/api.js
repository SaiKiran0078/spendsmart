// Tiny fetch wrapper: adds the auth header, turns errors into readable messages,
// and sends the user back to the sign-in page when the session expires.
const API = "/api";
const TOKEN_KEY = "spendsmart_token";

export function getToken() {
  try { return localStorage.getItem(TOKEN_KEY); } catch { return null; }
}

export function setToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch { /* storage unavailable */ }
}

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function readableError(body, fallback) {
  const detail = body && body.detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => String(item.msg || "").replace(/^Value error, /, "")).join(". ") || fallback;
  }
  return typeof detail === "string" ? detail : fallback;
}

/** Build a query string, skipping empty values. */
export function qs(params = {}) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") query.set(key, value);
  }
  const text = query.toString();
  return text ? `?${text}` : "";
}

export async function request(path, { method = "GET", body, form, formData, raw = false } = {}) {
  const headers = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let payload;
  if (formData) {
    payload = formData; // the browser sets the multipart boundary itself
  } else if (form) {
    payload = new URLSearchParams(form);
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  let response;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 30_000);
  try {
    response = await fetch(API + path, {
      method,
      headers,
      body: payload,
      signal: controller.signal,
    });
  } catch (error) {
    const message = error?.name === "AbortError"
      ? "The request timed out. Please try again."
      : "Can't reach the server. Check your connection and try again.";
    throw new ApiError(message, 0);
  } finally {
    clearTimeout(timeout);
  }

  if (response.status === 401 && token && !path.startsWith("/auth/login")) {
    setToken(null);
    location.replace("login.html");
    throw new ApiError("Your session has expired. Please log in again.", 401);
  }
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new ApiError(readableError(data, "Something went wrong. Please try again."), response.status);
  }
  if (raw) return response;
  return response.status === 204 ? null : response.json();
}

export const api = {
  get: (path, params) => request(path + qs(params)),
  post: (path, body) => request(path, { method: "POST", body }),
  put: (path, body) => request(path, { method: "PUT", body }),
  del: (path, body) => request(path, { method: "DELETE", body }),
};
