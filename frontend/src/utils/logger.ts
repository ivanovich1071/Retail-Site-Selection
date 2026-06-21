/**
 * Frontend logger: console output + best-effort remote flush to the backend
 * (/api/v1/logs/client) so frontend + backend events share one log file.
 *
 * warn/error are buffered and flushed; debug/info are console-only by default.
 * Uses raw fetch (not axios) to avoid recursive logging through interceptors.
 */
type Level = "debug" | "info" | "warn" | "error";

interface LogEntry {
  level: Level;
  message: string;
  context?: Record<string, any>;
  url?: string;
  ts: string;
}

const REMOTE_ENDPOINT = "/api/v1/logs/client";
const FLUSH_INTERVAL_MS = 4000;
const MAX_BUFFER = 50;
// Only these levels get shipped to the backend.
const REMOTE_LEVELS: Level[] = ["warn", "error"];

const buffer: LogEntry[] = [];
let flushing = false;

const STYLES: Record<Level, string> = {
  debug: "color:#888",
  info: "color:#1a5276",
  warn: "color:#d48806;font-weight:bold",
  error: "color:#cf1322;font-weight:bold",
};

function consoleOut(e: LogEntry) {
  const prefix = `%c[${e.ts.slice(11, 19)}] ${e.level.toUpperCase()}`;
  const fn = e.level === "error" ? console.error : e.level === "warn" ? console.warn : console.log;
  if (e.context) fn(prefix, STYLES[e.level], e.message, e.context);
  else fn(prefix, STYLES[e.level], e.message);
}

async function flush() {
  if (flushing || buffer.length === 0) return;
  flushing = true;
  const batch = buffer.splice(0, buffer.length);
  try {
    await fetch(REMOTE_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ logs: batch }),
      keepalive: true,
    });
  } catch {
    // Network/backend down — drop silently (don't recurse).
  } finally {
    flushing = false;
  }
}

function record(level: Level, message: string, context?: Record<string, any>) {
  const entry: LogEntry = {
    level,
    message,
    context,
    url: window.location.pathname,
    ts: new Date().toISOString(),
  };
  consoleOut(entry);
  if (REMOTE_LEVELS.includes(level)) {
    buffer.push(entry);
    if (buffer.length >= MAX_BUFFER) void flush();
  }
}

export const logger = {
  debug: (m: string, c?: Record<string, any>) => record("debug", m, c),
  info: (m: string, c?: Record<string, any>) => record("info", m, c),
  warn: (m: string, c?: Record<string, any>) => record("warn", m, c),
  error: (m: string, c?: Record<string, any>) => record("error", m, c),
  flush,
};

// Periodic flush + flush on page hide.
if (typeof window !== "undefined") {
  setInterval(() => void flush(), FLUSH_INTERVAL_MS);
  window.addEventListener("beforeunload", () => void flush());
}
