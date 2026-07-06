import { Card, Typography } from 'antd'

export default function Dashboard() {
  return (
    <Card>
      <Typography.Title level={3}>仪表盘</Typography.Title>
      <Typography.Text type="secondary">
        总资产 · 在跑网格 · 关注列表
      </Typography.Text>
    </Card>
  )
}
