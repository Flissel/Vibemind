import React from "react";

export function BrowserPreview({ url }: { url?: string }) {
  const src = url || undefined;
  return (
    <div className="card">
      <div className="card-header">Browser Preview</div>
      {src ? (
        <iframe
          title="playwright-browser-preview"
          src={src}
          className="frame frame-sm"
          style={{ border: 0 }}
        />
      ) : (
        <div className="card-body muted">Preview not available.</div>
      )}
    </div>
  );
}