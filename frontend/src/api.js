/**
 * API + live-channel client.
 *
 * Auth: the shared tournament password is kept in localStorage and sent on
 * every request as `Authorization: Token <password>`.
 */

const TOKEN_KEY = "sambotl.token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || "";
}

export function setToken(value) {
  if (value) {
    localStorage.setItem(TOKEN_KEY, value);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

export function isAuthed() {
  return Boolean(getToken());
}

export function logout() {
  setToken("");
}

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request(path, { method = "GET", body, params } = {}) {
  const url = new URL(path, window.location.origin);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, value);
      }
    }
  }

  const headers = { Accept: "application/json" };
  const token = getToken();
  if (token) headers.Authorization = `Token ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  let response;
  try {
    response = await fetch(url.toString(), {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (error) {
    throw new ApiError("Сервер недоступен. Проверьте сеть и адрес сервера.", 0);
  }

  if (response.status === 401 || response.status === 403) {
    throw new ApiError("Неверный пароль доступа или доступ запрещён.", response.status);
  }
  if (!response.ok) {
    let detail = `Ошибка запроса (${response.status})`;
    try {
      const data = await response.json();
      detail = data.error || data.detail || detail;
    } catch (ignored) {
      /* keep the default message */
    }
    throw new ApiError(detail, response.status);
  }
  if (response.status === 204) return null;
  return response.json();
}

function asList(data) {
  if (Array.isArray(data)) return data;
  if (data && Array.isArray(data.results)) return data.results;
  return [];
}

export const api = {
  health: () => request("/api/health/"),

  participants: (search) =>
    request("/api/participants/", { params: { search } }).then(asList),
  weighIns: () => request("/api/weigh-ins/").then(asList),
  weighIn: (payload) => request("/api/weigh-ins/", { method: "POST", body: payload }),
  weighingProgress: () => request("/api/weigh-ins/progress/"),

  brackets: () => request("/api/brackets/").then(asList),
  bracketSetup: () => request("/api/brackets/setup/", { method: "POST" }),
  bracketPreview: (id, strategy) =>
    request(`/api/brackets/${id}/preview/`, { method: "POST", body: { strategy } }),
  bracketGenerate: (id, strategy) =>
    request(`/api/brackets/${id}/generate/`, { method: "POST", body: { strategy } }),
  bracketApprove: (id) =>
    request(`/api/brackets/${id}/approve/`, { method: "POST" }),

  matsSchedule: () => request("/api/mats/schedule/", { method: "POST" }),
  mats: () => request("/api/mats/").then(asList),
  boutsProgram: () => request("/api/bouts/", { params: { program: 1 } }).then(asList),
  bouts: (params) => request("/api/bouts/", { params }).then(asList),

  boutStart: (id) => request(`/api/bouts/${id}/start/`, { method: "POST" }),
  boutScore: (id, side, value) =>
    request(`/api/bouts/${id}/score/`, { method: "POST", body: { side, value } }),
  boutWarning: (id, side) =>
    request(`/api/bouts/${id}/warning/`, { method: "POST", body: { side } }),
  boutFinish: (id, winnerSide, resultText) =>
    request(`/api/bouts/${id}/finish/`, {
      method: "POST",
      body: { winner_side: winnerSide, result_text: resultText },
    }),
};

/**
 * Download a report file (attaches the auth token, triggers a browser download).
 */
export function downloadReport(path, fallbackName) {
  const token = getToken();
  return fetch(path, {
    headers: token ? { Authorization: `Token ${token}` } : {},
  })
    .then((response) => {
      if (!response.ok) throw new ApiError(`Ошибка скачивания (${response.status})`, response.status);
      return response.blob();
    })
    .then((blob) => {
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = fallbackName;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    });
}

/**
 * Open the live WebSocket channel. Reconnects automatically — important on an
 * unstable tournament LAN.
 */
export function connectLive(onEvent) {
  let socket = null;
  let closed = false;
  let retry = 800;

  const open = () => {
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    socket = new WebSocket(`${proto}://${window.location.host}/ws/live/`);
    socket.onopen = () => {
      retry = 800;
    };
    socket.onmessage = (event) => {
      try {
        onEvent(JSON.parse(event.data));
      } catch (ignored) {
        /* ignore malformed frames */
      }
    };
    socket.onclose = () => {
      if (!closed) {
        setTimeout(open, retry);
        retry = Math.min(retry * 1.6, 8000);
      }
    };
  };

  open();
  return {
    close() {
      closed = true;
      if (socket) socket.close();
    },
  };
}
