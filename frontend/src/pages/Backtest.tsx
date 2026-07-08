import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  type BacktestResult as BacktestResultData,
  type DcaBacktestResult,
  runBacktest,
  runDcaBacktest,
} from '../api/client'
import { BacktestForm } from '../components/BacktestForm'
import { BacktestResult } from '../components/BacktestResult'
import { DcaForm } from '../components/DcaForm'
import { DcaResult } from '../components/DcaResult'
import { Panel } from '../components/Panel'
import { Placeholder } from '../components/Placeholder'
import { ScanPanel } from '../components/ScanPanel'
import { SectionTitle } from '../components/SectionTitle'
import { type BtForm, defaultForm, toBacktestBody } from '../utils/btForm'
import { type DcaForm as DcaFormState, defaultDcaForm, toDcaBody } from '../utils/dcaForm'

type Kind = 'grid' | 'dca'
const KINDS: [Kind, string][] = [
  ['grid', '网格'],
  ['dca', '定投'],
]

/** 参数回测：网格 / 定投 二选一。左配置表单 + 右结果；网格另带下方参数扫描。 */
export default function Backtest() {
  const [params] = useSearchParams()
  const symbol0 = params.get('symbol') ?? '159920'
  const [kind, setKind] = useState<Kind>('grid')
  const [form, setForm] = useState<BtForm>(() => defaultForm(symbol0))
  const [dca, setDca] = useState<DcaFormState>(() => defaultDcaForm(symbol0))

  const bt = useMutation({ mutationFn: runBacktest })
  const dt = useMutation({ mutationFn: runDcaBacktest })
  const runGrid = () => bt.mutate(toBacktestBody(form))
  const runDca = () => dt.mutate(toDcaBody(dca))
  const adopt = (patch: Partial<BtForm>) => setForm((f) => ({ ...f, ...patch }))

  const meta =
    kind === 'grid'
      ? bt.data
        ? `${form.symbol} · ${form.start}→${form.end}`
        : '待运行'
      : dt.data
        ? `${dca.symbol} · ${dca.start}→${dca.end}`
        : '待运行'

  return (
    <div className="view">
      <div className="bt-head">
        <SectionTitle title="参数回测" en="Backtest" />
        <div className="seg bt-kind">
          {KINDS.map(([v, l]) => (
            <span key={v} className={v === kind ? 'on' : undefined} onClick={() => setKind(v)}>
              {l}
            </span>
          ))}
        </div>
      </div>

      <div className="bt">
        <Panel kick="策略配置" en="CONFIG" className="rise d1">
          {kind === 'grid' ? (
            <BacktestForm form={form} onChange={setForm} onRun={runGrid} pending={bt.isPending} />
          ) : (
            <DcaForm form={dca} onChange={setDca} onRun={runDca} pending={dt.isPending} />
          )}
        </Panel>
        <Panel kick="回测结果" en="RESULT" meta={meta} className="rise d2">
          {kind === 'grid' ? (
            <GridResultArea pending={bt.isPending} error={bt.error} data={bt.data} />
          ) : (
            <DcaResultArea pending={dt.isPending} error={dt.error} data={dt.data} />
          )}
        </Panel>
      </div>

      {kind === 'grid' && <ScanPanel form={form} onAdopt={adopt} />}
    </div>
  )
}

function GridResultArea({
  pending,
  error,
  data,
}: {
  pending: boolean
  error: unknown
  data: BacktestResultData | undefined
}) {
  if (pending) return <Placeholder title="回测运行中…" fr="FR-7.2" />
  if (error) return <div className="bt-err">回测失败：{String(error)}</div>
  if (data) return <BacktestResult result={data} />
  return (
    <Placeholder
      title="填参数 → ▶ 跑回测。结果含净值 / 回撤 / 买入持有对照 + 期末阶梯"
      fr="FR-7.2 / 7.3 / 7.4"
    />
  )
}

function DcaResultArea({
  pending,
  error,
  data,
}: {
  pending: boolean
  error: unknown
  data: DcaBacktestResult | undefined
}) {
  if (pending) return <Placeholder title="定投回测运行中…" fr="M6" />
  if (error) return <div className="bt-err">回测失败：{String(error)}</div>
  if (data) return <DcaResult result={data} />
  return (
    <Placeholder
      title="填参数 → ▶ 跑定投回测。结果含累计投入 / XIRR / 净值 + 买入持有对照"
      fr="M6 · 定投"
    />
  )
}
