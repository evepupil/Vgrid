import * as ToggleGroup from '@radix-ui/react-toggle-group'
import { useMode, type Mode } from '../mode/context'

/** 实盘 ⇄ 模拟盘 全局切换。切到模拟盘整套强调色由琥珀变青，并亮出模拟横幅。 */
export function ModeSwitch() {
  const { mode, setMode } = useMode()

  return (
    <ToggleGroup.Root
      className="mode"
      type="single"
      value={mode}
      onValueChange={(v) => {
        // Radix 在点已选项时会回传空串，忽略以保证始终有一个模式选中
        if (v === 'live' || v === 'sim') setMode(v as Mode)
      }}
      aria-label="交易模式"
    >
      <ToggleGroup.Item className="mode__btn" value="live">
        <span className="d" />
        实盘 LIVE
      </ToggleGroup.Item>
      <ToggleGroup.Item className="mode__btn" value="sim">
        <span className="d" />
        模拟盘 SIM
      </ToggleGroup.Item>
    </ToggleGroup.Root>
  )
}
