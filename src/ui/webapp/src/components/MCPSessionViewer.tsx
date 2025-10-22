import React, { useEffect, useState, useRef } from 'react'

interface LogEntry {
  timestamp: number
  line: string
  type?: 'log' | 'agent' | 'tool' | 'error'
  agent?: string
  message?: string
}

interface MCPSessionViewerProps {
  sessionId: string
  targetTool: string
}

interface ClarificationRequest {
  question: string
  suggested_answers: string[]
  correlation_id: string
  timestamp: number
}

export function MCPSessionViewer({ sessionId, targetTool }: MCPSessionViewerProps) {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [connected, setConnected] = useState(false)
  const logsEndRef = useRef<HTMLDivElement>(null)
  const eventSourceRef = useRef<EventSource | null>(null)
  
  // User clarification state
  const [clarificationRequest, setClarificationRequest] = useState<ClarificationRequest | null>(null)
  const [userInput, setUserInput] = useState('')
  const [submittingAnswer, setSubmittingAnswer] = useState(false)
  const clarificationInputRef = useRef<HTMLInputElement>(null)

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  // Auto-focus clarification input when modal opens
  useEffect(() => {
    if (clarificationRequest && clarificationInputRef.current) {
      // Small delay to ensure modal is rendered
      setTimeout(() => {
        clarificationInputRef.current?.focus()
      }, 100)
    }
  }, [clarificationRequest])

  // Connect to agent's EventServer via proxy for Society of Mind dialogue
  useEffect(() => {
    const eventSource = new EventSource(`/mcp/${targetTool}/events`)
    eventSourceRef.current = eventSource

    eventSource.onopen = () => {
      setConnected(true)
      console.log(`[MCPViewer] Connected to ${targetTool} EventServer for session ${sessionId}`)
    }

    eventSource.onerror = (error) => {
      console.error(`[MCPViewer] Event source error:`, error)
      setConnected(false)
    }

    // Listen for agent EventServer events
    eventSource.addEventListener('message', (event) => {
      try {
        const data = JSON.parse(event.data)
        console.log('[MCPViewer] Received event:', data)

        const eventType = data.type
        const eventValue = data.value

        // Handle agent.message events (Society of Mind dialogue)
        if (eventType === 'agent.message') {
          const agent = eventValue.agent || 'Unknown'
          const role = eventValue.role || 'unknown'
          const content = eventValue.content || ''
          const icon = eventValue.icon || ''

          setLogs(prev => [...prev, {
            timestamp: Date.now(),
            line: `${icon} ${agent}: ${content}`,
            type: 'agent',
            agent,
            message: content
          }])
        }
        // Handle tool.call events
        else if (eventType === 'tool.call') {
          const tool = eventValue.tool || 'unknown'
          const icon = eventValue.icon || '🛠️'

          setLogs(prev => [...prev, {
            timestamp: Date.now(),
            line: `${icon} Tool: ${tool}`,
            type: 'tool'
          }])
        }
        // Handle user.clarification.request events (NEW)
        else if (eventType === 'user.clarification.request') {
          const question = eventValue.question || 'Bitte geben Sie die fehlenden Informationen ein:'
          const suggested_answers = eventValue.suggested_answers || []
          const correlation_id = eventValue.correlation_id || sessionId
          const timestamp = eventValue.timestamp || Date.now()

          console.log('[MCPViewer] Clarification request received:', { question, correlation_id, timestamp })

          // Force close any existing dialog first, then open new one
          setClarificationRequest(null)
          setUserInput('')

          // Use setTimeout to ensure state update completes before showing new dialog
          setTimeout(() => {
            setClarificationRequest({
              question,
              suggested_answers,
              correlation_id,
              timestamp
            })
          }, 10)

          // Add log entry
          setLogs(prev => [...prev, {
            timestamp: Date.now(),
            line: `❓ Agent fragt: ${question}`,
            type: 'agent'
          }])
        }
        // Handle user.clarification.response events (NEW)
        else if (eventType === 'user.clarification.response') {
          const answer = eventValue.answer || 'unknown'

          // Add log entry
          setLogs(prev => [...prev, {
            timestamp: Date.now(),
            line: `✅ User antwortete: ${answer}`,
            type: 'log'
          }])

          // Close dialog
          setClarificationRequest(null)
          setUserInput('')
        }
        // Handle user.clarification.timeout events (NEW)
        else if (eventType === 'user.clarification.timeout') {
          setLogs(prev => [...prev, {
            timestamp: Date.now(),
            line: `⏰ Timeout: Keine Antwort innerhalb von 60 Sekunden`,
            type: 'error'
          }])

          // Close dialog on timeout
          setClarificationRequest(null)
          setUserInput('')
        }
        // Handle user.clarification.skipped events (NEW)
        else if (eventType === 'user.clarification.skipped') {
          setLogs(prev => [...prev, {
            timestamp: Date.now(),
            line: `⏭️ User hat die Frage übersprungen`,
            type: 'log'
          }])

          // Close dialog
          setClarificationRequest(null)
          setUserInput('')
        }
        // Handle session.status events
        else if (eventType === 'session.status') {
          const status = eventValue.status || 'unknown'

          if (status === 'started') {
            setLogs(prev => [...prev, {
              timestamp: Date.now(),
              line: `🎭 Session started: ${eventValue.task || 'No task specified'}`,
              type: 'log'
            }])
          } else if (status === 'completed') {
            setLogs(prev => [...prev, {
              timestamp: Date.now(),
              line: `✅ Session completed (${eventValue.message_count || 0} messages)`,
              type: 'log'
            }])
            
            // Close EventSource to prevent resource leak
            console.log('[MCPViewer] Session completed - closing EventSource')
            if (eventSourceRef.current) {
              eventSourceRef.current.close()
              eventSourceRef.current = null
            }
            setConnected(false)
          } else if (status === 'error') {
            setLogs(prev => [...prev, {
              timestamp: Date.now(),
              line: `❌ Error: ${eventValue.error || 'Unknown error'}`,
              type: 'error'
            }])
          }
        }
        
        // Also handle session.completed event directly (sent at agent exit)
        else if (eventType === 'session.completed') {
          const status = eventValue.status || 'ok'
          
          setLogs(prev => [...prev, {
            timestamp: Date.now(),
            line: `✅ Session completed with status: ${status}`,
            type: 'log'
          }])
          
          // Close EventSource
          console.log('[MCPViewer] session.completed event - closing EventSource')
          if (eventSourceRef.current) {
            eventSourceRef.current.close()
            eventSourceRef.current = null
          }
          setConnected(false)
        }
      } catch (error) {
        console.error('[MCPViewer] Failed to parse event:', error)
      }
    })

    return () => {
      eventSource.close()
      eventSourceRef.current = null
    }
  }, [sessionId, targetTool])

  // Submit user answer to agent
  const handleSubmitAnswer = async (answer: string) => {
    if (!clarificationRequest || submittingAnswer) return

    setSubmittingAnswer(true)

    try {
      const response = await fetch(`/api/mcp/sessions/${sessionId}/clarification`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          answer,
          correlation_id: clarificationRequest.correlation_id,
          tool: targetTool
        })
      })

      if (!response.ok) {
        throw new Error(`Failed to submit answer: ${response.statusText}`)
      }

      console.log('[MCPViewer] Answer submitted successfully:', answer)

      // The response event will close the dialog
    } catch (error) {
      console.error('[MCPViewer] Failed to submit answer:', error)
      alert('Fehler beim Senden der Antwort. Bitte versuchen Sie es erneut.')
    } finally {
      setSubmittingAnswer(false)
    }
  }

  // Skip clarification question
  const handleSkipQuestion = async () => {
    if (!clarificationRequest || submittingAnswer) return

    setSubmittingAnswer(true)

    try {
      const response = await fetch(`/api/mcp/sessions/${sessionId}/clarification/skip`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          correlation_id: clarificationRequest.correlation_id,
          tool: targetTool
        })
      })

      if (!response.ok) {
        throw new Error(`Failed to skip: ${response.statusText}`)
      }

      console.log('[MCPViewer] Question skipped successfully')

      // Close dialog immediately
      setClarificationRequest(null)
      setUserInput('')
    } catch (error) {
      console.error('[MCPViewer] Failed to skip question:', error)
      alert('Fehler beim Überspringen. Bitte versuchen Sie es erneut.')
    } finally {
      setSubmittingAnswer(false)
    }
  }

  const getLogStyle = (entry: LogEntry) => {
    switch (entry.type) {
      case 'agent':
        return { color: '#3b82f6', fontWeight: 'bold' }
      case 'tool':
        return { color: '#10b981', fontFamily: 'monospace' }
      case 'error':
        return { color: '#ef4444', fontWeight: 'bold' }
      default:
        return { color: '#6b7280' }
    }
  }

  return (
    <div style={{
      border: '1px solid #ddd',
      borderRadius: '8px',
      backgroundColor: '#1e1e1e',
      color: '#d4d4d4',
      padding: '12px',
      fontFamily: 'monospace',
      fontSize: '13px',
      height: '500px',
      overflow: 'auto',
      position: 'relative'
    }}>
      <div style={{
        position: 'sticky',
        top: 0,
        backgroundColor: '#1e1e1e',
        padding: '8px 0',
        borderBottom: '1px solid #404040',
        marginBottom: '12px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <div>
          <div style={{ fontWeight: 'bold', color: '#fff', fontSize: '14px' }}>
            🎭 {targetTool.toUpperCase()} Society of Mind
          </div>
          <div style={{ fontSize: '10px', color: '#9ca3af', marginTop: '2px' }}>
            Operator + Clarification + QA Validator
          </div>
        </div>
        <div style={{
          fontSize: '11px',
          padding: '2px 8px',
          borderRadius: '4px',
          backgroundColor: connected ? '#10b981' : '#6b7280',
          color: '#fff'
        }}>
          {connected ? '● Live' : '○ Disconnected'}
        </div>
      </div>

      {logs.length === 0 ? (
        <div style={{ color: '#9ca3af', textAlign: 'center', padding: '20px' }}>
          <div style={{ fontSize: '24px', marginBottom: '8px' }}>🎭</div>
          <div>Waiting for agent dialogue...</div>
        </div>
      ) : (
        <div>
          {logs.map((entry, index) => {
            // Enhanced rendering for Society of Mind dialogue
            const isOperator = entry.line.includes('Operator:') || entry.line.includes('🔧')
            const isValidator = entry.line.includes('QAValidator:') || entry.line.includes('✓')
            const isClarification = entry.line.includes('UserClarificationAgent:') || entry.line.includes('❓')
            const isTool = entry.line.includes('🛠️') || entry.type === 'tool'
            const isHeader = entry.line.includes('='.repeat(20)) || entry.line.includes('Society of Mind')
            const isCompleted = entry.line.includes('✅')

            // Skip header lines
            if (isHeader) return null

            return (
              <div key={index} style={{
                marginBottom: '8px',
                padding: '8px 12px',
                borderLeft: isOperator ? '3px solid #3b82f6' : isValidator ? '3px solid #10b981' : isClarification ? '3px solid #f59e0b' : isTool ? '3px solid #f59e0b' : '3px solid transparent',
                backgroundColor: isOperator ? 'rgba(59, 130, 246, 0.1)' : isValidator ? 'rgba(16, 185, 129, 0.1)' : isClarification ? 'rgba(245, 158, 11, 0.1)' : isTool ? 'rgba(245, 158, 11, 0.1)' : 'transparent',
                borderRadius: '4px'
              }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                  <span style={{ color: '#6b7280', fontSize: '10px', flexShrink: 0, marginTop: '2px', fontFamily: 'monospace' }}>
                    {new Date(entry.timestamp).toLocaleTimeString()}
                  </span>
                  <div style={{ flex: 1 }}>
                    {isOperator && <span style={{ color: '#3b82f6', fontWeight: 'bold', marginRight: '8px' }}>🔧 Operator</span>}
                    {isValidator && <span style={{ color: '#10b981', fontWeight: 'bold', marginRight: '8px' }}>✓ Validator</span>}
                    {isClarification && <span style={{ color: '#f59e0b', fontWeight: 'bold', marginRight: '8px' }}>❓ Clarification</span>}
                    {isTool && <span style={{ color: '#f59e0b', fontWeight: 'bold', marginRight: '8px' }}>🛠️ Tool</span>}
                    {isCompleted && <span style={{ color: '#10b981', fontWeight: 'bold', marginRight: '8px' }}>✅</span>}
                    <span style={{
                      color: isOperator ? '#93c5fd' : isValidator ? '#6ee7b7' : isClarification ? '#fbbf24' : isTool ? '#fbbf24' : '#d4d4d4',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                      display: 'inline-block',
                      lineHeight: '1.5'
                    }}>
                      {entry.line.replace(/.*?Operator:|.*?QAValidator:|.*?UserClarificationAgent:|🛠️|✅|🔧|✓|❓/g, '').trim()}
                    </span>
                  </div>
                </div>
              </div>
            )
          })}
          <div ref={logsEndRef} />
        </div>
      )}
      
      {/* User Clarification Modal Dialog */}
      {clarificationRequest && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.7)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            backgroundColor: '#2d2d2d',
            borderRadius: '12px',
            padding: '24px',
            maxWidth: '500px',
            width: '90%',
            boxShadow: '0 10px 40px rgba(0, 0, 0, 0.5)'
          }}>
            <div style={{ marginBottom: '20px' }}>
              <div style={{ fontSize: '24px', marginBottom: '12px' }}>❓</div>
              <h3 style={{ color: '#fff', marginBottom: '8px', fontSize: '18px' }}>Agent benötigt Information</h3>
              <p style={{ color: '#d4d4d4', lineHeight: '1.6', fontSize: '14px' }}>
                {clarificationRequest.question}
              </p>
            </div>
            
            {/* Suggested Answers */}
            {clarificationRequest.suggested_answers.length > 0 && (
              <div style={{ marginBottom: '16px' }}>
                <div style={{ color: '#9ca3af', fontSize: '12px', marginBottom: '8px' }}>Vorschläge:</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                  {clarificationRequest.suggested_answers.map((suggestion, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSubmitAnswer(suggestion)}
                      disabled={submittingAnswer}
                      style={{
                        padding: '8px 16px',
                        backgroundColor: '#3b82f6',
                        color: '#fff',
                        border: 'none',
                        borderRadius: '6px',
                        cursor: submittingAnswer ? 'wait' : 'pointer',
                        fontSize: '13px',
                        fontFamily: 'monospace',
                        transition: 'background-color 0.2s'
                      }}
                      onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#2563eb'}
                      onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#3b82f6'}
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            )}
            
            {/* Custom Input */}
            <div style={{ marginBottom: '16px' }}>
              <div style={{ color: '#9ca3af', fontSize: '12px', marginBottom: '8px' }}>
                Oder eigene Antwort eingeben:
              </div>
              <input
                ref={clarificationInputRef}
                type="text"
                value={userInput}
                onChange={(e) => setUserInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && userInput.trim()) {
                    handleSubmitAnswer(userInput.trim())
                  }
                }}
                placeholder="Ihre Antwort hier..."
                disabled={submittingAnswer}
                autoFocus
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  backgroundColor: '#1e1e1e',
                  border: '1px solid #404040',
                  borderRadius: '6px',
                  color: '#d4d4d4',
                  fontSize: '14px',
                  fontFamily: 'monospace',
                  outline: 'none'
                }}
              />
            </div>
            
            {/* Action Buttons */}
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
              <button
                onClick={handleSkipQuestion}
                disabled={submittingAnswer}
                style={{
                  padding: '10px 20px',
                  backgroundColor: '#6b7280',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: submittingAnswer ? 'wait' : 'pointer',
                  fontSize: '14px',
                  fontWeight: 'bold'
                }}
                onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#4b5563'}
                onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#6b7280'}
              >
                Überspringen
              </button>
              <button
                onClick={() => handleSubmitAnswer(userInput.trim() || 'skip')}
                disabled={submittingAnswer}
                style={{
                  padding: '10px 20px',
                  backgroundColor: '#10b981',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: submittingAnswer ? 'wait' : 'pointer',
                  fontSize: '14px',
                  fontWeight: 'bold'
                }}
                onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#059669'}
                onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#10b981'}
              >
                {submittingAnswer ? 'Sende...' : 'Absenden'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
