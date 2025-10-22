import React, { useEffect, useState } from 'react'

interface StoredSecret {
  server_name: string
  key_name: string
  created_at: string
  updated_at: string
}

// MCP server list - all available servers
const MCP_SERVERS = [
  'github',
  'supabase',
  'context7',
  'redis',
  'docker',
  'desktop',
  'kubernetes',
  'playwright',
  'puppeteer',
  'time',
  'taskmanager',
  'windows-automation',
  'travliy',
  'cloudflare'
]

export function SecretsManager() {
  const [storedSecrets, setStoredSecrets] = useState<StoredSecret[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  // Form state
  const [selectedServer, setSelectedServer] = useState<string>('github')
  const [keyName, setKeyName] = useState<string>('')
  const [secretValue, setSecretValue] = useState<string>('')
  const [submitting, setSubmitting] = useState(false)

  // Load stored secrets on mount
  useEffect(() => {
    loadSecrets()
  }, [])

  const loadSecrets = async () => {
    try {
      const response = await fetch('/api/secrets')
      const data = await response.json()

      if (data.secrets) {
        setStoredSecrets(data.secrets)
      }
      setLoading(false)
    } catch (err) {
      console.error('Failed to load secrets:', err)
      setError('Failed to load secrets')
      setLoading(false)
    }
  }

  const handleAddSecret = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!keyName.trim() || !secretValue.trim()) {
      setError('Key name and secret value are required')
      return
    }

    setSubmitting(true)
    setError(null)
    setSuccess(null)

    try {
      const response = await fetch('/api/secrets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          server_name: selectedServer,
          key_name: keyName.trim(),
          value: secretValue
        })
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || 'Failed to save secret')
      }

      // Update stored secrets list
      if (data.secrets) {
        setStoredSecrets(data.secrets)
      }

      // Reset form
      setKeyName('')
      setSecretValue('')
      setSuccess(`Secret ${keyName} added successfully!`)
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save secret')
    } finally {
      setSubmitting(false)
    }
  }

  // Group secrets by server
  const secretsByServer: { [key: string]: StoredSecret[] } = {}
  storedSecrets.forEach(secret => {
    if (!secretsByServer[secret.server_name]) {
      secretsByServer[secret.server_name] = []
    }
    secretsByServer[secret.server_name].push(secret)
  })

  return (
    <div style={{ padding: '20px', maxWidth: '900px', margin: '0 auto' }}>
      <h2 style={{ marginBottom: '10px' }}>Encrypted Secrets Manager</h2>
      <p style={{ color: '#6b7280', marginBottom: '20px', fontSize: '14px' }}>
        Configure API keys and credentials for MCP servers. All secrets are encrypted using AES-256-GCM
        and stored in SQLite database at <code>data/secrets.db</code>.
      </p>

      {/* Add Secret Form */}
      <div style={{
        backgroundColor: '#f9fafb',
        padding: '20px',
        borderRadius: '8px',
        border: '1px solid #e5e7eb',
        marginBottom: '30px'
      }}>
        <h3 style={{ marginTop: '0', marginBottom: '16px', fontSize: '16px' }}>
          Add New Secret
        </h3>

        <form onSubmit={handleAddSecret}>
          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', marginBottom: '6px', fontWeight: '500', fontSize: '14px' }}>
              MCP Server:
            </label>
            <select
              value={selectedServer}
              onChange={(e) => setSelectedServer(e.target.value)}
              style={{
                width: '100%',
                padding: '8px 12px',
                borderRadius: '6px',
                border: '1px solid #d1d5db',
                fontSize: '14px'
              }}
            >
              {MCP_SERVERS.map(server => (
                <option key={server} value={server}>
                  {server}
                </option>
              ))}
            </select>
          </div>

          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', marginBottom: '6px', fontWeight: '500', fontSize: '14px' }}>
              Key Name: <span style={{ color: '#ef4444' }}>*</span>
            </label>
            <input
              type="text"
              value={keyName}
              onChange={(e) => setKeyName(e.target.value)}
              placeholder="e.g., GITHUB_PERSONAL_ACCESS_TOKEN"
              style={{
                width: '100%',
                padding: '8px 12px',
                borderRadius: '6px',
                border: '1px solid #d1d5db',
                fontSize: '14px',
                fontFamily: 'monospace'
              }}
            />
            <p style={{ fontSize: '12px', color: '#6b7280', marginTop: '4px', marginBottom: '0' }}>
              The environment variable name (e.g., API_KEY, ACCESS_TOKEN)
            </p>
          </div>

          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', marginBottom: '6px', fontWeight: '500', fontSize: '14px' }}>
              Secret Value: <span style={{ color: '#ef4444' }}>*</span>
            </label>
            <input
              type="password"
              value={secretValue}
              onChange={(e) => setSecretValue(e.target.value)}
              placeholder="Enter secret value..."
              style={{
                width: '100%',
                padding: '8px 12px',
                borderRadius: '6px',
                border: '1px solid #d1d5db',
                fontSize: '14px',
                fontFamily: 'monospace'
              }}
            />
            <p style={{ fontSize: '12px', color: '#6b7280', marginTop: '4px', marginBottom: '0' }}>
              The secret value will be encrypted with AES-256-GCM
            </p>
          </div>

          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <button
              type="submit"
              disabled={submitting}
              style={{
                padding: '10px 20px',
                backgroundColor: submitting ? '#9ca3af' : '#3b82f6',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                fontWeight: '500',
                cursor: submitting ? 'not-allowed' : 'pointer',
                fontSize: '14px'
              }}
            >
              {submitting ? 'Saving...' : 'Add Secret'}
            </button>

            {success && (
              <span style={{ color: '#10b981', fontSize: '14px' }}>
                {success}
              </span>
            )}

            {error && (
              <span style={{ color: '#ef4444', fontSize: '14px' }}>
                {error}
              </span>
            )}
          </div>
        </form>
      </div>

      {/* Stored Secrets List */}
      <div>
        <h3 style={{ marginTop: '0', marginBottom: '16px', fontSize: '16px' }}>
          Stored Secrets
        </h3>

        {loading ? (
          <p style={{ color: '#6b7280', fontSize: '14px' }}>Loading...</p>
        ) : storedSecrets.length === 0 ? (
          <p style={{ color: '#6b7280', fontSize: '14px' }}>
            No secrets stored yet. Add your first secret using the form above.
          </p>
        ) : (
          <div style={{ display: 'grid', gap: '16px' }}>
            {Object.keys(secretsByServer).sort().map(serverName => (
              <div
                key={serverName}
                style={{
                  backgroundColor: '#ffffff',
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px',
                  padding: '16px'
                }}
              >
                <h4 style={{ margin: '0 0 12px 0', fontSize: '15px', fontWeight: '600' }}>
                  {serverName}
                </h4>

                <div style={{ display: 'grid', gap: '8px' }}>
                  {secretsByServer[serverName].map(secret => (
                    <div
                      key={`${secret.server_name}-${secret.key_name}`}
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        padding: '8px 12px',
                        backgroundColor: '#f9fafb',
                        borderRadius: '4px',
                        fontSize: '14px'
                      }}
                    >
                      <div>
                        <code style={{ fontWeight: '500' }}>{secret.key_name}</code>
                        <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '2px' }}>
                          Updated: {new Date(secret.updated_at).toLocaleString()}
                        </div>
                      </div>
                      <span style={{
                        padding: '4px 8px',
                        backgroundColor: '#dcfce7',
                        color: '#166534',
                        borderRadius: '4px',
                        fontSize: '12px',
                        fontWeight: '500'
                      }}>
                        Encrypted
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Security notice */}
      <div style={{
        marginTop: '30px',
        padding: '12px',
        backgroundColor: '#dbeafe',
        border: '1px solid #93c5fd',
        borderRadius: '6px',
        fontSize: '13px'
      }}>
        <strong>Security Features:</strong>
        <ul style={{ margin: '8px 0 0 0', paddingLeft: '20px' }}>
          <li>All secrets encrypted with AES-256-GCM</li>
          <li>Machine-specific encryption keys (PBKDF2 with 100k iterations)</li>
          <li>Secrets stored in SQLite at <code>data/secrets.db</code></li>
          <li>Audit trail for all secret operations</li>
        </ul>
      </div>
    </div>
  )
}
