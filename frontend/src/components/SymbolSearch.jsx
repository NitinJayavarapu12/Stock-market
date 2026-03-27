import { useState, useRef, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import api from '../api/client'

export default function SymbolSearch({ onSelect, placeholder, className = '' }) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  const { data: results } = useQuery({
    queryKey: ['symbol-search', query],
    queryFn: () => api.get(`/api/stocks/search?q=${query}&limit=6`).then((r) => r.data),
    enabled: query.length >= 2,
    staleTime: 30_000,
  })

  useEffect(() => {
    function handleClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  function handleSelect(item) {
    setQuery(item.company + ' (' + item.symbol + ')')
    setOpen(false)
    onSelect(item.symbol)
  }

  return (
    <div ref={ref} className={`relative ${className}`}>
      <input
        value={query}
        onChange={(e) => { setQuery(e.target.value); setOpen(true) }}
        onFocus={() => setOpen(true)}
        placeholder={placeholder || 'Search by company name or symbol e.g. Infosys, INFY.NS'}
        className="w-full bg-[#12141e] border border-slate-700 rounded-lg px-4 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
      />
      {open && results?.length > 0 && (
        <ul className="absolute z-10 w-full mt-1 bg-[#1e2130] border border-slate-700 rounded-lg shadow-xl overflow-hidden">
          {results.map((item) => (
            <li
              key={item.symbol}
              onMouseDown={() => handleSelect(item)}
              className="px-4 py-2.5 cursor-pointer hover:bg-slate-700 flex justify-between items-center"
            >
              <span className="text-white text-sm">{item.company}</span>
              <span className="text-slate-400 text-xs font-mono">{item.symbol}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
