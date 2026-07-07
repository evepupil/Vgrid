/** 顶部滚动行情条。真实多标的报价待 FR-11.1 接入，现为占位。 */
const PLACEHOLDER = [
  '行情推流待接入',
  'FR-11.1 · 多标的实时报价',
  'FR-11.4 · 昨收基准',
  '关注列表标的将在此滚动',
]

export function Ticker() {
  // 轨道需两份内容首尾相接，才能无缝循环（translateX -50%）
  const items = [...PLACEHOLDER, ...PLACEHOLDER]
  return (
    <div className="ticker">
      <div className="ticker__track">
        {items.map((t, i) => (
          <span className="tk faint" key={i}>
            ○ {t}
          </span>
        ))}
      </div>
    </div>
  )
}
