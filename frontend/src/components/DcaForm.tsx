import type { DcaForm as DcaFormState, DcaTierForm } from '../utils/dcaForm'

interface Props {
  form: DcaFormState
  onChange: (f: DcaFormState) => void
  onRun: () => void
  pending: boolean
  compact?: boolean // 对比屏复用：藏标的/区间/周期（由外层共享），去掉运行按钮
}

/** 定投策略配置表单（受控）。频率决定星期/号数字段；金额规则决定跌幅档位/均线子表单。 */
export function DcaForm({ form, onChange, onRun, pending, compact = false }: Props) {
  const set = (k: keyof DcaFormState, v: string) => onChange({ ...form, [k]: v })
  const setTiers = (tiers: DcaTierForm[]) => onChange({ ...form, tiers })

  return (
    <div className="form">
      {!compact && (
        <>
          <div className="fg">
            <label>标的 SYMBOL</label>
            <input
              value={form.symbol}
              onChange={(e) => set('symbol', e.target.value)}
              spellCheck={false}
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
        </>
      )}

      <div className="fg">
        <label>定投频率</label>
        <Seg
          value={form.frequency}
          options={[
            ['daily', '每日'],
            ['weekly', '每周'],
            ['monthly', '每月'],
          ]}
          onPick={(v) => set('frequency', v)}
        />
      </div>
      {form.frequency === 'weekly' && (
        <div className="fg">
          <label>星期（1=周一…7=周日）</label>
          <select value={form.weekday} onChange={(e) => set('weekday', e.target.value)}>
            {['1', '2', '3', '4', '5', '6', '7'].map((d) => (
              <option key={d} value={d}>
                周{'一二三四五六日'[Number(d) - 1]}
              </option>
            ))}
          </select>
        </div>
      )}
      {form.frequency === 'monthly' && (
        <Field label="每月几号（超月末钳到月末）">
          <input
            type="number"
            value={form.day_of_month}
            onChange={(e) => set('day_of_month', e.target.value)}
          />
        </Field>
      )}

      <div className="frow">
        <Field label="每次投入">
          <input value={form.base_amount} onChange={(e) => set('base_amount', e.target.value)} />
        </Field>
        <Field label="累计投入上限">
          <input value={form.cash_cap} onChange={(e) => set('cash_cap', e.target.value)} />
        </Field>
      </div>

      <div className="fg">
        <label>金额规则</label>
        <Seg
          value={form.mode}
          options={[
            ['fixed', '固定'],
            ['drawdown', '跌幅加码'],
            ['ma_deviation', '均线偏离'],
          ]}
          onPick={(v) => set('mode', v)}
        />
      </div>

      {form.mode === 'drawdown' && (
        <div className="dca-policy">
          <Field label="回看根数（找近期高点）">
            <input
              type="number"
              value={form.lookback_days}
              onChange={(e) => set('lookback_days', e.target.value)}
            />
          </Field>
          <label className="dca-tiers__lbl">加码档位（回撤 ≥ 阈值 → 金额 ×倍数）</label>
          {form.tiers.map((t, i) => (
            <div className="frow dca-tier" key={i}>
              <Field label="回撤阈值">
                <input
                  value={t.drawdown}
                  onChange={(e) => setTiers(patch(form.tiers, i, { drawdown: e.target.value }))}
                />
              </Field>
              <Field label="金额倍数">
                <input
                  value={t.multiplier}
                  onChange={(e) => setTiers(patch(form.tiers, i, { multiplier: e.target.value }))}
                />
              </Field>
              <button
                type="button"
                className="dca-tier__rm"
                onClick={() => setTiers(form.tiers.filter((_, j) => j !== i))}
                aria-label="删除档位"
              >
                ×
              </button>
            </div>
          ))}
          <button
            type="button"
            className="dca-tier__add"
            onClick={() => setTiers([...form.tiers, { drawdown: '0.20', multiplier: '2' }])}
          >
            + 加一档
          </button>
        </div>
      )}

      {form.mode === 'ma_deviation' && (
        <div className="dca-policy">
          <Field label="均线窗口（根）">
            <input
              type="number"
              value={form.ma_window}
              onChange={(e) => set('ma_window', e.target.value)}
            />
          </Field>
          <div className="frow">
            <Field label="低于均线 ×">
              <input
                value={form.below_multiplier}
                onChange={(e) => set('below_multiplier', e.target.value)}
              />
            </Field>
            <Field label="高于均线 ×">
              <input
                value={form.above_multiplier}
                onChange={(e) => set('above_multiplier', e.target.value)}
              />
            </Field>
          </div>
        </div>
      )}

      {!compact && (
        <div className="fg">
          <label>周期</label>
          <select value={form.frame} onChange={(e) => set('frame', e.target.value)}>
            <option value="1d">日线</option>
            <option value="1m">1 分钟</option>
          </select>
        </div>
      )}

      {!compact && (
        <button type="button" className="run" onClick={onRun} disabled={pending}>
          {pending ? '⏳ 回测运行中…' : '▶ 跑定投回测'}
        </button>
      )}
    </div>
  )
}

function patch(tiers: DcaTierForm[], i: number, delta: Partial<DcaTierForm>): DcaTierForm[] {
  return tiers.map((t, j) => (j === i ? { ...t, ...delta } : t))
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
