import { useState, useRef, useEffect } from 'react'
import api from '../api/client'
import StreamingText from '../components/StreamingText'

function UserBubble({ text }) {
  return (
    <div className="flex justify-end">
      <div className="bg-blue-600 text-white rounded-2xl rounded-tr-sm px-4 py-2.5 max-w-[80%] text-sm">
        {text}
      </div>
    </div>
  )
}

function AssistantBubble({ text, streaming }) {
  return (
    <div className="flex justify-start">
      <div className="bg-[#1e2130] border border-slate-700/50 text-slate-200 rounded-2xl rounded-tl-sm px-4 py-2.5 max-w-[85%] text-sm">
        <StreamingText text={text} done={!streaming} />
      </div>
    </div>
  )
}

function ThinkingBubble() {
  return (
    <div className="flex justify-start">
      <div className="bg-[#1e2130] border border-slate-700/50 rounded-2xl rounded-tl-sm px-4 py-3">
        <span className="flex gap-1">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce"
              style={{ animationDelay: `${i * 0.15}s` }}
            />
          ))}
        </span>
      </div>
    </div>
  )
}

const SUGGESTIONS = [
  'How is the market today?',
  'Should I buy Reliance now?',
  'I bought 10 INFY shares at ₹1,400. Am I in profit?',
  'What is RSI and should I care about it?',
  'Compare TCS and Infosys',
]

export default function ChatAgent() {
  const [messages, setMessages] = useState(() => {
    try {
      const stored = sessionStorage.getItem('chat-messages')
      return stored ? JSON.parse(stored) : []
    } catch { return [] }
  })
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Persist messages to sessionStorage (exclude transient states)
  useEffect(() => {
    const toSave = messages
      .filter((m) => m.role !== 'thinking')
      .map((m) => ({ ...m, streaming: false }))
    try { sessionStorage.setItem('chat-messages', JSON.stringify(toSave)) } catch {}
  }, [messages])

  async function sendMessage(text) {
    if (!text.trim() || streaming) return
    const userMsg = { role: 'user', content: text.trim() }
    const history = messages.filter((m) => m.role !== 'thinking')
    setMessages((prev) => [...prev, userMsg, { role: 'thinking' }])
    setInput('')
    setStreaming(true)

    const baseURL = import.meta.env.VITE_API_URL || ''
    const es_history = history.map((m) => ({ role: m.role, content: m.content }))

    try {
      const response = await fetch(`${baseURL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMsg.content, history: es_history }),
      })

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let accumulated = ''

      // Replace thinking bubble with empty assistant message
      setMessages((prev) => [
        ...prev.filter((m) => m.role !== 'thinking'),
        { role: 'assistant', content: '', streaming: true },
      ])

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const chunk = decoder.decode(value)
        for (const line of chunk.split('\n')) {
          if (line.startsWith('data: ')) {
            const raw = line.slice(6)
            if (raw === '[DONE]') break
            try {
              const { text } = JSON.parse(raw)
              accumulated += text
              setMessages((prev) => {
                const copy = [...prev]
                const last = copy[copy.length - 1]
                if (last?.role === 'assistant') last.content = accumulated
                return copy
              })
            } catch {}
          }
        }
      }

      setMessages((prev) => {
        const copy = [...prev]
        const last = copy[copy.length - 1]
        if (last?.role === 'assistant') last.streaming = false
        return copy
      })
    } catch (e) {
      setMessages((prev) => [
        ...prev.filter((m) => m.role !== 'thinking'),
        { role: 'assistant', content: `⚠️ Connection error. Is the backend running?`, streaming: false },
      ])
    }

    setStreaming(false)
    inputRef.current?.focus()
  }

  function handleSubmit(e) {
    e.preventDefault()
    sendMessage(input)
  }

  return (
    <div className="flex flex-col h-[calc(100vh-120px)]">
      <h1 className="text-2xl font-bold text-white mb-4 shrink-0">Ask AI</h1>

      <div className="flex-1 overflow-y-auto space-y-3 pr-1 pb-2">
        {messages.length === 0 && (
          <div className="space-y-4 pt-4">
            <p className="text-slate-400 text-sm text-center">
              Ask anything about Indian stocks — prices, technicals, your portfolio, or the market.
            </p>
            <div className="flex flex-wrap gap-2 justify-center">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => sendMessage(s)}
                  className="bg-[#1e2130] border border-slate-700 hover:border-blue-500 text-slate-300 text-xs px-3 py-1.5 rounded-full transition"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => {
          if (m.role === 'thinking') return <ThinkingBubble key={i} />
          if (m.role === 'user') return <UserBubble key={i} text={m.content} />
          return <AssistantBubble key={i} text={m.content} streaming={m.streaming} />
        })}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={handleSubmit} className="mt-3 flex gap-2 shrink-0">
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={streaming}
          placeholder="Ask about any stock, your portfolio, or the market..."
          className="flex-1 bg-[#1e2130] border border-slate-700 rounded-xl px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 disabled:opacity-50 text-sm"
        />
        <button
          type="submit"
          disabled={!input.trim() || streaming}
          className="bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed text-white px-5 py-2.5 rounded-xl font-medium transition text-sm shrink-0"
        >
          Send
        </button>
      </form>

      <p className="text-slate-600 text-xs text-center mt-2 shrink-0">
        Educational purposes only. Not financial advice.
      </p>
    </div>
  )
}
