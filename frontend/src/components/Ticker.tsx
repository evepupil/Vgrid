import { useQuery } from '@tanstack/react-query'
import { getQuotes, listWatchlist } from '../api/client'
import { fmt, priceDecimals, signOf, upDown } from '../utils/format'

const PLACEHOLDER = ['行情推流待接入', 'FR-11.1 · 关注列表标的将在此滚动']

/** 顶部滚动行情条：取关注列表标的的实时报价，源不可用则降级为占位。 */
export function Ticker() {
  const wl = useQuery({ queryKey: ['watchlist'], queryFn: listWatchlist })
  const symbols = (wl.data ?? []).map((w) => w.symbol)
  const quotes = useQuery({
    queryKey: ['quotes', 'ticker', symbols.join(',')],
    queryFn: () => getQuotes(symbols),
    enabled: symbols.length > 0,
    refetchInterval: 15000,
  })

  const items = quotes.data?.quotes ?? []
  const track =
    items.length > 0
      ? items.map((q) => {
          const pct = q.change_pct != null ? Number(q.change_pct) : 0
          return {
            key: q.symbol,
            name: q.name ?? q.symbol,
            price: Number(q.price).toFixed(priceDecimals(Number(q.price) || 1)),
            pct: `${signOf(pct)}${fmt(pct)}%`,
            dir: upDown(pct),
          }
        })
      : null

  return (
    <div className="ticker">
      <div className="ticker__track">
        {track
          ? // 两份内容首尾相接以无缝循环
            [...track, ...track].map((t, i) => (
              <span className="tk" key={`${t.key}-${i}`}>
                {t.name} <b>{t.price}</b> <span className={t.dir}>{t.pct}</span>
              </span>
            ))
          : [...PLACEHOLDER, ...PLACEHOLDER].map((t, i) => (
              <span className="tk faint" key={i}>
                ○ {t}
              </span>
            ))}
      </div>
    </div>
  )
}
