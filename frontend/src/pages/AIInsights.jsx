import { useState, useRef, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import api from '../api/client'
import { useSSE } from '../hooks/useSSE'
import StreamingText from '../components/StreamingText'
import LoadingSpinner from '../components/LoadingSpinner'
import { useSessionState } from '../hooks/useSessionState'

function SymbolSearch({ onSelect }) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  const { data: results } = useQuery({
    queryKey: ['symbol-search', query],
    queryFn: () => api.get(`/api/stocks/search?q=${query}&limit=6`).then((r) => r.data),
    enabled: query.length >= 2,
    staleTime: 30_000,
  })

  useEffect(() => {
    function handleClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  function handleSelect(item) {
    setQuery(item.company + ' (' + item.symbol + ')')
    setOpen(false)
    onSelect(item.symbol)
  }

  return (
    <div ref={ref} className="relative flex-1">
      <input
        value={query}
        onChange={(e) => { setQuery(e.target.value); setOpen(true) }}
        onFocus={() => setOpen(true)}
        placeholder="Search by company name or symbol e.g. Infosys, INFY.NS"
        className="w-full bg-[#12141e] border border-slate-700 rounded-lg px-4 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
      />
      {open && results?.length > 0 && (
        <ul className="absolute z-10 w-full mt-1 bg-[#1e2130] border border-slate-700 rounded-lg shadow-xl overflow-hidden">
          {results.map((item) => (
            <li
              key={item.symbol}
              onMouseDown={() => handleSelect(item)}
              className="px-4 py-2.5 cursor-pointer hover:bg-slate-700 flex justify-between items-center"
            >
              <span className="text-white text-sm">{item.company}</span>
              <span className="text-slate-400 text-xs font-mono">{item.symbol}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default function AIInsights() {
  const [savedAnalysis, setSavedAnalysis] = useSessionState('ai-insights-analysis', null)
  const [activeSymbol, setActiveSymbol] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [selectedSymbol, setSelectedSymbol] = useState('')

  const { text, done, error } = useSSE(
    activeSymbol ? `/api/ai/insight/${activeSymbol}` : null,
    streaming,
  )

  // When streaming finishes, save to session
  useEffect(() => {
    if (done && text && activeSymbol) {
      setSavedAnalysis({ symbol: activeSymbol, text })
    }
  }, [done])

  const isActive = streaming || done
  const displaySymbol = isActive ? activeSymbol : savedAnalysis?.symbol
  const displayText = isActive ? text : savedAnalysis?.text
  const showResult = isActive ? (!!text || !!error) : !!savedAnalysis

  function handleAnalyse() {
    if (!selectedSymbol) return
    setSavedAnalysis(null)
    setActiveSymbol(selectedSymbol)
    setStreaming(true)
  }

  function handleReset() {
    setSavedAnalysis(null)
    setActiveSymbol('')
    setSelectedSymbol('')
    setStreaming(false)
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">AI Insights</h1>

      <div className="bg-[#1e2130] rounded-xl p-5 border border-slate-700/50">
        <p className="text-slate-400 text-sm mb-4">
          Search for a company to get an AI-powered analysis including sentiment, key risks, and simple advice.
          Note: this runs price predictions first (~60s) before streaming the analysis.
        </p>

        <div className="flex gap-2">
          <SymbolSearch onSelect={setSelectedSymbol} />
          {(!streaming) ? (
            <button
              onClick={handleAnalyse}
              disabled={!selectedSymbol}
              className="bg-purple-600 hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed text-white px-5 py-2 rounded-lg font-medium transition shrink-0"
            >
              Analyse
            </button>
          ) : (
            <button
              onClick={handleReset}
              className="bg-slate-700 hover:bg-slate-600 text-white px-5 py-2 rounded-lg font-medium transition shrink-0"
            >
              Cancel
            </button>
          )}
        </div>
      </div>

      {streaming && !text && !error && (
        <LoadingSpinner text="Running predictions (this takes ~60s)..." />
      )}

      {error && (
        <div className="bg-red-900/30 border border-red-700 rounded-xl p-4 text-red-300 text-sm">
          {error}
        </div>
      )}

      {showResult && displayText && (
        <div className="bg-[#1e2130] rounded-xl p-6 border border-slate-700/50">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-white">{displaySymbol} — AI Analysis</h2>
            <button onClick={handleReset} className="text-slate-400 hover:text-white text-xs underline">
              Analyse another
            </button>
          </div>
          <StreamingText text={displayText} done={!streaming} />
        </div>
      )}

      <div className="bg-yellow-900/20 border border-yellow-700/50 rounded-xl p-4 text-yellow-200/70 text-xs">
        ⚠️ This analysis is for educational purposes only and does not constitute financial advice.
        Always do your own research before investing.
      </div>
    </div>
  )
}
