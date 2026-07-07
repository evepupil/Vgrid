import type { ReactNode } from 'react'

interface PanelProps {
  /** 面板标题（kicker）。省略则不渲染头部。 */
  kick?: string
  /** 标题旁的英文小标 */
  en?: string
  /** 头部右侧的元信息 */
  meta?: ReactNode
  className?: string
  children: ReactNode
}

/** 带四角登记标记的面板，全站统一容器。 */
export function Panel({ kick, en, meta, className, children }: PanelProps) {
  return (
    <section className={className ? `panel ${className}` : 'panel'}>
      {kick !== undefined && (
        <div className="panel__h">
          <div className="kick">
            <span className="sq" />
            {kick}
            {en !== undefined && <em>{en}</em>}
          </div>
          {meta !== undefined && <div className="meta">{meta}</div>}
        </div>
      )}
      {children}
    </section>
  )
}
