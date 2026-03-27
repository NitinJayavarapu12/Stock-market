import { useState, useEffect } from 'react'

const BASE_URL = import.meta.env.VITE_API_URL || ''

export function useSSE(path, enabled) {
  const [text, setText] = useState('')
  const [done, setDone] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!enabled || !path) return
    setText('')
    setDone(false)
    setError(null)

    const es = new EventSource(`${BASE_URL}${path}`)

    es.onmessage = (e) => {
      if (e.data === '[DONE]') {
        setDone(true)
        es.close()
        return
      }
      try {
        const { text: chunk } = JSON.parse(e.data)
        setText((prev) => prev + chunk)
      } catch {
        // ignore malformed chunks
      }
    }

    es.onerror = () => {
      setError('Connection error')
      setDone(true)
      es.close()
    }

    return () => es.close()
  }, [path, enabled])

  return { text, done, error }
}
