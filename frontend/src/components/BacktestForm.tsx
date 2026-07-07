import type { BtForm } from '../utils/btForm'

interface Props {
  form: BtForm
  onChange: (f: BtForm) => void
  onRun: () => void
  pending: boolean
}

/** 回测策略配置表单（受控）。原生 input/select 贴终端皮，间距/建仓用 seg 切换。 */
export function BacktestForm({ form, onChange, onRun, pending }: Props) {
  const set = (k: keyof BtForm, v: string) => onChange({ ...form, [k]: v })

  return (
    <div className="form">
      <div className="fg">
        <label>标的 SYMBOL</label>
        <input value={form.symbol} onChange={(e) => set('symbol', e.target.value)} spellCheck={false} />
      </div>
      <div className="frow">
        <Field label="起始">
          <input type="date" value={form.start} onChange={(e) => set('start', e.target.value)} />
        </Field>
        <Field label="结束">
          <input type="date" value={form.end} onChange={(e) => set('end', e.target.value)} />
        </Field>
      </div>
      <div className="frow">
        <Field label="下沿">
          <input value={form.lower_price} onChange={(e) => set('lower_price', e.target.value)} />
        </Field>
        <Field label="上沿">
          <input value={form.upper_price} onChange={(e) => set('upper_price', e.target.value)} />
        </Field>
      </div>
      <div className="frow">
        <Field label="格数">
          <input
            type="number"
            value={form.grid_count}
            onChange={(e) => set('grid_count', e.target.value)}
          />
        </Field>
        <Field label="每格金额">
          <input
            value={form.per_grid_amount}
            onChange={(e) => set('per_grid_amount', e.target.value)}
          />
        </Field>
      </div>
      <div className="fg">
        <label>间距模式</label>
        <Seg
          value={form.spacing_mode}
          options={[
            ['arithmetic', '等差'],
            ['geometric', '等比'],
          ]}
          onPick={(v) => set('spacing_mode', v)}
        />
      </div>
      <div className="fg">
        <label>建仓模式</label>
        <Seg
          value={form.base_build_mode}
          options={[
            ['center', '中枢'],
            ['zero', '零底仓'],
          ]}
          onPick={(v) => set('base_build_mode', v)}
        />
      </div>
      <div className="frow">
        <Field label="资金上限">
          <input value={form.capital_cap} onChange={(e) => set('capital_cap', e.target.value)} />
        </Field>
        <Field label="周期">
          <select value={form.frame} onChange={(e) => set('frame', e.target.value)}>
            <option value="1d">日线</option>
            <option value="1m">1 分钟</option>
          </select>
        </Field>
      </div>
      <button type="button" className="run" onClick={onRun} disabled={pending}>
        {pending ? '⏳ 回测运行中…' : '▶ 跑回测'}
      </button>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="fg">
      <label>{label}</label>
      {children}
    </div>
  )
}

function Seg({
  value,
  options,
  onPick,
}: {
  value: string
  options: [string, string][]
  onPick: (v: string) => void
}) {
  return (
    <div className="seg">
      {options.map(([v, lbl]) => (
        <span key={v} className={v === value ? 'on' : undefined} onClick={() => onPick(v)}>
          {lbl}
        </span>
      ))}
    </div>
  )
}
