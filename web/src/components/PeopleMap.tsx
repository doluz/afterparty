import { hierarchy, pack, type HierarchyCircularNode } from 'd3-hierarchy'
import { useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import type { MapPerson } from '../lib/api'
import { CLUSTERS, n } from '../lib/format'

/** One colour per designation, from the wristband set; the two catch-alls stay muted. */
export const CLUSTER_COLOR: Record<string, string> = {
  founder: 'var(--color-band-orange)',
  investor: 'var(--color-band-pink)',
  engineering: 'var(--color-band-green)',
  product: 'var(--color-band-yellow)',
  design: 'var(--color-band-violet)',
  gtm_growth: 'var(--color-band-blue)',
  other: '#9a8ca6',
  unknown: '#5d5266',
}
const ORDER = ['founder', 'investor', 'engineering', 'product', 'design', 'gtm_growth', 'other', 'unknown']
const PLURAL: Record<string, string> = {
  founder: 'Founders',
  investor: 'Investors',
  engineering: 'Engineers',
  product: 'Product',
  design: 'Design',
  gtm_growth: 'GTM and growth',
  other: 'Other',
  unknown: 'No bio',
}

type Leaf = { person: MapPerson }
type Group = { cluster: string; children: Leaf[] }
type Root = { children: Group[] }
type Node = HierarchyCircularNode<Root | Group | Leaf>

const SIZE = 1000

export function PeopleMap({
  people,
  onOpen,
  onCluster,
}: {
  people: MapPerson[]
  onOpen: (id: string) => void
  onCluster: (cluster: string) => void
}) {
  const wrap = useRef<HTMLDivElement>(null)
  const [hover, setHover] = useState<{ p: MapPerson; x: number; y: number } | null>(null)

  const { groups, leaves } = useMemo(() => {
    const byCluster = new Map<string, Leaf[]>()
    for (const p of people) {
      const list = byCluster.get(p.cluster) ?? []
      list.push({ person: p })
      byCluster.set(p.cluster, list)
    }
    const root: Root = {
      children: ORDER.filter((c) => byCluster.has(c)).map((c) => ({ cluster: c, children: byCluster.get(c)! })),
    }
    // People you met more often take more room.
    const h = hierarchy<Root | Group | Leaf>(root, (d) => ('children' in d ? d.children : undefined))
      .sum((d) => ('person' in d ? 1 + Math.min(d.person.times_met - 1, 6) * 0.9 : 0))
      .sort((a, b) => (b.value ?? 0) - (a.value ?? 0))
    const laid = pack<Root | Group | Leaf>()
      .size([SIZE, SIZE])
      .padding((d) => (d.depth === 0 ? 22 : 1.6))(h) as Node
    return {
      groups: (laid.children ?? []) as Node[],
      leaves: laid.leaves() as Node[],
    }
  }, [people])

  const move = (e: React.MouseEvent<SVGSVGElement>) => {
    const i = (e.target as SVGElement).dataset?.i
    if (i === undefined) return setHover(null)
    const box = wrap.current!.getBoundingClientRect()
    setHover({ p: (leaves[Number(i)].data as Leaf).person, x: e.clientX - box.left, y: e.clientY - box.top })
  }
  const click = (e: React.MouseEvent<SVGSVGElement>) => {
    const i = (e.target as SVGElement).dataset?.i
    if (i !== undefined) onOpen((leaves[Number(i)].data as Leaf).person.person_id)
  }

  if (!people.length) return <p className="glass p-6 text-mute">Nobody matches these filters.</p>

  return (
    <div>
      <div ref={wrap} className="glass relative overflow-hidden p-2 sm:p-4">
        <svg
          viewBox={`0 0 ${SIZE} ${SIZE}`}
          className="mx-auto block h-auto w-full max-w-[52rem] cursor-default"
          role="img"
          aria-label={`Map of ${people.length} people grouped by designation`}
          onMouseMove={move}
          onMouseLeave={() => setHover(null)}
          onClick={click}
        >
          {groups.map((g) => {
            const c = (g.data as Group).cluster
            return (
              <circle
                key={c}
                cx={g.x}
                cy={g.y}
                r={g.r}
                fill={`color-mix(in oklab, ${CLUSTER_COLOR[c]} 9%, transparent)`}
                stroke={`color-mix(in oklab, ${CLUSTER_COLOR[c]} 40%, transparent)`}
                strokeWidth={1.5}
              />
            )
          })}
          {leaves.map((l, i) => {
            const p = (l.data as Leaf).person
            const contacted = p.follow_up === 'contacted'
            return (
              <circle
                key={p.person_id}
                data-i={i}
                cx={l.x}
                cy={l.y}
                r={Math.max(l.r, 1.6)}
                fill={CLUSTER_COLOR[p.cluster]}
                fillOpacity={p.reachable ? 0.95 : 0.38}
                stroke={contacted ? 'var(--color-ok)' : hover?.p.person_id === p.person_id ? '#fff' : 'none'}
                strokeWidth={contacted ? 2 : 1.5}
                className="cursor-pointer"
              />
            )
          })}
          {groups.map((g) => {
            const c = (g.data as Group).cluster
            const size = Math.max(15, Math.min(30, g.r / 5.5))
            return (
              <text
                key={`l-${c}`}
                x={g.x}
                y={g.y - g.r + size + 8}
                textAnchor="middle"
                className="pointer-events-none font-display font-semibold"
                style={{ fontSize: size, fill: '#f6f1fa', paintOrder: 'stroke', stroke: '#0f0b14', strokeWidth: 5, strokeLinejoin: 'round' }}
              >
                {PLURAL[c] ?? c} {n((g.data as Group).children.length)}
              </text>
            )
          })}
        </svg>
        {hover && (
          <div
            className="pointer-events-none absolute z-10 max-w-64 rounded-2xl border border-white/10 bg-night/95 px-3.5 py-2.5 shadow-xl backdrop-blur"
            style={{ left: Math.min(hover.x + 14, (wrap.current?.clientWidth ?? 600) - 260), top: hover.y + 14 }}
          >
            <p className="font-semibold">{hover.p.name}</p>
            <p className="text-caption" style={{ color: CLUSTER_COLOR[hover.p.cluster] }}>
              {CLUSTERS[hover.p.cluster] ?? hover.p.cluster}
              {hover.p.times_met > 1 && <span className="text-mute">, met {hover.p.times_met}×</span>}
            </p>
            {hover.p.bio && <p className="mt-1 line-clamp-3 text-caption text-mute">{hover.p.bio}</p>}
          </div>
        )}
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        {groups.map((g) => {
          const c = (g.data as Group).cluster
          return (
            <button key={c} type="button" className="chip" onClick={() => onCluster(c)} title={`List ${PLURAL[c]}`}>
              <span className="size-2.5 rounded-full" style={{ background: CLUSTER_COLOR[c] }} />
              {PLURAL[c] ?? c} <span className="opacity-60">{n((g.data as Group).children.length)}</span>
            </button>
          )
        })}
      </div>
      <p className="mt-3 text-caption text-faint">
        Bigger dot: met more often. Bright dot: has a social link. Green ring: contacted. Designations come from each
        person's Partiful bio;{' '}
        <Link to="/how-it-works#designation" className="font-semibold text-mute hover:text-ink">
          see how they are decided
        </Link>
        .
      </p>
    </div>
  )
}
