import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { type IncomeRow, runIncomeCompare } from '../api/client'
import { IncomeChart } from '../components/IncomeChart'
import { Panel } from '../components/Panel'
import { Placeholder } from '../components/Placeholder'
import { SectionTitle } from '../components/SectionTitle'
import { type IncomeForm, defaultIncomeForm, toIncomeBody } from '../utils/incomeForm'
import { upDown } from '../utils/format'

/** 红利 ETF 收益对比：关键词 / 代码筛池 → 排名表（四口径收益 + 年化 + 回撤 + 分红率 + 费用 + 质量）
 * + 点行看该 ETF 四曲线（价格 / 价+现分 / 价+分再投 / 累计净值）。 */
export default function Income() {
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
    <div className="view">
      <SectionTitle title="红利对比" en="Income" />
      <div className="cmp">
        <Panel kick="对比配置" en="CONFIG" className="rise d1">
          <div className="form">
            <div className="fg">
              <label>关键词（逗号分隔，留空用默认红利池）</label>
              <input
                value={form.keywords}
                onChange={(e) => set('keywords', e.target.value)}
                spellCheck={false}
              />
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
              <input
                value={form.initial_cash}
                onChange={(e) => set('initial_cash', e.target.value)}
              />
            </Field>
            <button type="button" className="run" onClick={run} disabled={cmp.isPending}>
              {cmp.isPending ? '⏳ 对比运行中…' : '▶ 跑红利对比'}
            </button>
            <div className="cmp-hint">
              批量抓红利 ETF 的分红 / 价格 / 净值比四口径收益。首次跑要拉全市场名录 +
              逐只分红净值，较慢（池大时几十秒）。
            </div>
          </div>
        </Panel>

        <Panel
          kick="对比结果"
          en="RESULT"
          meta={
            cmp.data
              ? `${cmp.data.start}→${cmp.data.end} · 池 ${cmp.data.pool_size}、纳入 ${rows.length}`
              : '待运行'
          }
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
                  <div className="inc-detail__title">
                    {selected.code} {selected.name} · 四口径收益曲线
                  </div>
                  <IncomeChart row={selected} />
                  <div className="scanrow bt-warn">
                    ⚠ 费用只展示不从收益扣（净值/价格已含费，避免重复扣）。「再投年化」是自然日
                    复利；累计净值是含历史分红的长期校验基准，两者差异过大说明数据口径可能不一致。
                  </div>
                </div>
              )}
            </div>
          ) : (
            <Placeholder
              title="填关键词或代码 → ▶ 跑红利对比。排名表 + 点行看四曲线"
              fr="M7 · 红利对比"
            />
          )}
        </Panel>
      </div>
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
            <tr
              key={r.code}
              className={r.code === selCode ? 'inc-sel' : undefined}
              onClick={() => onPick(r.code)}
            >
              <td>{i + 1}</td>
              <td className="b">{r.code}</td>
              <td>{r.name}</td>
              <td className={upDown(Number(r.metrics.annualized_return))}>
                {pct(r.metrics.annualized_return)}
              </td>
              <td className={upDown(Number(r.metrics.reinvest_return))}>
                {pct(r.metrics.reinvest_return)}
              </td>
              <td>{pct(r.metrics.price_return)}</td>
              <td>{pct(r.metrics.cash_dividend_return)}</td>
              <td>{pct(r.metrics.acc_nav_return)}</td>
              <td className="down">−{(Number(r.metrics.max_drawdown) * 100).toFixed(1)}%</td>
              <td>{pct(r.metrics.ttm_dividend_yield)}</td>
              <td>{r.metrics.total_expense_rate ? pct(r.metrics.total_expense_rate) : '—'}</td>
              <td>
                <span className={`inc-q inc-q--${r.metrics.data_quality}`}>
                  {qualityLabel(r.metrics.data_quality)}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
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
