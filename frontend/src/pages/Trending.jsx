import { useQuery } from '@tanstack/react-query'
import api from '../api/client'
import StockChart from '../components/StockChart'
import LoadingSpinner from '../components/LoadingSpinner'

export default function Trending() {
  const { data: treemap, isLoading: tmLoading } = useQuery({
    queryKey: ['trending-chart'],
    queryFn: () => api.get('/api/trending/chart-json').then((r) => r.data),
    staleTime: 5 * 60_000,
  })

  const { data: commentary, isLoading: comLoading } = useQuery({
    queryKey: ['trending-commentary'],
    queryFn: () => api.get('/api/trending/commentary').then((r) => r.data),
    staleTime: 10 * 60_000,
  })

  const { data: stocks, isLoading: stocksLoading } = useQuery({
    queryKey: ['trending-stocks'],
    queryFn: () => api.get('/api/trending?top_n=15').then((r) => r.data),
    staleTime: 5 * 60_000,
  })

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">Trending Stocks</h1>

      {/* AI Commentary */}
      <div className="bg-[#1e2130] rounded-xl p-5 border border-slate-700/50">
        <h2 className="text-base font-semibold text-white mb-2">AI Commentary</h2>
        {comLoading ? (
          <p className="text-slate-400 text-sm animate-pulse">Generating commentary...</p>
        ) : (
          <p className="text-slate-300 text-sm leading-relaxed">{commentary?.text || '—'}</p>
        )}
      </div>

      {/* Treemap */}
      <div className="bg-[#1e2130] rounded-xl p-4 border border-slate-700/50">
        <h2 className="text-base font-semibold text-white mb-3">Volume Heatmap</h2>
        {tmLoading ? <LoadingSpinner text="Loading heatmap..." /> : (
          treemap && Object.keys(treemap).length > 0 && <StockChart figJson={treemap} />
        )}
      </div>

      {/* Table */}
      <div className="bg-[#1e2130] rounded-xl p-4 border border-slate-700/50 overflow-x-auto">
        <h2 className="text-base font-semibold text-white mb-3">Top Trending</h2>
        {stocksLoading ? <LoadingSpinner text="Loading stocks..." /> : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-slate-500 text-left border-b border-slate-700">
                {['Stock', 'Price', 'Day %', 'Trending Score', 'Vol Spike %'].map((h) => (
                  <th key={h} className="pb-2 pr-4 font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {(stocks || []).map((s) => (
                <tr key={s.symbol} className="text-slate-300">
                  <td className="py-2 pr-4 font-medium text-white">{s.name}</td>
                  <td className="py-2 pr-4">₹{s.price?.toFixed(2)}</td>
                  <td className={`py-2 pr-4 ${s.day_change_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {s.day_change_pct >= 0 ? '+' : ''}{s.day_change_pct?.toFixed(2)}%
                  </td>
                  <td className="py-2 pr-4">
                    <div className="flex items-center gap-2">
                      <div className="h-1.5 bg-blue-600 rounded" style={{ width: `${s.trending_score}%` }} />
                      <span className="text-slate-400">{s.trending_score}</span>
                    </div>
                  </td>
                  <td className="py-2">{s.volume_spike_pct?.toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
