import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import Clock from './components/Clock'
import Dashboard from './pages/Dashboard'
import StockSearch from './pages/StockSearch'
import Trending from './pages/Trending'
import AIInsights from './pages/AIInsights'
import Predictions from './pages/Predictions'
import Watchlist from './pages/Watchlist'
import ChatAgent from './pages/ChatAgent'

const NAV = [
  { to: '/', label: '📊 Dashboard' },
  { to: '/search', label: '🔍 Stock Search' },
  { to: '/trending', label: '🔥 Trending' },
  { to: '/ai', label: '🤖 AI Insights' },
  { to: '/predictions', label: '🔮 Predictions' },
  { to: '/watchlist', label: '⭐ Watchlist' },
  { to: '/ask', label: '💬 Ask AI' },
]

function Sidebar() {
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
      <Clock />
    </aside>
  )
}

function MobileNav() {
  return (
    <div className="md:hidden bg-[#12141e] border-b border-slate-800">
      <div className="flex items-center justify-between px-3 pt-2 pb-1">
        <span className="text-white text-sm font-bold">📈 Stock Insights</span>
        <Clock compact={true} />
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

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <MobileNav />
          <main className="flex-1 p-4 md:p-6 max-w-5xl w-full mx-auto">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/search" element={<StockSearch />} />
              <Route path="/trending" element={<Trending />} />
              <Route path="/ai" element={<AIInsights />} />
              <Route path="/predictions" element={<Predictions />} />
              <Route path="/watchlist" element={<Watchlist />} />
              <Route path="/ask" element={<ChatAgent />} />
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  )
}
