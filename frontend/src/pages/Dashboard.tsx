import { useQuery } from '@tanstack/react-query'
import { Card, Col, Empty, Row, Statistic, Table, Tag } from 'antd'
import type { TableProps } from 'antd'
import { Link } from 'react-router-dom'
import {
  getPortfolioSummary,
  listRunners,
  type InstanceView,
} from '../api/client'

type Columns<T> = NonNullable<TableProps<T>['columns']>

export default function Dashboard() {
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
  const s = summary.data

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
    { title: '持仓格数', dataIndex: 'open_lots' },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
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

      <Card
        title="模拟盘实例"
        extra={<Link to="/runners">看盘 →</Link>}
      >
        {runners.data && runners.data.length > 0 ? (
          <Table
            size="small"
            dataSource={runners.data}
            loading={runners.isLoading}
            rowKey="name"
            columns={columns}
            pagination={false}
          />
        ) : (
          <Empty description="还没有模拟盘实例。用 vgrid paper run --db 启动一个" />
        )}
      </Card>
    </div>
  )
}
