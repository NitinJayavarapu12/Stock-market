import { BrowserRouter, Routes, Route, NavLink, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import Clock from './components/Clock'
import Dashboard from './pages/Dashboard'
import StockAnalysis from './pages/StockAnalysis'
import Trending from './pages/Trending'
import Predictions from './pages/Predictions'
import Watchlist from './pages/Watchlist'
import ChatAgent from './pages/ChatAgent'
import Login from './pages/Login'
import Register from './pages/Register'

const NAV = [
  { to: '/', label: '📊 Dashboard' },
  { to: '/analysis', label: '🔍 Stock Analysis' },
  { to: '/trending', label: '🔥 Trending' },
  { to: '/predictions', label: '🔮 Predictions' },
  { to: '/watchlist', label: '⭐ Watchlist' },
  { to: '/ask', label: '💬 Ask AI' },
]

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return (
    <div className="min-h-screen bg-[#0d0f1a] flex items-center justify-center">
      <p className="text-slate-400">Loading...</p>
    </div>
  )
  if (!user) return <Navigate to="/login" replace />
  return children
}

function Sidebar() {
  const { user, signOut } = useAuth()
  return (
    <aside className="w-56 shrink-0 hidden md:flex flex-col bg-[#12141e] border-r border-slate-800 h-screen sticky top-0 p-4 gap-1">
      <div className="mb-6 px-2">
        <h1 className="text-lg font-bold text-white">📈 Stock Insights</h1>
        <p className="text-xs text-slate-500 mt-0.5">Indian Markets</p>
      </div>
      {NAV.map(({ to, label }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          className={({ isActive }) =>
            `px-3 py-2 rounded-lg text-sm transition ${
              isActive
                ? 'bg-blue-600 text-white font-medium'
                : 'text-slate-400 hover:text-white hover:bg-slate-800'
            }`
          }
        >
          {label}
        </NavLink>
      ))}
      <div className="mt-auto space-y-2">
        <Clock />
        <div className="border-t border-slate-800 pt-2">
          <p className="text-slate-500 text-xs px-2 truncate">{user?.email}</p>
          <button
            onClick={signOut}
            className="mt-1 w-full text-left px-2 py-1.5 text-slate-400 hover:text-red-400 text-xs rounded transition"
          >
            Sign out
          </button>
        </div>
      </div>
    </aside>
  )
}

function MobileNav() {
  const { signOut } = useAuth()
  return (
    <div className="md:hidden bg-[#12141e] border-b border-slate-800">
      <div className="flex items-center justify-between px-3 pt-2 pb-1">
        <span className="text-white text-sm font-bold">📈 Stock Insights</span>
        <div className="flex items-center gap-3">
          <Clock compact={true} />
          <button onClick={signOut} className="text-slate-500 hover:text-red-400 text-xs transition">
            Sign out
          </button>
        </div>
      </div>
      <nav className="flex overflow-x-auto px-2 pb-1 gap-1">
        {NAV.map(({ to, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `shrink-0 px-3 py-1.5 rounded-lg text-xs whitespace-nowrap transition ${
                isActive ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white'
              }`
            }
          >
            {label}
          </NavLink>
        ))}
      </nav>
    </div>
  )
}

function AppShell() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <MobileNav />
        <main className="flex-1 p-4 md:p-6 max-w-5xl w-full mx-auto">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/analysis" element={<StockAnalysis />} />
            <Route path="/trending" element={<Trending />} />
            <Route path="/predictions" element={<Predictions />} />
            <Route path="/watchlist" element={<Watchlist />} />
            <Route path="/ask" element={<ChatAgent />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route
            path="/*"
            element={
              <ProtectedRoute>
                <AppShell />
              </ProtectedRoute>
            }
          />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
