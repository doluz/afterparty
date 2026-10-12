import { Link } from 'react-router-dom'
import { Wordmark } from '../components/bits'

const SECTIONS: { title: string; body: string[] }[] = [
  {
    title: 'What Afterparty is',
    body: [
      'Afterparty is an invite-only tool that shows you the people at the Partiful events you went to, so you can follow up with them. It is not made by or affiliated with Partiful.',
    ],
  },
  {
    title: 'What we keep about you',
    body: [
      'Your email address and name from Google or the email link you signed in with, and whether your access is approved.',
      'Your Partiful user id, your Partiful display name, and an encrypted Partiful sign-in token. The token lets Afterparty read your events once a day. It is encrypted at rest with a key that only the Afterparty server can use, and it is never sent back to your browser.',
      'Your follow-up status and notes on people.',
    ],
  },
  {
    title: 'What we keep about the people you met',
    body: [
      'For events you attended, hosted or are going to, Afterparty stores the guest list that Partiful already shows you: each guest’s name, photo link, bio, and the social links they made visible to you. Afterparty never sees guest lists that Partiful hides from you.',
      'This data is visible only to you. Other Afterparty users cannot see your events, your guests or your notes.',
    ],
  },
  {
    title: 'Exports',
    body: [
      'You can export people to a CSV file. The file is made on request, sent only to you, and not kept by Afterparty. What you do with it, including importing it into other tools, is up to you and the privacy laws that apply to you.',
    ],
  },
  {
    title: 'What the Chrome connector does',
    body: [
      'The Afterparty Connector reads your Partiful sign-in from partiful.com only when you select Connect Partiful on an Afterparty page, and gives it to that page. It answers only Afterparty’s own web addresses, stores nothing, and reads nothing else.',
    ],
  },
  {
    title: 'What Afterparty never does',
    body: [
      'It never posts, RSVPs, messages or follows anyone for you, on Partiful or anywhere else. It does not sell or share your data, and it shows no ads.',
    ],
  },
  {
    title: 'Where it lives',
    body: [
      'On the server of whoever runs this Afterparty instance. Sign-in uses Firebase Authentication, or, on a personal local instance, no password at all.',
    ],
  },
  {
    title: 'Your choices',
    body: [
      'Disconnect Partiful in Settings at any time. That deletes the stored Partiful token; your events and notes stay until you delete them.',
      'Delete everything in Settings. That removes your account, the Partiful connection, every synced event and guest, and your notes. It cannot be undone.',
    ],
  },
]

export function Privacy() {
  return (
    <div className="min-h-dvh px-5 py-5">
      <Link to="/" className="inline-block">
        <Wordmark />
      </Link>
      <main className="mx-auto max-w-2xl py-12">
        <h1 className="text-display">Privacy</h1>
        <p className="mt-3 text-mute">How Afterparty handles your data and the data of the people you met. Last updated 10 October 2026.</p>
        <div className="mt-10 space-y-9">
          {SECTIONS.map((s) => (
            <section key={s.title}>
              <h2 className="text-section">{s.title}</h2>
              <div className="mt-3 space-y-3 text-ink/85">
                {s.body.map((b) => (
                  <p key={b}>{b}</p>
                ))}
              </div>
            </section>
          ))}
        </div>
      </main>
    </div>
  )
}
