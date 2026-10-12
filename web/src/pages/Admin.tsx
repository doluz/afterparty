import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Avatar, ErrorNote, PageLoading } from '../components/bits'
import { PageTitle } from '../components/Shell'
import { api, type AdminUser } from '../lib/api'
import { ago, dayYear, n } from '../lib/format'

export function Admin() {
  const qc = useQueryClient()
  const users = useQuery({ queryKey: ['admin-users'], queryFn: () => api<AdminUser[]>('/api/admin/users') })
  const set = useMutation({
    mutationFn: ({ id, status }: { id: number; status: AdminUser['status'] }) =>
      api(`/api/admin/users/${id}`, { method: 'POST', body: JSON.stringify({ status }) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-users'] }),
  })

  if (users.isLoading) return <PageLoading />
  const all = users.data ?? []
  const pending = all.filter((u) => u.status === 'pending')
  const rest = all.filter((u) => u.status !== 'pending')

  return (
    <div>
      <PageTitle sub="Approve who can use Afterparty.">Access</PageTitle>
      <ErrorNote error={users.error || set.error} />

      <section>
        <h2 className="text-section">Requests</h2>
        {pending.length === 0 ? (
          <p className="glass mt-4 p-6 text-mute">No one is waiting.</p>
        ) : (
          <ul className="glass mt-4 divide-y divide-white/[0.06] overflow-hidden">
            {pending.map((u) => (
              <li key={u.id} className="flex flex-wrap items-center gap-4 px-5 py-4">
                <Avatar name={u.name ?? u.email} src={u.photo_url} />
                <div className="min-w-0 flex-1">
                  <p className="font-semibold">{u.name ?? u.email}</p>
                  <p className="text-small text-mute">
                    {u.email}, asked {ago(u.created_at)}
                  </p>
                </div>
                <div className="flex gap-2">
                  <button type="button" className="btn btn-primary" disabled={set.isPending} onClick={() => set.mutate({ id: u.id, status: 'approved' })}>
                    Approve
                  </button>
                  <button type="button" className="btn btn-quiet" disabled={set.isPending} onClick={() => set.mutate({ id: u.id, status: 'denied' })}>
                    Decline
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="mt-12">
        <h2 className="text-section">Members</h2>
        <div className="glass mt-4 overflow-x-auto px-5">
          <table className="w-full min-w-[40rem] text-left text-small">
            <thead className="text-mute">
              <tr className="border-b border-white/[0.06]">
                <th className="py-2 pr-4 font-medium">Person</th>
                <th className="py-2 pr-4 font-medium">Access</th>
                <th className="py-2 pr-4 font-medium">Partiful</th>
                <th className="py-2 pr-4 font-medium">Events</th>
                <th className="py-2 font-medium" />
              </tr>
            </thead>
            <tbody>
              {rest.map((u) => (
                <tr key={u.id} className="border-b border-white/[0.06]">
                  <td className="py-3 pr-4">
                    <p className="font-medium">{u.name ?? u.email}</p>
                    <p className="text-mute">{u.email}</p>
                  </td>
                  <td className="py-3 pr-4">
                    {u.role === 'admin' ? 'Admin' : u.status === 'approved' ? `Approved ${dayYear(u.approved_at)}` : 'Declined'}
                  </td>
                  <td className="py-3 pr-4 text-mute">
                    {u.token_error ? <span className="text-danger">Session expired</span> : u.partiful_name ? `Synced ${ago(u.last_sync_at)}` : 'Not connected'}
                  </td>
                  <td className="py-3 pr-4 text-mute">{n(u.events)}</td>
                  <td className="py-3 text-right">
                    {u.role !== 'admin' &&
                      (u.status === 'approved' ? (
                        <button type="button" className="btn btn-quiet h-9 text-caption" onClick={() => set.mutate({ id: u.id, status: 'denied' })}>
                          Remove access
                        </button>
                      ) : (
                        <button type="button" className="btn btn-quiet h-9 text-caption" onClick={() => set.mutate({ id: u.id, status: 'approved' })}>
                          Approve
                        </button>
                      ))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
