export default function IndexCard({ name, data }) {
  if (!data) return null
  const up = data.change_pct >= 0
  const color = up ? 'text-green-400' : 'text-red-400'
  const sign = up ? '+' : ''

  return (
    <div className="bg-[#1e2130] rounded-xl p-4 border border-slate-700/50">
      <p className="text-slate-400 text-xs mb-1">{name}</p>
      <p className="text-white text-xl font-semibold">{data.current?.toLocaleString('en-IN')}</p>
      <p className={`text-sm mt-1 ${color}`}>
        {sign}{data.change?.toFixed(2)} ({sign}{data.change_pct?.toFixed(2)}%)
      </p>
    </div>
  )
}
