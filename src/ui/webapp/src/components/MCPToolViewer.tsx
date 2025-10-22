import React, { useEffect, useState, useRef } from 'react'
import { FinalResponseModal, type FinalResponse } from './FinalResponseModal'

interface MCPToolViewerProps {
  sessionId: string
  toolName: string
  sessionName?: string
}

interface ToolEvent {
  timestamp: string
  type: string
  payload: any
}

interface ToolMetrics {
  operationsCount: number
  errorCount: number
  avgResponseTime: number
  lastActivity: string
}

export function MCPToolViewer({ sessionId, toolName, sessionName }: MCPToolViewerProps) {
  const [connected, setConnected] = useState(false)
  const [events, setEvents] = useState<ToolEvent[]>([])
  const [metrics, setMetrics] = useState<ToolMetrics>({
    operationsCount: 0,
    errorCount: 0,
    avgResponseTime: 0,
    lastActivity: 'Never'
  })
  const [visualData, setVisualData] = useState<any>(null)
  const [finalResponse, setFinalResponse] = useState<FinalResponse | null>(null)
  const [showFinalResponseModal, setShowFinalResponseModal] = useState(false)
  const eventsEndRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new events arrive
  useEffect(() => {
    eventsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [events])

  // Poll for events
  useEffect(() => {
    let cancelled = false
    let pollTimer: number | null = null

    async function pollEvents() {
      try {
        const response = await fetch(`/api/mcp/${toolName}/sessions/${sessionId}/events`)
        if (!response.ok) throw new Error('Failed to fetch events')

        const data = await response.json()
        if (cancelled) return

        if (data.events && data.events.length > 0) {
          setEvents(prev => [...prev, ...data.events])
          setConnected(true)

          // Update metrics
          const totalOps = data.events.length
          const errors = data.events.filter((e: any) => e.type === 'error').length
          setMetrics({
            operationsCount: totalOps,
            errorCount: errors,
            avgResponseTime: data.avgResponseTime || 0,
            lastActivity: new Date().toLocaleTimeString()
          })

          // Extract visual data based on tool type
          const latestVisual = data.events.find((e: any) =>
            e.type === 'screenshot' || e.type === 'result' || e.type === 'data'
          )
          if (latestVisual) {
            setVisualData(latestVisual.payload)
          }

          // Extract final response (look for completion or final result events)
          const finalEvent = data.events.find((e: any) =>
            e.type === 'completion' || e.type === 'final_result' || e.type === 'agent.completion'
          )
          if (finalEvent && finalEvent.payload) {
            const response: FinalResponse = {
              status: finalEvent.payload.status || 'success',
              content: typeof finalEvent.payload === 'string' ? finalEvent.payload : JSON.stringify(finalEvent.payload, null, 2),
              tool: toolName,
              timestamp: finalEvent.timestamp,
              metadata: finalEvent.payload.metadata
            }
            setFinalResponse(response)
          }

          // Also check for error events as final response
          const errorEvent = data.events.filter((e: any) => e.type === 'error').slice(-1)[0]
          if (errorEvent && !finalEvent) {
            const response: FinalResponse = {
              status: 'error',
              content: '',
              tool: toolName,
              timestamp: errorEvent.timestamp,
              error: typeof errorEvent.payload === 'string' ? errorEvent.payload : JSON.stringify(errorEvent.payload, null, 2)
            }
            setFinalResponse(response)
          }
        }

        if (!cancelled) {
          pollTimer = setTimeout(pollEvents, 2000)
        }
      } catch (error) {
        console.error('Poll error:', error)
        setConnected(false)
        if (!cancelled) {
          pollTimer = setTimeout(pollEvents, 3000)
        }
      }
    }

    pollEvents()

    return () => {
      cancelled = true
      if (pollTimer) clearTimeout(pollTimer)
    }
  }, [sessionId, toolName])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: '#0b0f12', color: '#e6edf3' }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px',
        background: '#11181f',
        borderBottom: '1px solid #26313a',
        display: 'flex',
        alignItems: 'center',
        gap: '10px'
      }}>
        <strong>{toolName.toUpperCase()} Tool Viewer</strong>
        <span style={{
          display: 'inline-block',
          padding: '2px 8px',
          fontSize: '12px',
          borderRadius: '999px',
          border: '1px solid #26313a',
          background: '#0b1116',
          color: '#9fb3c8'
        }}>
          Server: {toolName}
        </span>
        <span style={{
          display: 'inline-block',
          padding: '2px 8px',
          fontSize: '12px',
          borderRadius: '999px',
          border: connected ? '1px solid #155e42' : '1px solid #5a4a00',
          background: connected ? '#0b1512' : '#141107',
          color: connected ? '#0fd88f' : '#e0b400'
        }}>
          {connected ? 'Connected' : 'Connecting...'}
        </span>
        {sessionName && (
          <span style={{
            display: 'inline-block',
            padding: '2px 8px',
            fontSize: '12px',
            borderRadius: '999px',
            border: '1px solid #2b3f63',
            background: '#0b1116',
            color: '#91a7ff'
          }}>
            {sessionName}
          </span>
        )}
      </div>

      {/* Metrics Bar */}
      <div style={{
        padding: '8px 16px',
        background: '#0f1419',
        borderBottom: '1px solid #26313a',
        display: 'flex',
        gap: '20px',
        fontSize: '12px',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{ display: 'flex', gap: '20px' }}>
          <div>
            <span style={{ color: '#9fb3c8' }}>Operations: </span>
            <span style={{ color: '#0fd88f', fontWeight: 'bold' }}>{metrics.operationsCount}</span>
          </div>
          <div>
            <span style={{ color: '#9fb3c8' }}>Errors: </span>
            <span style={{ color: metrics.errorCount > 0 ? '#ff7b72' : '#0fd88f', fontWeight: 'bold' }}>
              {metrics.errorCount}
            </span>
          </div>
          <div>
            <span style={{ color: '#9fb3c8' }}>Avg Response: </span>
            <span style={{ color: '#91a7ff', fontWeight: 'bold' }}>
              {metrics.avgResponseTime > 0 ? `${metrics.avgResponseTime}ms` : 'N/A'}
            </span>
          </div>
          <div>
            <span style={{ color: '#9fb3c8' }}>Last Activity: </span>
            <span style={{ color: '#91a7ff', fontWeight: 'bold' }}>{metrics.lastActivity}</span>
          </div>
        </div>
        {finalResponse && (
          <button
            onClick={() => setShowFinalResponseModal(true)}
            style={{
              padding: '6px 14px',
              background: 'linear-gradient(135deg, #0fd88f 0%, #0ab370 100%)',
              border: 'none',
              borderRadius: '6px',
              color: '#0b1512',
              cursor: 'pointer',
              fontSize: '12px',
              fontWeight: 600,
              transition: 'transform 0.2s, box-shadow 0.2s',
              boxShadow: '0 2px 8px rgba(15, 216, 143, 0.3)'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-1px)'
              e.currentTarget.style.boxShadow = '0 4px 12px rgba(15, 216, 143, 0.4)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)'
              e.currentTarget.style.boxShadow = '0 2px 8px rgba(15, 216, 143, 0.3)'
            }}
          >
            📄 View Final Response
          </button>
        )}
      </div>

      {/* Main Content Area */}
      <div style={{ display: 'flex', gap: '12px', padding: '12px', flex: 1, overflow: 'hidden' }}>
        {/* Visual Data Panel (if applicable) */}
        {visualData && (
          <div style={{
            flex: 1,
            background: '#0f1419',
            border: '1px solid #26313a',
            borderRadius: '8px',
            overflow: 'auto',
            minHeight: '60vh',
            maxHeight: '80vh'
          }}>
            <h3 style={{
              margin: 0,
              padding: '10px 12px',
              borderBottom: '1px solid #26313a',
              background: '#0b1116',
              position: 'sticky',
              top: 0,
              fontSize: '14px'
            }}>
              Visual Output
            </h3>
            <div style={{ padding: '12px' }}>
              <ToolVisualOutput toolName={toolName} data={visualData} />
            </div>
          </div>
        )}

        {/* Events Log Panel */}
        <div style={{
          flex: 1,
          background: '#0f1419',
          border: '1px solid #26313a',
          borderRadius: '8px',
          overflow: 'auto',
          minHeight: '60vh',
          maxHeight: '80vh'
        }}>
          <h3 style={{
            margin: 0,
            padding: '10px 12px',
            borderBottom: '1px solid #26313a',
            background: '#0b1116',
            position: 'sticky',
            top: 0,
            fontSize: '14px'
          }}>
            Event Log
          </h3>
          <div>
            {events.length === 0 ? (
              <div style={{ padding: '12px', color: '#9fb3c8', fontStyle: 'italic' }}>
                No events yet... Waiting for activity
              </div>
            ) : (
              events.map((event, index) => (
                <EventItem key={index} event={event} />
              ))
            )}
            <div ref={eventsEndRef} />
          </div>
        </div>
      </div>

      {/* Final Response Modal */}
      {showFinalResponseModal && finalResponse && (
        <FinalResponseModal
          response={finalResponse}
          onClose={() => setShowFinalResponseModal(false)}
        />
      )}
    </div>
  )
}

// Event item component
function EventItem({ event }: { event: ToolEvent }) {
  const getEventColor = (type: string) => {
    if (type === 'error') return '#ff7b72'
    if (type === 'warning') return '#e0b400'
    if (type === 'success') return '#0fd88f'
    return '#91a7ff'
  }

  return (
    <div style={{
      padding: '8px 12px',
      borderLeft: `3px solid ${getEventColor(event.type)}`,
      margin: '4px 8px',
      background: '#0b1116',
      borderRadius: '4px',
      fontSize: '12px',
      lineHeight: '1.5'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
        <span style={{ fontWeight: 'bold', color: getEventColor(event.type) }}>
          {event.type.toUpperCase()}
        </span>
        <span style={{ color: '#9fb3c8', fontSize: '11px' }}>
          {event.timestamp}
        </span>
      </div>
      <div style={{ color: '#e6edf3', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
        {typeof event.payload === 'string'
          ? event.payload
          : JSON.stringify(event.payload, null, 2)
        }
      </div>
    </div>
  )
}

// Tool-specific visual output renderer
function ToolVisualOutput({ toolName, data }: { toolName: string, data: any }) {
  // GitHub: Show repo/issue/PR data
  if (toolName === 'github') {
    return <GitHubVisual data={data} />
  }

  // Docker: Show container list/stats
  if (toolName === 'docker') {
    return <DockerVisual data={data} />
  }

  // Desktop: Show file tree or operation results
  if (toolName === 'desktop') {
    return <DesktopVisual data={data} />
  }

  // Supabase: Show query results as tables
  if (toolName === 'supabase') {
    return <SupabaseVisual data={data} />
  }

  // Redis: Show key-value data
  if (toolName === 'redis') {
    return <RedisVisual data={data} />
  }

  // Context7: Show search results
  if (toolName === 'context7') {
    return <Context7Visual data={data} />
  }

  // Windows-automation: Show screenshots or operation results
  if (toolName === 'windows-automation') {
    return <WindowsAutomationVisual data={data} />
  }

  // Default: JSON view
  return (
    <pre style={{
      whiteSpace: 'pre-wrap',
      wordWrap: 'break-word',
      margin: 0,
      padding: 0,
      color: '#e6edf3',
      fontSize: '12px'
    }}>
      {JSON.stringify(data, null, 2)}
    </pre>
  )
}

// Tool-specific visual components (placeholders for now)
function GitHubVisual({ data }: { data: any }) {
  if (Array.isArray(data)) {
    return (
      <div>
        {data.map((item, i) => (
          <div key={i} style={{
            padding: '12px',
            background: '#11181f',
            border: '1px solid #26313a',
            borderRadius: '6px',
            marginBottom: '8px'
          }}>
            <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>{item.title || item.name}</div>
            <div style={{ fontSize: '12px', color: '#9fb3c8' }}>
              {item.description || item.body || 'No description'}
            </div>
          </div>
        ))}
      </div>
    )
  }
  return <pre style={{ margin: 0, color: '#e6edf3' }}>{JSON.stringify(data, null, 2)}</pre>
}

function DockerVisual({ data }: { data: any }) {
  if (Array.isArray(data)) {
    return (
      <div>
        {data.map((container, i) => (
          <div key={i} style={{
            padding: '12px',
            background: '#11181f',
            border: '1px solid #26313a',
            borderRadius: '6px',
            marginBottom: '8px'
          }}>
            <div style={{ fontWeight: 'bold' }}>{container.name || container.Names}</div>
            <div style={{ fontSize: '12px', color: '#9fb3c8' }}>
              Status: <span style={{ color: container.status === 'running' ? '#0fd88f' : '#ff7b72' }}>
                {container.status || container.State}
              </span>
            </div>
            <div style={{ fontSize: '11px', color: '#6b7280', marginTop: '4px' }}>
              {container.image || container.Image}
            </div>
          </div>
        ))}
      </div>
    )
  }
  return <pre style={{ margin: 0, color: '#e6edf3' }}>{JSON.stringify(data, null, 2)}</pre>
}

function DesktopVisual({ data }: { data: any }) {
  return <pre style={{ margin: 0, color: '#e6edf3', fontSize: '12px' }}>{JSON.stringify(data, null, 2)}</pre>
}

function SupabaseVisual({ data }: { data: any }) {
  if (Array.isArray(data) && data.length > 0) {
    const keys = Object.keys(data[0])
    return (
      <table style={{
        width: '100%',
        borderCollapse: 'collapse',
        fontSize: '12px',
        color: '#e6edf3'
      }}>
        <thead>
          <tr style={{ background: '#11181f', borderBottom: '2px solid #26313a' }}>
            {keys.map(key => (
              <th key={key} style={{ padding: '8px', textAlign: 'left', fontWeight: 'bold' }}>
                {key}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={i} style={{ borderBottom: '1px solid #1a2229' }}>
              {keys.map(key => (
                <td key={key} style={{ padding: '8px' }}>
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

function RedisVisual({ data }: { data: any }) {
  return <pre style={{ margin: 0, color: '#e6edf3', fontSize: '12px' }}>{JSON.stringify(data, null, 2)}</pre>
}

function Context7Visual({ data }: { data: any }) {
  return <pre style={{ margin: 0, color: '#e6edf3', fontSize: '12px' }}>{JSON.stringify(data, null, 2)}</pre>
}

function WindowsAutomationVisual({ data }: { data: any }) {
  if (data.screenshot) {
    return <img src={data.screenshot} alt="Screenshot" style={{ maxWidth: '100%', borderRadius: '6px' }} />
  }
  return <pre style={{ margin: 0, color: '#e6edf3', fontSize: '12px' }}>{JSON.stringify(data, null, 2)}</pre>
}
