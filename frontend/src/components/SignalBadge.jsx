const COLORS = {
  Bullish: 'bg-green-900/50 text-green-300 border-green-700',
  'Bullish Crossover': 'bg-green-900/50 text-green-300 border-green-700',
  Bearish: 'bg-red-900/50 text-red-300 border-red-700',
  'Bearish Crossover': 'bg-red-900/50 text-red-300 border-red-700',
  Neutral: 'bg-yellow-900/50 text-yellow-300 border-yellow-700',
  Overbought: 'bg-orange-900/50 text-orange-300 border-orange-700',
  Oversold: 'bg-blue-900/50 text-blue-300 border-blue-700',
}

export default function SignalBadge({ signal }) {
  const cls = COLORS[signal] || 'bg-slate-800 text-slate-300 border-slate-600'
  return (
    <span className={`text-xs px-2 py-0.5 rounded border ${cls}`}>
      {signal}
    </span>
  )
}
