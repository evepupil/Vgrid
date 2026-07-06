import { useMutation, useQuery } from '@tanstack/react-query'
import { Line } from '@ant-design/charts'
import {
  AutoComplete,
  Button,
  Card,
  Col,
  DatePicker,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  message,
} from 'antd'
import type { TableProps } from 'antd'
import dayjs from 'dayjs'
import { useState } from 'react'
import {
  getStrategy,
  listStrategies,
  listWatchlist,
  runBacktest,
  type BacktestResult,
  type Fill,
} from '../api/client'

type Columns<T> = NonNullable<TableProps<T>['columns']>

export default function Backtest() {
  const strategies = useQuery({ queryKey: ['strategies'], queryFn: listStrategies })
  const watchlist = useQuery({ queryKey: ['watchlist'], queryFn: listWatchlist })
  const [etf, setEtf] = useState<string>()
  const [strategy, setStrategy] = useState<string>()
  const [start, setStart] = useState<dayjs.Dayjs | null>(null)
  const [end, setEnd] = useState<dayjs.Dayjs | null>(null)
  const [frame, setFrame] = useState('1d')
  const [result, setResult] = useState<BacktestResult>()

  const run = useMutation({
    mutationFn: async () => {
      if (!strategy || !start || !end) throw new Error('请选策略和区间')
      const config = await getStrategy(strategy)
      return runBacktest({
        start: start.format('YYYY-MM-DD'),
        end: end.format('YYYY-MM-DD'),
        frame,
        config,
        symbol: etf, // 可选，覆盖 config.symbol（同策略测不同标的）
      })
    },
    onSuccess: setResult,
    onError: (e: Error) => message.error(e.message),
  })

  const m = result?.metrics
  const chartData = (result?.equity_curve ?? []).map((p) => ({
    ts: p.ts,
    equity: Number(p.equity),
  }))

  const fillColumns: Columns<Fill> = [
    {
      title: '时间',
      dataIndex: 'ts',
      render: (v) => (v ? new Date(v).toLocaleString() : '—'),
    },
    {
      title: '方向',
      dataIndex: 'side',
      render: (v) =>
        v === 'buy' ? <Tag color="green">买</Tag> : <Tag color="red">卖</Tag>,
    },
    { title: '价格', dataIndex: 'price' },
    { title: '份额', dataIndex: 'shares' },
    { title: '手续费', dataIndex: 'fee' },
    { title: '已实现盈亏', dataIndex: 'realized_pnl', render: (v) => v ?? '—' },
  ]

  const etfOptions = (watchlist.data ?? []).map((w) => ({
    value: w.symbol,
    label: w.name ? `${w.symbol} · ${w.name}` : w.symbol,
  }))

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Card title="回测">
        <Space wrap>
          <AutoComplete
            placeholder="ETF 代码（可从关注列表选）"
            value={etf}
            onChange={setEtf}
            options={etfOptions}
            filterOption
            style={{ width: 240 }}
          />
          <Select
            placeholder="策略"
            style={{ width: 200 }}
            value={strategy}
            onChange={setStrategy}
            options={
              strategies.data?.map((s) => ({
                label: `${s.name} (${s.symbol})`,
                value: s.name,
              })) ?? []
            }
          />
          <DatePicker value={start} onChange={setStart} placeholder="开始" />
          <DatePicker value={end} onChange={setEnd} placeholder="结束" />
          <Select
            value={frame}
            onChange={setFrame}
            style={{ width: 100 }}
            options={[
              { label: '日线', value: '1d' },
              { label: '1分', value: '1m' },
              { label: '5分', value: '5m' },
            ]}
          />
          <Button type="primary" onClick={() => run.mutate()} loading={run.isPending}>
            跑回测
          </Button>
        </Space>
      </Card>

      {m && (
        <>
          <Row gutter={16}>
            <Col span={4}>
              <Card>
                <Statistic title="总收益" value={m.total_return} />
              </Card>
            </Col>
            <Col span={4}>
              <Card>
                <Statistic title="最大回撤" value={m.max_drawdown} />
              </Card>
            </Col>
            <Col span={4}>
              <Card>
                <Statistic title="夏普" value={m.sharpe} />
              </Card>
            </Col>
            <Col span={4}>
              <Card>
                <Statistic title="买入持有" value={m.buy_hold_return} />
              </Card>
            </Col>
            <Col span={4}>
              <Card>
                <Statistic title="成交" value={`${m.n_buys}/${m.n_sells}`} />
              </Card>
            </Col>
            <Col span={4}>
              <Card>
                <Statistic title="手续费" value={m.total_fee} />
              </Card>
            </Col>
          </Row>

          <Card title="净值曲线">
            <Line data={chartData} xField="ts" yField="equity" height={320} />
          </Card>

          <Card title="成交明细">
            <Table
              size="small"
              dataSource={result?.fills ?? []}
              rowKey={(r) => `${r.ts}-${r.side}-${r.price}`}
              columns={fillColumns}
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </>
      )}
    </div>
  )
}
