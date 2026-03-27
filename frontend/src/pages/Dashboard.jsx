import { useQuery } from '@tanstack/react-query'
import api from '../api/client'
import IndexCard from '../components/IndexCard'
import LoadingSpinner from '../components/LoadingSpinner'

function MoverTable({ title, rows, loading, accent }) {
  return (
    <div className="bg-[#1e2130] rounded-xl p-4 border border-slate-700/50">
      <h2 className={`text-base font-semibold mb-3 ${accent}`}>{title}</h2>
      {loading ? (
        <LoadingSpinner text="Loading..." />
      ) : !rows?.length ? (
        <p className="text-slate-500 text-sm">No data available</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-slate-400 text-xs border-b border-slate-700">
              <th className="text-left pb-2">Stock</th>
              <th className="text-right pb-2">Price</th>
              <th className="text-right pb-2">Change</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.symbol} className="border-b border-slate-800/50">
                <td className="py-2 text-white font-mono text-xs">{r.symbol.replace('.NS', '').replace('.BO', '')}</td>
                <td className="py-2 text-right text-slate-300">₹{r.price.toLocaleString('en-IN')}</td>
                <td className={`py-2 text-right font-medium ${r.change_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {r.change_pct >= 0 ? '+' : ''}{r.change_pct.toFixed(2)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

export default function Dashboard() {
  const { data: indices, isLoading: idxLoading } = useQuery({
    queryKey: ['indices'],
    queryFn: () => api.get('/api/market/indices').then((r) => r.data),
    refetchInterval: 60_000,
  })

  const { data: status } = useQuery({
    queryKey: ['market-status'],
    queryFn: () => api.get('/api/market/status').then((r) => r.data),
    refetchInterval: 60_000,
  })

  const { data: movers, isLoading: moversLoading } = useQuery({
    queryKey: ['movers'],
    queryFn: () => api.get('/api/market/movers').then((r) => r.data),
    staleTime: 5 * 60_000,
  })

  const { data: overview, isLoading: overviewLoading } = useQuery({
    queryKey: ['market-overview'],
    queryFn: () => api.get('/api/market/overview').then((r) => r.data),
    staleTime: 10 * 60_000,
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Market Dashboard</h1>
        {status && (
          <span className="text-sm text-slate-300">{status.label}</span>
        )}
      </div>

      {/* Index Cards */}
      {idxLoading ? (
        <LoadingSpinner text="Fetching indices..." />
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {indices && Object.entries(indices).map(([name, data]) => (
            <IndexCard key={name} name={name} data={data} />
          ))}
        </div>
      )}

      {/* AI Market Overview */}
      <div className="bg-[#1e2130] rounded-xl p-5 border border-slate-700/50">
        <h2 className="text-lg font-semibold text-white mb-3">AI Market Overview</h2>
        {overviewLoading ? (
          <p className="text-slate-400 text-sm animate-pulse">Generating market overview...</p>
        ) : (
          <p className="text-slate-300 text-sm leading-relaxed">{overview?.text || 'No overview available.'}</p>
        )}
      </div>

      {/* Movers */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <MoverTable title="Top Gainers" rows={movers?.gainers} loading={moversLoading} accent="text-green-400" />
        <MoverTable title="Top Losers" rows={movers?.losers} loading={moversLoading} accent="text-red-400" />
      </div>
    </div>
  )
}
