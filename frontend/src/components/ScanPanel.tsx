import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { type ScanMetric, type ScanResult, runScan } from '../api/client'
import type { BtForm } from '../utils/btForm'
import { Panel } from './Panel'

const METRICS: [ScanMetric, string][] = [
  ['sharpe', '夏普'],
  ['total_return', '总收益'],
  ['annualized_return', '年化'],
  ['calmar', 'Calmar'],
]

interface Props {
  form: BtForm
  onAdopt: (patch: Partial<BtForm>) => void
}

/** 参数扫描：从当前回测表单取固定配置，扫 grid_count / 每格金额 候选，按 metric 排 top-N。 */
export function ScanPanel({ form, onAdopt }: Props) {
  const [metric, setMetric] = useState<ScanMetric>('sharpe')
  const [top, setTop] = useState('10')
  const [gridCounts, setGridCounts] = useState('6,10,15,20,30')
  const [amounts, setAmounts] = useState('')

  const scan = useMutation({ mutationFn: runScan })

  const run = () => {
    const vary: Record<string, unknown[]> = {}
    const gc = parseNums(gridCounts)
    if (gc.length) vary.grid_count = gc
    const amt = parseList(amounts)
    if (amt.length) vary.per_grid_amount = amt

    const fixed: Record<string, unknown> = {
      symbol: form.symbol,
      lower_price: form.lower_price,
      upper_price: form.upper_price,
      per_grid_amount: form.per_grid_amount,
      capital_cap: form.capital_cap,
      spacing_mode: form.spacing_mode,
      base_build_mode: form.base_build_mode,
      grid_count: Number(form.grid_count),
    }
    for (const k of Object.keys(vary)) delete fixed[k]

    scan.mutate({ start: form.start, end: form.end, frame: form.frame, fixed, vary, metric, top: Number(top) })
  }

  const noVary = parseNums(gridCounts).length === 0 && parseList(amounts).length === 0

  return (
    <Panel kick="参数扫描" en="SWEEP" meta="穷举 · 样本内排序" className="rise d3">
      <div className="scan">
        <div className="scan-ctl">
          <label>
            扫描格数
            <input value={gridCounts} onChange={(e) => setGridCounts(e.target.value)} placeholder="6,10,15,20" />
          </label>
          <label>
            扫描每格金额
            <input value={amounts} onChange={(e) => setAmounts(e.target.value)} placeholder="留空=不扫" />
          </label>
          <label>
            排序
            <select value={metric} onChange={(e) => setMetric(e.target.value as ScanMetric)}>
              {METRICS.map(([v, l]) => (
                <option key={v} value={v}>
                  {l}
                </option>
              ))}
            </select>
          </label>
          <label>
            Top
            <input className="scan-top" type="number" value={top} onChange={(e) => setTop(e.target.value)} />
          </label>
          <button type="button" className="run scan-run" onClick={run} disabled={scan.isPending || noVary}>
            {scan.isPending ? '⏳ 扫描中…' : '穷举扫描'}
          </button>
        </div>

        {scan.error ? (
          <div className="bt-err">扫描失败：{String(scan.error)}</div>
        ) : scan.data ? (
          <ScanTable data={scan.data} onAdopt={onAdopt} />
        ) : (
          <div className="scan-hint faint">
            给格数 / 每格金额几个候选值（逗号分隔），穷举回测后按所选指标排序。⚠ 样本内最优，实盘未必。
          </div>
        )}
      </div>
    </Panel>
  )
}

function ScanTable({ data, onAdopt }: { data: ScanResult; onAdopt: (patch: Partial<BtForm>) => void }) {
  const adopt = (params: Record<string, string | number>) => {
    const patch: Partial<BtForm> = {}
    if ('grid_count' in params) patch.grid_count = String(params.grid_count)
    if ('per_grid_amount' in params) patch.per_grid_amount = String(params.per_grid_amount)
    onAdopt(patch)
  }
  return (
    <div className="scan-scroll">
      <div className="scan-sum faint">
        共扫 {data.total} 组，按 {metricLabel(data.metric)} 取前 {data.shown}。第 1 行为样本内最优。
      </div>
      <table>
        <thead>
          <tr>
            {data.vary_keys.map((k) => (
              <th key={k}>{fieldLabel(k)}</th>
            ))}
            <th>夏普</th>
            <th>总收益</th>
            <th>年化</th>
            <th>回撤</th>
            <th>胜率</th>
            <th>末权益</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {data.rows.map((r, i) => (
            <tr key={i} className={i === 0 ? 'scan-best' : undefined}>
              {data.vary_keys.map((k) => (
                <td key={k} className="b">
                  {r.params[k]}
                </td>
              ))}
              <td>{Number(r.metrics.sharpe).toFixed(2)}</td>
              <td className={Number(r.metrics.total_return) >= 0 ? 'up' : 'down'}>
                {pct(r.metrics.total_return)}
              </td>
              <td>{pct(r.metrics.annualized_return)}</td>
              <td className="down">−{(Number(r.metrics.max_drawdown) * 100).toFixed(1)}%</td>
              <td>{(Number(r.metrics.win_rate) * 100).toFixed(0)}%</td>
              <td>¥{Number(r.metrics.final_equity).toLocaleString('en-US', { maximumFractionDigits: 0 })}</td>
              <td>
                <span className="act" onClick={() => adopt(r.params)}>
                  采用
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function pct(v: string): string {
  const n = Number(v) * 100
  return `${n >= 0 ? '+' : ''}${n.toFixed(1)}%`
}

function parseNums(s: string): number[] {
  return parseList(s)
    .map(Number)
    .filter((n) => Number.isFinite(n))
}

function parseList(s: string): string[] {
  return s
    .split(/[,，\s]+/)
    .map((x) => x.trim())
    .filter(Boolean)
}

function fieldLabel(k: string): string {
  if (k === 'grid_count') return '格数'
  if (k === 'per_grid_amount') return '每格金额'
  return k
}

function metricLabel(k: string): string {
  return METRICS.find(([v]) => v === k)?.[1] ?? k
}
