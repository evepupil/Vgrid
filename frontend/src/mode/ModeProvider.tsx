import { useCallback, useLayoutEffect, useState, type ReactNode } from 'react'
import { setApiMode } from '../api/client'
import { ModeContext, readInitialMode, STORAGE_KEY, type Mode } from './context'

/** 全局交易模式 Provider：把模式写到根元素 data-mode（CSS 靠它切换强调色）并持久化。 */
export function ModeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<Mode>(readInitialMode)

  useLayoutEffect(() => {
    document.documentElement.dataset.mode = mode
  }, [mode])

  const setMode = useCallback((m: Mode) => {
    setModeState(m)
    setApiMode(m) // 同步给 API client，mode 相关请求随之带 ?mode=（FR-1.2）
    try {
      localStorage.setItem(STORAGE_KEY, m)
    } catch {
      // localStorage 不可用（隐私模式等）时忽略，模式仍在内存生效
    }
  }, [])

  return <ModeContext value={{ mode, setMode }}>{children}</ModeContext>
}
