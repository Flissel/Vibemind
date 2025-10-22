import { ensureSessionState, sessionStore } from "./usePlaywrightSessionViewer";

const sources = new Map<string, EventSource>();
const polls = new Map<string, number>();
const seqs = new Map<string, number>();

export function ensureSessionStream(sessionId: string) {
  if (!sessionId) return;
  if (sources.has(sessionId)) return; // already connected
  const baseUrl = `/mcp/playwright/session/${encodeURIComponent(sessionId)}`;
  const es = new EventSource(`${baseUrl}/events`);
  sources.set(sessionId, es);

  es.onopen = () => {
    const s = ensureSessionState(sessionId);
    s.connected = true;
    s.lastUpdateTs = Date.now();
    sessionStore.set(sessionId, s);
    window.dispatchEvent(new CustomEvent("viewer-state-changed", { detail: { sid: sessionId } }));
  };

  es.onerror = () => {
    const s = ensureSessionState(sessionId);
    s.connected = false;
    sessionStore.set(sessionId, s);
    window.dispatchEvent(new CustomEvent("viewer-state-changed", { detail: { sid: sessionId } }));
    // start polling fallback
    if (!polls.has(sessionId)) {
      const timer = window.setInterval(async () => {
        try {
          const since = seqs.get(sessionId) || 0;
          const res = await fetch(`${baseUrl}/events.json?since=${since}`, { headers: { Accept: "application/json" } });
          if (!res.ok) return;
          const data = await res.json();
          if (Array.isArray(data?.events)) {
            for (const ev of data.events) {
              const s2 = ensureSessionState(sessionId);
              if (ev.chunk || ev.text) s2.modelText += String(ev.chunk ?? ev.text);
              if (ev.type || ev.event) s2.toolEvents.push({ type: String(ev.type ?? ev.event), time: Date.now(), payload: ev });
              if (ev.url || ev.previewUrl || ev.data_uri) s2.previewUrl = String(ev.url ?? ev.previewUrl ?? ev.data_uri);
              s2.lastUpdateTs = Date.now();
              sessionStore.set(sessionId, s2);
              window.dispatchEvent(new CustomEvent("viewer-state-changed", { detail: { sid: sessionId } }));
              seqs.set(sessionId, Math.max(since, Number(ev.seq || 0)));
            }
          }
        } catch {}
      }, 3000);
      polls.set(sessionId, timer);
    }
  };

  es.addEventListener("message", (ev: MessageEvent) => {
    try {
      const data = typeof ev.data === "string" ? JSON.parse(ev.data) : ev.data;
      const s = ensureSessionState(sessionId);
      if (data?.chunk || data?.text) s.modelText += String(data.chunk ?? data.text);
      if (data?.type || data?.event) s.toolEvents.push({ type: String(data.type ?? data.event), time: Date.now(), payload: data });
      if (data?.url || data?.previewUrl || data?.data_uri) s.previewUrl = String(data.url ?? data.previewUrl ?? data.data_uri);
      s.lastUpdateTs = Date.now();
      sessionStore.set(sessionId, s);
      window.dispatchEvent(new CustomEvent("viewer-state-changed", { detail: { sid: sessionId } }));
    } catch {}
  });
}

export function stopSessionStream(sessionId: string) {
  const es = sources.get(sessionId);
  if (es) {
    es.close();
    sources.delete(sessionId);
  }
  const t = polls.get(sessionId);
  if (t) {
    window.clearInterval(t);
    polls.delete(sessionId);
  }
}

export function stopAllStreams() {
  for (const sid of Array.from(sources.keys())) stopSessionStream(sid);
}