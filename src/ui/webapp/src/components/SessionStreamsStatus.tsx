import React from "react";
import { getViewerState } from "../hooks/usePlaywrightSessionViewer";

type Props = {
  sessions: Array<{ id: string; name?: string; status?: string }>;
};

export default function SessionStreamsStatus({ sessions }: Props) {
  return (
    <div className="card" style={{ marginTop: 12 }}>
      <div className="card-header">MCP Sessions</div>
      <div className="card-body" style={{ display: "grid", gridTemplateColumns: "1fr 120px 120px 80px", gap: 8 }}>
        <div style={{ fontSize: 12, opacity: 0.7 }}>Session</div>
        <div style={{ fontSize: 12, opacity: 0.7 }}>Connected</div>
        <div style={{ fontSize: 12, opacity: 0.7 }}>Last Update</div>
        <div style={{ fontSize: 12, opacity: 0.7 }}>Events</div>
      </div>
      {sessions.map((s) => {
        const st = getViewerState(s.id);
        const last = new Date(st.lastUpdateTs);
        const lastStr = isNaN(last.getTime()) ? "—" : last.toLocaleTimeString();
        return (
          <div key={s.id} style={{ display: "grid", gridTemplateColumns: "1fr 120px 120px 80px", gap: 8, padding: "6px 0", borderBottom: "1px solid hsl(var(--border))" }}>
            <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{s.name || s.id}</div>
            <div>{st.connected ? "Yes" : "No"}</div>
            <div>{lastStr}</div>
            <div>{st.toolEvents.length}</div>
          </div>
        );
      })}
    </div>
  );
}