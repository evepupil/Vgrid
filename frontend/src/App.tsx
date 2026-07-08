import { Route, Routes } from 'react-router-dom'
import { Background } from './components/Background'
import { Rail } from './components/Rail'
import { SimBanner } from './components/SimBanner'
import { Ticker } from './components/Ticker'
import { Topbar } from './components/Topbar'
import Backtest from './pages/Backtest'
import Compare from './pages/Compare'
import Dashboard from './pages/Dashboard'
import Income from './pages/Income'
import Portfolio from './pages/Portfolio'
import Strategies from './pages/Strategies'
import Watchlist from './pages/Watchlist'

/** 应用外壳：背景层 + 左导航 + 顶栏/行情/模拟横幅 + 路由舞台。 */
export default function App() {
  return (
    <>
      <Background />
      <div className="app">
        <Rail />
        <div className="main">
          <Topbar />
          <Ticker />
          <SimBanner />
          <div className="stage">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/portfolio" element={<Portfolio />} />
              <Route path="/backtest" element={<Backtest />} />
              <Route path="/compare" element={<Compare />} />
              <Route path="/income" element={<Income />} />
              <Route path="/strategies" element={<Strategies />} />
              <Route path="/watchlist" element={<Watchlist />} />
            </Routes>
          </div>
        </div>
      </div>
    </>
  )
}
