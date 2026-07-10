import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import {
  type IncomeEnhanceResult,
  type IncomeRow,
  getStrategy,
  listStrategies,
  runIncomeCompare,
  runIncomeEnhance,
} from '../api/client'
import { EnhanceChart } from '../components/EnhanceChart'
import { IncomeChart } from '../components/IncomeChart'
import { Panel } from '../components/Panel'
import { Placeholder } from '../components/Placeholder'
import { SectionTitle } from '../components/SectionTitle'
import { DcaForm } from '../components/DcaForm'
import { type IncomeForm, defaultIncomeForm, toIncomeBody } from '../utils/incomeForm'
import { type DcaForm as DcaFormState, defaultDcaForm, toDcaConfig } from '../utils/dcaForm'
import { fmt, upDown } from '../utils/format'

type Mode = 'compare' | 'enhance'

/** 红利页：横向对比（批量四口径）/ 增强回测（单只策略 + 分红再投）两个 Tab。 */
export default function Income() {
  const [mode, setMode] = useState<Mode>('compare')
  return (
    <div className="view">
      <SectionTitle title="红利" en="Income" />
      <div className="bt-kind">
        <button type="button" className={mode === 'compare' ? 'on' : ''} onClick={() => setMode('compare')}>
          红利对比
        </button>
        <button type="button" className={mode === 'enhance' ? 'on' : ''} onClick={() => setMode('enhance')}>
          增强回测
        </button>
      </div>
      {mode === 'compare' ? <ComparePanel /> : <EnhancePanel />}
    </div>
  )
}

/** 批量红利 ETF 四口径对比。 */
function ComparePanel() {
  const [form, setForm] = useState<IncomeForm>(() => defaultIncomeForm())
  const [selCode, setSelCode] = useState<string | null>(null)
  const cmp = useMutation({ mutationFn: runIncomeCompare })
  const run = () => {
    cmp.mutate(toIncomeBody(form))
    setSelCode(null)
  }
  const rows: IncomeRow[] = cmp.data?.rows ?? []
  const selected = rows.find((r) => r.code === selCode) ?? rows[0]
  const set = (k: keyof IncomeForm, v: string) => setForm((f) => ({ ...f, [k]: v }))

  return (
    <div className="cmp">
      <Panel kick="对比配置" en="CONFIG" className="rise d1">
        <div className="form">
          <div className="fg">
            <label>关键词（逗号分隔，留空用默认红利池）</label>
            <input value={form.keywords} onChange={(e) => set('keywords', e.target.value)} spellCheck={false} />
          </div>
          <div className="fg">
            <label>或 直接指定代码（逗号分隔，给了跳过关键词）</label>
            <input
              value={form.symbols}
              onChange={(e) => set('symbols', e.target.value)}
              spellCheck={false}
              placeholder="如 510880,515180"
            />
          </div>
          <div className="frow">
            <Field label="起始">
              <input type="date" value={form.start} onChange={(e) => set('start', e.target.value)} />
            </Field>
            <Field label="结束">
              <input type="date" value={form.end} onChange={(e) => set('end', e.target.value)} />
            </Field>
          </div>
          <Field label="起始现金（各口径同基准满仓）">
            <input value={form.initial_cash} onChange={(e) => set('initial_cash', e.target.value)} />
          </Field>
          <button type="button" className="run" onClick={run} disabled={cmp.isPending}>
            {cmp.isPending ? '⏳ 对比运行中…' : '▶ 跑红利对比'}
          </button>
          <div className="cmp-hint">
            批量抓红利 ETF 的分红 / 价格 / 净值比四口径收益。首次跑要拉全市场名录 + 逐只分红净值，较慢。
          </div>
        </div>
      </Panel>

      <Panel
        kick="对比结果"
        en="RESULT"
        meta={cmp.data ? `查询 ${cmp.data.start}→${cmp.data.end} · 池 ${cmp.data.pool_size}、纳入 ${rows.length}` : '待运行'}
        className="rise d2"
      >
        {cmp.isPending ? (
          <Placeholder title="对比运行中…（首次抓全市场名录较慢）" fr="M7 · 红利对比" />
        ) : cmp.error ? (
          <div className="bt-err">对比失败：{String(cmp.error)}</div>
        ) : cmp.data ? (
          <div className="inc-result">
            {cmp.data.skipped.length > 0 && (
              <div className="scanrow bt-warn">
                ⚠ 跳过 {cmp.data.skipped.length} 只（无日线）：{cmp.data.skipped.slice(0, 8).join('、')}
                {cmp.data.skipped.length > 8 ? ' …' : ''}
              </div>
            )}
            <IncomeTable rows={rows} selCode={selected?.code ?? null} onPick={setSelCode} />
            {selected && (
              <div className="inc-detail">
                <div className="inc-detail__title">{selected.code} {selected.name} · 四口径收益曲线</div>
                <IncomeChart row={selected} />
                <div className="scanrow bt-warn">
                  ⚠ 费用只展示不从收益扣。「再投年化」是自然日复利；累计净值是含历史分红的长期校验基准，
                  两者差异过大说明数据口径可能不一致。
                </div>
              </div>
            )}
          </div>
        ) : (
          <Placeholder title="填关键词或代码 → ▶ 跑红利对比。排名表 + 点行看四曲线" fr="M7 · 红利对比" />
        )}
      </Panel>
    </div>
  )
}

/** 单只红利 ETF：策略（定投 / 网格）+ 分红再投增强。 */
function EnhancePanel() {
  const [symbol, setSymbol] = useState('510880')
  const [start, setStart] = useState('2021-01-01')
  const [end, setEnd] = useState('2024-12-31')
  const [kind, setKind] = useState<'dca' | 'grid'>('dca')
  const [gridName, setGridName] = useState('')
  const [dca, setDca] = useState<DcaFormState>(() => defaultDcaForm('510880'))
  const strategies = useQuery({ queryKey: ['strategies'], queryFn: listStrategies })

  const enh = useMutation({
    mutationFn: async (): Promise<IncomeEnhanceResult> => {
      const config =
        kind === 'dca' ? toDcaConfig({ ...dca, symbol }) : await getStrategy(gridName)
      return runIncomeEnhance({ symbol, start, end, strategy: kind, config })
    },
  })
  const canRun = kind === 'dca' || gridName !== ''
  const run = () => {
    if (canRun) enh.mutate()
  }
  const d = enh.data

  return (
    <div className="cmp">
      <Panel kick="增强配置" en="CONFIG" className="rise d1">
        <div className="form">
          <div className="frow">
            <Field label="标的 SYMBOL">
              <input value={symbol} onChange={(e) => setSymbol(e.target.value)} spellCheck={false} />
            </Field>
            <Field label="策略">
              <select value={kind} onChange={(e) => setKind(e.target.value as 'dca' | 'grid')}>
                <option value="dca">定投</option>
                <option value="grid">网格（策略库）</option>
              </select>
            </Field>
          </div>
          <div className="frow">
            <Field label="起始">
              <input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
            </Field>
            <Field label="结束">
              <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
            </Field>
          </div>

          {kind === 'dca' ? (
            <DcaForm form={dca} onChange={setDca} onRun={() => {}} pending={false} compact />
          ) : (
            <div className="fg">
              <label>网格策略（从策略库）</label>
              <select value={gridName} onChange={(e) => setGridName(e.target.value)}>
                <option value="">（选一个）</option>
                {(strategies.data ?? []).map((s) => (
                  <option key={s.name} value={s.name}>{s.name} · {s.symbol}</option>
                ))}
              </select>
            </div>
          )}

          <button type="button" className="run" onClick={run} disabled={!canRun || enh.isPending}>
            {enh.isPending ? '⏳ 增强回测中…' : '▶ 跑增强回测'}
          </button>
          <div className="cmp-hint">
            策略跑在不复权价上，分红按持仓在发放日到账、下一开盘再投。直观量化「分红给策略加了多少」。
          </div>
        </div>
      </Panel>

      <Panel
        kick="增强结果"
        en="RESULT"
        meta={d ? `${symbol} · ${start}→${end}` : '待运行'}
        className="rise d2"
      >
        {enh.isPending ? (
          <Placeholder title="增强回测运行中…" fr="M7 · 红利增强" />
        ) : enh.error ? (
          <div className="bt-err">增强失败：{String(enh.error)}</div>
        ) : d ? (
          <div className="inc-result">
            <div className="inc-kpi">
              <Kpi label="策略收益（价格口径）" v={d.strategy_return} tone={upDown(Number(d.strategy_return))} />
              <Kpi label="分红再投增强" v={d.enhanced_return} tone={upDown(Number(d.enhanced_return))} />
              <Kpi label="分红贡献（增强−策略）" v={d.dividend_boost} tone={upDown(Number(d.dividend_boost))} />
              <Kpi label="累计到账分红" v={`¥ ${fmt(Number(d.dividend_cash_total), 0)}`} />
            </div>
            <EnhanceChart result={d} />
            <div className="scanrow bt-warn">
              ⚠ 策略在除权日价格真跌（不复权），分红作补偿：按持仓在发放日到账、下一开盘再投（扣银河费、
              买不满一手留现金）。增强线与策略线之差就是分红的累积贡献。
            </div>
          </div>
        ) : (
          <Placeholder title="选策略 + 配定投 → ▶ 跑增强回测。策略 vs 分红再投两条曲线" fr="M7 · 红利增强" />
        )}
      </Panel>
    </div>
  )
}

function Kpi({ label, v, tone }: { label: string; v: string; tone?: string }) {
  const n = Number(v)
  const shown = isNaN(n) ? v : `${n >= 0 ? '+' : ''}${(n * 100).toFixed(2)}%`
  return (
    <div className="inc-kpi__cell">
      <div className="inc-kpi__label">{label}</div>
      <div className={`inc-kpi__value ${tone ?? ''}`}>{shown}</div>
    </div>
  )
}

function IncomeTable({
  rows,
  selCode,
  onPick,
}: {
  rows: IncomeRow[]
  selCode: string | null
  onPick: (code: string) => void
}) {
  return (
    <div className="scan-scroll">
      <table className="inc-table">
        <thead>
          <tr>
            <th>#</th>
            <th>代码</th>
            <th>名称</th>
            <th>样本期</th>
            <th>再投年化</th>
            <th>分红再投</th>
            <th>价格</th>
            <th>现金分红</th>
            <th>累计净值</th>
            <th>回撤</th>
            <th>近12月分红率</th>
            <th>费用</th>
            <th>质量</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.code} className={r.code === selCode ? 'inc-sel' : undefined} onClick={() => onPick(r.code)}>
              <td>{i + 1}</td>
              <td className="b">{r.code}</td>
              <td>{r.name}</td>
              <td className="faint">{fmtMonth(r.metrics.sample_start)}~{fmtMonth(r.metrics.sample_end)}</td>
              <td className={upDown(Number(r.metrics.annualized_return))}>{pct(r.metrics.annualized_return)}</td>
              <td className={upDown(Number(r.metrics.reinvest_return))}>{pct(r.metrics.reinvest_return)}</td>
              <td>{pct(r.metrics.price_return)}</td>
              <td>{pct(r.metrics.cash_dividend_return)}</td>
              <td>{pct(r.metrics.acc_nav_return)}</td>
              <td className="down">−{(Number(r.metrics.max_drawdown) * 100).toFixed(1)}%</td>
              <td>{pct(r.metrics.ttm_dividend_yield)}</td>
              <td>{r.metrics.total_expense_rate ? pct(r.metrics.total_expense_rate) : '—'}</td>
              <td>
                <span className={`inc-q inc-q--${r.metrics.data_quality}`}>{qualityLabel(r.metrics.data_quality)}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function fmtMonth(s: string): string {
  return s.slice(0, 7)
}

function pct(v: string | null): string {
  if (v == null) return '—'
  const n = Number(v) * 100
  return `${n >= 0 ? '+' : ''}${n.toFixed(1)}%`
}

function qualityLabel(q: string): string {
  const map: Record<string, string> = {
    ok: '完整',
    partial: '缺口',
    missing_dividend: '缺分红',
    missing_nav: '缺净值',
    price_only: '仅价',
  }
  return map[q] ?? q
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="fg">
      <label>{label}</label>
      {children}
    </div>
  )
}
