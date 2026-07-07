import { useQuery } from '@tanstack/react-query'
import { getStrategy, listStrategies, previewLadder, type LadderView } from '../api/client'
import { GridLadder } from './GridLadder'
import { Placeholder } from './Placeholder'

/** 取第一个策略的 config 预览其网格阶梯。实例绑定（FR-3）落地后改走 /api/state 的真实阶梯。 */
export function LadderPanel() {
  const q = useQuery({
    queryKey: ['ladder', 'preview', 'first-strategy'],
    queryFn: async (): Promise<LadderView | null> => {
      const strategies = await listStrategies()
      const first = strategies[0]
      if (first === undefined) return null
      const config = await getStrategy(first.name)
      return previewLadder(config)
    },
  })

  if (q.isLoading) {
    return (
      <div className="placeholder">
        <span className="ph-title">加载阶梯…</span>
      </div>
    )
  }
  if (q.isError) {
    return (
      <div className="placeholder">
        <span className="ph-mark">✕</span>
        <span className="ph-title">阶梯加载失败：{(q.error as Error).message}</span>
      </div>
    )
  }
  if (!q.data) {
    return <Placeholder title="无策略：去「策略库」新建一条，阶梯将按它预览" fr="FR-4 · 需要策略配置" />
  }
  return <GridLadder view={q.data} />
}
