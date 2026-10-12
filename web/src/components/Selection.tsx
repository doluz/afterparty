import { Download, X } from 'lucide-react'
import { useState } from 'react'
import { exportPeople, type ExportRequest } from '../lib/api'
import { n, plural } from '../lib/format'
import { Spinner } from './bits'

/** Multi-select state for a people list: explicit ids, or "everyone matching". */
export function useSelection() {
  const [ids, setIds] = useState<Set<string>>(new Set())
  const [all, setAll] = useState(false)
  return {
    ids,
    all,
    has: (id: string) => all || ids.has(id),
    toggle: (id: string, on: boolean) => {
      setAll(false)
      setIds((cur) => {
        const next = new Set(cur)
        if (on) next.add(id)
        else next.delete(id)
        return next
      })
    },
    selectAll: () => setAll(true),
    clear: () => {
      setAll(false)
      setIds(new Set())
    },
  }
}

/** Export with feedback: a button state and a short "Exported N people" note. */
export function useExport() {
  const [busy, setBusy] = useState(false)
  const [note, setNote] = useState<string | null>(null)
  const run = async (req: ExportRequest) => {
    setBusy(true)
    setNote(null)
    try {
      const count = await exportPeople(req)
      setNote(`Exported ${plural(count, 'person', 'people')} to CSV.`)
    } catch (e) {
      setNote((e as Error).message)
    } finally {
      setBusy(false)
      setTimeout(() => setNote(null), 4000)
    }
  }
  return { busy, note, run }
}

export function ExportButton({ label, onClick, busy }: { label: string; onClick: () => void; busy: boolean }) {
  return (
    <button type="button" className="btn btn-quiet" onClick={onClick} disabled={busy}>
      {busy ? <Spinner /> : <Download className="size-4" aria-hidden />}
      {label}
    </button>
  )
}

/** Floating bar while something is selected: count, select-all, export, clear. */
export function SelectionBar({
  sel,
  total,
  onExport,
  busy,
}: {
  sel: ReturnType<typeof useSelection>
  total: number
  onExport: () => void
  busy: boolean
}) {
  const count = sel.all ? total : sel.ids.size
  if (!count) return null
  return (
    <div className="fixed inset-x-3 bottom-24 z-40 flex justify-center md:bottom-6">
      <div className="rise flex flex-wrap items-center gap-2 rounded-full border border-white/10 bg-dusk/95 py-2 pl-5 pr-2 shadow-[0_16px_50px_-12px_rgb(0_0_0/0.9)] backdrop-blur-xl">
        <span className="text-small font-semibold">{n(count)} selected</span>
        {!sel.all && total > count && (
          <button type="button" className="text-small font-semibold text-uv hover:underline" onClick={sel.selectAll}>
            Select all {n(total)}
          </button>
        )}
        <button type="button" className="btn btn-primary h-10" onClick={onExport} disabled={busy}>
          {busy ? <Spinner /> : <Download className="size-4" aria-hidden />}
          Export CSV
        </button>
        <button type="button" className="btn btn-quiet size-10 p-0" onClick={sel.clear} aria-label="Clear selection">
          <X className="size-4" />
        </button>
      </div>
    </div>
  )
}

export function Toast({ text }: { text: string | null }) {
  if (!text) return null
  return (
    <div role="status" className="fixed inset-x-0 top-20 z-50 flex justify-center px-4">
      <p className="rise rounded-full border border-white/10 bg-dusk/95 px-4 py-2 text-small font-semibold shadow-xl backdrop-blur">
        {text}
      </p>
    </div>
  )
}
