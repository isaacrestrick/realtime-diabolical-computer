import {
  OpenAIRealtimeWebRTC,
  RealtimeAgent,
  RealtimeSession,
  type RealtimeItem,
} from '@openai/agents/realtime'
import { type FormEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import './App.css'

type ConnectionStatus = 'disconnected' | 'connecting' | 'connected'
type CaptureScreenshotOptions = {
  triggerResponse?: boolean
  allowWhileSpeaking?: boolean
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

async function fetchEphemeralKeyFromBackend(): Promise<string> {
  const response = await fetch('/api/realtime/ephemeral-key', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  })

  let data: unknown = null
  try {
    data = await response.json()
  } catch {
    // Ignore JSON parse errors; we'll fall back to statusText.
  }

  if (!response.ok) {
    const detail =
      isRecord(data) && 'detail' in data ? data['detail'] : data
    throw new Error(
      `Backend failed to mint an ephemeral key (${response.status}): ${stringifyUnknown(detail || response.statusText)}`,
    )
  }

  const apiKey = isRecord(data) ? data['apiKey'] : null

  if (typeof apiKey !== 'string' || apiKey.length === 0) {
    throw new Error(
      `Backend response missing apiKey. Response: ${stringifyUnknown(data)}`,
    )
  }

  return apiKey
}

function stringifyUnknown(value: unknown): string {
  if (value instanceof Error) return value.message
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean' || value == null) {
    return String(value)
  }
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

function formatError(caught: unknown): string {
  const message = stringifyUnknown(caught)
  const looksLikeBackendDown =
    message.includes('Failed to fetch') ||
    message.includes('NetworkError') ||
    message.includes('Load failed')
  const looksLikeSdpParseError =
    message.includes('setRemoteDescription') ||
    message.includes('Failed to parse SessionDescription') ||
    message.includes('Expect line: v=')

  if (looksLikeBackendDown) {
    return `${message}\n\nTip: start the backend on http://localhost:8000 and ensure backend/.env contains OPENAI_API_KEY.`
  }

  if (!looksLikeSdpParseError) return message

  return `${message}\n\nTip: this usually means https://api.openai.com/v1/realtime/calls returned an error JSON (not SDP). Generate a fresh ephemeral key (ek_...) and retry. In DevTools → Network, open the /v1/realtime/calls request to see the actual error body.`
}

function getItemText(item: RealtimeItem): string {
  if (item.type === 'message') {
    const parts = item.content
      .map((content) => {
        switch (content.type) {
          case 'input_text':
          case 'output_text':
            return content.text
          case 'input_audio':
            return content.transcript ?? ''
          case 'output_audio':
            return content.transcript ?? ''
          default:
            return ''
        }
      })
      .filter(Boolean)
    return parts.join('\n').trim()
  }

  if (item.type === 'function_call') {
    return `${item.name}(${item.arguments})`
  }

  if (item.type === 'mcp_call' || item.type === 'mcp_tool_call') {
    return `${item.name}(${item.arguments})`
  }

  return ''
}

function App() {
  const [connectionStatus, setConnectionStatus] =
    useState<ConnectionStatus>('disconnected')
  const [manualMuted, setManualMuted] = useState(false)
  const [agentSpeaking, setAgentSpeaking] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [fetchingKey, setFetchingKey] = useState(false)
  const [history, setHistory] = useState<RealtimeItem[]>([])
  const [eventTypes, setEventTypes] = useState<string[]>([])
  const [textMessage, setTextMessage] = useState('')
  const [screenSharing, setScreenSharing] = useState(false)
  const [lastScreenshotAt, setLastScreenshotAt] = useState<Date | null>(null)

  const sessionRef = useRef<RealtimeSession | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const screenVideoRef = useRef<HTMLVideoElement | null>(null)
  const screenStreamRef = useRef<MediaStream | null>(null)
  const screenSharingRef = useRef(false)
  const micStreamRef = useRef<MediaStream | null>(null)
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const screenshotInFlightRef = useRef(false)
  const captureScreenshotRef = useRef<(options?: CaptureScreenshotOptions) => void>(() => {})
  const lastAutoScreenshotMsRef = useRef(0)

  const effectiveMuted = manualMuted || agentSpeaking

  const canConnect = useMemo(() => {
    return connectionStatus === 'disconnected' && !fetchingKey
  }, [connectionStatus, fetchingKey])

  const messageHistory = useMemo(() => {
    return history.filter(
      (item): item is Extract<RealtimeItem, { type: 'message' }> => item.type === 'message',
    )
  }, [history])

  const stopScreenShare = useCallback(() => {
    if (screenStreamRef.current) {
      for (const track of screenStreamRef.current.getTracks()) {
        track.stop()
      }
      screenStreamRef.current = null
    }
    if (screenVideoRef.current) {
      screenVideoRef.current.srcObject = null
    }
    setScreenSharing(false)
    screenSharingRef.current = false
  }, [])

  const stopMicrophone = useCallback(() => {
    if (micStreamRef.current) {
      for (const track of micStreamRef.current.getTracks()) {
        track.stop()
      }
      micStreamRef.current = null
    }
  }, [])

  const disconnect = useCallback(() => {
    stopScreenShare()
    stopMicrophone()

    sessionRef.current?.close()
    sessionRef.current = null

    setConnectionStatus('disconnected')
    setManualMuted(false)
    setAgentSpeaking(false)
  }, [stopMicrophone, stopScreenShare])

  const connect = useCallback(async () => {
    if (connectionStatus !== 'disconnected') return

    setError(null)
    setConnectionStatus('connecting')

    let session: RealtimeSession | null = null
    try {
      setFetchingKey(true)
      const trimmedKey = await fetchEphemeralKeyFromBackend()
      const micStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          channelCount: 1,
        },
        video: false,
      })
      micStreamRef.current = micStream
      setFetchingKey(false)

      const agent = new RealtimeAgent({
        name: 'screen-agent',
        instructions:
          'You are a helpful assistant. The user may share screenshots of their screen (a stream of images). Use the latest screenshot(s) to answer questions about what they are seeing.',
      })

      const transport = new OpenAIRealtimeWebRTC({
        audioElement: audioRef.current ?? undefined,
        mediaStream: micStream,
      })

      session = new RealtimeSession(agent, {
        transport,
        config: {
          audio: {
            input: {
              // These help avoid "assistant interrupts itself" when using speakers.
              turnDetection: {
                type: 'server_vad',
                interrupt_response: false,
                silence_duration_ms: 900,
              },
              noiseReduction: { type: 'near_field' },
            },
          },
        },
      })

      session.on('history_updated', (newHistory) => {
        setHistory([...newHistory])
      })

      session.on('transport_event', (event) => {
        setEventTypes((previous) => {
          const next = previous.length >= 200 ? previous.slice(-199) : previous
          return [...next, event.type]
        })

        if (event.type === 'input_audio_buffer.speech_started') {
          if (screenSharingRef.current) {
            const now = Date.now()
            if (now - lastAutoScreenshotMsRef.current > 2500) {
              lastAutoScreenshotMsRef.current = now
              void captureScreenshotRef.current({
                triggerResponse: false,
                allowWhileSpeaking: true,
              })
            }
          }
        }

        if (event.type === 'output_audio_buffer.started') {
          setAgentSpeaking(true)
        } else if (
          event.type === 'response.output_audio.done' ||
          event.type === 'output_audio_buffer.cleared' ||
          event.type === 'response.done'
        ) {
          setAgentSpeaking(false)
        }
      })

      session.on('error', (err) => {
        if (err?.type !== 'error') {
          setError('Unknown error')
          return
        }

        setError(formatError(err.error))
      })

      await session.connect({ apiKey: trimmedKey })

      sessionRef.current = session
      if (screenSharingRef.current) {
        void captureScreenshotRef.current({ triggerResponse: false, allowWhileSpeaking: true })
      }
      setConnectionStatus('connected')
    } catch (caught) {
      setConnectionStatus('disconnected')
      setError(formatError(caught))
      session?.close()
      sessionRef.current = null
      stopMicrophone()
      setFetchingKey(false)
    }
  }, [connectionStatus, stopMicrophone])

  useEffect(() => {
    const session = sessionRef.current
    if (!session || session.muted === null) return

    session.mute(effectiveMuted)
  }, [connectionStatus, effectiveMuted])

  const toggleMute = useCallback(() => {
    setManualMuted((value) => !value)
  }, [])

  const interrupt = useCallback(() => {
    sessionRef.current?.interrupt()
  }, [])

  const captureScreenshot = useCallback(async (options: CaptureScreenshotOptions = {}) => {
    const { triggerResponse = false, allowWhileSpeaking = false } = options

    const session = sessionRef.current
    const video = screenVideoRef.current
    if (!session || !video) return
    if (session.transport.status !== 'connected') return
    if (!screenSharingRef.current) return
    if (!allowWhileSpeaking && agentSpeaking) return
    if (screenshotInFlightRef.current) return
    if (video.videoWidth === 0 || video.videoHeight === 0) return

    screenshotInFlightRef.current = true
    try {
      const canvas =
        canvasRef.current ?? (canvasRef.current = document.createElement('canvas'))
      const ctx = canvas.getContext('2d')
      if (!ctx) return

      const maxWidth = 768
      const scale = Math.min(1, maxWidth / video.videoWidth)
      canvas.width = Math.max(1, Math.round(video.videoWidth * scale))
      canvas.height = Math.max(1, Math.round(video.videoHeight * scale))

      ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
      const dataUrl = canvas.toDataURL('image/jpeg', 0.6)
      session.addImage(dataUrl, { triggerResponse })
      setLastScreenshotAt(new Date())
    } finally {
      screenshotInFlightRef.current = false
    }
  }, [agentSpeaking])
  captureScreenshotRef.current = captureScreenshot

  const startScreenShare = useCallback(async () => {
    setError(null)
    if (screenStreamRef.current) return

    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: true,
        audio: false,
      })

      screenStreamRef.current = stream
      setScreenSharing(true)
      screenSharingRef.current = true

      const [track] = stream.getVideoTracks()
      track?.addEventListener(
        'ended',
        () => {
          stopScreenShare()
        },
        { once: true },
      )

      if (screenVideoRef.current) {
        screenVideoRef.current.srcObject = stream
        await screenVideoRef.current.play()
      }

      void captureScreenshot({ triggerResponse: false, allowWhileSpeaking: true })
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught))
    }
  }, [captureScreenshot, stopScreenShare])

  const sendText = useCallback(
    (event?: FormEvent) => {
      event?.preventDefault()

      const session = sessionRef.current
      if (!session || connectionStatus !== 'connected') return

      const trimmed = textMessage.trim()
      if (!trimmed) return

      void captureScreenshot({ triggerResponse: false, allowWhileSpeaking: true })
      session.sendMessage(trimmed)
      setTextMessage('')
    },
    [captureScreenshot, connectionStatus, textMessage],
  )

  useEffect(() => {
    return () => disconnect()
  }, [disconnect])

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>Realtime Screen Agent</h1>
          <p className="subtle">
            Connect with an ephemeral Realtime key, then share your screen so the model can see it.
          </p>
        </div>
        <div className="status">
          <span
            className={`pill pill--${connectionStatus}`}
            title="Realtime connection status"
          >
            {connectionStatus}
          </span>
        </div>
      </header>

      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}

      <section className="panel">
        <h2>Connection</h2>
        <div className="row">
          <button disabled={!canConnect} onClick={() => void connect()}>
            {fetchingKey ? 'Getting Key…' : 'Connect'}
          </button>
          <button
            disabled={connectionStatus === 'disconnected'}
            onClick={() => disconnect()}
          >
            Disconnect
          </button>
          <button
            disabled={connectionStatus !== 'connected'}
            onClick={() => toggleMute()}
          >
            {manualMuted ? 'Unmute Mic' : 'Mute Mic'}
          </button>
          <button
            disabled={connectionStatus !== 'connected'}
            onClick={() => interrupt()}
            title="Stops the agent from speaking"
          >
            Interrupt
          </button>
        </div>
        <div className="subtle">
          Mic: {effectiveMuted ? (agentSpeaking && !manualMuted ? 'auto-muted' : 'muted') : 'live'}
        </div>
        <audio ref={audioRef} autoPlay />
      </section>

      <section className="grid">
        <div className="panel">
          <h2>Screen</h2>
          <div className="row">
            <button disabled={screenSharing} onClick={() => void startScreenShare()}>
              Share Screen
            </button>
            <button disabled={!screenSharing} onClick={() => stopScreenShare()}>
              Stop Sharing
            </button>
            <button
              disabled={!screenSharing || connectionStatus !== 'connected'}
              onClick={() =>
                void captureScreenshot({ triggerResponse: true, allowWhileSpeaking: true })
              }
              title="Sends one screenshot and triggers an immediate response"
            >
              Send Screenshot
            </button>
          </div>
          <div className="subtle">
            {!screenSharing
              ? 'Not sharing.'
              : connectionStatus !== 'connected'
                ? 'Sharing preview (connect to send screenshots to the model).'
                : `Sends a screenshot when you start speaking, when you send a chat message, or when you click “Send Screenshot”${lastScreenshotAt ? ` (last: ${lastScreenshotAt.toLocaleTimeString()})` : ''}.`}
          </div>
          <div className="screenPreview">
            <video ref={screenVideoRef} autoPlay playsInline muted />
          </div>
        </div>

        <div className="panel">
          <h2>Chat</h2>
          <form className="row" onSubmit={sendText}>
            <input
              value={textMessage}
              onChange={(e) => setTextMessage(e.target.value)}
              placeholder={
                connectionStatus === 'connected'
                  ? 'Type a message…'
                  : 'Connect first…'
              }
              disabled={connectionStatus !== 'connected'}
            />
            <button type="submit" disabled={connectionStatus !== 'connected'}>
              Send
            </button>
          </form>

          <h2>Transcript</h2>
          <div className="transcript">
            {messageHistory.length === 0 ? (
              <div className="subtle">No messages yet.</div>
            ) : (
              messageHistory.map((item) => {
                const text = getItemText(item)
                if (!text) return null
                return (
                  <div key={item.itemId} className={`msg msg--${item.role}`}>
                    <div className="msgRole">{item.role}</div>
                    <pre className="msgText">{text}</pre>
                  </div>
                )
              })
            )}
          </div>
        </div>
      </section>

      <details className="panel">
        <summary>Transport events ({eventTypes.length})</summary>
        <div className="events">
          {eventTypes.length === 0 ? (
            <div className="subtle">No events yet.</div>
          ) : (
            <ul>
              {eventTypes.slice(-200).map((type, idx) => (
                <li key={`${idx}-${type}`}>{type}</li>
              ))}
            </ul>
          )}
        </div>
      </details>
    </div>
  )
}

export default App
