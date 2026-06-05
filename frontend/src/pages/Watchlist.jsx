import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../api/client'
import LoadingSpinner from '../components/LoadingSpinner'
import SymbolSearch from '../components/SymbolSearch'

function AlertRow({ symbol, alerts, onSave, onRemove }) {
  const existing = alerts?.find((a) => a.symbol === symbol) || {}
  const [above, setAbove] = useState(existing.above ?? '')
  const [below, setBelow] = useState(existing.below ?? '')
  const [open, setOpen] = useState(false)

  function handleSave() {
    onSave(symbol, {
      above: above !== '' ? parseFloat(above) : null,
      below: below !== '' ? parseFloat(below) : null,
    })
    setOpen(false)
  }

  const hasAlert = existing.above != null || existing.below != null

  return (
    <td className="px-4 py-3">
      <div className="flex items-center gap-2">
        {hasAlert && (
          <span className="text-yellow-400 text-xs">🔔</span>
        )}
        <button
          onClick={() => setOpen((v) => !v)}
          className="text-slate-400 hover:text-white text-xs underline"
        >
          {hasAlert ? 'Edit alert' : 'Set alert'}
        </button>
        {hasAlert && (
          <button onClick={() => onRemove(symbol)} className="text-red-400 hover:text-red-300 text-xs">
            ✕
          </button>
        )}
      </div>
      {open && (
        <div className="mt-2 bg-[#12141e] border border-slate-700 rounded-lg p-3 space-y-2 min-w-[180px]">
          <div>
            <label className="text-slate-400 text-xs block mb-1">Alert above ₹</label>
            <input
              type="number"
              value={above}
              onChange={(e) => setAbove(e.target.value)}
              placeholder="e.g. 1800"
              className="w-full bg-slate-800 border border-slate-600 rounded px-2 py-1 text-white text-xs focus:outline-none focus:border-blue-500"
            />
          </div>
          <div>
            <label className="text-slate-400 text-xs block mb-1">Alert below ₹</label>
            <input
              type="number"
              value={below}
              onChange={(e) => setBelow(e.target.value)}
              placeholder="e.g. 1300"
              className="w-full bg-slate-800 border border-slate-600 rounded px-2 py-1 text-white text-xs focus:outline-none focus:border-blue-500"
            />
          </div>
          <div className="flex gap-2 pt-1">
            <button
              onClick={handleSave}
              className="flex-1 bg-blue-600 hover:bg-blue-700 text-white text-xs py-1 rounded transition"
            >
              Save
            </button>
            <button
              onClick={() => setOpen(false)}
              className="flex-1 bg-slate-700 hover:bg-slate-600 text-white text-xs py-1 rounded transition"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </td>
  )
}

export default function Watchlist() {
  const qc = useQueryClient()

  const { data: watchlist, isLoading } = useQuery({
    queryKey: ['watchlist'],
    queryFn: () => api.get('/api/watchlist').then((r) => r.data),
    refetchInterval: 60_000,
  })

  const { data: alertsData, refetch: refetchAlerts } = useQuery({
    queryKey: ['alerts'],
    queryFn: () => api.get('/api/alerts').then((r) => r.data),
  })

  const [emailInput, setEmailInput] = useState('')
  const [emailSaved, setEmailSaved] = useState(false)
  const [prefsSaved, setPrefsSaved] = useState(false)

  const NOTIF_LABELS = [
    { key: 'notif_daily_reports',    label: 'Morning & Evening Reports',   desc: '9:15 AM open + 3:35 PM close emails' },
    { key: 'notif_price_alerts',     label: 'Price Threshold Alerts',      desc: 'When a stock crosses your set price' },
    { key: 'notif_market_anomaly',   label: 'Market Anomaly Alerts',       desc: 'Unusual NIFTY/SENSEX moves (2σ+)' },
    { key: 'notif_watchlist_spikes', label: 'Watchlist Spike Alerts',      desc: 'Unusual moves in your watchlist' },
    { key: 'notif_portfolio_moves',  label: 'Portfolio Move Alerts',       desc: 'When a holding moves ≥3% intraday' },
    { key: 'notif_recommendations',  label: 'Daily Buy Recommendations',   desc: 'Morning scan for buying opportunities' },
  ]

  const addMutation = useMutation({
    mutationFn: (sym) => api.post(`/api/watchlist/${sym}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['watchlist'] }),
  })

  const removeMutation = useMutation({
    mutationFn: (sym) => api.delete(`/api/watchlist/${sym}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['watchlist'] }),
  })

  async function saveEmail(e) {
    e.preventDefault()
    await api.put('/api/alerts/config', { email: emailInput.trim() })
    setEmailSaved(true)
    refetchAlerts()
    setTimeout(() => setEmailSaved(false), 2000)
  }

  async function togglePref(key, value) {
    await api.put('/api/alerts/preferences', { [key]: value })
    refetchAlerts()
  }

  async function savePrefs() {
    setPrefsSaved(true)
    setTimeout(() => setPrefsSaved(false), 1500)
  }

  async function saveAlert(symbol, thresholds) {
    await api.post(`/api/alerts/${symbol}`, thresholds)
    refetchAlerts()
  }

  async function removeAlert(symbol) {
    await api.delete(`/api/alerts/${symbol}`)
    refetchAlerts()
  }

  const currentEmail = alertsData?.email || ''

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">Watchlist</h1>

      <div className="bg-[#1e2130] rounded-xl p-5 border border-slate-700/50">
        <SymbolSearch
          placeholder="Search company to add e.g. Reliance, TCS"
          onSelect={(sym) => addMutation.mutate(sym)}
        />
      </div>

      {/* Alert email config */}
      <div className="bg-[#1e2130] rounded-xl p-5 border border-slate-700/50">
        <h2 className="text-sm font-semibold text-white mb-1">📧 Email Alerts & Reports</h2>
        <p className="text-slate-400 text-xs mb-3">
          Receive price alerts and daily market reports (opening at 9:15am + closing at 3:35pm IST).
        </p>
        <form onSubmit={saveEmail} className="flex gap-2">
          <input
            type="email"
            value={emailInput || currentEmail}
            onChange={(e) => setEmailInput(e.target.value)}
            placeholder="your@email.com"
            className="flex-1 bg-[#12141e] border border-slate-700 rounded-lg px-4 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 text-sm"
          />
          <button
            type="submit"
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition shrink-0"
          >
            {emailSaved ? '✓ Saved' : 'Save'}
          </button>
        </form>
      </div>

      {/* Notification toggles */}
      {currentEmail && (
        <div className="bg-[#1e2130] rounded-xl p-5 border border-slate-700/50">
          <h2 className="text-sm font-semibold text-white mb-1">🔔 Notification Settings</h2>
          <p className="text-slate-400 text-xs mb-4">Choose which emails you want to receive.</p>
          <div className="space-y-3">
            {NOTIF_LABELS.map(({ key, label, desc }) => {
              const prefs = alertsData?.preferences || {}
              const enabled = prefs[key] !== false
              return (
                <div key={key} className="flex items-center justify-between gap-4">
                  <div className="min-w-0">
                    <p className="text-slate-200 text-sm">{label}</p>
                    <p className="text-slate-500 text-xs">{desc}</p>
                  </div>
                  <button
                    onClick={() => togglePref(key, !enabled)}
                    className={`shrink-0 relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                      enabled ? 'bg-blue-600' : 'bg-slate-700'
                    }`}
                  >
                    <span
                      className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
                        enabled ? 'translate-x-4' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {isLoading ? (
        <LoadingSpinner text="Loading watchlist..." />
      ) : !watchlist?.length ? (
        <div className="bg-[#1e2130] rounded-xl p-8 border border-slate-700/50 text-center text-slate-400">
          Your watchlist is empty. Add stocks above.
        </div>
      ) : (
        <div className="bg-[#1e2130] rounded-xl border border-slate-700/50 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-slate-500 text-left border-b border-slate-700">
                {['Symbol', 'Price', 'Day %', '5D %', '20D %', '60D %', 'Alert', ''].map((h) => (
                  <th key={h} className="px-4 py-3 font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {watchlist.map((s) => {
                const pct = (v) => {
                  if (v == null) return '—'
                  const c = v >= 0 ? 'text-green-400' : 'text-red-400'
                  return <span className={c}>{v >= 0 ? '+' : ''}{v?.toFixed(2)}%</span>
                }
                return (
                  <tr key={s.symbol} className="text-slate-300 hover:bg-slate-800/50 align-top">
                    <td className="px-4 py-3 font-semibold text-white">{s.symbol}</td>
                    <td className="px-4 py-3">
                      {s.price ? `₹${s.price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}` : '—'}
                    </td>
                    <td className="px-4 py-3">{pct(s.day_change_pct)}</td>
                    <td className="px-4 py-3">{pct(s.ret_5d)}</td>
                    <td className="px-4 py-3">{pct(s.ret_20d)}</td>
                    <td className="px-4 py-3">{pct(s.ret_60d)}</td>
                    <AlertRow
                      symbol={s.symbol}
                      alerts={alertsData?.alerts}
                      onSave={saveAlert}
                      onRemove={removeAlert}
                    />
                    <td className="px-4 py-3">
                      <button
                        onClick={() => removeMutation.mutate(s.symbol)}
                        className="text-red-400 hover:text-red-300 text-xs"
                      >
                        Remove
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
