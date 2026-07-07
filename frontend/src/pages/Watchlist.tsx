import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  type ColumnDef,
  type SortingState,
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { type EnrichedWatch, addWatch, listWatchlistEnriched, removeWatch } from '../api/client'
import { Panel } from '../components/Panel'
import { SectionTitle } from '../components/SectionTitle'
import { Sparkline } from '../components/Sparkline'
import { FitnessGauge } from '../components/FitnessGauge'
import { fmt, signOf, upDown } from '../utils/format'

const POLL = 30000
const col = createColumnHelper<EnrichedWatch>()

/** 关注列表（实盘/模拟盘共享）：TanStack Table，可按适配分/振幅/涨跌排序，帮选标的。 */
export default function Watchlist() {
  const qc = useQueryClient()
  const nav = useNavigate()
  const [sorting, setSorting] = useState<SortingState>([{ id: 'fitness', desc: true }])
  const [sym, setSym] = useState('')

  const q = useQuery({
    queryKey: ['watchlist-enriched'],
    queryFn: listWatchlistEnriched,
    refetchInterval: POLL,
  })
  const rows = q.data ?? []

  const invalidate = () => qc.invalidateQueries({ queryKey: ['watchlist-enriched'] })
  const add = useMutation({
    mutationFn: (s: string) => addWatch(s),
    onSuccess: () => {
      setSym('')
      invalidate()
    },
  })
  const remove = useMutation({ mutationFn: (s: string) => removeWatch(s), onSuccess: invalidate })

  const columns = makeColumns(nav, (s) => remove.mutate(s))
  const table = useReactTable({
    data: rows,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  })

  const submitAdd = () => {
    const s = sym.trim()
    if (s) add.mutate(s)
  }

  return (
    <div className="view">
      <SectionTitle
        title="关注列表"
        en="Watchlist"
        extra={<span className="chip acc">◈ 实盘 / 模拟盘 共享</span>}
      />

      <div className="wl-add rise d1">
        <input
          value={sym}
          onChange={(e) => setSym(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && submitAdd()}
          placeholder="加自选：ETF 代码（如 159920）"
          spellCheck={false}
        />
        <button type="button" onClick={submitAdd} disabled={add.isPending || !sym.trim()}>
          + 关注
        </button>
      </div>

      <Panel className="rise d2">
        {rows.length === 0 ? (
          <div className="wl-empty faint">
            还没关注任何标的。上面输入 ETF 代码加一个——列表会补上现价、振幅、
            <b>网格适配评分</b>和近 60 日走势。
          </div>
        ) : (
          <div className="wl-scroll">
            <table>
              <thead>
                {table.getHeaderGroups().map((hg) => (
                  <tr key={hg.id}>
                    {hg.headers.map((h) => {
                      const sortable = h.column.getCanSort()
                      const dir = h.column.getIsSorted()
                      return (
                        <th
                          key={h.id}
                          onClick={h.column.getToggleSortingHandler()}
                          className={sortable ? 'wl-th-sort' : undefined}
                        >
                          {flexRender(h.column.columnDef.header, h.getContext())}
                          {dir ? (dir === 'desc' ? ' ▾' : ' ▴') : sortable ? ' ⋯' : ''}
                        </th>
                      )
                    })}
                  </tr>
                ))}
              </thead>
              <tbody>
                {table.getRowModel().rows.map((r) => (
                  <tr key={r.id}>
                    {r.getVisibleCells().map((c) => (
                      <td key={c.id}>{flexRender(c.column.columnDef.cell, c.getContext())}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  )
}

/** 近 60 日走势 sparkline，颜色随 60 日方向（末价 ≥ 首价红，否则绿）。 */
function TrendCell({ trend }: { trend: string[] }) {
  const pts = trend.map(Number)
  if (pts.length < 2) return <span className="faint">—</span>
  const up = (pts[pts.length - 1] ?? 0) >= (pts[0] ?? 0)
  return <Sparkline points={pts} stroke={up ? 'var(--up)' : 'var(--down)'} height={22} />
}

function makeColumns(
  nav: (to: string) => void,
  onRemove: (symbol: string) => void,
): ColumnDef<EnrichedWatch>[] {
  return [
    col.accessor('symbol', { header: '代码', cell: (c) => <b>{c.getValue()}</b> }) as ColumnDef<EnrichedWatch>,
    col.accessor('name', {
      header: '名称',
      cell: (c) => <span className="wl-name">{c.getValue() ?? c.row.original.symbol}</span>,
    }) as ColumnDef<EnrichedWatch>,
    col.accessor((r) => num(r.price), {
      id: 'price',
      header: '现价',
      cell: (c) => (c.getValue<number>() > 0 ? c.getValue<number>().toFixed(3) : '—'),
    }) as ColumnDef<EnrichedWatch>,
    col.accessor((r) => num(r.change_pct), {
      id: 'chg',
      header: '涨跌%',
      cell: (c) => <ChangeCell v={c.row.original.change_pct} />,
    }) as ColumnDef<EnrichedWatch>,
    col.accessor((r) => num(r.amplitude_pct), {
      id: 'amp',
      header: '振幅%',
      cell: (c) => (c.getValue<number>() > 0 ? `${fmt(c.getValue<number>())}%` : '—'),
    }) as ColumnDef<EnrichedWatch>,
    col.accessor((r) => r.fitness_score ?? -1, {
      id: 'fitness',
      header: '网格适配',
      cell: (c) => <FitnessGauge score={c.row.original.fitness_score} />,
    }) as ColumnDef<EnrichedWatch>,
    col.accessor('trend', {
      header: '60日走势',
      enableSorting: false,
      cell: (c) => <TrendCell trend={c.getValue()} />,
    }) as ColumnDef<EnrichedWatch>,
    col.display({
      id: 'act',
      header: '操作',
      cell: (c) => {
        const s = c.row.original.symbol
        return (
          <span className="wl-acts">
            <span className="act" onClick={() => nav(`/backtest?symbol=${s}`)}>
              回测
            </span>
            <span className="act" onClick={() => nav(`/strategies?symbol=${s}`)}>
              部署
            </span>
            <span className="act del" onClick={() => onRemove(s)} title="取消关注">
              ×
            </span>
          </span>
        )
      },
    }) as ColumnDef<EnrichedWatch>,
  ]
}

function ChangeCell({ v }: { v: string | null }) {
  if (v === null) return <span className="faint">—</span>
  const n = Number(v)
  return (
    <span className={upDown(n)}>
      {n >= 0 ? '▲ ' : '▼ '}
      {signOf(n)}
      {fmt(n)}%
    </span>
  )
}

function num(v: string | null): number {
  return v === null ? 0 : Number(v)
}
