import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { runBacktest } from '../api/client'
import { BacktestForm } from '../components/BacktestForm'
import { BacktestResult } from '../components/BacktestResult'
import { Panel } from '../components/Panel'
import { Placeholder } from '../components/Placeholder'
import { ScanPanel } from '../components/ScanPanel'
import { SectionTitle } from '../components/SectionTitle'
import { type BtForm, defaultForm, toBacktestBody } from '../utils/btForm'

/** 参数回测：左配置表单 + 右结果（净值/回撤/买入持有 + 期末阶梯），下方参数扫描。 */
export default function Backtest() {
  const [params] = useSearchParams()
  const symbol0 = params.get('symbol') ?? '159920'
  const [form, setForm] = useState<BtForm>(() => defaultForm(symbol0))

  const bt = useMutation({ mutationFn: runBacktest })
  const run = () => bt.mutate(toBacktestBody(form))
  const adopt = (patch: Partial<BtForm>) => setForm((f) => ({ ...f, ...patch }))

  return (
    <div className="view">
      <SectionTitle title="参数回测" en="Backtest" />
      <div className="bt">
        <Panel kick="策略配置" en="CONFIG" className="rise d1">
          <BacktestForm form={form} onChange={setForm} onRun={run} pending={bt.isPending} />
        </Panel>
        <Panel
          kick="回测结果"
          en="RESULT"
          meta={bt.data ? `${form.symbol} · ${form.start}→${form.end}` : '待运行'}
          className="rise d2"
        >
          {bt.isPending ? (
            <Placeholder title="回测运行中…" fr="FR-7.2" />
          ) : bt.error ? (
            <div className="bt-err">回测失败：{String(bt.error)}</div>
          ) : bt.data ? (
            <BacktestResult result={bt.data} />
          ) : (
            <Placeholder
              title="填参数 → ▶ 跑回测。结果含净值 / 回撤 / 买入持有对照 + 期末阶梯"
              fr="FR-7.2 / 7.3 / 7.4"
            />
          )}
        </Panel>
      </div>

      <ScanPanel form={form} onAdopt={adopt} />
    </div>
  )
}
