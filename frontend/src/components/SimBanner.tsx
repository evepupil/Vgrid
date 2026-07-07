import { useMode } from '../mode/context'

/** 模拟盘横幅：只在模拟盘模式显示，讲清「不下真单、镜像独立、仅关注共享」。 */
export function SimBanner() {
  const { mode } = useMode()
  if (mode !== 'sim') return null
  return (
    <div className="simbar">
      <span className="tag">模拟</span> 跟随实时行情计算盈亏 · <b>不触发真实下单</b> ·
      镜像独立账户，仅「关注列表」与实盘共享
    </div>
  )
}
