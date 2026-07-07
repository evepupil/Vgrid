import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  type DeployResult,
  type EnrichedStrategy,
  deleteStrategy,
  deployStrategy,
  listStrategiesEnriched,
} from '../api/client'
import { Panel } from '../components/Panel'
import { Placeholder } from '../components/Placeholder'
import { SectionTitle } from '../components/SectionTitle'
import { StrategyEditor } from '../components/StrategyEditor'

const POLL = 20000

/** 策略库（FR-9）：策略表 + 状态/夏普/关联实例 + 新建/编辑（react-hook-form）+ 部署。 */
export default function Strategies() {
  const qc = useQueryClient()
  const nav = useNavigate()
  const [params] = useSearchParams()
  // 关注屏「部署」带 ?symbol= 过来 → 直接开新建编辑器、预填该标的
  const deploySymbol = params.get('symbol')
  const [editName, setEditName] = useState<string | null | undefined>(
    deploySymbol ? null : undefined,
  ) // undefined=关；null=新建
  const [deployed, setDeployed] = useState<DeployResult | null>(null)

  const q = useQuery({
    queryKey: ['strategies-enriched'],
    queryFn: listStrategiesEnriched,
    refetchInterval: POLL,
  })
  const rows = q.data ?? []

  const invalidate = () => qc.invalidateQueries({ queryKey: ['strategies-enriched'] })
  const deploy = useMutation({
    mutationFn: (name: string) => deployStrategy(name, 'sim'),
    onSuccess: (r) => {
      setDeployed(r)
      invalidate()
    },
  })
  const remove = useMutation({
    mutationFn: (name: string) => deleteStrategy(name),
    onSuccess: invalidate,
  })

  const onDelete = (name: string) => {
    if (confirm(`删除策略「${name}」？`)) remove.mutate(name)
  }

  return (
    <div className="view">
      <SectionTitle
        title="策略库"
        en="Strategies"
        extra={
          <button type="button" className="run stbl-new" onClick={() => setEditName(null)}>
            + 新建策略
          </button>
        }
      />

      {deployed && (
        <div className="deploy-banner rise d1">
          <div className="deploy-msg">
            ✓ 已部署 <b>{deployed.instance_name}</b>（{deployed.symbol}），已在
            <span className="link" onClick={() => nav('/portfolio')}>
              组合总览
            </span>
            出现。开始跟盘运行：
          </div>
          <code className="deploy-cmd">{deployed.start_command}</code>
          <span className="deploy-x" onClick={() => setDeployed(null)}>
            ×
          </span>
        </div>
      )}

      <Panel className="rise d2 stbl">
        {rows.length === 0 ? (
          <Placeholder
            title="还没有策略。点右上「+ 新建策略」建一条，或从关注屏/扫描结果部署。"
            fr="FR-9.1"
          />
        ) : (
          <div className="stbl-scroll">
            <table>
              <thead>
                <tr>
                  <th>策略名</th>
                  <th>标的</th>
                  <th>区间 / 格数</th>
                  <th>模式</th>
                  <th>夏普</th>
                  <th>状态</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((s) => (
                  <Row
                    key={s.name}
                    s={s}
                    onBacktest={() => nav(`/backtest?symbol=${s.symbol}`)}
                    onEdit={() => setEditName(s.name)}
                    onDeploy={() => deploy.mutate(s.name)}
                    onDelete={() => onDelete(s.name)}
                    deploying={deploy.isPending}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      {editName !== undefined && (
        <StrategyEditor
          editName={editName}
          initialSymbol={editName === null && deploySymbol ? deploySymbol : undefined}
          onClose={() => setEditName(undefined)}
        />
      )}
    </div>
  )
}

function spacingLabel(m: string): string {
  return m === 'geometric' ? '等比' : '等差'
}
function buildLabel(m: string): string {
  return m === 'zero' ? '零底仓' : '中枢'
}

function StatusCell({ status }: { status: EnrichedStrategy['status'] }) {
  if (status === 'running') return <span className="accc">● 运行中</span>
  if (status === 'idle') return <span className="st-idle">◐ 已部署 · 停歇</span>
  return <span className="faint">○ 草稿</span>
}

function Row({
  s,
  onBacktest,
  onEdit,
  onDeploy,
  onDelete,
  deploying,
}: {
  s: EnrichedStrategy
  onBacktest: () => void
  onEdit: () => void
  onDeploy: () => void
  onDelete: () => void
  deploying: boolean
}) {
  const deployed = s.status !== 'draft'
  return (
    <tr>
      <td className="b">{s.name}</td>
      <td>{s.symbol}</td>
      <td>
        {s.lower_price}–{s.upper_price} / {s.grid_count}
      </td>
      <td>
        <span className="tagchip">
          {spacingLabel(s.spacing_mode)}·{buildLabel(s.base_build_mode)}
        </span>
      </td>
      <td className={s.sharpe && Number(s.sharpe) >= 0 ? 'up' : undefined}>
        {s.sharpe ? Number(s.sharpe).toFixed(2) : '—'}
      </td>
      <td>
        <StatusCell status={s.status} />
      </td>
      <td>
        <span className="act" onClick={onBacktest}>
          回测
        </span>
        <span className="act" onClick={onEdit}>
          编辑
        </span>
        {deployed ? (
          <span className="act faint" title="已部署">
            已部署
          </span>
        ) : (
          <span className={`act${deploying ? ' faint' : ''}`} onClick={onDeploy}>
            部署
          </span>
        )}
        <span className="act del" onClick={onDelete} title="删除">
          删除
        </span>
      </td>
    </tr>
  )
}
