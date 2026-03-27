import { useEffect, useRef, useMemo } from 'react'
import Plotly from 'plotly.js-dist-min'

export default function StockChart({ figJson, style }) {
  const ref = useRef(null)

  const fig = useMemo(() => {
    if (!figJson) return null
    try {
      return typeof figJson === 'string' ? JSON.parse(figJson) : figJson
    } catch {
      return null
    }
  }, [figJson])

  useEffect(() => {
    if (!ref.current || !fig?.data) return
    Plotly.newPlot(
      ref.current,
      fig.data,
      {
        ...fig.layout,
        autosize: true,
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
      },
      { responsive: true, displayModeBar: false },
    )
    return () => {
      if (ref.current) Plotly.purge(ref.current)
    }
  }, [figJson])

  if (!fig?.data) return null
  return <div ref={ref} style={{ width: '100%', ...style }} />
}
