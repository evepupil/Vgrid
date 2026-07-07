import * as ToggleGroup from '@radix-ui/react-toggle-group'
import type { InstanceView } from '../api/client'

interface Props {
  instances: InstanceView[]
  selectedDb: string
  onSelect: (db: string) => void
}

/** 标的切换器（FR-3.1）：当前模式下在跑的实例，Radix ToggleGroup。 */
export function InstancePills({ instances, selectedDb, onSelect }: Props) {
  return (
    <ToggleGroup.Root
      className="pills rise d1"
      type="single"
      value={selectedDb}
      onValueChange={(v) => {
        if (v) onSelect(v)
      }}
      aria-label="标的切换"
    >
      {instances.map((i) => (
        <ToggleGroup.Item key={i.db_path} value={i.db_path}>
          {i.name}
          <span className="c">{i.symbol}</span>
        </ToggleGroup.Item>
      ))}
    </ToggleGroup.Root>
  )
}
