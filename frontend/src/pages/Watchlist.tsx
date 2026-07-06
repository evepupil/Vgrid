import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Button,
  Card,
  Input,
  message,
  Popconfirm,
  Space,
  Table,
} from 'antd'
import type { TableProps } from 'antd'
import { useState } from 'react'
import {
  addWatch,
  getEtfInfo,
  listWatchlist,
  removeWatch,
  type WatchItem,
} from '../api/client'

type Columns<T> = NonNullable<TableProps<T>['columns']>

export default function Watchlist() {
  const qc = useQueryClient()
  const list = useQuery({ queryKey: ['watchlist'], queryFn: listWatchlist })
  const [symbol, setSymbol] = useState('')
  const [name, setName] = useState('')
  const [fetching, setFetching] = useState(false)

  const fetchName = async () => {
    if (!symbol) return
    setFetching(true)
    try {
      const info = await getEtfInfo(symbol)
      setName(info.name)
    } catch {
      setName('')
      message.warning(`未找到 ${symbol}，可手动填名称`)
    } finally {
      setFetching(false)
    }
  }

  const addMut = useMutation({
    mutationFn: () => addWatch(symbol, name || null),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['watchlist'] })
      message.success('已关注')
      setSymbol('')
      setName('')
    },
    onError: (e: Error) => message.error(e.message),
  })
  const delMut = useMutation({
    mutationFn: (sym: string) => removeWatch(sym),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['watchlist'] }),
    onError: (e: Error) => message.error(e.message),
  })

  const columns: Columns<WatchItem> = [
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
    <Card title="关注列表">
      <Space style={{ marginBottom: 16 }} wrap>
        <Input
          placeholder="代码 如 159920"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          onBlur={fetchName}
          style={{ width: 160 }}
        />
        <Input
          placeholder="名称（输入代码后自动拉取，或手填）"
          value={name}
          onChange={(e) => setName(e.target.value)}
          style={{ width: 260 }}
        />
        <Button onClick={fetchName} loading={fetching}>
          查名称
        </Button>
        <Button
          type="primary"
          onClick={() => addMut.mutate()}
          loading={addMut.isPending}
          disabled={!symbol}
        >
          加入
        </Button>
      </Space>
      <Table
        size="small"
        dataSource={list.data ?? []}
        loading={list.isLoading}
        rowKey="symbol"
        columns={columns}
        pagination={false}
      />
    </Card>
  )
}
