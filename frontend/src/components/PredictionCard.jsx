export default function PredictionCard({ label, result }) {
  if (!result) return null
  const up = result.percent_change >= 0
  const color = up ? 'text-green-400' : 'text-red-400'
  const sign = up ? '+' : ''
  const arrow = result.trend_direction === 'Upward' ? '↑' : result.trend_direction === 'Downward' ? '↓' : '→'

  return (
    <div className="bg-[#1e2130] rounded-xl p-5 border border-slate-700/50">
      <p className="text-slate-400 text-sm mb-2">{label}</p>
      <p className="text-white text-2xl font-bold">
        ₹{result.predicted_price?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
      </p>
      <p className={`text-sm mt-1 font-medium ${color}`}>
        {arrow} {sign}{result.percent_change?.toFixed(2)}%
      </p>
      <p className="text-slate-500 text-xs mt-2">{result.confidence_range}</p>
    </div>
  )
}
