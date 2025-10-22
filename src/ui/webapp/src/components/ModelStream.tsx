import React from "react";

export function ModelStream({ text }: { text: string }) {
  return (
    <div className="card" style={{
      padding: 8,
      fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
      whiteSpace: "pre-wrap",
      maxHeight: 240,
      overflow: "auto",
    }}>
      {text || ""}
    </div>
  );
}