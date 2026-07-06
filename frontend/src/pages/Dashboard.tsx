import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Button,
  Card,
  Col,
  Input,
  message,
  Popconfirm,
  Row,
  Space,
  Statistic,
  Table,
  Tag,
} from 'antd'
import type { TableProps } from 'antd'
import { useState } from 'react'

type Columns<T> = NonNullable<TableProps<T>['columns']>
import {
  addWatch,
  getPortfolioSummary,
  listRunners,
  listWatchlist,
  removeWatch,
  type InstanceView,
  type WatchItem,
} from '../api/client'

export default function Dashboard() {
  const qc = useQueryClient()
  const summary = useQuery({
    queryKey: ['portfolio', 'summary'],
    queryFn: getPortfolioSummary,
    refetchInterval: 5000,
  })
  const runners = useQuery({
    queryKey: ['portfolio', 'runners'],
    queryFn: listRunners,
    refetchInterval: 5000,
  })
  const watchlist = useQuery({ queryKey: ['watchlist'], queryFn: listWatchlist })

  const [wSymbol, setWSymbol] = useState('')
  const [wName, setWName] = useState('')

  const addMut = useMutation({
    mutationFn: (v: { symbol: string; name: string | null }) =>
      addWatch(v.symbol, v.name),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['watchlist'] })
      message.success('已关注')
      setWSymbol('')
      setWName('')
    },
    onError: (e: Error) => message.error(e.message),
  })
  const delMut = useMutation({
    mutationFn: (symbol: string) => removeWatch(symbol),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['watchlist'] }),
    onError: (e: Error) => message.error(e.message),
  })

  const s = summary.data

  const runnerColumns: Columns<InstanceView> = [
    { title: '名称', dataIndex: 'name' },
    { title: '标的', dataIndex: 'symbol' },
    {
      title: '状态',
      dataIndex: 'status',
      render: (v) => <Tag color={v === 'running' ? 'green' : 'default'}>{v}</Tag>,
    },
    { title: '权益', dataIndex: 'equity' },
    { title: '已实现盈亏', dataIndex: 'realized_pnl' },
    { title: '最新价', dataIndex: 'last_price', render: (v) => v ?? '—' },
    { title: '持仓格数', dataIndex: 'open_lots' },
  ]

  const watchColumns: Columns<WatchItem> = [
    { title: '代码', dataIndex: 'symbol' },
    { title: '名称', dataIndex: 'name', render: (v) => v ?? '—' },
    {
      title: '加入时间',
      dataIndex: 'added_at',
      render: (v) => (v ? new Date(v).toLocaleString() : '—'),
    },
    {
      title: '操作',
      render: (_v, r) => (
        <Popconfirm title="取消关注？" onConfirm={() => delMut.mutate(r.symbol)}>
          <Button danger size="small">
            删
          </Button>
        </Popconfirm>
      ),
    },
  ]

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Row gutter={16}>
        <Col span={6}>
          <Card>
            <Statistic title="总资产" value={s?.total_equity ?? '—'} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="在跑实例"
              value={s?.n_running ?? 0}
              suffix={`/ ${s?.n_instances ?? 0}`}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="累计已实现盈亏" value={s?.total_realized_pnl ?? '—'} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="累计手续费" value={s?.total_fee ?? '—'} />
          </Card>
        </Col>
      </Row>

      <Card title="模拟盘实例">
        <Table
          size="small"
          dataSource={runners.data ?? []}
          loading={runners.isLoading}
          rowKey="name"
          columns={runnerColumns}
          pagination={false}
        />
      </Card>

      <Card title="关注列表">
        <Space style={{ marginBottom: 16 }}>
          <Input
            placeholder="代码 如 159920"
            value={wSymbol}
            onChange={(e) => setWSymbol(e.target.value)}
            style={{ width: 160 }}
          />
          <Input
            placeholder="名称（可选）"
            value={wName}
            onChange={(e) => setWName(e.target.value)}
            style={{ width: 200 }}
          />
          <Button
            type="primary"
            onClick={() =>
              wSymbol &&
              addMut.mutate({ symbol: wSymbol, name: wName || null })
            }
            loading={addMut.isPending}
          >
            加入
          </Button>
        </Space>
        <Table
          size="small"
          dataSource={watchlist.data ?? []}
          loading={watchlist.isLoading}
          rowKey="symbol"
          columns={watchColumns}
          pagination={false}
        />
      </Card>
    </Space>
  )
}
