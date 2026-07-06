import { Card, Typography } from 'antd'

export default function Backtest() {
  return (
    <Card>
      <Typography.Title level={3}>回测</Typography.Title>
      <Typography.Text type="secondary">
        选 ETF + 区间 + 策略，跑回测看净值曲线 / 回撤 / 夏普 / 成交点
      </Typography.Text>
    </Card>
  )
}
