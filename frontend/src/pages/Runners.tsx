import { Card, Typography } from 'antd'

export default function Runners() {
  return (
    <Card>
      <Typography.Title level={3}>模拟盘</Typography.Title>
      <Typography.Text type="secondary">
        在跑实例 · 单实例看盘（净值 / 持仓 / 成交）
      </Typography.Text>
    </Card>
  )
}
