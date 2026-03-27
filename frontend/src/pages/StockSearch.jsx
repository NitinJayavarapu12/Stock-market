import { useQuery } from '@tanstack/react-query'
import api from '../api/client'
import StockChart from '../components/StockChart'
import SignalBadge from '../components/SignalBadge'
import LoadingSpinner from '../components/LoadingSpinner'
import { useSessionState } from '../hooks/useSessionState'

const PERIODS = { '1M': 30, '3M': 90, '6M': 180, '1Y': 365, '2Y': 730 }

export default function StockSearch() {
  const [symbol, setSymbol] = useSessionState('ss-symbol', 'RELIANCE.NS')
  const [input, setInput] = useSessionState('ss-input', 'RELIANCE.NS')
  const [days, setDays] = useSessionState('ss-days', 365)
  const [tab, setTab] = useSessionState('ss-tab', 'chart')

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

  function handleSearch(e) {
    e.preventDefault()
    if (input.trim()) setSymbol(input.trim().toUpperCase())
  }

  const stats = indData?.stats
  const ind = indData?.indicators

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">Stock Search</h1>

      {/* Search form */}
      <form onSubmit={handleSearch} className="flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="e.g. RELIANCE.NS, TCS.NS"
          className="flex-1 bg-[#1e2130] border border-slate-700 rounded-lg px-4 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
        />
        <button
          type="submit"
          className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2 rounded-lg font-medium transition"
        >
          Search
        </button>
      </form>

      {/* Stats header */}
      {stats && (
        <div className="bg-[#1e2130] rounded-xl p-4 border border-slate-700/50">
          <div className="flex items-baseline gap-3 flex-wrap">
            <h2 className="text-2xl font-bold text-white">
              ₹{stats.price?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </h2>
            <span className={`text-sm font-medium ${stats.day_change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {stats.day_change >= 0 ? '+' : ''}{stats.day_change?.toFixed(2)} ({stats.day_change_pct?.toFixed(2)}%)
            </span>
            <span className="text-slate-400 text-sm">{symbol}</span>
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

      {/* Period selector + tabs */}
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

      {/* Chart tab */}
      {tab === 'chart' && (
        <div className="bg-[#1e2130] rounded-xl p-4 border border-slate-700/50">
          {chartLoading ? <LoadingSpinner text="Loading chart..." /> : (
            chartData && <StockChart figJson={chartData} />
          )}
        </div>
      )}

      {/* Indicators tab */}
      {tab === 'indicators' && (
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
    </div>
  )
}
