import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import api from '../api/client'
import { useSSE } from '../hooks/useSSE'
import StockChart from '../components/StockChart'
import SignalBadge from '../components/SignalBadge'
import StreamingText from '../components/StreamingText'
import LoadingSpinner from '../components/LoadingSpinner'
import SymbolSearch from '../components/SymbolSearch'
import { useSessionState } from '../hooks/useSessionState'

const PERIODS = { '1M': 30, '3M': 90, '6M': 180, '1Y': 365, '2Y': 730 }

const FUND_COLOR = {
  green:  { value: 'text-green-400',  badge: 'bg-green-900/50 text-green-300 border border-green-700' },
  yellow: { value: 'text-yellow-400', badge: 'bg-yellow-900/50 text-yellow-300 border border-yellow-700' },
  red:    { value: 'text-red-400',    badge: 'bg-red-900/50 text-red-300 border border-red-700' },
  gray:   { value: 'text-slate-400',  badge: 'bg-slate-800 text-slate-400 border border-slate-600' },
}

function FundamentalCard({ title, metric }) {
  if (!metric) {
    return (
      <div className="bg-[#161827] rounded-xl p-4 border border-slate-700/50 animate-pulse">
        <p className="text-slate-500 text-xs mb-2">{title}</p>
        <div className="h-6 bg-slate-700 rounded w-16 mb-2" />
        <div className="h-4 bg-slate-800 rounded w-24" />
      </div>
    )
  }
  const colors = FUND_COLOR[metric.color] || FUND_COLOR.gray
  const displayValue = metric.value !== null ? metric.value + metric.unit : 'N/A'
  return (
    <div className="bg-[#161827] rounded-xl p-4 border border-slate-700/50">
      <p className="text-slate-500 text-xs mb-1">{title}</p>
      <p className={`text-xl font-bold ${colors.value}`}>{displayValue}</p>
      <span className={`text-xs px-2 py-0.5 rounded mt-1 inline-block ${colors.badge}`}>
        {metric.label}
      </span>
    </div>
  )
}

export default function StockAnalysis() {
  const [symbol, setSymbol] = useSessionState('sa-symbol', '')
  const [days, setDays] = useSessionState('sa-days', 365)
  const [tab, setTab] = useSessionState('sa-tab', 'chart')
  const [savedAnalysis, setSavedAnalysis] = useSessionState('sa-analysis', null)

  const [activeSymbol, setActiveSymbol] = useState('')
  const [streaming, setStreaming] = useState(false)

  const { text, done, error: sseError } = useSSE(
    activeSymbol ? `/api/ai/insight/${activeSymbol}` : null,
    streaming,
  )

  useEffect(() => {
    if (done && text && activeSymbol) {
      setSavedAnalysis({ symbol: activeSymbol, text })
    }
  }, [done])

  const { data: chartData, isFetching: chartLoading } = useQuery({
    queryKey: ['chart', symbol, days],
    queryFn: () => api.get(`/api/stocks/${symbol}/chart-json?days=${days}`).then((r) => r.data),
    enabled: !!symbol,
  })

  const { data: indData, isFetching: indLoading } = useQuery({
    queryKey: ['indicators', symbol],
    queryFn: () => api.get(`/api/stocks/${symbol}/indicators`).then((r) => r.data),
    enabled: !!symbol,
  })

  const { data: fundData } = useQuery({
    queryKey: ['fundamentals', symbol],
    queryFn: () => api.get(`/api/stocks/${symbol}/fundamentals`).then((r) => r.data),
    enabled: !!symbol,
    staleTime: 5 * 60 * 1000,
    retry: 1,
  })

  const stats = indData?.stats
  const ind = indData?.indicators

  const isStreaming = streaming || (!!text && !done)
  const displayText = isStreaming ? text : savedAnalysis?.symbol === symbol ? savedAnalysis?.text : null
  const showAnalysis = !!displayText || !!sseError

  function handleSelectSymbol(sym) {
    setSymbol(sym)
    setSavedAnalysis(null)
    setActiveSymbol('')
    setStreaming(false)
  }

  function handleGetInsight() {
    if (!symbol) return
    setSavedAnalysis(null)
    setActiveSymbol(symbol)
    setStreaming(true)
  }

  function handleCancelInsight() {
    setActiveSymbol('')
    setStreaming(false)
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">Stock Analysis</h1>

      {/* Search */}
      <div className="bg-[#1e2130] rounded-xl p-5 border border-slate-700/50">
        <SymbolSearch
          onSelect={handleSelectSymbol}
          placeholder="Search company e.g. Reliance, Infosys, HDFC Bank"
        />
      </div>

      {/* Stats header */}
      {stats && (
        <div className="bg-[#1e2130] rounded-xl p-4 border border-slate-700/50">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-baseline gap-3 flex-wrap">
              <h2 className="text-2xl font-bold text-white">
                ₹{stats.price?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </h2>
              <span className={`text-sm font-medium ${stats.day_change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {stats.day_change >= 0 ? '+' : ''}{stats.day_change?.toFixed(2)} ({stats.day_change_pct?.toFixed(2)}%)
              </span>
              <span className="text-slate-400 text-sm">{symbol}</span>
            </div>
            {/* AI Insight button */}
            {!isStreaming ? (
              <button
                onClick={handleGetInsight}
                className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition"
              >
                🤖 Get AI Insight
              </button>
            ) : (
              <button
                onClick={handleCancelInsight}
                className="bg-slate-700 hover:bg-slate-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition"
              >
                Cancel
              </button>
            )}
          </div>
          <div className="grid grid-cols-4 gap-4 mt-4 text-sm">
            {[
              ['Open', `₹${stats.open}`],
              ['High', `₹${stats.high}`],
              ['Low', `₹${stats.low}`],
              ['52W High', `₹${stats.week_52_high}`],
              ['52W Low', `₹${stats.week_52_low}`],
              ['5D Return', `${stats.ret_5d >= 0 ? '+' : ''}${stats.ret_5d?.toFixed(2)}%`],
              ['20D Return', `${stats.ret_20d >= 0 ? '+' : ''}${stats.ret_20d?.toFixed(2)}%`],
              ['Vol Spike', `${stats.volume_spike_pct?.toFixed(1)}%`],
            ].map(([label, val]) => (
              <div key={label}>
                <p className="text-slate-500 text-xs">{label}</p>
                <p className="text-white">{val}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Fundamentals */}
      {stats && (
        <div>
          <h3 className="text-sm font-medium text-slate-400 mb-2">Fundamentals</h3>
          <div className="grid grid-cols-3 gap-3">
            <FundamentalCard title="ROCE" metric={fundData?.roce} />
            <FundamentalCard title="ROE" metric={fundData?.roe} />
            <FundamentalCard title="PEG Ratio" metric={fundData?.peg} />
          </div>
        </div>
      )}

      {/* Chart tabs + period selector */}
      {stats && (
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex gap-1">
            {['chart', 'indicators'].map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-4 py-1.5 rounded-lg text-sm font-medium transition capitalize ${
                  tab === t ? 'bg-blue-600 text-white' : 'bg-[#1e2130] text-slate-400 hover:text-white'
                }`}
              >
                {t === 'chart' ? 'Price Chart' : 'Technical Indicators'}
              </button>
            ))}
          </div>
          {tab === 'chart' && (
            <div className="flex gap-1">
              {Object.entries(PERIODS).map(([label, d]) => (
                <button
                  key={label}
                  onClick={() => setDays(d)}
                  className={`px-3 py-1 rounded text-xs font-medium transition ${
                    days === d ? 'bg-blue-600 text-white' : 'bg-[#1e2130] text-slate-400 hover:text-white'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Chart */}
      {stats && tab === 'chart' && (
        <div className="bg-[#1e2130] rounded-xl p-4 border border-slate-700/50">
          {chartLoading ? <LoadingSpinner text="Loading chart..." /> : (
            chartData && <StockChart figJson={chartData} />
          )}
        </div>
      )}

      {/* Technical indicators */}
      {stats && tab === 'indicators' && (
        <div className="bg-[#1e2130] rounded-xl p-5 border border-slate-700/50">
          {indLoading ? <LoadingSpinner text="Loading indicators..." /> : ind && (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-slate-500 text-left border-b border-slate-700">
                  <th className="pb-2 font-medium">Indicator</th>
                  <th className="pb-2 font-medium">Value</th>
                  <th className="pb-2 font-medium">Signal</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {[
                  ['RSI (14)', ind.rsi?.toFixed(1), ind.rsi_signal],
                  ['MACD', ind.macd?.toFixed(3), ind.macd_signal],
                  ['Bollinger Bands', '—', ind.bb_position],
                  ['EMA 20', `₹${ind.ema_20?.toFixed(2)}`, ind.trend],
                  ['EMA 50', `₹${ind.ema_50?.toFixed(2)}`, ind.trend],
                ].map(([name, val, sig]) => (
                  <tr key={name} className="text-slate-300">
                    <td className="py-2 text-slate-400">{name}</td>
                    <td className="py-2 font-mono">{val}</td>
                    <td className="py-2"><SignalBadge signal={sig} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* AI Insight loading */}
      {isStreaming && !text && !sseError && (
        <LoadingSpinner text="Running predictions then streaming analysis (~60s)..." />
      )}

      {/* AI Insight error */}
      {sseError && (
        <div className="bg-red-900/30 border border-red-700 rounded-xl p-4 text-red-300 text-sm">
          {sseError}
        </div>
      )}

      {/* AI Insight result */}
      {showAnalysis && displayText && (
        <div className="bg-[#1e2130] rounded-xl p-6 border border-slate-700/50">
          <h2 className="text-base font-semibold text-white mb-4">
            🤖 {symbol} — AI Analysis
          </h2>
          <StreamingText text={displayText} done={!isStreaming} />
        </div>
      )}

      {showAnalysis && (
        <div className="bg-yellow-900/20 border border-yellow-700/50 rounded-xl p-4 text-yellow-200/70 text-xs">
          ⚠️ This analysis is for educational purposes only and does not constitute financial advice.
          Always do your own research before investing.
        </div>
      )}
    </div>
  )
}
