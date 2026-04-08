import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import api from '../api/client'
import SymbolSearch from '../components/SymbolSearch'

function HoldingRow({ holding, onRemove }) {
  return (
    <div className="flex items-center justify-between bg-[#12141e] rounded-lg px-3 py-2 text-sm">
      <div>
        <span className="text-white font-medium">{holding.symbol}</span>
        <span className="text-slate-400 ml-2">{holding.company}</span>
      </div>
      <div className="flex items-center gap-3">
        <span className="text-slate-300">{holding.quantity} shares @ ₹{holding.avg_buy_price}</span>
        <button onClick={() => onRemove(holding.symbol)} className="text-red-400 hover:text-red-300 text-xs">✕</button>
      </div>
    </div>
  )
}

export default function Register() {
  const { signUp, signIn } = useAuth()
  const navigate = useNavigate()

  const [step, setStep] = useState(1) // 1 = account, 2 = portfolio
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  // Portfolio step
  const [holdings, setHoldings] = useState([])
  const [selectedSymbol, setSelectedSymbol] = useState('')
  const [selectedCompany, setSelectedCompany] = useState('')
  const [qty, setQty] = useState('')
  const [buyPrice, setBuyPrice] = useState('')
  const [csvFile, setCsvFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [session, setSession] = useState(null)

  async function handleAccountSubmit(e) {
    e.preventDefault()
    setError('')
    if (password !== confirm) { setError('Passwords do not match'); return }
    if (password.length < 6) { setError('Password must be at least 6 characters'); return }
    setLoading(true)
    try {
      const data = await signUp(email, password)
      // Sign in immediately after signup to get a session
      const signedIn = await signIn(email, password)
      setSession(signedIn.session)
      setStep(2)
    } catch (err) {
      setError(err.message || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  function addHolding() {
    if (!selectedSymbol || !qty || !buyPrice) return
    const existing = holdings.find(h => h.symbol === selectedSymbol)
    if (existing) return
    setHoldings(prev => [...prev, {
      symbol: selectedSymbol,
      company: selectedCompany,
      quantity: parseFloat(qty),
      avg_buy_price: parseFloat(buyPrice),
    }])
    setSelectedSymbol('')
    setSelectedCompany('')
    setQty('')
    setBuyPrice('')
  }

  function removeHolding(symbol) {
    setHoldings(prev => prev.filter(h => h.symbol !== symbol))
  }

  async function handleCsvUpload() {
    if (!csvFile || !session) return
    setUploading(true)
    const form = new FormData()
    form.append('file', csvFile)
    try {
      const resp = await api.post('/api/portfolio/upload-csv', form, {
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          'Content-Type': 'multipart/form-data',
        },
      })
      alert(`Imported ${resp.data.imported} holdings from CSV`)
      navigate('/')
    } catch (err) {
      setError(err.response?.data?.detail || 'CSV upload failed')
    } finally {
      setUploading(false)
    }
  }

  async function handlePortfolioSubmit() {
    if (!session) { navigate('/'); return }
    setLoading(true)
    try {
      for (const h of holdings) {
        await api.post('/api/portfolio', h, {
          headers: { Authorization: `Bearer ${session.access_token}` },
        })
      }
      navigate('/')
    } catch (err) {
      setError('Failed to save portfolio. You can add it later from the Dashboard.')
      navigate('/')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#0d0f1a] flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white">📈 Stock Insights</h1>
          <p className="text-slate-400 mt-2">Create your account</p>
        </div>

        {/* Step indicator */}
        <div className="flex items-center gap-2 mb-6">
          {['Account', 'Portfolio'].map((label, i) => (
            <div key={label} className="flex items-center gap-2">
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${step > i + 1 ? 'bg-green-600 text-white' : step === i + 1 ? 'bg-blue-600 text-white' : 'bg-slate-700 text-slate-400'}`}>
                {step > i + 1 ? '✓' : i + 1}
              </div>
              <span className={`text-sm ${step === i + 1 ? 'text-white' : 'text-slate-500'}`}>{label}</span>
              {i < 1 && <div className="flex-1 h-px bg-slate-700 mx-2" />}
            </div>
          ))}
        </div>

        <div className="bg-[#1e2130] rounded-2xl p-8 border border-slate-700/50">

          {/* Step 1: Account */}
          {step === 1 && (
            <>
              <h2 className="text-xl font-semibold text-white mb-6">Create account</h2>
              <form onSubmit={handleAccountSubmit} className="space-y-4">
                <div>
                  <label className="text-slate-400 text-sm block mb-1">Email</label>
                  <input type="email" value={email} onChange={e => setEmail(e.target.value)} required
                    placeholder="you@example.com"
                    className="w-full bg-[#12141e] border border-slate-700 rounded-lg px-4 py-2.5 text-white placeholder-slate-600 focus:outline-none focus:border-blue-500" />
                </div>
                <div>
                  <label className="text-slate-400 text-sm block mb-1">Password</label>
                  <input type="password" value={password} onChange={e => setPassword(e.target.value)} required
                    placeholder="Min 6 characters"
                    className="w-full bg-[#12141e] border border-slate-700 rounded-lg px-4 py-2.5 text-white placeholder-slate-600 focus:outline-none focus:border-blue-500" />
                </div>
                <div>
                  <label className="text-slate-400 text-sm block mb-1">Confirm Password</label>
                  <input type="password" value={confirm} onChange={e => setConfirm(e.target.value)} required
                    placeholder="••••••••"
                    className="w-full bg-[#12141e] border border-slate-700 rounded-lg px-4 py-2.5 text-white placeholder-slate-600 focus:outline-none focus:border-blue-500" />
                </div>
                {error && <p className="text-red-400 text-sm bg-red-900/20 border border-red-800 rounded-lg px-3 py-2">{error}</p>}
                <button type="submit" disabled={loading}
                  className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white py-2.5 rounded-lg font-medium transition">
                  {loading ? 'Creating account...' : 'Continue'}
                </button>
              </form>
              <p className="text-slate-500 text-sm text-center mt-6">
                Already have an account?{' '}
                <Link to="/login" className="text-blue-400 hover:text-blue-300">Sign in</Link>
              </p>
            </>
          )}

          {/* Step 2: Portfolio */}
          {step === 2 && (
            <>
              <h2 className="text-xl font-semibold text-white mb-1">Add your portfolio</h2>
              <p className="text-slate-400 text-sm mb-6">Add your current stock holdings so the AI can give personalised advice. You can skip this and add later.</p>

              {/* CSV upload option */}
              <div className="bg-[#12141e] rounded-lg p-4 border border-slate-700 mb-4">
                <p className="text-slate-300 text-sm font-medium mb-2">📁 Upload from broker (CSV)</p>
                <p className="text-slate-500 text-xs mb-3">Download your holdings CSV from Zerodha, Groww, Upstox or any broker and upload here.</p>
                <div className="flex gap-2">
                  <input type="file" accept=".csv" onChange={e => setCsvFile(e.target.files[0])}
                    className="flex-1 text-slate-400 text-xs file:mr-2 file:py-1 file:px-3 file:rounded file:border-0 file:bg-slate-700 file:text-white file:text-xs" />
                  <button onClick={handleCsvUpload} disabled={!csvFile || uploading}
                    className="bg-green-700 hover:bg-green-600 disabled:opacity-50 text-white px-3 py-1.5 rounded text-xs font-medium transition">
                    {uploading ? 'Uploading...' : 'Upload'}
                  </button>
                </div>
              </div>

              <div className="flex items-center gap-3 mb-4">
                <div className="flex-1 h-px bg-slate-700" />
                <span className="text-slate-500 text-xs">or add manually</span>
                <div className="flex-1 h-px bg-slate-700" />
              </div>

              {/* Manual add */}
              <div className="space-y-2 mb-4">
                <SymbolSearch
                  placeholder="Search company e.g. Infosys, TCS"
                  onSelect={(sym, company) => { setSelectedSymbol(sym); setSelectedCompany(company || '') }}
                />
                <div className="grid grid-cols-2 gap-2">
                  <input type="number" value={qty} onChange={e => setQty(e.target.value)} placeholder="Quantity"
                    className="bg-[#12141e] border border-slate-700 rounded-lg px-3 py-2 text-white text-sm placeholder-slate-600 focus:outline-none focus:border-blue-500" />
                  <input type="number" value={buyPrice} onChange={e => setBuyPrice(e.target.value)} placeholder="Avg buy price (₹)"
                    className="bg-[#12141e] border border-slate-700 rounded-lg px-3 py-2 text-white text-sm placeholder-slate-600 focus:outline-none focus:border-blue-500" />
                </div>
                <button onClick={addHolding} disabled={!selectedSymbol || !qty || !buyPrice}
                  className="w-full bg-slate-700 hover:bg-slate-600 disabled:opacity-40 text-white py-2 rounded-lg text-sm transition">
                  + Add holding
                </button>
              </div>

              {/* Holdings list */}
              {holdings.length > 0 && (
                <div className="space-y-2 mb-4 max-h-48 overflow-y-auto">
                  {holdings.map(h => <HoldingRow key={h.symbol} holding={h} onRemove={removeHolding} />)}
                </div>
              )}

              {error && <p className="text-red-400 text-sm mb-3">{error}</p>}

              <div className="flex gap-2">
                <button onClick={() => navigate('/')} className="flex-1 bg-slate-800 hover:bg-slate-700 text-slate-300 py-2.5 rounded-lg text-sm transition">
                  Skip for now
                </button>
                <button onClick={handlePortfolioSubmit} disabled={loading}
                  className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white py-2.5 rounded-lg text-sm font-medium transition">
                  {loading ? 'Saving...' : `Save & Continue${holdings.length > 0 ? ` (${holdings.length})` : ''}`}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
