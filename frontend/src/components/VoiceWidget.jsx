import React, { useState, useEffect, useRef } from 'react'

export function VoiceWidget({ onCatalogSearch, onOrderPlaced, wsUrl }) {
  const [visualState, setVisualState] = useState('idle') // 'idle' | 'listening' | 'processing' | 'speaking'
  const [isConnected, setIsConnected] = useState(false)
  const [isExpanded, setIsExpanded] = useState(false)
  const [logs, setLogs] = useState([])
  const [recentOrder, setRecentOrder] = useState(null)

  const wsRef = useRef(null)
  const captureAudioCtxRef = useRef(null)
  const playbackAudioCtxRef = useRef(null)
  const mediaStreamRef = useRef(null)
  const scriptProcessorRef = useRef(null)
  const nextPlayTimeRef = useRef(0)
  const activePlaybackSourcesRef = useRef(0)

  const targetWsUrl = wsUrl || `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/voice`

  const addLog = (msg) => {
    setLogs((prev) => [...prev.slice(-9), `[${new Date().toLocaleTimeString()}] ${msg}`])
  }

  const toggleConnection = () => {
    if (isConnected) {
      disconnectVoice()
    } else {
      connectVoice()
    }
  }

  const connectVoice = () => {
    try {
      addLog('Connecting to voice assistant...')
      const ws = new WebSocket(targetWsUrl)
      ws.binaryType = 'arraybuffer'

      ws.onopen = () => {
        setIsConnected(true)
        addLog('Connected to Voice Concierge WebSocket')
        startMicrophoneCapture(ws)
      }

      ws.onmessage = async (event) => {
        if (typeof event.data === 'string') {
          try {
            const data = JSON.parse(event.data)
            if (data.type === 'catalog_search') {
              setVisualState('processing')
              addLog(`Catalog search: "${data.query || ''}" (${data.items?.length || 0} items)`)
              if (onCatalogSearch) onCatalogSearch(data)
              setTimeout(() => {
                if (activePlaybackSourcesRef.current === 0) {
                  setVisualState('listening')
                }
              }, 1200)
            } else if (data.type === 'order_placed') {
              setVisualState('processing')
              const o = data.order || {}
              addLog(`Order Placed: #${o.order_id || o.id || 'N/A'} - ${o.product_title || 'Item'}`)
              setRecentOrder(o)
              if (onOrderPlaced) onOrderPlaced(data)
              setTimeout(() => {
                if (activePlaybackSourcesRef.current === 0) {
                  setVisualState('listening')
                }
              }, 1500)
            }
          } catch (e) {
            console.error('Error parsing WS JSON message:', e)
          }
        } else if (event.data instanceof ArrayBuffer) {
          playIncomingPcmAudio(event.data)
        }
      }

      ws.onerror = (err) => {
        console.error('WebSocket Error:', err)
        addLog('WebSocket connection error')
      }

      ws.onclose = () => {
        addLog('Disconnected from Voice Concierge')
        disconnectVoice()
      }

      wsRef.current = ws
    } catch (e) {
      console.error('Failed to initiate WS connection:', e)
      addLog(`Connection failed: ${e.message}`)
    }
  }

  const disconnectVoice = () => {
    stopMicrophoneCapture()
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setIsConnected(false)
    setVisualState('idle')
  }

  const startMicrophoneCapture = async (ws) => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          channelCount: 1,
        }
      })
      mediaStreamRef.current = stream

      const audioCtx = new (window.AudioContext || window.webkitAudioContext)()
      captureAudioCtxRef.current = audioCtx
      const sampleRate = audioCtx.sampleRate

      const source = audioCtx.createMediaStreamSource(stream)
      const processor = audioCtx.createScriptProcessor(4096, 1, 1)
      scriptProcessorRef.current = processor

      processor.onaudioprocess = (e) => {
        if (!ws || ws.readyState !== WebSocket.OPEN) return

        const inputBuffer = e.inputBuffer.getChannelData(0)
        const targetSampleRate = 16000
        const ratio = sampleRate / targetSampleRate
        const newLength = Math.floor(inputBuffer.length / ratio)
        const resampled = new Float32Array(newLength)

        for (let i = 0; i < newLength; i++) {
          const originIdx = i * ratio
          const idx = Math.floor(originIdx)
          const frac = originIdx - idx
          const nextIdx = Math.min(idx + 1, inputBuffer.length - 1)
          resampled[i] = inputBuffer[idx] * (1 - frac) + inputBuffer[nextIdx] * frac
        }

        const pcm16 = new Int16Array(resampled.length)
        let isSpeakingSignal = false
        for (let i = 0; i < resampled.length; i++) {
          const s = Math.max(-1, Math.min(1, resampled[i]))
          if (Math.abs(s) > 0.05) isSpeakingSignal = true
          pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF
        }

        if (activePlaybackSourcesRef.current === 0) {
          setVisualState(isSpeakingSignal ? 'listening' : 'listening')
        }

        ws.send(pcm16.buffer)
      }

      const muteNode = audioCtx.createGain()
      muteNode.gain.value = 0
      source.connect(processor)
      processor.connect(muteNode)
      muteNode.connect(audioCtx.destination)
      setVisualState('listening')
    } catch (e) {
      console.error('Microphone Access Error:', e)
      addLog(`Mic Error: ${e.message}`)
      setVisualState('idle')
    }
  }

  const stopMicrophoneCapture = () => {
    if (scriptProcessorRef.current) {
      scriptProcessorRef.current.disconnect()
      scriptProcessorRef.current = null
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop())
      mediaStreamRef.current = null
    }
    if (captureAudioCtxRef.current) {
      captureAudioCtxRef.current.close()
      captureAudioCtxRef.current = null
    }
  }

  const playIncomingPcmAudio = (arrayBuffer) => {
    try {
      if (!playbackAudioCtxRef.current || playbackAudioCtxRef.current.state === 'closed') {
        playbackAudioCtxRef.current = new (window.AudioContext || window.webkitAudioContext)()
      }
      const playbackCtx = playbackAudioCtxRef.current

      if (playbackCtx.state === 'suspended') {
        playbackCtx.resume()
      }

      const int16Array = new Int16Array(arrayBuffer)
      if (int16Array.length === 0) return

      const float32Array = new Float32Array(int16Array.length)
      for (let i = 0; i < int16Array.length; i++) {
        float32Array[i] = int16Array[i] / 32768.0
      }

      // Gemini Live native audio is 24000 Hz PCM
      const audioBuffer = playbackCtx.createBuffer(1, float32Array.length, 24000)
      audioBuffer.getChannelData(0).set(float32Array)

      const source = playbackCtx.createBufferSource()
      source.buffer = audioBuffer
      source.connect(playbackCtx.destination)

      const now = playbackCtx.currentTime
      const startTime = Math.max(now, nextPlayTimeRef.current)
      source.start(startTime)
      nextPlayTimeRef.current = startTime + audioBuffer.duration

      activePlaybackSourcesRef.current += 1
      setVisualState('speaking')

      source.onended = () => {
        activePlaybackSourcesRef.current = Math.max(0, activePlaybackSourcesRef.current - 1)
        if (activePlaybackSourcesRef.current === 0) {
          setVisualState(isConnected ? 'listening' : 'idle')
        }
      }
    } catch (e) {
      console.error('Audio Playback Error:', e)
    }
  }

  useEffect(() => {
    return () => {
      disconnectVoice()
      if (playbackAudioCtxRef.current) {
        playbackAudioCtxRef.current.close()
      }
    }
  }, [])

  const getStateMeta = () => {
    switch (visualState) {
      case 'listening':
        return { label: 'Listening...', color: '#ef4444', class: 'state-listening' }
      case 'processing':
        return { label: 'Processing...', color: '#f59e0b', class: 'state-processing' }
      case 'speaking':
        return { label: 'Speaking...', color: '#3b82f6', class: 'state-speaking' }
      case 'idle':
      default:
        return { label: isConnected ? 'Active' : 'Offline', color: '#6b7280', class: 'state-idle' }
    }
  }

  const meta = getStateMeta()

  return (
    <div className="voice-widget-floating">
      {isExpanded && (
        <div className="voice-widget-card">
          <div className="voice-widget-header">
            <div className="voice-widget-title-group">
              <span className="voice-widget-dot" style={{ backgroundColor: meta.color }} />
              <h4 className="voice-widget-title">Voice Concierge</h4>
            </div>
            <button className="voice-widget-close-btn" onClick={() => setIsExpanded(false)}>
              &times;
            </button>
          </div>

          <div className="voice-widget-status-banner">
            <span className={`status-badge ${meta.class}`}>{meta.label}</span>
            <span className="status-ws-info">{isConnected ? 'WS Connected' : 'WS Disconnected'}</span>
          </div>

          {recentOrder && (
            <div className="voice-widget-order-toast">
              <strong>Order Confirmed!</strong>
              <p>#{recentOrder.order_id || recentOrder.id}: {recentOrder.product_title || 'Product'}</p>
              <p>Total: ${recentOrder.total_price || recentOrder.unit_price}</p>
            </div>
          )}

          <div className="voice-widget-logs">
            {logs.length === 0 ? (
              <p className="logs-empty">Click start to speak with assistant.</p>
            ) : (
              logs.map((log, idx) => <div key={idx} className="log-line">{log}</div>)
            )}
          </div>

          <div className="voice-widget-actions">
            <button
              className={`voice-toggle-btn ${isConnected ? 'btn-active' : 'btn-primary'}`}
              onClick={toggleConnection}
            >
              {isConnected ? 'Stop Assistant' : 'Start Voice Assistant'}
            </button>
          </div>
        </div>
      )}

      <button
        className={`voice-widget-fab ${meta.class} ${isConnected ? 'fab-active' : ''}`}
        onClick={() => setIsExpanded(!isExpanded)}
        title="Toggle Voice Concierge"
      >
        <svg className="mic-icon" viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
          <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" />
          <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
        </svg>
      </button>
    </div>
  )
}

export default VoiceWidget
