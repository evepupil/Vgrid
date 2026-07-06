import { useQuery } from '@tanstack/react-query'
import { Line } from '@ant-design/charts'
import { Card, Col, Row, Statistic, Table, Tag, Typography } from 'antd'
import type { TableProps } from 'antd'
import { useState } from 'react'
import {
  getState,
  listRunners,
  type InstanceView,
  type StateView,
} from '../api/client'

type Columns<T> = NonNullable<TableProps<T>['columns']>

export default function Runners() {
  const runners = useQuery({
    queryKey: ['portfolio', 'runners'],
    queryFn: listRunners,
    refetchInterval: 5000,
  })
  const [selected, setSelected] = useState<InstanceView>()

  const state = useQuery({
    queryKey: ['state', selected?.db_path],
    queryFn: () => getState(selected!.db_path),
    enabled: !!selected,
    refetchInterval: 5000,
  })

  const columns: Columns<InstanceView> = [
    { title: '名称', dataIndex: 'name' },
    { title: '标的', dataIndex: 'symbol' },
    {
      title: '状态',
      dataIndex: 'status',
      render: (v) => (
        <Tag color={v === 'running' ? 'green' : 'default'}>{v}</Tag>
      ),
    },
    { title: '权益', dataIndex: 'equity' },
    { title: '已实现盈亏', dataIndex: 'realized_pnl' },
    { title: '最新价', dataIndex: 'last_price', render: (v) => v ?? '—' },
  ]

  return (
    <div style={{ display: 'flex', gap: 16 }}>
      <Card
        title="实例列表"
        style={{ width: 360, alignSelf: 'flex-start' }}
      >
        <Table
          size="small"
          dataSource={runners.data ?? []}
          loading={runners.isLoading}
          rowKey="name"
          columns={columns}
          pagination={false}
          rowSelection={{
            type: 'radio',
            selectedRowKeys: selected ? [selected.name] : [],
            onChange: (_keys, rows) => setSelected(rows[0]),
          }}
          onRow={(r) => ({ onClick: () => setSelected(r) })}
        />
        <Typography.Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
          启停用 <code>vgrid paper run --db</code>
        </Typography.Text>
      </Card>

      <div style={{ flex: 1, minWidth: 0 }}>
        {state.data ? (
          <RunnerDetail state={state.data} />
        ) : (
          <Card>
            <Typography.Text type="secondary">选一个实例看盘</Typography.Text>
          </Card>
        )}
      </div>
    </div>
  )
}

function RunnerDetail({ state }: { state: StateView }) {
  const snap = state.snapshot
  const m = state.metrics
  const chartData = state.equity_curve.map((p) => ({
    ts: p.ts,
    equity: Number(p.equity),
  }))

  const fillColumns: Columns<StateView['fills'][number]> = [
    {
      title: '时间',
      dataIndex: 'ts',
      render: (v) => (v ? new Date(v).toLocaleString() : '—'),
    },
    {
      title: '方向',
      dataIndex: 'side',
      render: (v) => (v === 'buy' ? <Tag color="green">买</Tag> : <Tag color="red">卖</Tag>),
    },
    { title: '价格', dataIndex: 'price' },
    { title: '份额', dataIndex: 'shares' },
    { title: '手续费', dataIndex: 'fee' },
    { title: '已实现盈亏', dataIndex: 'realized_pnl', render: (v) => v ?? '—' },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Row gutter={16}>
        <Col span={4}>
          <Card>
            <Statistic title="最新价" value={String(snap.last_price ?? '—')} />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic title="持仓格数" value={Number(snap.open_lots ?? 0)} />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic title="占用资金" value={String(snap.committed ?? '—')} />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic title="已实现盈亏" value={String(snap.realized_pnl ?? '—')} />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic title="手续费" value={String(snap.total_fee ?? '—')} />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic title="总收益" value={m.total_return} />
          </Card>
        </Col>
      </Row>

      <Card title={`净值曲线 · ${state.symbol}（${state.n_ticks} ticks）`}>
        <Line data={chartData} xField="ts" yField="equity" height={320} />
      </Card>

      <Card title="成交明细">
        <Table
          size="small"
          dataSource={state.fills}
          rowKey={(r) => `${r.ts}-${r.side}-${r.price}`}
          columns={fillColumns}
          pagination={{ pageSize: 10 }}
        />
      </Card>
    </div>
  )
}
