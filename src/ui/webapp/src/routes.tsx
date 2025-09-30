import React, { useEffect, useState, useRef } from 'react'
import { Outlet, Link } from '@tanstack/react-router'

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
async function getSessions(): Promise<{ sessions: Array<{ session_id: string; name: string; model: string; tools: string[]; status: string; host?: string; port?: number; agent_pid?: number }> }> {
  const res = await fetch('/api/sessions')
  return await res.json()
}

async function createSession(sessionData: { name: string; model: string; tools: string[] }): Promise<{ success: boolean; session?: any; error?: string }> {
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
export function RootLayout() {
  return (
    <div style={{ fontFamily: 'sans-serif' }}>
      <nav style={{ display: 'flex', gap: 12, padding: 12, borderBottom: '1px solid #ddd' }}>
        <Link to="/" activeOptions={{ exact: true }}>Chat</Link>
        <Link to="/sessions">Sessions</Link>
        <Link to="/tools">Tools</Link>
      </nav>
      <div style={{ padding: 16 }}>
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

  const append = (m: { role: 'user' | 'assistant'; text: string }) => {
    setMessages(prev => {
      const next = [...prev, m]
      try { localStorage.setItem('chat_history', JSON.stringify(next)) } catch {}
      return next
    })
  }

  const onSend = async () => {
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
  }

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
  loading?: boolean  // Frontend-only state
  iframeKey?: number  // Frontend-only state for iframe refresh
}

export function PlaywrightView() {
  // Multi-session state management - now using backend sessions
  const [sessions, setSessions] = useState<PlaywrightSession[]>([])
  const [loading, setLoading] = useState(false)

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
    if (confirm('Are you sure you want to delete this session?')) {
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

  // Polling for all sessions - refresh from backend periodically
  useEffect(() => {
    const pollInterval = setInterval(() => {
      refreshSessions()
    }, 3000)  // Increased to 3 seconds to reduce load
    
    return () => clearInterval(pollInterval)
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
  const [sessions, setSessions] = useState<Array<{ session_id: string; name: string; model: string; tools: string[]; status: string; host?: string; port?: number; agent_pid?: number }>>([])
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [newSessionName, setNewSessionName] = useState('')
  const [newSessionModel, setNewSessionModel] = useState('gpt-4')
  const [newSessionTools, setNewSessionTools] = useState(['playwright'])
  const viewerRef = useRef<HTMLIFrameElement | null>(null)

  // Refresh sessions from API
  const refreshSessions = async () => {
    try {
      const result = await getSessions()
      setSessions(result.sessions || [])
      // Auto-select first session if none selected
      if (!selectedSessionId && result.sessions.length > 0) {
        setSelectedSessionId(result.sessions[0].session_id)
      }
    } catch (error) {
      console.error('Failed to refresh sessions:', error)
    }
  }

  // Auto-refresh sessions every 3 seconds
  useEffect(() => {
    refreshSessions()
    const interval = setInterval(refreshSessions, 3000)
    return () => clearInterval(interval)
  }, [])

  // When switching session tabs, bring the live viewer into focus
  useEffect(() => {
    const el = viewerRef.current
    if (el) {
      try {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' })
        el.focus()
      } catch {}
    }
  }, [selectedSessionId])

  // Create new session
  const handleCreateSession = async () => {
    if (newSessionName.trim()) {
      setLoading(true)
      try {
        const result = await createSession({
          name: newSessionName.trim(),
          model: newSessionModel,
          tools: newSessionTools
        })
        if (result.success && result.session) {
          await refreshSessions()
          setSelectedSessionId(result.session.session_id)
          setShowCreateForm(false)
          setNewSessionName('')
          setNewSessionModel('gpt-4')
          setNewSessionTools(['playwright'])
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
    if (confirm('Are you sure you want to delete this session?')) {
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

  const selectedSession = sessions.find(s => s.session_id === selectedSessionId)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Header with session tabs and controls */}
      <div style={{ borderBottom: '1px solid #ddd', padding: '8px 16px', backgroundColor: '#f8f9fa' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
          <h3 style={{ margin: 0, fontSize: '16px' }}>Agent Sessions</h3>
          <button 
            onClick={() => setShowCreateForm(!showCreateForm)} 
            style={{ padding: '4px 8px', fontSize: '12px' }}
            disabled={loading}
          >
            + New Session
          </button>
          <button 
            onClick={refreshSessions} 
            style={{ padding: '4px 8px', fontSize: '12px' }}
            disabled={loading}
          >
            Refresh
          </button>
        </div>

        {/* Create session form */}
        {showCreateForm && (
          <div style={{ padding: '12px', border: '1px solid #ddd', borderRadius: '4px', backgroundColor: 'white', marginBottom: '8px' }}>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
              <input
                type="text"
                placeholder="Session name"
                value={newSessionName}
                onChange={(e) => setNewSessionName(e.target.value)}
                style={{ padding: '4px 8px', minWidth: '120px' }}
              />
              <select
                value={newSessionModel}
                onChange={(e) => setNewSessionModel(e.target.value)}
                style={{ padding: '4px 8px' }}
              >
                <option value="gpt-4">GPT-4</option>
                <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                <option value="claude-3">Claude 3</option>
              </select>
              <button
                onClick={handleCreateSession}
                disabled={loading || !newSessionName.trim()}
                style={{ padding: '4px 12px' }}
              >
                Create
              </button>
              <button
                onClick={() => setShowCreateForm(false)}
                style={{ padding: '4px 8px' }}
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Session tabs */}
        <div style={{ display: 'flex', gap: '2px', overflowX: 'auto' }}>
          {sessions.map((session) => (
            <div
              key={session.session_id}
              style={{
                display: 'flex',
                alignItems: 'center',
                padding: '4px 8px',
                border: '1px solid #ddd',
                borderRadius: '4px 4px 0 0',
                backgroundColor: selectedSessionId === session.session_id ? 'white' : '#f0f0f0',
                cursor: 'pointer',
                minWidth: '100px',
                fontSize: '11px'
              }}
              onClick={() => setSelectedSessionId(session.session_id)}
            >
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 'bold', marginBottom: '1px', fontSize: '11px' }}>{session.name}</div>
                <div style={{ color: '#666', fontSize: '9px', lineHeight: '1.2' }}>
                  <span style={{ 
                    padding: '1px 3px', 
                    borderRadius: '6px', 
                    backgroundColor: session.status === 'running' ? '#d4edda' : '#f8d7da',
                    color: session.status === 'running' ? '#155724' : '#721c24'
                  }}>
                    {session.status}
                  </span>
                  <span style={{ margin: '0 2px' }}>•</span>
                  <span>{session.model.replace('gpt-', '').replace('-turbo', '')}</span>
                </div>
                <div style={{ color: '#0066cc', fontSize: '9px', fontWeight: 'bold' }}>
                  {session.tools.join(', ')}
                </div>
              </div>
              <div style={{ display: 'flex', gap: '1px', marginLeft: '4px' }}>
                {session.status === 'running' ? (
                  <button
                    onClick={(e) => { e.stopPropagation(); handleStopSession(session.session_id) }}
                    style={{ padding: '2px 4px', fontSize: '10px' }}
                    disabled={loading}
                  >
                    Stop
                  </button>
                ) : (
                  <button
                    onClick={(e) => { e.stopPropagation(); handleStartSession(session.session_id) }}
                    style={{ padding: '2px 4px', fontSize: '10px' }}
                    disabled={loading}
                  >
                    Start
                  </button>
                )}
                <button
                  onClick={(e) => { e.stopPropagation(); handleDeleteSession(session.session_id) }}
                  style={{ padding: '2px 4px', fontSize: '10px', color: 'red' }}
                  disabled={loading}
                >
                  ×
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Session details and iframe */}
      <div style={{ flex: 1, padding: '16px' }}>
        {selectedSession ? (
          <div>
            <h4>Session: {selectedSession.name}</h4>
            <div style={{ 
              marginBottom: '16px', 
              padding: '8px', 
              backgroundColor: '#f8f9fa', 
              border: '1px solid #dee2e6', 
              borderRadius: '4px',
              fontSize: '12px'
            }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <strong style={{ fontSize: '11px' }}>Status:</strong> 
                  <span style={{ 
                    padding: '1px 6px', 
                    borderRadius: '8px', 
                    fontSize: '10px',
                    backgroundColor: selectedSession.status === 'running' ? '#d4edda' : '#f8d7da',
                    color: selectedSession.status === 'running' ? '#155724' : '#721c24'
                  }}>
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
                <div style={{ gridColumn: '1 / -1', fontSize: '11px', marginTop: '2px' }}>
                  <strong>ID:</strong> 
                  <code style={{ 
                    marginLeft: '6px', 
                    padding: '1px 4px', 
                    backgroundColor: '#f1f3f4', 
                    borderRadius: '3px',
                    fontSize: '10px',
                    fontFamily: 'monospace'
                  }}>
                    {selectedSession.session_id}
                  </code>
                </div>
              </div>
            </div>

            {/* Iframe for running sessions */}
            {selectedSession.status === 'running' && selectedSession.host && selectedSession.port && (
              <div>
                <h5>Playwright Viewer</h5>
                <iframe
                  ref={viewerRef}
                  tabIndex={-1}
                  title={`Playwright Viewer - ${selectedSession.name}`}
                  src={`/mcp/playwright/session/${selectedSession.session_id}/`}
                  style={{ width: '100%', height: '480px', border: '1px solid #ccc' }}
                />
              </div>
            )}

            {/* Message for stopped sessions */}
            {selectedSession.status !== 'running' && (
              <div style={{ padding: '20px', textAlign: 'center', color: '#666' }}>
                <p>Session is not running. Start the session to view the Playwright interface.</p>
              </div>
            )}
          </div>
        ) : (
          <div style={{ padding: '20px', textAlign: 'center', color: '#666' }}>
            <p>No sessions available. Create a new session to get started.</p>
          </div>
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