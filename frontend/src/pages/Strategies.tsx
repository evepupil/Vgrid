import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, Card, message, Popconfirm, Space, Table, Tag } from 'antd'
import type { TableProps } from 'antd'
import { useState } from 'react'
import {
  createStrategy,
  deleteStrategy,
  getStrategy,
  listStrategies,
  updateStrategy,
  type StrategyConfig,
  type StrategySummary,
} from '../api/client'
import StrategyForm, { formToConfig, type FormValues } from '../components/StrategyForm'

type Columns<T> = NonNullable<TableProps<T>['columns']>

interface ModalState {
  mode: 'create' | 'edit'
  name: string
  config: StrategyConfig | null
}

export default function Strategies() {
  const qc = useQueryClient()
  const list = useQuery({ queryKey: ['strategies'], queryFn: listStrategies })
  const [modal, setModal] = useState<ModalState | null>(null)

  const openEdit = async (name: string) => {
    try {
      const config = await getStrategy(name)
      setModal({ mode: 'edit', name, config })
    } catch (e) {
      message.error((e as Error).message)
    }
  }
  const openCopy = async (name: string) => {
    try {
      const config = await getStrategy(name)
      setModal({ mode: 'create', name: '', config })
    } catch (e) {
      message.error((e as Error).message)
    }
  }

  const saveMut = useMutation({
    mutationFn: async (v: FormValues) => {
      const config = formToConfig(v)
      if (modal?.mode === 'edit' && modal.name) {
        await updateStrategy(modal.name, config)
      } else {
        await createStrategy(v.name, config)
      }
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['strategies'] })
      message.success('已保存')
      setModal(null)
    },
    onError: (e: Error) => message.error(e.message),
  })

  const delMut = useMutation({
    mutationFn: (name: string) => deleteStrategy(name),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['strategies'] })
      message.success('已删除')
    },
    onError: (e: Error) => message.error(e.message),
  })

  const columns: Columns<StrategySummary> = [
    { title: '名称', dataIndex: 'name' },
    { title: '标的', dataIndex: 'symbol' },
    {
      title: '间距',
      dataIndex: 'spacing_mode',
      render: (v) => (v === 'geometric' ? <Tag>等比</Tag> : <Tag>等差</Tag>),
    },
    { title: '格数', dataIndex: 'grid_count' },
    {
      title: '区间',
      render: (_, r) => `${r.lower_price} ~ ${r.upper_price}`,
    },
    {
      title: '操作',
      render: (_v, r) => (
        <Space>
          <Button size="small" onClick={() => openEdit(r.name)}>
            编辑
          </Button>
          <Button size="small" onClick={() => openCopy(r.name)}>
            复制
          </Button>
          <Popconfirm title="删除策略？" onConfirm={() => delMut.mutate(r.name)}>
            <Button danger size="small">
              删
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Card
        title="策略库"
        extra={
          <Button
            type="primary"
            onClick={() => setModal({ mode: 'create', name: '', config: null })}
          >
            新建策略
          </Button>
        }
      >
        <Table
          size="small"
          dataSource={list.data ?? []}
          loading={list.isLoading}
          rowKey="name"
          columns={columns}
          pagination={false}
        />
      </Card>
      <StrategyForm
        open={modal !== null}
        initial={modal?.config ? { name: modal.name, config: modal.config } : null}
        onCancel={() => setModal(null)}
        onSubmit={(v) => saveMut.mutate(v)}
      />
    </Space>
  )
}
