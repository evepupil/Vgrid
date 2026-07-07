import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import { type UseFormRegisterReturn, useForm } from 'react-hook-form'
import {
  type StrategyConfig,
  createStrategy,
  getStrategy,
  updateStrategy,
} from '../api/client'

interface FormValues {
  name: string
  symbol: string
  lower_price: string
  upper_price: string
  grid_count: string
  per_grid_amount: string
  capital_cap: string
  spacing_mode: string
  base_build_mode: string
  upper_rebuild_ratio: string
  down_spacing_factor: string
  down_amount_factor: string
}

const DEFAULTS: FormValues = {
  name: '',
  symbol: '159920',
  lower_price: '1.000',
  upper_price: '1.350',
  grid_count: '20',
  per_grid_amount: '2000',
  capital_cap: '50000',
  spacing_mode: 'arithmetic',
  base_build_mode: 'center',
  upper_rebuild_ratio: '0',
  down_spacing_factor: '1',
  down_amount_factor: '1',
}

function toConfig(v: FormValues): StrategyConfig {
  return {
    symbol: v.symbol,
    lower_price: v.lower_price,
    upper_price: v.upper_price,
    grid_count: Number(v.grid_count),
    per_grid_amount: v.per_grid_amount,
    capital_cap: v.capital_cap,
    spacing_mode: v.spacing_mode,
    base_build_mode: v.base_build_mode,
    upper_rebuild_ratio: v.upper_rebuild_ratio,
    down_spacing_factor: v.down_spacing_factor,
    down_amount_factor: v.down_amount_factor,
  }
}

function fromConfig(name: string, c: StrategyConfig): FormValues {
  const s = (k: string, fb: string) => (c[k] === undefined ? fb : String(c[k]))
  return {
    name,
    symbol: s('symbol', ''),
    lower_price: s('lower_price', ''),
    upper_price: s('upper_price', ''),
    grid_count: s('grid_count', '20'),
    per_grid_amount: s('per_grid_amount', '2000'),
    capital_cap: s('capital_cap', '50000'),
    spacing_mode: s('spacing_mode', 'arithmetic'),
    base_build_mode: s('base_build_mode', 'center'),
    upper_rebuild_ratio: s('upper_rebuild_ratio', '0'),
    down_spacing_factor: s('down_spacing_factor', '1'),
    down_amount_factor: s('down_amount_factor', '1'),
  }
}

interface Props {
  editName: string | null // null=新建；否则编辑该策略
  initialSymbol?: string // 新建时预填标的（关注屏「部署」带 ?symbol= 过来）
  onClose: () => void
}

/** 策略编辑器（react-hook-form）：新建 / 编辑 GridConfig 全字段。校验 + 后端二次把关。 */
export function StrategyEditor({ editName, initialSymbol, onClose }: Props) {
  const qc = useQueryClient()
  const isEdit = editName !== null

  const existing = useQuery({
    queryKey: ['strategy', editName],
    queryFn: () => getStrategy(editName as string),
    enabled: isEdit,
  })

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormValues>({
    defaultValues: initialSymbol ? { ...DEFAULTS, symbol: initialSymbol } : DEFAULTS,
  })

  // 编辑：配置拉到后回填表单
  useEffect(() => {
    if (isEdit && existing.data) reset(fromConfig(editName as string, existing.data))
  }, [isEdit, existing.data, editName, reset])

  const save = useMutation({
    mutationFn: (v: FormValues) =>
      isEdit ? updateStrategy(v.name, toConfig(v)) : createStrategy(v.name, toConfig(v)),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['strategies-enriched'] })
      onClose()
    },
  })

  return (
    <div className="editor-backdrop" onClick={onClose}>
      <div className="editor" onClick={(e) => e.stopPropagation()}>
        <div className="editor-h">
          <b>{isEdit ? `编辑策略 · ${editName}` : '新建策略'}</b>
          <span className="editor-x" onClick={onClose}>
            ×
          </span>
        </div>

        <form className="form" onSubmit={handleSubmit((v) => save.mutate(v))}>
          <div className="fg">
            <label>策略名 NAME</label>
            <input
              {...register('name', { required: '必填' })}
              disabled={isEdit}
              placeholder="如 恒生-稳健网格"
              spellCheck={false}
            />
            {errors.name && <span className="fg-err">{errors.name.message}</span>}
          </div>
          <div className="fg">
            <label>标的 SYMBOL</label>
            <input {...register('symbol', { required: '必填' })} spellCheck={false} />
          </div>
          <div className="frow">
            <Num label="下沿" reg={register('lower_price', { required: true })} />
            <Num label="上沿" reg={register('upper_price', { required: true })} />
          </div>
          <div className="frow">
            <div className="fg">
              <label>格数</label>
              <input type="number" {...register('grid_count', { required: true, min: 1 })} />
            </div>
            <Num label="每格金额" reg={register('per_grid_amount', { required: true })} />
          </div>
          <div className="fg">
            <label>间距模式</label>
            <select {...register('spacing_mode')}>
              <option value="arithmetic">等差</option>
              <option value="geometric">等比</option>
            </select>
          </div>
          <div className="fg">
            <label>建仓模式</label>
            <select {...register('base_build_mode')}>
              <option value="center">中枢</option>
              <option value="zero">零底仓</option>
            </select>
          </div>
          <Num label="资金上限" reg={register('capital_cap', { required: true })} />
          <div className="frow frow3">
            <Num label="上破重建" reg={register('upper_rebuild_ratio')} />
            <Num label="下沿放大格距" reg={register('down_spacing_factor')} />
            <Num label="下沿放大金额" reg={register('down_amount_factor')} />
          </div>

          {save.error && <div className="fg-err">保存失败：{String(save.error)}</div>}

          <div className="editor-acts">
            <button type="button" className="btn-ghost" onClick={onClose}>
              取消
            </button>
            <button type="submit" className="run" disabled={save.isPending || (isEdit && existing.isLoading)}>
              {save.isPending ? '保存中…' : isEdit ? '保存修改' : '创建策略'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function Num({ label, reg }: { label: string; reg: UseFormRegisterReturn }) {
  return (
    <div className="fg">
      <label>{label}</label>
      <input inputMode="decimal" {...reg} />
    </div>
  )
}
