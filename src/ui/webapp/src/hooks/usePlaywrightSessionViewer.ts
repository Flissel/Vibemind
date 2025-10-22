import { useEffect, useMemo, useRef, useState } from "react";

export type ViewerState = {
  connected: boolean;
  modelText: string;
  toolEvents: Array<{ type: string; time?: number; payload?: any }>;
  previewUrl?: string;
  lastUpdateTs: number;
};

// Persistent per-session store, survives component unmounts and tab switches
export const sessionStore: Map<string, ViewerState> = new Map();

export function ensureSessionState(sessionId: string): ViewerState {
  const existing = sessionStore.get(sessionId);
  if (existing) return existing;
  const created: ViewerState = {
    connected: false,
    modelText: "",
    toolEvents: [],
    previewUrl: undefined,
    lastUpdateTs: Date.now(),
  };
  sessionStore.set(sessionId, created);
  return created;
}

export function usePlaywrightSessionViewer(sessionId?: string) {
  const sid = sessionId ?? "";
  const [state, setState] = useState<ViewerState>(() => ensureSessionState(sid));
  const sseRef = useRef<EventSource | null>(null);
  const reconnectTimer = useRef<number | null>(null);
  const pollTimer = useRef<number | null>(null);
  const lastSeqRef = useRef<number>(0);

  const baseUrl = useMemo(() => {
    if (!sid) return null;
    return `/mcp/playwright/session/${encodeURIComponent(sid)}`;
  }, [sid]);

  useEffect(() => {
    if (!sid || !baseUrl) return;

    // Apply current persisted state immediately
    setState(ensureSessionState(sid));

    // Clean up previous SSE/poll
    if (sseRef.current) {
      sseRef.current.close();
      sseRef.current = null;
    }
    if (pollTimer.current) {
      window.clearInterval(pollTimer.current);
      pollTimer.current = null;
    }

    // Connect to SSE stream for live updates
    const es = new EventSource(`${baseUrl}/events`);
    sseRef.current = es;

    es.onopen = () => {
      const current = ensureSessionState(sid);
      current.connected = true;
      current.lastUpdateTs = Date.now();
      sessionStore.set(sid, current);
      setState({ ...current });
    };

    es.onerror = () => {
      const current = ensureSessionState(sid);
      current.connected = false;
      sessionStore.set(sid, current);
      setState({ ...current });
      // Attempt reconnect after a short delay
      if (reconnectTimer.current) window.clearTimeout(reconnectTimer.current);
      reconnectTimer.current = window.setTimeout(() => {
        // Trigger effect re-run by cloning state (noop)
        setState((prev) => ({ ...prev }));
      }, 1500);
      // Start polling fallback for JSON events if upstream provides it
      if (!pollTimer.current) {
        pollTimer.current = window.setInterval(async () => {
          try {
            const url = `${baseUrl}/events.json?since=${lastSeqRef.current || 0}`;
            const res = await fetch(url, { headers: { Accept: "application/json" } });
            if (!res.ok) return;
            const data = await res.json();
            if (Array.isArray(data?.events)) {
              for (const ev of data.events) {
                lastSeqRef.current = Math.max(lastSeqRef.current, Number(ev.seq || 0));
                applyGenericEvent(sid, ev);
              }
            }
          } catch {
            /* ignore */
          }
        }, 1500);
      }
    };

    // Generic message fallback
    es.addEventListener("message", (ev: MessageEvent) => {
      const payload = safeJson(ev.data);
      applyGenericEvent(sid, payload);
    });

    es.addEventListener("model_stream", (ev: MessageEvent) => {
      const current = ensureSessionState(sid);
      const payload = safeJson(ev.data);
      if (payload?.chunk) {
        current.modelText += String(payload.chunk);
        current.lastUpdateTs = Date.now();
        sessionStore.set(sid, current);
        setState({ ...current });
      }
    });

    es.addEventListener("tool_event", (ev: MessageEvent) => {
      const current = ensureSessionState(sid);
      const payload = safeJson(ev.data);
      current.toolEvents.push({ type: payload?.type ?? "tool_event", time: Date.now(), payload });
      current.lastUpdateTs = Date.now();
      sessionStore.set(sid, current);
      setState({ ...current });
    });

    es.addEventListener("preview", (ev: MessageEvent) => {
      const current = ensureSessionState(sid);
      const payload = safeJson(ev.data);
      if (payload?.url) current.previewUrl = String(payload.url);
      current.lastUpdateTs = Date.now();
      sessionStore.set(sid, current);
      setState({ ...current });
    });

    es.addEventListener("browser", (ev: MessageEvent) => {
      const current = ensureSessionState(sid);
      const payload = safeJson(ev.data);
      if (payload?.data_uri) current.previewUrl = String(payload.data_uri);
      current.lastUpdateTs = Date.now();
      sessionStore.set(sid, current);
      setState({ ...current });
    });

    return () => {
      if (sseRef.current) {
        sseRef.current.close();
        sseRef.current = null;
      }
      if (reconnectTimer.current) {
        window.clearTimeout(reconnectTimer.current);
        reconnectTimer.current = null;
      }
      if (pollTimer.current) {
        window.clearInterval(pollTimer.current);
        pollTimer.current = null;
      }
    };
  }, [sid, baseUrl]);

  // Listen for external store updates (from multi-subscription manager)
  useEffect(() => {
    const onUpdate = (e: any) => {
      try {
        const detailSid = e?.detail?.sid;
        if (!detailSid || detailSid !== sid) return;
        setState({ ...ensureSessionState(sid) });
      } catch {}
    };
    window.addEventListener("viewer-state-changed", onUpdate as EventListener);
    return () => window.removeEventListener("viewer-state-changed", onUpdate as EventListener);
  }, [sid]);

  return state;
}

function safeJson(data: any) {
  try {
    return typeof data === "string" ? JSON.parse(data) : data;
  } catch {
    return undefined;
  }
}

function applyGenericEvent(sid: string, payload: any) {
  const current = ensureSessionState(sid);
  if (!payload) return;
  // Heuristics: map common keys
  if (payload.chunk || payload.text) {
    current.modelText += String(payload.chunk ?? payload.text ?? "");
  }
  if (payload.type || payload.event) {
    current.toolEvents.push({ type: String(payload.type ?? payload.event), time: Date.now(), payload });
  }
  if (payload.url || payload.previewUrl || payload.data_uri) {
    current.previewUrl = String(payload.url ?? payload.previewUrl ?? payload.data_uri);
  }
  current.lastUpdateTs = Date.now();
  sessionStore.set(sid, current);
}

export function getViewerState(sessionId: string): ViewerState {
  return ensureSessionState(sessionId);
}