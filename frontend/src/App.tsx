import { Layout, Menu } from 'antd'
import { Link, Route, Routes, useLocation } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Backtest from './pages/Backtest'
import Strategies from './pages/Strategies'
import Runners from './pages/Runners'
import Watchlist from './pages/Watchlist'

const { Sider, Content } = Layout

const NAV = [
  { path: '/', label: '仪表盘' },
  { path: '/backtest', label: '回测' },
  { path: '/strategies', label: '策略库' },
  { path: '/runners', label: '模拟盘' },
  { path: '/watchlist', label: '关注列表' },
] as const

function App() {
  const location = useLocation()
  const current =
    NAV.find(
      (n) =>
        n.path === location.pathname ||
        (n.path !== '/' && location.pathname.startsWith(n.path)),
    )?.path ?? '/'

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider theme="dark" width={180} breakpoint="lg" collapsible>
        <div
          style={{
            color: '#fff',
            padding: '20px 16px',
            fontSize: '20px',
            fontWeight: 600,
            letterSpacing: 1,
          }}
        >
          Vgrid
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[current]}
          items={NAV.map((n) => ({
            key: n.path,
            label: <Link to={n.path}>{n.label}</Link>,
          }))}
        />
      </Sider>
      <Layout>
        <Content style={{ padding: 24, background: '#f0f2f5' }}>
          <div style={{ maxWidth: 1200, margin: '0 auto' }}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/backtest" element={<Backtest />} />
              <Route path="/strategies" element={<Strategies />} />
              <Route path="/runners" element={<Runners />} />
              <Route path="/watchlist" element={<Watchlist />} />
            </Routes>
          </div>
        </Content>
      </Layout>
    </Layout>
  )
}

export default App
