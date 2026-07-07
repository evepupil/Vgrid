/** 数字/价格格式化，跟原型口径一致。红涨绿跌由 up/down 类承载。 */

export function fmt(v: number, d = 2): string {
  return v.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d })
}

export function signOf(v: number): string {
  return v >= 0 ? '+' : ''
}

/** 涨跌类：>=0 红（up），<0 绿（down）。 */
export function upDown(v: number): 'up' | 'down' {
  return v >= 0 ? 'up' : 'down'
}

/** 价格小数位：<2 元 4 位、<10 元 3 位、否则 2 位。 */
export function priceDecimals(p: number): number {
  if (p < 2) return 4
  if (p < 10) return 3
  return 2
}
