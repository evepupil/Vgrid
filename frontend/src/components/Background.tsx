/** 全屏背景层：方格纸 / 光晕 / 暗角 / 噪点。纯装饰，不接收指针事件。 */
export function Background() {
  return (
    <>
      <div className="bg" />
      <div className="glow" />
      <div className="vig" />
      <div className="grain" />
    </>
  )
}
