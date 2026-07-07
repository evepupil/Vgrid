interface PlaceholderProps {
  /** 这块将要展示什么 */
  title: string
  /** 对应的需求编号，如 "FR-4 网格阶梯" */
  fr: string
}

/** 骨架占位：标明此处待接入的功能与需求编号，把前端骨架与需求清单挂钩。 */
export function Placeholder({ title, fr }: PlaceholderProps) {
  return (
    <div className="placeholder">
      <span className="ph-mark">◌</span>
      <span className="ph-title">{title}</span>
      <span className="ph-fr">待接入 · {fr}</span>
    </div>
  )
}
