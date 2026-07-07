import { createContext, useContext } from 'react'

/** 交易模式：实盘 / 模拟盘。两套镜像账户，除关注列表外全隔离（FR-1.1）。 */
export type Mode = 'live' | 'sim'

export interface ModeContextValue {
  mode: Mode
  setMode: (m: Mode) => void
}

export const STORAGE_KEY = 'vgrid.mode'

export const ModeContext = createContext<ModeContextValue | null>(null)

export function readInitialMode(): Mode {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'live' ? 'live' : 'sim'
  } catch {
    return 'sim'
  }
}

export function useMode(): ModeContextValue {
  const ctx = useContext(ModeContext)
  if (ctx === null) {
    throw new Error('useMode 必须在 ModeProvider 内使用')
  }
  return ctx
}
