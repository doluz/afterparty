import { useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Wordmark } from '../components/bits'
import { CLUSTER_COLOR } from '../components/PeopleMap'
import { useAuth } from '../lib/auth'

/** Where every field comes from. Mirrors the code: afterparty/core/roles.py and afterparty/people.py. */
const FIELDS: { field: string; source: string }[] = [
  { field: 'Name, photo, bio', source: 'The person’s Partiful profile, as Partiful shows it to you.' },
  { field: 'X, Instagram, TikTok, Facebook, Snapchat', source: 'The handles they added to their Partiful profile. Afterparty keeps a link only when it points at that platform.' },
  { field: 'LinkedIn', source: 'Their Partiful LinkedIn field, or a linkedin.com/in/ link they pasted into their bio.' },
  { field: 'Designation', source: 'Read from the bio with the keyword rules below.' },
  { field: 'Company (in exports)', source: 'The words after “at” or “@” in the bio, as in “CEO at Lumen”. A hint for enrichment tools; empty when the bio says it another way.' },
  { field: 'Met N times, events together', source: 'Counted across the events you attended or hosted.' },
  { field: 'Follow-up and notes', source: 'You. Nobody else sees them.' },
]

const RULES: { key: string; label: string; words: string; example: string }[] = [
  { key: 'founder', label: 'Founder', words: 'founder, co-founder, founding, founded, CEO, owner, chairman, entrepreneur', example: '“Co-founder & CTO at Kiln” is a Founder: founder words win over job words.' },
  { key: 'investor', label: 'Investor', words: 'investor(s), venture(s), VC(s), angel(s), capital, limited partner', example: '“Managing Partner, Northwind Ventures” is an Investor (from “Ventures”).' },
  { key: 'engineering', label: 'Engineer', words: 'engineer, engineering, developer, CTO, SDE, SWE, DevOps, software, full-stack, backend, frontend, machine learning, data scientist', example: '“Growth engineer” is an Engineer: engineering is checked before growth.' },
  { key: 'product', label: 'Product', words: 'product manager, product management, product lead, product owner, CPO, head of product', example: '“Product lead at Quill” is Product.' },
  { key: 'design', label: 'Design', words: 'designer, design lead, UX, product design', example: '“Product designer” is Design.' },
  { key: 'gtm_growth', label: 'GTM and growth', words: 'GTM, go-to-market, growth, marketing, CMO, sales, business development, partnerships, revenue', example: '“Head of partnerships” is GTM and growth.' },
  { key: 'other', label: 'Other', words: 'A bio with none of the words above.', example: '“Partner at Seed Fund” is Other: a bare “partner” also matches law and accounting firms, so it is not used.' },
  { key: 'unknown', label: 'No bio', words: 'The person left their Partiful bio empty.', example: 'Most guests: on a typical Tech Week list, more than half have no bio.' },
]

const STEPS = [
  { title: 'Filter or tick the people you want', body: 'On People or on any event’s guest list. Every filter applies to the export: search, designation, socials, met more than once, follow-up status.' },
  { title: 'Export to CSV', body: 'One row per person: name, first and last name, designation, company from bio, bio, LinkedIn, X, Instagram, TikTok, Facebook, Partiful profile, times met, events, first and last met, your follow-up and note.' },
  { title: 'Enrich it in your own tool', body: 'Import the CSV into Clay, your CRM’s enrichment, or any tool that takes a CSV. Match on LinkedIn URL first, then name plus company. Add work email, title, company size and funding.' },
  { title: 'Run your follow-up', body: 'Push the enriched list to HubSpot, Attio, Salesforce or your sequencer, or work it in Google Sheets. Mark people as contacted in Afterparty as you go.' },
]

export function HowItWorks() {
  const { state } = useAuth()
  const { hash } = useLocation()
  useEffect(() => {
    if (hash) document.getElementById(hash.slice(1))?.scrollIntoView({ block: 'start' })
  }, [hash])

  return (
    <div className="min-h-dvh px-5 py-5">
      <div className="flex items-center justify-between">
        <Link to={state.status === 'signedIn' ? '/home' : '/'}>
          <Wordmark />
        </Link>
        {state.status === 'signedIn' && (
          <Link to="/people" className="btn btn-quiet h-10">
            Back to People
          </Link>
        )}
      </div>
      <main className="mx-auto max-w-3xl py-12">
        <h1 className="text-display">How Afterparty reads people</h1>
        <p className="mt-4 max-w-2xl text-body text-mute">
          Everything Afterparty shows comes from the Partiful guest lists you can already see. It looks nobody up in
          other databases, finds no emails and scrapes no LinkedIn. Here is where each field comes from, and how to take
          your list further.
        </p>

        <section className="mt-12" id="fields">
          <h2 className="text-section">Where each field comes from</h2>
          <div className="glass mt-4 overflow-hidden">
            <dl className="divide-y divide-white/[0.06]">
              {FIELDS.map((f) => (
                <div key={f.field} className="grid gap-1 px-5 py-4 sm:grid-cols-[13rem_1fr] sm:gap-6">
                  <dt className="font-semibold">{f.field}</dt>
                  <dd className="text-mute">{f.source}</dd>
                </div>
              ))}
            </dl>
          </div>
        </section>

        <section className="mt-14 scroll-mt-24" id="designation">
          <h2 className="text-section">How a designation is decided</h2>
          <p className="mt-3 text-mute">
            Partiful has no job-title field, so Afterparty reads the bio. It checks the groups below in this order and
            the first group with a matching word wins. It only counts whole words, and it would rather say Other than
            guess: a wrong label is worse than none.
          </p>
          <ol className="mt-5 space-y-3">
            {RULES.map((r) => (
              <li key={r.key} className="glass grid gap-2 p-5 sm:grid-cols-[11rem_1fr] sm:gap-6">
                <div className="flex items-center gap-2.5">
                  <span className="size-3 rounded-full" style={{ background: CLUSTER_COLOR[r.key], boxShadow: `0 0 12px ${CLUSTER_COLOR[r.key]}` }} />
                  <span className="font-semibold">{r.label}</span>
                </div>
                <div>
                  <p className="text-small">{r.words}</p>
                  <p className="mt-1.5 text-small text-mute">{r.example}</p>
                </div>
              </li>
            ))}
          </ol>
        </section>

        <section className="mt-14 scroll-mt-24" id="export">
          <h2 className="text-section">Take your list further</h2>
          <p className="mt-3 text-mute">
            Afterparty stops at what Partiful shows you. To add work emails, titles or company data for a campaign,
            export and use the enrichment tool you already have.
          </p>
          <ol className="mt-5 grid gap-3 sm:grid-cols-2">
            {STEPS.map((s, i) => (
              <li key={s.title} className="glass p-5">
                <span className="flex size-8 items-center justify-center rounded-full bg-white/10 font-display font-bold">{i + 1}</span>
                <h3 className="mt-4 text-body font-semibold">{s.title}</h3>
                <p className="mt-1.5 text-small text-mute">{s.body}</p>
              </li>
            ))}
          </ol>
          <p className="mt-5 text-small text-faint">
            These are people who were at an event with you, not opted-in contacts. Reach out the way you would after
            meeting someone, honour opt-outs, and follow the privacy and email laws that apply to you.
          </p>
        </section>
      </main>
    </div>
  )
}
