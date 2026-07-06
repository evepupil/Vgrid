import { Form, Input, InputNumber, Modal, Select } from 'antd'
import { useEffect } from 'react'
import type { StrategyConfig } from '../api/client'

export interface FormValues {
  name: string
  symbol: string
  lower_price: string
  upper_price: string
  grid_count: number
  per_grid_amount: string
  capital_cap: string
  spacing_mode: string
  base_build_mode: string
  upper_rebuild_ratio: string
  down_spacing_factor: string
  down_amount_factor: string
  fee_rate: string
  fee_min_fee: string
  lot_size: number
  price_tick: string
}

interface Props {
  open: boolean
  initial: { name: string; config: StrategyConfig } | null
  onCancel: () => void
  onSubmit: (values: FormValues) => void
}

export function configToForm(name: string, c: StrategyConfig): FormValues {
  const fee = (c.fee ?? {}) as { rate?: unknown; min_fee?: unknown }
  return {
    name,
    symbol: String(c.symbol ?? ''),
    lower_price: String(c.lower_price ?? ''),
    upper_price: String(c.upper_price ?? ''),
    grid_count: Number(c.grid_count ?? 16),
    per_grid_amount: String(c.per_grid_amount ?? ''),
    capital_cap: String(c.capital_cap ?? ''),
    spacing_mode: String(c.spacing_mode ?? 'geometric'),
    base_build_mode: String(c.base_build_mode ?? 'center'),
    upper_rebuild_ratio: String(c.upper_rebuild_ratio ?? '0'),
    down_spacing_factor: String(c.down_spacing_factor ?? '1'),
    down_amount_factor: String(c.down_amount_factor ?? '1'),
    fee_rate: String(fee.rate ?? '0.00005'),
    fee_min_fee: String(fee.min_fee ?? '0.1'),
    lot_size: Number(c.lot_size ?? 100),
    price_tick: String(c.price_tick ?? '0.001'),
  }
}

export function formToConfig(v: FormValues): StrategyConfig {
  return {
    symbol: v.symbol,
    lower_price: v.lower_price,
    upper_price: v.upper_price,
    grid_count: v.grid_count,
    per_grid_amount: v.per_grid_amount,
    capital_cap: v.capital_cap,
    spacing_mode: v.spacing_mode,
    base_build_mode: v.base_build_mode,
    upper_rebuild_ratio: v.upper_rebuild_ratio,
    down_spacing_factor: v.down_spacing_factor,
    down_amount_factor: v.down_amount_factor,
    fee: { rate: v.fee_rate, min_fee: v.fee_min_fee },
    lot_size: v.lot_size,
    price_tick: v.price_tick,
  }
}

const NUM = { width: '100%' } as const

export default function StrategyForm({ open, initial, onCancel, onSubmit }: Props) {
  const [form] = Form.useForm<FormValues>()
  useEffect(() => {
    if (open) {
      if (initial) {
        form.setFieldsValue(configToForm(initial.name, initial.config))
      } else {
        form.resetFields()
      }
    }
  }, [open, initial, form])

  return (
    <Modal
      title={initial?.name ? '编辑策略' : '新建策略'}
      open={open}
      onCancel={onCancel}
      onOk={() =>
        form
          .validateFields()
          .then(onSubmit)
          .catch(() => {})
      }
      width={680}
      destroyOnClose
    >
      <Form form={form} layout="vertical" preserve={false}>
        <Form.Item name="name" label="策略名" rules={[{ required: true }]}>
          <Input placeholder="如 恒生_0.3%" />
        </Form.Item>
        <Form.Item name="symbol" label="标的代码" rules={[{ required: true }]}>
          <Input placeholder="如 159920" />
        </Form.Item>
        <Form.Item name="grid_count" label="格数" rules={[{ required: true }]}>
          <InputNumber min={1} style={NUM} />
        </Form.Item>
        <Form.Item name="per_grid_amount" label="每格金额" rules={[{ required: true }]}>
          <InputNumber stringMode min="0" style={NUM} />
        </Form.Item>
        <Form.Item name="capital_cap" label="资金上限" rules={[{ required: true }]}>
          <InputNumber stringMode min="0" style={NUM} />
        </Form.Item>
        <Form.Item name="lower_price" label="区间下沿" rules={[{ required: true }]}>
          <InputNumber stringMode min="0" style={NUM} />
        </Form.Item>
        <Form.Item name="upper_price" label="区间上沿" rules={[{ required: true }]}>
          <InputNumber stringMode min="0" style={NUM} />
        </Form.Item>
        <Form.Item name="spacing_mode" label="间距模式">
          <Select
            options={[
              { value: 'geometric', label: '等比' },
              { value: 'arithmetic', label: '等差' },
            ]}
          />
        </Form.Item>
        <Form.Item name="base_build_mode" label="建仓模式">
          <Select
            options={[
              { value: 'center', label: '中枢建仓' },
              { value: 'zero', label: '零底仓' },
            ]}
          />
        </Form.Item>
        <Form.Item name="upper_rebuild_ratio" label="向上重建比例 [0,1]">
          <InputNumber stringMode min="0" max="1" style={NUM} />
        </Form.Item>
        <Form.Item name="down_spacing_factor" label="向下格距系数 ≥1">
          <InputNumber stringMode min="1" style={NUM} />
        </Form.Item>
        <Form.Item name="down_amount_factor" label="向下金额系数 >0">
          <InputNumber stringMode min="0" style={NUM} />
        </Form.Item>
        <Form.Item name="fee_rate" label="费率">
          <InputNumber stringMode min="0" style={NUM} />
        </Form.Item>
        <Form.Item name="fee_min_fee" label="最低手续费">
          <InputNumber stringMode min="0" style={NUM} />
        </Form.Item>
        <Form.Item name="lot_size" label="一手份额">
          <InputNumber min={1} style={NUM} />
        </Form.Item>
        <Form.Item name="price_tick" label="价格变动单位">
          <InputNumber stringMode min="0" style={NUM} />
        </Form.Item>
      </Form>
    </Modal>
  )
}
