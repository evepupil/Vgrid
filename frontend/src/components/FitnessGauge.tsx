/** 网格适配评分槽（0–100）：一条进度条 + 数字。高分红（好）、中分强调色、低分灰。 */

interface Props {
  score: number | null
}

function color(score: number): string {
  if (score > 75) return 'var(--up)' // 高分：红=适合（吃震荡）
  if (score > 45) return 'var(--acc)'
  return 'var(--faint)'
}

export function FitnessGauge({ score }: Props) {
  if (score === null) return <span className="faint">—</span>
  const pct = Math.max(0, Math.min(100, score))
  return (
    <span className="wl-fit">
      <span className="gauge">
        <i style={{ width: `${pct}%`, background: color(score) }} />
      </span>
      {score}
    </span>
  )
}
