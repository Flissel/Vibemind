import React, { useEffect, useState, useRef, useCallback } from 'react'
import { Outlet, Link } from '@tanstack/react-router'
import { ensureSessionStream, stopSessionStream } from './hooks/streamsManager'
import SessionStreamsStatus from './components/SessionStreamsStatus'
import { MCPSessionViewer } from './components/MCPSessionViewer'
import { SecretsManager } from './components/SecretsManager'
import { MCPToolViewer } from './components/MCPToolViewer'

// --- Typed API client (clear comments for easy debug) ---
// Playwright session status shape
interface PlaywrightSessionStatus {
  connected: boolean
  session_id?: string | null
  host?: string | null
  port?: number | null
  agent_pid?: number | null
  agent_running?: boolean
}

// GET helper for session status
async function getSessionStatus(): Promise<PlaywrightSessionStatus> {
  const res = await fetch('/api/playwright/session/status')
  return await res.json()
}

// POST helper to spawn agent
async function spawnSession(): Promise<{ success: boolean; session_id?: string; pid?: number; error?: string }> {
  const res = await fetch('/api/playwright/session/spawn', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({})
  })
  return await res.json()
}

// POST helper to stop playwright agent
async function stopPlaywrightSession(): Promise<{ success: boolean; error?: string }> {
  const res = await fetch('/api/playwright/session/stop', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({})
  })
  return await res.json()
}

// GET helper for plugins (clear comments for easy debug)
async function getPlugins(): Promise<{ plugins: Array<{ name: string; version: string; description?: string; commands?: string[] }> }> {
  const res = await fetch('/api/plugins')
  return await res.json()
}

// Session management API functions
async function getSessions(): Promise<{ sessions: Array<{ session_id: string; name: string; model: string; tools: string[]; status: string; host?: string; port?: number; agent_pid?: number; connected?: boolean; task?: string; target_tool?: string; last_response?: string; last_tool_executed?: string; started_at?: number; stopped_at?: number; duration_ms?: number }> }> {
  const res = await fetch('/api/sessions')
  return await res.json()
}

async function createSession(sessionData: { name: string; model: string; tools: string[]; task?: string; target_tool?: string }): Promise<{ success: boolean; session?: any; error?: string }> {
  const res = await fetch('/api/sessions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(sessionData)
  })
  return await res.json()
}

async function startSession(sessionId: string): Promise<{ success: boolean; error?: string }> {
  const res = await fetch(`/api/sessions/${sessionId}/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({})
  })
  return await res.json()
}

async function stopSession(sessionId: string): Promise<{ success: boolean; error?: string }> {
  const res = await fetch(`/api/sessions/${sessionId}/stop`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({})
  })
  return await res.json()
}

async function deleteSession(sessionId: string): Promise<{ success: boolean; error?: string }> {
  const res = await fetch(`/api/sessions/${sessionId}/delete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({})
  })
  return await res.json()
}

// Playwright-specific session creation API (uses same endpoint as createSession but with explicit Playwright tools)
async function createPlaywrightSession(sessionData: { name: string; model: string; tools?: string[] }): Promise<{ success: boolean; session?: any; error?: string }> {
  const res = await fetch('/api/sessions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ...sessionData,
      tools: sessionData.tools || ['playwright']  // Ensure Playwright is included
    })
  })
  return await res.json()
}

// Get session logs
async function getSessionLogs(sessionId: string): Promise<{ session_id: string; lines: string[]; total_lines: number; showing_lines: number }> {
  const res = await fetch(`/api/sessions/${sessionId}/logs`)
  return await res.json()
}

// SessionViewerModal component with logs
function SessionViewerModal({ sessionId, sessions, onClose }: { sessionId: string; sessions: any[]; onClose: () => void }) {
  const [showLogs, setShowLogs] = useState(false)
  const [logs, setLogs] = useState<string[]>([])
  const [logsError, setLogsError] = useState<string | null>(null)

  useEffect(() => {
    if (!showLogs) return

    const loadLogs = async () => {
      try {
        const data = await getSessionLogs(sessionId)
        setLogs(data.lines || [])
        setLogsError(null)
      } catch (e: any) {
        setLogsError(e.message || 'Failed to load logs')
      }
    }

    loadLogs()
    const interval = setInterval(loadLogs, 3000)
    return () => clearInterval(interval)
  }, [sessionId, showLogs])

  const session = sessions.find(s => s.session_id === sessionId)

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.8)',
      zIndex: 1000,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '10px'
    }} onClick={onClose}>
      <div style={{
        backgroundColor: 'white',
        borderRadius: '8px',
        maxWidth: '98vw',
        maxHeight: '98vh',
        width: '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden'
      }} onClick={(e) => e.stopPropagation()}>
        <div style={{ padding: '16px', borderBottom: '1px solid #ddd', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ margin: 0 }}>
            {session?.name || 'Session Viewer'}
          </h3>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <button
              onClick={() => setShowLogs(!showLogs)}
              className="btn btn-secondary"
              style={{ fontSize: '14px', padding: '6px 12px' }}
            >
              {showLogs ? 'Hide Logs' : 'Show Logs'}
            </button>
            <button
              onClick={onClose}
              className="btn btn-ghost"
              style={{ fontSize: '20px', padding: '4px 12px' }}
            >
              ×
            </button>
          </div>
        </div>
        <div style={{ flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column' }}>
          <div style={{ flex: showLogs ? '0 0 60%' : 1, overflow: 'auto' }}>
            {(() => {
              if (!session) return <div style={{ padding: '20px' }}>Session not found</div>

              if (session.target_tool === 'playwright') {
                return (
                  <iframe
                    key={sessionId}
                    title={`Playwright Viewer - ${session.name}`}
                    src={`/mcp/playwright/session/${sessionId}/`}
                    style={{ width: '100%', height: '100%', border: 'none' }}
                  />
                )
              } else if (session.target_tool === 'github') {
                return (
                  <MCPSessionViewer
                    sessionId={sessionId}
                    targetTool="github"
                  />
                )
              } else {
                return (
                  <MCPToolViewer
                    sessionId={sessionId}
                    toolName={session.target_tool || 'unknown'}
                    sessionName={session.name}
                  />
                )
              }
            })()}
          </div>
          {showLogs && (
            <div style={{ flex: '0 0 40%', borderTop: '2px solid #343a40', display: 'flex', flexDirection: 'column', backgroundColor: '#1e1e1e' }}>
              <div style={{ padding: '8px 16px', backgroundColor: '#2d2d30', fontWeight: 'bold', fontSize: '13px', color: '#d4d4d4', borderBottom: '1px solid #3e3e42' }}>
                Session Logs ({logs.length} lines)
              </div>
              <div style={{ flex: 1, overflow: 'auto', padding: '12px', fontFamily: 'Consolas, "Courier New", monospace', fontSize: '12px', lineHeight: '1.5', backgroundColor: '#1e1e1e' }}>
                {logsError ? (
                  <div style={{ color: '#f48771' }}>Error: {logsError}</div>
                ) : logs.length === 0 ? (
                  <div style={{ color: '#858585' }}>No logs available yet...</div>
                ) : (
                  <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word', color: '#d4d4d4' }}>
                    {logs.join('\n')}
                  </pre>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export function RootLayout() {
  return (
    <div className="app-root">
      <nav className="app-nav">
        <Link to="/" activeOptions={{ exact: true }} className="nav-link">Chat</Link>
        <Link to="/sessions" className="nav-link">Sessions</Link>
        <Link to="/tools" className="nav-link">Tools</Link>
        <Link to="/secrets" className="nav-link">Secrets</Link>
      </nav>
      <div className="app-content">
        <Outlet />
      </div>
    </div>
  )
}

// Simple chat helpers
async function sendMessage(input: string): Promise<{ reply?: string; error?: string; [k: string]: any }> {
  const res = await fetch('/api/message', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ input })
  })
  try { return await res.json() } catch { return { error: 'Invalid JSON' } }
}

export function ChatView() {
  const [messages, setMessages] = useState<Array<{ role: 'user' | 'assistant'; text: string }>>(() => {
    try {
      const raw = localStorage.getItem('chat_history')
      return raw ? JSON.parse(raw) : []
    } catch {
      return []
    }
  })
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)

  const append = useCallback((m: { role: 'user' | 'assistant'; text: string }) => {
    setMessages(prev => {
      const next = [...prev, m]
      try { localStorage.setItem('chat_history', JSON.stringify(next)) } catch {}
      return next
    })
  }, [])

  const onSend = useCallback(async () => {
    const text = input.trim()
    if (!text) return
    setSending(true)
    append({ role: 'user', text })
    setInput('')
    try {
      const resp = await sendMessage(text)
      const reply = typeof resp.reply === 'string' ? resp.reply : JSON.stringify(resp)
      append({ role: 'assistant', text: reply })
    } catch (e: any) {
      append({ role: 'assistant', text: `Error: ${e?.message || 'Failed to send'}` })
    } finally {
      setSending(false)
    }
  }, [input, append])

  return (
    <div style={{ display: 'grid', gridTemplateRows: '1fr auto', height: '70vh' }}>
      <div style={{ overflow: 'auto', padding: 12, border: '1px solid #ddd', borderRadius: 8, marginBottom: 12 }}>
        {messages.length === 0 ? (
          <div style={{ color: '#666' }}>Start chatting with the assistant.</div>
        ) : (
          messages.map((m, i) => (
            <div key={i} style={{ marginBottom: 8 }}>
              <strong>{m.role === 'user' ? 'You' : 'Assistant'}:</strong>
              <div style={{ whiteSpace: 'pre-wrap' }}>{m.text}</div>
            </div>
          ))
        )}
      </div>

      <div style={{ display: 'flex', gap: 8 }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Type a message"
          style={{ flex: 1, padding: 8 }}
          onKeyDown={e => { if (e.key === 'Enter') onSend() }}
        />
        <button onClick={onSend} disabled={sending}>
          {sending ? 'Sending…' : 'Send'}
        </button>
      </div>
    </div>
  )
}

// Session interface for managing multiple sessions - updated to match backend structure
interface PlaywrightSession {
  session_id: string  // Changed from 'id' to 'session_id' to match backend
  name: string
  model: string
  tools: string[]
  status: string
  connected: boolean
  host?: string | null
  port?: number | null
  agent_pid?: number | null
  agent_running?: boolean
  // NEW: session metadata fields from backend
  task?: string
  target_tool?: string
  last_response?: string
  last_tool_executed?: string
  started_at?: number
  stopped_at?: number
  duration_ms?: number
  loading?: boolean  // Frontend-only state
  iframeKey?: number  // Frontend-only state for iframe refresh
}

export function PlaywrightView() {
  // Multi-session state management - now using backend sessions
  const [sessions, setSessions] = useState<PlaywrightSession[]>([])
  const [loading, setLoading] = useState(false)
  const [viewerSessionId, setViewerSessionId] = useState<string | null>(null)

  // Function to fetch all sessions from backend
  const refreshSessions = async () => {
    try {
      const result = await getSessions()
      if (result.sessions) {
        // Add frontend-only properties to backend sessions
        const sessionsWithFrontendState = result.sessions.map(session => ({
          ...session,
          // Ensure required runtime field exists for type compatibility
          connected: Boolean((session as any).connected ?? false),
          loading: false,
          iframeKey: 0
        }))
        setSessions(sessionsWithFrontendState)
      }
    } catch (error) {
      console.error('Failed to refresh sessions:', error)
    }
  }

  // Function to fetch session status for a specific session
  const getSessionStatusById = async (sessionId: string): Promise<PlaywrightSessionStatus> => {
    const res = await fetch(`/api/playwright/session/${sessionId}/status`)
    return await res.json()
  }

  // Function to spawn a new session
  const spawnSessionById = async (sessionId: string): Promise<{ success: boolean; session_id?: string; pid?: number; error?: string }> => {
    const res = await fetch(`/api/playwright/session/${sessionId}/spawn`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId })
    })
    return await res.json()
  }

  // Function to stop a specific session
  const stopSessionById = async (sessionId: string): Promise<{ success: boolean; error?: string }> => {
    const res = await fetch(`/api/playwright/session/${sessionId}/stop`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId })
    })
    return await res.json()
  }

  // Update session status for a specific session
  const updateSessionStatus = async (sessionId: string) => {
    try {
      const newStatus = await getSessionStatusById(sessionId)
      setSessions(prev => prev.map(session => 
        session.session_id === sessionId 
          ? { ...session, connected: newStatus.connected, host: newStatus.host, port: newStatus.port }
          : session
      ))
    } catch (error) {
      // Ignore errors for debug simplicity
    }
  }

  // Create a new session using Playwright-specific backend API
  const addNewSession = async () => {
    setLoading(true)
    try {
      const result = await createPlaywrightSession({
        name: `Playwright Session ${sessions.length + 1}`,
        model: 'gpt-4',
        tools: ['playwright']
      })
      
      if (result.success && result.session) {
        await refreshSessions()
        // Auto-start the new session
        setTimeout(() => handleSpawn(result.session.session_id), 100)
      } else {
        alert(`Failed to create session: ${result.error || 'Unknown error'}`)
      }
    } catch (error) {
      alert(`Failed to create session: ${error}`)
    } finally {
      setLoading(false)
    }
  }

  // Remove a session using backend API
  const removeSession = async (sessionId: string) => {
    const skipConfirmation = localStorage.getItem('skipDeleteConfirmation') === 'true'

    if (skipConfirmation || confirm('Are you sure you want to delete this session?')) {
      setLoading(true)
      try {
        const result = await deleteSession(sessionId)
        if (result.success) {
          await refreshSessions()
        } else {
          alert(`Failed to delete session: ${result.error || 'Unknown error'}`)
        }
      } catch (error) {
        alert(`Failed to delete session: ${error}`)
      } finally {
        setLoading(false)
      }
    }
  }

  // Action handlers for specific sessions
  const handleSpawn = async (sessionId: string) => {
    setSessions(prev => prev.map(session => 
      session.session_id === sessionId 
        ? { ...session, loading: true }
        : session
    ))
    
    try {
      await spawnSessionById(sessionId)
      // Small delay to allow agent to boot and server to attach
      await new Promise((r) => setTimeout(r, 600))
      await updateSessionStatus(sessionId)
      await refreshSessions()  // Refresh to get updated status from backend
    } finally {
      setSessions(prev => prev.map(session => 
        session.session_id === sessionId 
          ? { ...session, loading: false }
          : session
      ))
    }
  }

  const handleStop = async (sessionId: string) => {
    setSessions(prev => prev.map(session => 
      session.session_id === sessionId 
        ? { ...session, loading: true }
        : session
    ))
    
    try {
      await stopSessionById(sessionId)
      await updateSessionStatus(sessionId)
      await refreshSessions()  // Refresh to get updated status from backend
    } finally {
      setSessions(prev => prev.map(session => 
        session.session_id === sessionId 
          ? { ...session, loading: false }
          : session
      ))
    }
  }

  // Initial setup - load sessions from backend
  useEffect(() => {
    refreshSessions()
  }, [])

  // Track connection status changes and refresh iframe when it changes
  useEffect(() => {
    setSessions(prev => prev.map(session => ({
      ...session,
      iframeKey: (session.iframeKey || 0) + 1
    })))
  }, [sessions.map(s => s.connected).join(',')])

  // Render individual session component
  const renderSession = (session: PlaywrightSession) => {
    const connected = session.connected
    const summary = connected
      ? `connected (id=${session.session_id.substring(0, 8)}... @ ${session.host}:${session.port})`
      : 'not connected'

    return (
      <div key={session.session_id} style={{ 
        border: '1px solid #ddd', 
        borderRadius: '8px', 
        padding: '16px', 
        marginBottom: '16px',
        backgroundColor: '#f9f9f9'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 'bold' }}>
            {session.name}
          </h3>
          <button 
            onClick={() => removeSession(session.session_id)}
            style={{ 
              background: '#ff4444', 
              color: 'white', 
              border: 'none', 
              borderRadius: '4px', 
              padding: '4px 8px',
              cursor: 'pointer',
              fontSize: '12px'
            }}
            disabled={session.loading || loading}
          >
            Remove
          </button>
        </div>
        
        <p style={{ margin: '0 0 12px 0', fontSize: '14px' }}>
          Session status: {summary}
        </p>
        
        <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
          <button 
            onClick={() => handleSpawn(session.session_id)} 
            disabled={session.loading || loading}
          >
            {session.loading ? 'Starting…' : connected ? 'Restart Agent' : 'Start Agent'}
          </button>
          <button 
            onClick={() => handleStop(session.session_id)} 
            disabled={session.loading || loading || !connected}
          >
            Stop Agent
          </button>
        </div>
        
        {/* Session-specific iframe - fixed routing to use proper session endpoint */}
        <iframe 
          key={session.iframeKey} 
          title={`Playwright Viewer - ${session.name}`}
          src={`/mcp/playwright/session/${session.session_id}/`}
          style={{ width: '100%', height: 480, border: '1px solid #ccc' }} 
        />
      </div>
    )
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2 style={{ margin: 0 }}>Playwright Sessions</h2>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button 
            onClick={refreshSessions}
            style={{ 
              background: '#6c757d', 
              color: 'white', 
              border: 'none', 
              borderRadius: '6px', 
              padding: '8px 16px',
              cursor: 'pointer',
              fontWeight: 'bold'
            }}
            disabled={loading}
          >
            Refresh
          </button>
          <button 
            onClick={addNewSession}
            style={{ 
              background: '#007bff', 
              color: 'white', 
              border: 'none', 
              borderRadius: '6px', 
              padding: '8px 16px',
              cursor: 'pointer',
              fontWeight: 'bold'
            }}
            disabled={loading}
          >
            {loading ? 'Creating...' : 'Add Agent'}
          </button>
        </div>
      </div>
      
      {sessions.length === 0 ? (
        <p>No sessions available. Click "Add Agent" to create a new session.</p>
      ) : (
        sessions.map(renderSession)
      )}
    </div>
  )
}

// Duplicate ToolsView removed — see ToolsView defined later with delegate functionality.

export function SessionsView() {
  // State management for sessions
  const [sessions, setSessions] = useState<PlaywrightSession[]>([])
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null)
  const [viewerSessionId, setViewerSessionId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [newSessionName, setNewSessionName] = useState('')
  const [newSessionModel, setNewSessionModel] = useState('openai/gpt-4o')
  const [newSessionTools, setNewSessionTools] = useState<string[]>([])
  const [newSessionTask, setNewSessionTask] = useState('')
  const [newTargetTool, setNewTargetTool] = useState('playwright')
  const [skipDeleteConfirmation, setSkipDeleteConfirmation] = useState(() =>
    localStorage.getItem('skipDeleteConfirmation') === 'true'
  )
  const [availableModels, setAvailableModels] = useState<Array<{id: string; name: string; type: string}>>([])
  const [availableTools, setAvailableTools] = useState<Array<{name: string; description: string}>>([])

  // Fetch available models and tools on mount
  useEffect(() => {
    const fetchAvailableOptions = async () => {
      try {
        // Fetch models
        const modelsRes = await fetch('/api/models/available')
        const modelsData = await modelsRes.json()

        // Filter to only show top-tier models (Sonnet 4.0, GPT-4o, and minis)
        const topTierModels = modelsData.available_models?.filter((m: any) =>
          m.id === 'anthropic/claude-sonnet-4.0' ||
          m.id === 'openai/gpt-4o' ||
          m.id === 'openai/gpt-4o-mini' ||
          m.id === 'anthropic/claude-3.5-haiku'
        ) || []

        setAvailableModels(topTierModels)

        // Fetch tools
        const toolsRes = await fetch('/api/mcp/tools')
        const toolsData = await toolsRes.json()
        setAvailableTools(toolsData.tools || [])
      } catch (error) {
        console.error('Failed to fetch available options:', error)
      }
    }
    fetchAvailableOptions()
  }, [])
  const [showDevSettings, setShowDevSettings] = useState(false)

  // Sync tools array with selected target tool
  React.useEffect(() => {
    setNewSessionTools([newTargetTool])
  }, [newTargetTool])

  // Refresh sessions from API
  const refreshSessions = async () => {
    try {
      const result = await getSessions()
      const normalized = (result.sessions || []).map(session => ({
        ...session,
        connected: Boolean((session as any).connected ?? false)
      }))
      setSessions(normalized)

      // Only clear selection if selected session was deleted
      if (normalized.length === 0) {
        setSelectedSessionId(null)
      } else if (selectedSessionId && !normalized.find(s => s.session_id === selectedSessionId)) {
        setSelectedSessionId(null)
      }
    } catch (error) {
      console.error('Failed to refresh sessions:', error)
    }
  }

  // Auto-refresh sessions every 3 seconds (not too aggressive)
  useEffect(() => {
    refreshSessions()
    const interval = setInterval(refreshSessions, 3000)
    return () => clearInterval(interval)
  }, [])

  // Ensure background streaming for running sessions and cleanup stopped ones
  useEffect(() => {
    // Health-aware filter: must have status='running', host/port, AND agent_running=true
    const runningSessions = sessions.filter(s =>
      s.status === 'running' &&
      s.host &&
      s.port &&
      s.agent_running !== false  // Include if undefined (older sessions) or true
    )
    const runningIds = new Set(runningSessions.map(s => s.session_id))

    // Start streams ONLY for Playwright sessions (others use MCPSessionViewer with own SSE)
    runningSessions
      .filter(s => s.target_tool === 'playwright')
      .forEach(s => ensureSessionStream(s.session_id))

    // Stop streams for sessions that are no longer running
    sessions
      .filter(s => s.status !== 'running' && !runningIds.has(s.session_id))
      .forEach(s => stopSessionStream(s.session_id))
  }, [sessions])

  // Create new session with auto-generated UUID-based name
  const handleCreateSession = async () => {
    if (newSessionTask.trim()) {
      setLoading(true)
      try {
        // Generate UUID-based name
        const uuid = crypto.randomUUID()
        const shortId = uuid.split('-')[0]
        const autoGeneratedName = `session-${shortId}`

        const result = await createSession({
          name: autoGeneratedName,
          model: newSessionModel,
          tools: newSessionTools,
          task: newSessionTask.trim(),
          target_tool: newTargetTool.trim() || undefined
        })
        if (result.success && result.session) {
          await refreshSessions()
          setSelectedSessionId(result.session.session_id)
          setShowCreateForm(false)
          setNewSessionModel('gpt-4')
          setNewSessionTools(['playwright'])
          setNewSessionTask('')
          setNewTargetTool('playwright')
        } else {
          alert(`Failed to create session: ${result.error || 'Unknown error'}`)
        }
      } catch (error) {
        alert(`Failed to create session: ${error}`)
      } finally {
        setLoading(false)
      }
    }
  }

  // Start session
  const handleStartSession = async (sessionId: string) => {
    setLoading(true)
    try {
      const result = await startSession(sessionId)
      if (result.success) {
        await refreshSessions()
      } else {
        alert(`Failed to start session: ${result.error || 'Unknown error'}`)
      }
    } catch (error) {
      alert(`Failed to start session: ${error}`)
    } finally {
      setLoading(false)
    }
  }

  // Stop session
  const handleStopSession = async (sessionId: string) => {
    setLoading(true)
    try {
      const result = await stopSession(sessionId)
      if (result.success) {
        await refreshSessions()
      } else {
        alert(`Failed to stop session: ${result.error || 'Unknown error'}`)
      }
    } catch (error) {
      alert(`Failed to stop session: ${error}`)
    } finally {
      setLoading(false)
    }
  }

  // Delete session
  const handleDeleteSession = async (sessionId: string) => {
    const skipConfirmation = localStorage.getItem('skipDeleteConfirmation') === 'true'

    if (skipConfirmation || confirm('Are you sure you want to delete this session?')) {
      setLoading(true)
      try {
        const result = await deleteSession(sessionId)
        if (result.success) {
          // Clear selection if deleting selected session
          if (selectedSessionId === sessionId) {
            setSelectedSessionId(null)
          }
          await refreshSessions()
        } else {
          alert(`Failed to delete session: ${result.error || 'Unknown error'}`)
        }
      } catch (error) {
        alert(`Failed to delete session: ${error}`)
      } finally {
        setLoading(false)
      }
    }
  }

  // Toggle skip delete confirmation setting
  const toggleSkipDeleteConfirmation = () => {
    const newValue = !skipDeleteConfirmation
    setSkipDeleteConfirmation(newValue)
    localStorage.setItem('skipDeleteConfirmation', String(newValue))
  }

  const selectedSession = sessions.find(s => s.session_id === selectedSessionId)
  // Health-aware filter for viewer display: exclude stuck/unhealthy sessions
  const runningSessions = sessions.filter(s =>
    s.status === 'running' &&
    s.host &&
    s.port &&
    s.agent_running !== false  // Exclude explicitly dead agents
  )

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Header with session tabs and controls */}
      <div className="card">
        <div className="card-header" style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ fontSize: 16, fontWeight: 600 }}>Agent Sessions</div>
          <button
            onClick={() => setShowCreateForm(!showCreateForm)}
            className="btn btn-primary"
            disabled={loading}
          >
            + New Session
          </button>
          <button
            onClick={refreshSessions}
            className="btn btn-ghost"
            disabled={loading}
          >
            Refresh
          </button>
          <div style={{ marginLeft: 'auto' }}>
            <button
              onClick={() => setShowDevSettings(!showDevSettings)}
              className="btn btn-ghost"
              style={{ fontSize: 12 }}
            >
              {showDevSettings ? '⚙️ Hide Dev' : '⚙️ Dev'}
            </button>
          </div>
        </div>

        {/* Dev Settings Panel */}
        {showDevSettings && (
          <div className="card" style={{ margin: '8px 12px', backgroundColor: '#f5f5f5' }}>
            <div className="card-body" style={{ padding: '12px' }}>
              <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>Developer Settings</div>
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={skipDeleteConfirmation}
                  onChange={toggleSkipDeleteConfirmation}
                />
                <span>Skip delete confirmation dialogs</span>
              </label>
            </div>
          </div>
        )}

        {/* Compact status table fed by background streams */}
        {sessions.length > 0 && (
          <SessionStreamsStatus sessions={sessions.map(s => ({ id: s.session_id, name: s.name, status: s.status }))} />
        )}

        {/* Create session form - simplified with auto-generated name */}
        {showCreateForm && (
          <div className="card" style={{ margin: '8px 12px' }}>
            <div className="card-body" style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
              <input
                type="text"
                placeholder="Task (required)"
                value={newSessionTask}
                onChange={(e) => setNewSessionTask(e.target.value)}
                className="input"
                style={{ minWidth: '300px', flex: 1 }}
              />
              <select
                value={newSessionModel}
                onChange={(e) => setNewSessionModel(e.target.value)}
                className="input"
              >
                {availableModels.length > 0 ? (
                  availableModels.map((model) => (
                    <option key={model.id} value={model.id}>
                      {model.name}
                    </option>
                  ))
                ) : (
                  <>
                    <option value="openai/gpt-4o">GPT-4o</option>
                    <option value="anthropic/claude-sonnet-4.0">Claude Sonnet 4.0</option>
                    <option value="openai/gpt-4o-mini">GPT-4o Mini</option>
                    <option value="anthropic/claude-3.5-haiku">Claude 3.5 Haiku</option>
                  </>
                )}
              </select>
              <select
                value={newTargetTool}
                onChange={(e) => setNewTargetTool(e.target.value)}
                className="input"
                title={availableTools.find(t => t.name === newTargetTool)?.description || ''}
              >
                {availableTools.length > 0 ? (
                  availableTools.map((tool) => (
                    <option key={tool.name} value={tool.name} title={tool.description}>
                      {tool.name}
                    </option>
                  ))
                ) : (
                  <>
                    <option value="playwright">playwright</option>
                    <option value="github">github</option>
                    <option value="docker">docker</option>
                    <option value="desktop">desktop</option>
                    <option value="context7">context7</option>
                    <option value="redis">redis</option>
                    <option value="supabase">supabase</option>
                  </>
                )}
              </select>
              <button
                onClick={handleCreateSession}
                disabled={loading || !newSessionTask.trim()}
                className="btn btn-primary"
              >
                Create
              </button>
              <button
                onClick={() => setShowCreateForm(false)}
                className="btn btn-ghost"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Session list */}
        {sessions.length > 0 && (
          <div style={{ margin: '12px' }}>
            {sessions.map((session) => (
              <div
                key={session.session_id}
                className="card"
                style={{ marginBottom: '8px', cursor: 'pointer' }}
                onClick={() => setSelectedSessionId(session.session_id)}
              >
                <div className="card-body" style={{ padding: '12px', display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                      <div style={{ fontWeight: 'bold', fontSize: '13px' }}>{session.name}</div>
                      <span className={`badge ${
                        session.status === 'running' && session.agent_running !== false
                          ? 'badge-success'
                          : session.status === 'running' && session.agent_running === false
                          ? 'badge-warning'
                          : session.status === 'completed'
                          ? 'badge-info'
                          : 'badge-danger'
                      }`} style={{ fontSize: '10px' }}>
                        {session.status === 'running' && session.agent_running === false ? 'stuck' : session.status}
                      </span>
                      <span style={{ fontSize: '11px', color: '#666' }}>{session.model}</span>
                      <span style={{ fontSize: '11px', fontWeight: 'bold', color: '#888' }}>
                        {session.tools.join(', ')}
                      </span>
                    </div>
                    {session.task && (
                      <div style={{ fontSize: '11px', color: '#555', marginBottom: '4px' }}>
                        Task: {session.task}
                      </div>
                    )}
                    {session.last_response && (
                      <div style={{ fontSize: '11px', color: '#007bff', marginTop: '4px', padding: '4px 8px', backgroundColor: '#e7f3ff', borderRadius: '4px' }}>
                        <strong>Final Response:</strong> {session.last_response}
                      </div>
                    )}
                  </div>
                  <div style={{ display: 'flex', gap: '6px', flexShrink: 0 }}>
                    {session.status === 'running' && session.agent_running !== false && (
                      <button
                        onClick={(e) => { e.stopPropagation(); setViewerSessionId(session.session_id) }}
                        className="btn btn-primary"
                        style={{ fontSize: '11px', padding: '4px 10px' }}
                        disabled={loading}
                      >
                        View Live
                      </button>
                    )}
                    {session.status === 'running' ? (
                      <button
                        onClick={(e) => { e.stopPropagation(); handleStopSession(session.session_id) }}
                        className="btn btn-danger"
                        style={{ fontSize: '11px', padding: '4px 10px' }}
                        disabled={loading}
                      >
                        Stop
                      </button>
                    ) : (
                      <button
                        onClick={(e) => { e.stopPropagation(); handleStartSession(session.session_id) }}
                        className="btn btn-primary"
                        style={{ fontSize: '11px', padding: '4px 10px' }}
                        disabled={loading}
                      >
                        Start
                      </button>
                    )}
                    <button
                      onClick={(e) => { e.stopPropagation(); handleDeleteSession(session.session_id) }}
                      className="btn btn-ghost"
                      style={{ fontSize: '11px', padding: '4px 10px' }}
                      disabled={loading}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Session details */}
      <div style={{ flex: 1, padding: '16px', overflow: 'auto' }}>
        {selectedSession ? (
          <div>
            <h4>Session: {selectedSession.name}</h4>
            <div className="card" style={{ marginBottom: '16px', fontSize: '12px' }}>
              <div className="card-body" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <strong style={{ fontSize: '11px' }}>Status:</strong> 
                  <span className={`badge ${selectedSession.status === 'running' ? 'badge-success' : 'badge-danger'}`} style={{ fontSize: '10px' }}>
                    {selectedSession.status}
                  </span>
                </div>
                <div style={{ fontSize: '11px' }}>
                  <strong>Model:</strong> {selectedSession.model}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <strong style={{ fontSize: '11px' }}>Tool:</strong> 
                  <span style={{ 
                    padding: '1px 6px', 
                    borderRadius: '8px', 
                    fontSize: '10px',
                    backgroundColor: '#e7f3ff',
                    color: '#0066cc',
                    fontWeight: 'bold'
                  }}>
                    {selectedSession.tools.join(', ')}
                  </span>
                </div>
                {selectedSession.host && selectedSession.port && (
                  <div style={{ fontSize: '11px' }}>
                    <strong>Endpoint:</strong> {selectedSession.host}:{selectedSession.port}
                  </div>
                )}
                {selectedSession.agent_pid && (
                  <div style={{ fontSize: '11px' }}>
                    <strong>PID:</strong> {selectedSession.agent_pid}
                  </div>
                )}
                {selectedSession.task && (
                  <div style={{ fontSize: '11px' }}>
                    <strong>Task:</strong> {selectedSession.task}
                  </div>
                )}
                <div style={{ fontSize: '11px' }}>
                  <strong>Target Tool:</strong> {selectedSession.target_tool || '-'}
                </div>
                <div style={{ fontSize: '11px' }}>
                  <strong>Last Tool:</strong> {selectedSession.last_tool_executed || '-'}
                </div>
                <div style={{ fontSize: '11px' }}>
                  <strong>Duration:</strong> {typeof selectedSession.duration_ms === 'number' ? `${Math.round(selectedSession.duration_ms / 1000)}s` : '-'}
                </div>
                <div style={{ gridColumn: '1 / -1', fontSize: '11px' }}>
                  <strong>Last Response:</strong> <span title={selectedSession.last_response || ''}>{selectedSession.last_response ? `${selectedSession.last_response.slice(0, 160)}${selectedSession.last_response.length > 160 ? '…' : ''}` : '-'}</span>
                </div>
                <div style={{ gridColumn: '1 / -1', fontSize: '11px', marginTop: '2px' }}>
                  <strong>ID:</strong> 
                  <code className="card-surface" style={{ marginLeft: '6px', padding: '1px 4px', fontSize: '10px', fontFamily: 'monospace' }}>
                    {selectedSession.session_id}
                  </code>
                </div>
              </div>
            </div>

            {/* Session task info */}
            {selectedSession.task && (
              <div className="card" style={{ marginTop: '12px' }}>
                <div className="card-header">Task</div>
                <div className="card-body" style={{ fontSize: '12px' }}>
                  {selectedSession.task}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div style={{ padding: '20px', textAlign: 'center', color: '#666' }}>
            <p>No sessions available. Create a new session to get started.</p>
          </div>
        )}

        {/* Modal viewer for active sessions */}
        {viewerSessionId && (
          <SessionViewerModal
            sessionId={viewerSessionId}
            sessions={sessions}
            onClose={() => setViewerSessionId(null)}
          />
        )}
      </div>
    </div>
  )
}
// Minimal tools view: list plugins and run a delegate goal
async function runDelegate(goal: string): Promise<any> {
  const res = await fetch('/api/delegate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ goal })
  })
  try { return await res.json() } catch { return { error: 'Invalid JSON' } }
}

export function ToolsView() {
  const [plugins, setPlugins] = useState<Array<{ name: string; version: string; description?: string; commands?: string[] }>>([])
  const [goal, setGoal] = useState('')
  const [result, setResult] = useState<string>('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    getPlugins().then(r => setPlugins(r.plugins || [])).catch(() => setPlugins([]))
  }, [])

  const onRun = async () => {
    const g = goal.trim()
    if (!g) return
    setLoading(true)
    try {
      const resp = await runDelegate(g)
      setResult(typeof resp === 'string' ? resp : JSON.stringify(resp, null, 2))
    } catch (e: any) {
      setResult(`Error: ${e?.message || 'Failed to run delegate'}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h3>Tools</h3>
      <div style={{ marginBottom: 12 }}>
        <input
          value={goal}
          onChange={e => setGoal(e.target.value)}
          placeholder="Describe the task to solve"
          style={{ width: '60%', padding: 8 }}
          onKeyDown={e => { if (e.key === 'Enter') onRun() }}
        />
        <button style={{ marginLeft: 8 }} onClick={onRun} disabled={loading}>{loading ? 'Running…' : 'Run'}</button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 3fr', gap: 12 }}>
        <div style={{ border: '1px solid #ddd', borderRadius: 8, padding: 12 }}>
          <h4 style={{ marginTop: 0 }}>Available Plugins</h4>
          {plugins.length === 0 ? (
            <div style={{ color: '#666' }}>No plugins found.</div>
          ) : (
            plugins.map(p => (
              <div key={p.name} style={{ marginBottom: 8 }}>
                <strong>{p.name}</strong> <span style={{ color: '#666' }}>v{p.version}</span>
                {p.description && <div style={{ fontSize: 12 }}>{p.description}</div>}
                {p.commands && p.commands.length > 0 && (
                  <div style={{ fontSize: 12, color: '#333' }}>commands: {p.commands.join(', ')}</div>
                )}
              </div>
            ))
          )}
        </div>

        <div style={{ border: '1px solid #ddd', borderRadius: 8, padding: 12 }}>
          <h4 style={{ marginTop: 0 }}>Result</h4>
          <pre style={{ whiteSpace: 'pre-wrap' }}>{result || 'Result will appear here.'}</pre>
        </div>
      </div>
    </div>
  )
}

export function SecretsView() {
  return <SecretsManager />
}