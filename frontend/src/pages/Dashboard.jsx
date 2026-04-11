import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import api from '../api/client'
import IndexCard from '../components/IndexCard'
import LoadingSpinner from '../components/LoadingSpinner'
import SymbolSearch from '../components/SymbolSearch'

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

function PortfolioSection() {
  const [showAdd, setShowAdd] = useState(false)
  const [selectedSymbol, setSelectedSymbol] = useState('')
  const [selectedCompany, setSelectedCompany] = useState('')
  const [qty, setQty] = useState('')
  const [buyPrice, setBuyPrice] = useState('')
  const [saving, setSaving] = useState(false)
  const [csvUploading, setCsvUploading] = useState(false)
  const [csvMsg, setCsvMsg] = useState('')

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['portfolio'],
    queryFn: () => api.get('/api/portfolio').then(r => r.data),
    staleTime: 2 * 60_000,
  })

  const summary = data?.summary
  const holdings = data?.holdings || []

  async function handleAdd() {
    if (!selectedSymbol || !qty || !buyPrice) return
    setSaving(true)
    try {
      await api.post('/api/portfolio', {
        symbol: selectedSymbol,
        company: selectedCompany,
        quantity: parseFloat(qty),
        avg_buy_price: parseFloat(buyPrice),
      })
      setSelectedSymbol(''); setSelectedCompany(''); setQty(''); setBuyPrice('')
      setShowAdd(false)
      refetch()
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(symbol) {
    await api.delete(`/api/portfolio/${symbol}`)
    refetch()
  }

  async function handleCsvUpload(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setCsvUploading(true)
    setCsvMsg('')
    const form = new FormData()
    form.append('file', file)
    try {
      const resp = await api.post('/api/portfolio/upload-csv', form)
      setCsvMsg(`✓ Imported ${resp.data.imported} holdings`)
      refetch()
    } catch (err) {
      setCsvMsg(err.response?.data?.detail || 'CSV upload failed')
    } finally {
      setCsvUploading(false)
      e.target.value = ''
    }
  }

  if (isLoading) return <LoadingSpinner text="Loading portfolio..." />

  return (
    <div className="bg-[#1e2130] rounded-xl p-5 border border-slate-700/50">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-white">My Portfolio</h2>
        <div className="flex items-center gap-2">
          <label className={`text-xs px-3 py-1.5 rounded-lg transition cursor-pointer ${csvUploading ? 'bg-slate-600 text-slate-400' : 'bg-slate-700 hover:bg-slate-600 text-white'}`}>
            {csvUploading ? 'Uploading...' : '⬆ Upload CSV'}
            <input type="file" accept=".csv" className="hidden" onChange={handleCsvUpload} disabled={csvUploading} />
          </label>
          <button
            onClick={() => setShowAdd(s => !s)}
            className="text-xs bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded-lg transition"
          >
            {showAdd ? 'Cancel' : '+ Add Stock'}
          </button>
        </div>
      </div>
      {csvMsg && (
        <p className={`text-xs mb-3 ${csvMsg.startsWith('✓') ? 'text-green-400' : 'text-red-400'}`}>{csvMsg}</p>
      )}

      {/* Summary cards */}
      {summary && summary.count > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
          {[
            { label: 'Invested', value: `₹${summary.total_invested.toLocaleString('en-IN')}`, color: 'text-slate-300' },
            { label: 'Current Value', value: `₹${summary.total_value.toLocaleString('en-IN')}`, color: 'text-white' },
            { label: 'Total P&L', value: `${summary.total_pnl >= 0 ? '+' : ''}₹${summary.total_pnl.toLocaleString('en-IN')}`, color: summary.total_pnl >= 0 ? 'text-green-400' : 'text-red-400' },
            { label: 'Return', value: `${summary.total_pnl_pct >= 0 ? '+' : ''}${summary.total_pnl_pct}%`, color: summary.total_pnl_pct >= 0 ? 'text-green-400' : 'text-red-400' },
          ].map(({ label, value, color }) => (
            <div key={label} className="bg-[#161827] rounded-lg p-3 border border-slate-700/50">
              <p className="text-slate-500 text-xs mb-1">{label}</p>
              <p className={`text-base font-bold ${color}`}>{value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Add holding form */}
      {showAdd && (
        <div className="bg-[#12141e] rounded-lg p-4 border border-slate-700 mb-4 space-y-3">
          <SymbolSearch
            placeholder="Search company e.g. Infosys, Reliance"
            onSelect={(sym, company) => { setSelectedSymbol(sym); setSelectedCompany(company || '') }}
          />
          <div className="grid grid-cols-2 gap-2">
            <input type="number" value={qty} onChange={e => setQty(e.target.value)} placeholder="Quantity"
              className="bg-[#1e2130] border border-slate-700 rounded-lg px-3 py-2 text-white text-sm placeholder-slate-600 focus:outline-none focus:border-blue-500" />
            <input type="number" value={buyPrice} onChange={e => setBuyPrice(e.target.value)} placeholder="Avg buy price (₹)"
              className="bg-[#1e2130] border border-slate-700 rounded-lg px-3 py-2 text-white text-sm placeholder-slate-600 focus:outline-none focus:border-blue-500" />
          </div>
          <button onClick={handleAdd} disabled={!selectedSymbol || !qty || !buyPrice || saving}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white py-2 rounded-lg text-sm font-medium transition">
            {saving ? 'Saving...' : 'Add to Portfolio'}
          </button>
        </div>
      )}

      {/* Holdings table */}
      {holdings.length === 0 ? (
        <p className="text-slate-500 text-sm text-center py-4">
          No holdings yet. Add stocks above or upload a CSV from your broker.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-slate-400 text-xs border-b border-slate-700">
                <th className="text-left pb-2">Stock</th>
                <th className="text-right pb-2">Qty</th>
                <th className="text-right pb-2">Avg Price</th>
                <th className="text-right pb-2">Current</th>
                <th className="text-right pb-2">P&L</th>
                <th className="text-right pb-2">Return</th>
                <th className="pb-2"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {holdings.map(h => (
                <tr key={h.symbol} className="text-slate-300">
                  <td className="py-2">
                    <p className="text-white font-medium text-xs font-mono">{h.symbol.replace('.NS','').replace('.BO','')}</p>
                    <p className="text-slate-500 text-xs">{h.company}</p>
                  </td>
                  <td className="py-2 text-right text-xs">{h.quantity}</td>
                  <td className="py-2 text-right text-xs">₹{h.avg_buy_price.toLocaleString('en-IN')}</td>
                  <td className="py-2 text-right text-xs">₹{h.current_price.toLocaleString('en-IN')}</td>
                  <td className={`py-2 text-right text-xs font-medium ${h.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {h.pnl >= 0 ? '+' : ''}₹{h.pnl.toLocaleString('en-IN')}
                  </td>
                  <td className={`py-2 text-right text-xs ${h.pnl_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {h.pnl_pct >= 0 ? '+' : ''}{h.pnl_pct}%
                  </td>
                  <td className="py-2 text-right">
                    <button onClick={() => handleDelete(h.symbol)} className="text-slate-600 hover:text-red-400 text-xs transition">✕</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
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
        {status && <span className="text-sm text-slate-300">{status.label}</span>}
      </div>

      {/* Portfolio */}
      <PortfolioSection />

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
