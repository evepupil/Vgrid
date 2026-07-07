import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ModeProvider } from './mode/ModeProvider'
import 'uplot/dist/uPlot.min.css'
import './styles/tokens.css'
import './styles/base.css'
import './styles/shell.css'
import './styles/ladder.css'
import './styles/chart.css'
import './styles/portfolio.css'
import './styles/watchlist.css'
import './styles/backtest.css'
import './styles/strategies.css'
import './styles/risk.css'
import App from './App.tsx'

const queryClient = new QueryClient()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ModeProvider>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </ModeProvider>
    </QueryClientProvider>
  </StrictMode>,
)
