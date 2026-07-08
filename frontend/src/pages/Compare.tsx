import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { type CompareResult, type CompareRow, getStrategy, listStrategies, runCompare } from '../api/client'
import { CompareChart } from '../components/CompareChart'
import { DcaForm } from '../components/DcaForm'
import { Panel } from '../components/Panel'
import { Placeholder } from '../components/Placeholder'
import { SectionTitle } from '../components/SectionTitle'
import { type DcaForm as DcaFormState, defaultDcaForm, toDcaConfig } from '../utils/dcaForm'
import { fmt, upDown } from '../utils/format'

/** 策略对比：共享区间 + 网格策略（选库里的）+ 定投（内联）→ 三方净值叠加 + 收益/XIRR 对照表。 */
export default function Compare() {
  const [params] = useSearchParams()
  const symbol0 = params.get('symbol') ?? '159920'
  const [symbol, setSymbol] = useState(symbol0)
  const [start, setStart] = useState('2024-01-01')
  const [end, setEnd] = useState('2025-07-01')
  const [frame, setFrame] = useState('1d')
  const [initialCash, setInitialCash] = useState('50000')
  const [gridName, setGridName] = useState('')
  const [dcaOn, setDcaOn] = useState(true)
  const [dca, setDca] = useState<DcaFormState>(() => defaultDcaForm(symbol0))

  const strategies = useQuery({ queryKey: ['strategies'], queryFn: listStrategies })

  const cmp = useMutation({
    mutationFn: async (): Promise<CompareResult> => {
      const grid_config = gridName ? await getStrategy(gridName) : null
      const dca_config = dcaOn ? toDcaConfig({ ...dca, symbol }) : null
      return runCompare({
        symbol,
        start,
        end,
        frame,
        initial_cash: initialCash || null,
        grid_config,
        dca_config,
      })
    },
  })

  const hasStrategy = !!gridName || dcaOn
  const run = () => {
    if (hasStrategy) cmp.mutate()
  }
  const meta = cmp.data ? `${symbol} · ${start}→${end}` : '待运行'

  return (
    <div className="view">
      <SectionTitle title="策略对比" en="Compare" />
      <div className="cmp">
        <Panel kick="对比配置" en="CONFIG" className="rise d1">
          <div className="form">
            <div className="fg">
              <label>标的 SYMBOL</label>
              <input value={symbol} onChange={(e) => setSymbol(e.target.value)} spellCheck={false} />
            </div>
            <div className="frow">
              <Field label="起始">
                <input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
              </Field>
              <Field label="结束">
                <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
              </Field>
            </div>
            <div className="frow">
              <Field label="起始现金">
                <input value={initialCash} onChange={(e) => setInitialCash(e.target.value)} />
              </Field>
              <Field label="周期">
                <select value={frame} onChange={(e) => setFrame(e.target.value)}>
                  <option value="1d">日线</option>
                  <option value="1m">1 分钟</option>
                </select>
              </Field>
            </div>

            <div className="fg">
              <label>网格策略（从策略库）</label>
              <select value={gridName} onChange={(e) => setGridName(e.target.value)}>
                <option value="">（不比网格）</option>
                {(strategies.data ?? []).map((s) => (
                  <option key={s.name} value={s.name}>
                    {s.name} · {s.symbol}
                  </option>
                ))}
              </select>
            </div>

            <label className="cmp-toggle">
              <input type="checkbox" checked={dcaOn} onChange={(e) => setDcaOn(e.target.checked)} />
              比定投
            </label>
            {dcaOn && (
              <DcaForm form={dca} onChange={setDca} onRun={() => {}} pending={false} compact />
            )}

            <button type="button" className="run" onClick={run} disabled={!hasStrategy || cmp.isPending}>
              {cmp.isPending ? '⏳ 对比运行中…' : '▶ 跑对比'}
            </button>
            {!hasStrategy && <div className="cmp-hint">至少选一个网格策略，或勾选「比定投」。</div>}
          </div>
        </Panel>

        <Panel kick="对比结果" en="RESULT" meta={meta} className="rise d2">
          {cmp.isPending ? (
            <Placeholder title="对比运行中…" fr="M6 · 对比" />
          ) : cmp.error ? (
            <div className="bt-err">对比失败：{String(cmp.error)}</div>
          ) : cmp.data ? (
            <CompareView result={cmp.data} />
          ) : (
            <Placeholder
              title="选网格策略 + 配定投 → ▶ 跑对比。三方净值叠加 + 收益 / 年化 / 回撤 / XIRR 对照"
              fr="M6 · 对比"
            />
          )}
        </Panel>
      </div>
    </div>
  )
}

function CompareView({ result }: { result: CompareResult }) {
  let best: CompareRow | undefined
  for (const r of result.rows) {
    if (!best || Number(r.final_equity) > Number(best.final_equity)) best = r
  }
  return (
    <div className="cmp-result">
      <CompareChart rows={result.rows} />
      <div className="scan-scroll">
        <table className="cmp-table">
          <thead>
            <tr>
              <th>策略</th>
              <th>末权益</th>
              <th>净利</th>
              <th>收益率</th>
              <th>年化</th>
              <th>最大回撤</th>
              <th>手续费</th>
              <th>笔数</th>
              <th>实际投入</th>
              <th>XIRR</th>
            </tr>
          </thead>
          <tbody>
            {result.rows.map((r) => (
              <Row key={r.name} r={r} best={best?.name === r.name} />
            ))}
          </tbody>
        </table>
      </div>
      <div className="scanrow bt-warn">
        ⚠ 收益率对起始现金 ¥ {fmt(Number(result.initial_cash), 0)} 算（同一笔钱、同一段行情谁最后更有钱）。
        定投的钱分批进场，另给 XIRR（按每笔投入时间贴现的真实年化），和年化的自然日口径不同，别直接相较。
      </div>
    </div>
  )
}

function Row({ r, best }: { r: CompareRow; best: boolean }) {
  return (
    <tr className={best ? 'cmp-best' : undefined}>
      <td className={best ? 'b' : undefined}>{r.name}</td>
      <td>¥ {fmt(Number(r.final_equity), 0)}</td>
      <td className={upDown(Number(r.profit))}>¥ {fmt(Number(r.profit), 0)}</td>
      <td className={upDown(Number(r.total_return))}>{pct(r.total_return)}</td>
      <td>{pct(r.annualized_return)}</td>
      <td className="down">−{(Number(r.max_drawdown) * 100).toFixed(1)}%</td>
      <td>¥ {fmt(Number(r.total_fee), 2)}</td>
      <td>{r.n_trades}</td>
      <td>{r.invested ? `¥ ${fmt(Number(r.invested), 0)}` : '—'}</td>
      <td className={r.xirr ? upDown(Number(r.xirr)) : undefined}>{pct(r.xirr)}</td>
    </tr>
  )
}

function pct(v: string | null): string {
  if (v == null) return '—'
  const n = Number(v) * 100
  return `${n >= 0 ? '+' : ''}${n.toFixed(1)}%`
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="fg">
      <label>{label}</label>
      {children}
    </div>
  )
}
