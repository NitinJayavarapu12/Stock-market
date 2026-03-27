import { useState, useEffect } from 'react'

export default function Clock({ compact = false }) {
  const [now, setNow] = useState(new Date())

  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(t)
  }, [])

  const ist = new Intl.DateTimeFormat('en-IN', {
    timeZone: 'Asia/Kolkata',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: true,
  }).format(now)

  const date = new Intl.DateTimeFormat('en-IN', {
    timeZone: 'Asia/Kolkata',
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(now)

  if (compact) {
    return (
      <div className="text-right">
        <p className="text-white text-xs font-mono font-semibold">{ist} <span className="text-slate-500">IST</span></p>
        <p className="text-slate-500 text-xs">{date}</p>
      </div>
    )
  }

  return (
    <div className="px-2 py-3 border-t border-slate-800 mt-auto">
      <p className="text-white text-sm font-mono font-semibold">{ist}</p>
      <p className="text-slate-500 text-xs mt-0.5">{date}</p>
      <p className="text-slate-600 text-xs">IST (UTC+5:30)</p>
    </div>
  )
}
