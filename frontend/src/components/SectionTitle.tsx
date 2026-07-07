import type { ReactNode } from 'react'

interface SectionTitleProps {
  title: string
  en: string
  /** 标题行右侧附加内容（按钮 / 标签等） */
  extra?: ReactNode
}

/** 区块标题：中文标题 + 英文小标 + 分隔线。 */
export function SectionTitle({ title, en, extra }: SectionTitleProps) {
  return (
    <div className="secttl">
      <h2>{title}</h2>
      <span className="en">{en}</span>
      <span className="ln" />
      {extra}
    </div>
  )
}
