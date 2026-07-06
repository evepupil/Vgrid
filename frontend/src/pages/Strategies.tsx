import { Card, Typography } from 'antd'

export default function Strategies() {
  return (
    <Card>
      <Typography.Title level={3}>策略库</Typography.Title>
      <Typography.Text type="secondary">
        策略列表 · 编辑 / 复制 / 删除
      </Typography.Text>
    </Card>
  )
}
