import React from "react";

type EventItem = { type: string; time?: number; payload?: any };

export function ToolEvents({ events }: { events: EventItem[] }) {
  return (
    <div className="card">
      <div className="card-header">Tool Events</div>
      <div className="card-body" style={{ padding: 8 }}>
      {events.length === 0 ? (
        <div className="muted">No events yet.</div>
      ) : (
        <ul style={{ listStyle: "none", padding: 0, margin: 0, maxHeight: 240, overflow: "auto" }}>
          {events.map((ev, idx) => (
            <li key={idx} style={{ borderBottom: "1px solid hsl(var(--border))", padding: "6px 0" }}>
              <div className="muted" style={{ fontSize: 12 }}>{new Date(ev.time || Date.now()).toLocaleTimeString()}</div>
              <div style={{ fontWeight: 600 }}>{ev.type}</div>
              {ev.payload ? (
                <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{safeString(ev.payload)}</pre>
              ) : null}
            </li>
          ))}
        </ul>
      )}
      </div>
    </div>
  );
}

function safeString(obj: any) {
  try {
    return typeof obj === "string" ? obj : JSON.stringify(obj, null, 2);
  } catch {
    return String(obj);
  }
}