import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import api from '../api/client'

export function usePredictionJob() {
  const [jobId, setJobId] = useState(null)
  const [symbol, setSymbol] = useState(null)
  const [status, setStatus] = useState('idle') // idle | starting | pending | done | error
  const [result, setResult] = useState(null)

  const { data: pollData } = useQuery({
    queryKey: ['prediction-job', jobId],
    queryFn: () => api.get(`/api/predictions/jobs/${jobId}`).then((r) => r.data),
    enabled: status === 'pending' && !!jobId,
    refetchInterval: 3000,
  })

  // Handle poll result
  if (pollData && status === 'pending') {
    if (pollData.status === 'done') {
      setResult(pollData.result)
      setStatus('done')
    } else if (pollData.status === 'error') {
      setStatus('error')
    }
  }

  async function startPrediction(sym) {
    setSymbol(sym)
    setStatus('starting')
    setResult(null)
    setJobId(null)
    try {
      const { data } = await api.post(`/api/predictions/${sym}/start`)
      setJobId(data.job_id)
      setStatus('pending')
    } catch {
      setStatus('error')
    }
  }

  function reset() {
    setJobId(null)
    setSymbol(null)
    setStatus('idle')
    setResult(null)
  }

  return { startPrediction, reset, status, result, symbol }
}
