import { useState, useEffect, useRef } from 'react'
import Plotly from 'plotly.js-dist-min'
import { usePredictionJob } from '../hooks/usePredictionJob'
import PredictionCard from '../components/PredictionCard'
import StockChart from '../components/StockChart'
import LoadingSpinner from '../components/LoadingSpinner'
import SymbolSearch from '../components/SymbolSearch'
import { useSessionState } from '../hooks/useSessionState'

const HORIZONS = ['1 Week', '1 Month', '3 Months', '6 Months']

function CurrentPriceCard({ result }) {
  const hp = result?.historical_points
  if (!hp?.length) return null
  const price = hp[hp.length - 1].y
  return (
    <div className="bg-[#1e2130] rounded-xl p-5 border border-blue-500/40">
      <p className="text-slate-400 text-sm mb-2">Current Price</p>
      <p className="text-white text-2xl font-bold">
        ₹{price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
      </p>
      <p className="text-blue-400 text-xs mt-2">As of last trading day</p>
    </div>
  )
}

function PredictionChart({ horizonResult, symbol, label }) {
  const ref = useRef(null)

  useEffect(() => {
    if (!ref.current || !horizonResult?.forecast_points?.length) return
    const fp = horizonResult.forecast_points
    const hp = horizonResult.historical_points || []

    const traces = []
    if (hp.length) {
      traces.push({
        x: hp.map((p) => p.ds),
        y: hp.map((p) => p.y),
        type: 'scatter',
        mode: 'lines',
        name: 'Historical',
        line: { color: '#64b5f6', width: 2 },
      })
    }
    traces.push({
      x: [...fp.map((p) => p.ds), ...fp.map((p) => p.ds).reverse()],
      y: [...fp.map((p) => p.yhat_upper), ...fp.map((p) => p.yhat_lower).reverse()],
      fill: 'toself',
      fillcolor: 'rgba(255,214,0,0.08)',
      line: { color: 'rgba(255,214,0,0)' },
      name: 'Confidence Band',
    })
    traces.push({
      x: fp.map((p) => p.ds),
      y: fp.map((p) => p.yhat),
      type: 'scatter',
      mode: 'lines',
      name: `Predicted (${label})`,
      line: { color: '#ffd600', width: 2, dash: 'dash' },
    })

    const currentPrice = hp.length ? hp[hp.length - 1].y : null
    const shapes = currentPrice ? [{
      type: 'line',
      xref: 'paper', x0: 0, x1: 1,
      yref: 'y', y0: currentPrice, y1: currentPrice,
      line: { color: '#60a5fa', width: 1, dash: 'dot' },
    }] : []
    const annotations = currentPrice ? [{
      xref: 'paper', x: 0.01,
      yref: 'y', y: currentPrice,
      text: `Current ₹${currentPrice.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`,
      showarrow: false,
      font: { color: '#60a5fa', size: 11 },
      yanchor: 'bottom',
    }] : []

    Plotly.newPlot(ref.current, traces, {
      template: 'plotly_dark',
      height: 380,
      margin: { l: 0, r: 0, t: 30, b: 0 },
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      title: `${symbol} — ${label} Prediction`,
      legend: { orientation: 'h', y: 1.08, x: 1, xanchor: 'right' },
      yaxis: { gridcolor: 'rgba(255,255,255,0.05)' },
      xaxis: { gridcolor: 'rgba(255,255,255,0.05)' },
      shapes,
      annotations,
    }, { responsive: true, displayModeBar: false })

    return () => { if (ref.current) Plotly.purge(ref.current) }
  }, [horizonResult, symbol, label])

  if (!horizonResult?.forecast_points?.length) return null
  return <div ref={ref} style={{ width: '100%' }} />
}

export default function Predictions() {
  const [input, setInput] = useSessionState('pred-input', 'RELIANCE.NS')
  const [activeTab, setActiveTab] = useSessionState('pred-tab', '1 Week')
  const [savedPrediction, setSavedPrediction] = useSessionState('pred-session', null)
  const { startPrediction, reset, status, result, symbol } = usePredictionJob()
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    if (status !== 'pending') { setElapsed(0); return }
    const t = setInterval(() => setElapsed((e) => e + 1), 1000)
    return () => clearInterval(t)
  }, [status])

  // Save completed prediction to session
  useEffect(() => {
    if (status === 'done' && result && symbol) {
      setSavedPrediction({ symbol, result })
    }
  }, [status, result, symbol])

  function handleSubmit(e) {
    e.preventDefault()
    const sym = input.trim().toUpperCase()
    if (sym) { setSavedPrediction(null); startPrediction(sym) }
  }

  function handleReset() {
    reset()
    setSavedPrediction(null)
  }

  const isActiveJob = status === 'pending' || status === 'starting' || status === 'done' || status === 'error'
  const displayResult = status === 'done' ? result : (!isActiveJob ? savedPrediction?.result : null)
  const displaySymbol = status === 'done' ? symbol : savedPrediction?.symbol
  const showResult = status === 'done' || (!isActiveJob && !!savedPrediction?.result)

  const horizonResult = displayResult?.[activeTab]

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">Price Predictions</h1>

      <div className="bg-[#1e2130] rounded-xl p-5 border border-slate-700/50">
        <p className="text-slate-400 text-sm mb-4">
          Uses Meta Prophet to forecast price across 4 time horizons. Takes ~60 seconds.
        </p>
        <div className="flex gap-2">
          <SymbolSearch
            className="flex-1"
            placeholder="Search company e.g. Reliance, TCS"
            onSelect={(sym) => { setInput(sym); setSavedPrediction(null); startPrediction(sym) }}
          />
          <button
            type="button"
            disabled={!input || status === 'pending' || status === 'starting'}
            onClick={() => { if (input) { setSavedPrediction(null); startPrediction(input) } }}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-5 py-2 rounded-lg font-medium transition shrink-0"
          >
            Predict
          </button>
          {(status === 'done' || status === 'error' || savedPrediction) && (
            <button
              type="button"
              onClick={handleReset}
              className="bg-slate-700 hover:bg-slate-600 text-white px-4 py-2 rounded-lg text-sm transition"
            >
              Reset
            </button>
          )}
        </div>
      </div>

      {(status === 'pending' || status === 'starting') && (
        <LoadingSpinner text={`Running Prophet predictions... ${elapsed}s`} />
      )}

      {status === 'error' && (
        <div className="bg-red-900/30 border border-red-700 rounded-xl p-4 text-red-300 text-sm">
          Prediction failed. Please try again.
        </div>
      )}

      {showResult && displayResult && (
        <>
          <div className="flex gap-1 flex-wrap">
            {HORIZONS.map((h) => (
              <button
                key={h}
                onClick={() => setActiveTab(h)}
                className={`px-4 py-1.5 rounded-lg text-sm font-medium transition ${
                  activeTab === h ? 'bg-blue-600 text-white' : 'bg-[#1e2130] text-slate-400 hover:text-white'
                }`}
              >
                {h}
              </button>
            ))}
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <CurrentPriceCard result={displayResult['1 Week']} />
            {HORIZONS.map((h) => (
              <PredictionCard key={h} label={h} result={displayResult[h]} />
            ))}
          </div>

          <div className="bg-[#1e2130] rounded-xl p-4 border border-slate-700/50">
            <PredictionChart horizonResult={horizonResult} symbol={displaySymbol} label={activeTab} />
          </div>

          {horizonResult?.error && (
            <p className="text-yellow-400 text-xs">Note: {horizonResult.error}</p>
          )}
        </>
      )}
    </div>
  )
}
