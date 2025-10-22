import React from 'react'

export interface FinalResponse {
  status: 'success' | 'error'
  content: string
  tool: string
  timestamp?: string
  error?: string
  metadata?: Record<string, any>
}

interface FinalResponseModalProps {
  response: FinalResponse
  onClose: () => void
}

export function FinalResponseModal({ response, onClose }: FinalResponseModalProps) {
  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0,0,0,0.85)',
        zIndex: 2000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px',
        backdropFilter: 'blur(4px)'
      }}
      onClick={onClose}
    >
      <div
        style={{
          backgroundColor: '#0b0f12',
          borderRadius: '12px',
          maxWidth: '900px',
          width: '100%',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          border: '1px solid #26313a',
          boxShadow: '0 20px 60px rgba(0,0,0,0.6)'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            padding: '16px 20px',
            borderBottom: '1px solid #26313a',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            background: 'linear-gradient(135deg, #11181f 0%, #0f1419 100%)'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <h3 style={{ margin: 0, color: '#e6edf3', fontSize: '18px', fontWeight: 600 }}>
              {getToolIcon(response.tool)} {response.tool.toUpperCase()} Response
            </h3>
            <span
              style={{
                display: 'inline-block',
                padding: '4px 12px',
                fontSize: '12px',
                borderRadius: '999px',
                border: response.status === 'success' ? '1px solid #155e42' : '1px solid #732f2f',
                background: response.status === 'success' ? '#0b1512' : '#1a0f0f',
                color: response.status === 'success' ? '#0fd88f' : '#ff7b72',
                fontWeight: 600
              }}
            >
              {response.status === 'success' ? '✓ SUCCESS' : '✗ ERROR'}
            </span>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              fontSize: '28px',
              cursor: 'pointer',
              color: '#9fb3c8',
              lineHeight: 1,
              padding: '0 4px',
              transition: 'color 0.2s'
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = '#e6edf3')}
            onMouseLeave={(e) => (e.currentTarget.style.color = '#9fb3c8')}
          >
            ×
          </button>
        </div>

        {/* Metadata Bar */}
        {response.timestamp && (
          <div
            style={{
              padding: '8px 20px',
              background: '#0f1419',
              borderBottom: '1px solid #1a2229',
              fontSize: '12px',
              color: '#9fb3c8',
              display: 'flex',
              gap: '16px'
            }}
          >
            <span>
              <strong style={{ color: '#e6edf3' }}>Timestamp:</strong> {response.timestamp}
            </span>
            {response.metadata && Object.keys(response.metadata).length > 0 && (
              <>
                {Object.entries(response.metadata).map(([key, value]) => (
                  <span key={key}>
                    <strong style={{ color: '#e6edf3' }}>{key}:</strong> {String(value)}
                  </span>
                ))}
              </>
            )}
          </div>
        )}

        {/* Content */}
        <div
          style={{
            flex: 1,
            overflow: 'auto',
            padding: '20px',
            background: '#0b0f12'
          }}
        >
          {response.status === 'error' ? (
            <div
              style={{
                padding: '16px',
                background: '#1a0f0f',
                border: '1px solid #732f2f',
                borderRadius: '8px',
                color: '#ff7b72'
              }}
            >
              <div style={{ fontSize: '14px', fontWeight: 600, marginBottom: '8px' }}>
                ⚠ Error Occurred
              </div>
              <pre
                style={{
                  margin: 0,
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  fontSize: '13px',
                  lineHeight: '1.6',
                  fontFamily: 'Consolas, "Courier New", monospace'
                }}
              >
                {response.error || response.content}
              </pre>
            </div>
          ) : (
            <FormattedResponse tool={response.tool} content={response.content} />
          )}
        </div>

        {/* Footer */}
        <div
          style={{
            padding: '12px 20px',
            borderTop: '1px solid #26313a',
            background: '#0f1419',
            display: 'flex',
            justifyContent: 'flex-end',
            gap: '10px'
          }}
        >
          <button
            onClick={() => {
              navigator.clipboard.writeText(response.content)
              alert('Response copied to clipboard!')
            }}
            style={{
              padding: '8px 16px',
              background: '#11181f',
              border: '1px solid #26313a',
              borderRadius: '6px',
              color: '#91a7ff',
              cursor: 'pointer',
              fontSize: '13px',
              fontWeight: 500,
              transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = '#1a2229'
              e.currentTarget.style.borderColor = '#2b3f63'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = '#11181f'
              e.currentTarget.style.borderColor = '#26313a'
            }}
          >
            📋 Copy Response
          </button>
          <button
            onClick={onClose}
            style={{
              padding: '8px 16px',
              background: '#0fd88f',
              border: 'none',
              borderRadius: '6px',
              color: '#0b1512',
              cursor: 'pointer',
              fontSize: '13px',
              fontWeight: 600,
              transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = '#1fd99d')}
            onMouseLeave={(e) => (e.currentTarget.style.background = '#0fd88f')}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

// Tool-specific response formatting
function FormattedResponse({ tool, content }: { tool: string; content: string }) {
  // Try to parse as JSON first
  let parsed: any = null
  try {
    parsed = JSON.parse(content)
  } catch {
    // Not JSON, treat as plain text
  }

  // GitHub: Format issues, PRs, repos
  if (tool === 'github' && parsed) {
    return <GitHubResponseFormat data={parsed} />
  }

  // Docker: Format containers, images, stats
  if (tool === 'docker' && parsed) {
    return <DockerResponseFormat data={parsed} />
  }

  // Time: Format timestamps nicely
  if (tool === 'time' && parsed) {
    return <TimeResponseFormat data={parsed} />
  }

  // Memory: Format knowledge graph data
  if (tool === 'memory' && parsed) {
    return <MemoryResponseFormat data={parsed} />
  }

  // Filesystem: Format file listings
  if (tool === 'filesystem' && parsed) {
    return <FilesystemResponseFormat data={parsed} />
  }

  // TaskManager: Format tasks
  if (tool === 'taskmanager' && parsed) {
    return <TaskManagerResponseFormat data={parsed} />
  }

  // Redis: Format key-value data
  if (tool === 'redis' && parsed) {
    return <RedisResponseFormat data={parsed} />
  }

  // Supabase: Format query results as table
  if (tool === 'supabase' && parsed) {
    return <SupabaseResponseFormat data={parsed} />
  }

  // Default: Formatted JSON or plain text
  if (parsed) {
    return (
      <pre
        style={{
          margin: 0,
          padding: '16px',
          background: '#0f1419',
          border: '1px solid #26313a',
          borderRadius: '8px',
          color: '#e6edf3',
          fontSize: '13px',
          lineHeight: '1.6',
          fontFamily: 'Consolas, "Courier New", monospace',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
          overflow: 'auto'
        }}
      >
        {JSON.stringify(parsed, null, 2)}
      </pre>
    )
  }

  return (
    <div
      style={{
        padding: '16px',
        background: '#0f1419',
        border: '1px solid #26313a',
        borderRadius: '8px',
        color: '#e6edf3',
        fontSize: '14px',
        lineHeight: '1.8',
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word'
      }}
    >
      {content}
    </div>
  )
}

// Tool Icons
function getToolIcon(tool: string): string {
  const icons: Record<string, string> = {
    github: '🐙',
    docker: '🐳',
    time: '⏰',
    memory: '🧠',
    filesystem: '📁',
    taskmanager: '✅',
    redis: '🔴',
    supabase: '⚡',
    desktop: '🖥️',
    'windows-core': '🪟',
    fetch: '🌐',
    youtube: '📺',
    n8n: '🔄',
    'sequential-thinking': '🤔',
    tavily: '🔍',
    'brave-search': '🦁',
    context7: '📚'
  }
  return icons[tool] || '🛠️'
}

// Tool-specific formatters
function GitHubResponseFormat({ data }: { data: any }) {
  if (Array.isArray(data)) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {data.map((item, i) => (
          <div
            key={i}
            style={{
              padding: '16px',
              background: '#0f1419',
              border: '1px solid #26313a',
              borderRadius: '8px'
            }}
          >
            <div style={{ fontSize: '16px', fontWeight: 600, color: '#91a7ff', marginBottom: '8px' }}>
              {item.title || item.name || `Item ${i + 1}`}
            </div>
            <div style={{ fontSize: '13px', color: '#9fb3c8', lineHeight: '1.6' }}>
              {item.description || item.body || 'No description'}
            </div>
            {item.url && (
              <a
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                style={{ fontSize: '12px', color: '#0fd88f', marginTop: '8px', display: 'inline-block' }}
              >
                View on GitHub →
              </a>
            )}
          </div>
        ))}
      </div>
    )
  }
  return <pre style={{ margin: 0, color: '#e6edf3' }}>{JSON.stringify(data, null, 2)}</pre>
}

function DockerResponseFormat({ data }: { data: any }) {
  if (Array.isArray(data)) {
    return (
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '12px' }}>
        {data.map((container, i) => (
          <div
            key={i}
            style={{
              padding: '14px',
              background: '#0f1419',
              border: '1px solid #26313a',
              borderRadius: '8px'
            }}
          >
            <div style={{ fontSize: '14px', fontWeight: 600, color: '#91a7ff', marginBottom: '6px' }}>
              {container.name || container.Names || `Container ${i + 1}`}
            </div>
            <div style={{ fontSize: '12px', color: '#9fb3c8', marginBottom: '4px' }}>
              <strong>Status:</strong>{' '}
              <span style={{ color: container.status === 'running' ? '#0fd88f' : '#ff7b72' }}>
                {container.status || container.State}
              </span>
            </div>
            <div style={{ fontSize: '11px', color: '#6b7280' }}>
              {container.image || container.Image}
            </div>
          </div>
        ))}
      </div>
    )
  }
  return <pre style={{ margin: 0, color: '#e6edf3' }}>{JSON.stringify(data, null, 2)}</pre>
}

function TimeResponseFormat({ data }: { data: any }) {
  return (
    <div
      style={{
        padding: '20px',
        background: '#0f1419',
        border: '1px solid #26313a',
        borderRadius: '8px',
        textAlign: 'center'
      }}
    >
      <div style={{ fontSize: '32px', fontWeight: 700, color: '#91a7ff', marginBottom: '8px' }}>
        {data.time || data.current_time || data}
      </div>
      {data.timezone && (
        <div style={{ fontSize: '14px', color: '#9fb3c8' }}>
          Timezone: {data.timezone}
        </div>
      )}
    </div>
  )
}

function MemoryResponseFormat({ data }: { data: any }) {
  if (data.entities || data.relations) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {data.entities && (
          <div>
            <h4 style={{ color: '#91a7ff', marginBottom: '8px' }}>Entities</h4>
            {data.entities.map((entity: any, i: number) => (
              <div key={i} style={{ padding: '10px', background: '#0f1419', border: '1px solid #26313a', borderRadius: '6px', marginBottom: '6px' }}>
                <strong style={{ color: '#0fd88f' }}>{entity.name}</strong>
                <span style={{ color: '#9fb3c8', marginLeft: '8px', fontSize: '12px' }}>({entity.type})</span>
              </div>
            ))}
          </div>
        )}
        {data.relations && (
          <div>
            <h4 style={{ color: '#91a7ff', marginBottom: '8px' }}>Relations</h4>
            {data.relations.map((rel: any, i: number) => (
              <div key={i} style={{ padding: '10px', background: '#0f1419', border: '1px solid #26313a', borderRadius: '6px', marginBottom: '6px', fontSize: '13px', color: '#e6edf3' }}>
                {rel.from} → <strong style={{ color: '#0fd88f' }}>{rel.type}</strong> → {rel.to}
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }
  return <pre style={{ margin: 0, color: '#e6edf3' }}>{JSON.stringify(data, null, 2)}</pre>
}

function FilesystemResponseFormat({ data }: { data: any }) {
  if (Array.isArray(data)) {
    return (
      <div style={{ fontFamily: 'Consolas, "Courier New", monospace', fontSize: '13px' }}>
        {data.map((file: any, i: number) => (
          <div key={i} style={{ padding: '6px 10px', borderBottom: '1px solid #1a2229', color: '#e6edf3' }}>
            {file.type === 'directory' ? '📁' : '📄'} {file.name || file}
            {file.size && <span style={{ color: '#9fb3c8', marginLeft: '12px', fontSize: '11px' }}>({file.size})</span>}
          </div>
        ))}
      </div>
    )
  }
  return <pre style={{ margin: 0, color: '#e6edf3' }}>{JSON.stringify(data, null, 2)}</pre>
}

function TaskManagerResponseFormat({ data }: { data: any }) {
  if (Array.isArray(data)) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {data.map((task: any, i: number) => (
          <div key={i} style={{ padding: '12px', background: '#0f1419', border: '1px solid #26313a', borderRadius: '6px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '18px' }}>{task.completed ? '✅' : '⬜'}</span>
              <span style={{ color: task.completed ? '#9fb3c8' : '#e6edf3', fontSize: '14px', fontWeight: 500 }}>
                {task.title || task.name}
              </span>
            </div>
            {task.description && (
              <div style={{ marginTop: '6px', fontSize: '12px', color: '#9fb3c8', marginLeft: '26px' }}>
                {task.description}
              </div>
            )}
          </div>
        ))}
      </div>
    )
  }
  return <pre style={{ margin: 0, color: '#e6edf3' }}>{JSON.stringify(data, null, 2)}</pre>
}

function RedisResponseFormat({ data }: { data: any }) {
  if (typeof data === 'object' && !Array.isArray(data)) {
    return (
      <div style={{ fontFamily: 'Consolas, "Courier New", monospace', fontSize: '13px' }}>
        {Object.entries(data).map(([key, value], i) => (
          <div key={i} style={{ padding: '8px 12px', borderBottom: '1px solid #1a2229' }}>
            <span style={{ color: '#91a7ff', fontWeight: 600 }}>{key}:</span>{' '}
            <span style={{ color: '#e6edf3' }}>{String(value)}</span>
          </div>
        ))}
      </div>
    )
  }
  return <pre style={{ margin: 0, color: '#e6edf3' }}>{JSON.stringify(data, null, 2)}</pre>
}

function SupabaseResponseFormat({ data }: { data: any }) {
  if (Array.isArray(data) && data.length > 0) {
    const keys = Object.keys(data[0])
    return (
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px', color: '#e6edf3' }}>
        <thead>
          <tr style={{ background: '#0f1419', borderBottom: '2px solid #26313a' }}>
            {keys.map((key) => (
              <th key={key} style={{ padding: '10px', textAlign: 'left', fontWeight: 600, color: '#91a7ff' }}>
                {key}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={i} style={{ borderBottom: '1px solid #1a2229' }}>
              {keys.map((key) => (
                <td key={key} style={{ padding: '10px' }}>
                  {String(row[key])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    )
  }
  return <pre style={{ margin: 0, color: '#e6edf3' }}>{JSON.stringify(data, null, 2)}</pre>
}
