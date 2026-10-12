// Talks to the Afterparty Connector extension. Chrome exposes
// chrome.runtime.sendMessage to pages listed in the extension's
// "externally_connectable"; without the extension it is missing or errors.

type ChromeRuntime = {
  sendMessage: (id: string, msg: unknown, cb: (resp: unknown) => void) => void
  lastError?: { message?: string }
}

function runtime(): ChromeRuntime | null {
  const c = (window as unknown as { chrome?: { runtime?: ChromeRuntime } }).chrome
  return c?.runtime?.sendMessage ? c.runtime : null
}

/** Phones and tablets can't run Chrome extensions at all. */
export const isMobile = () => /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent)

/** Chromium-family browser (Chrome, Arc, Brave, Edge): the only kind that can run the connector. */
export const isChromium = () =>
  !!(window as unknown as { chrome?: unknown }).chrome || /Chrome\//.test(navigator.userAgent)

function send<T>(extensionId: string, msg: unknown, timeoutMs = 30000): Promise<T | null> {
  const rt = runtime()
  if (!rt || !extensionId) return Promise.resolve(null)
  return new Promise((resolve) => {
    const timer = setTimeout(() => resolve(null), timeoutMs)
    try {
      rt.sendMessage(extensionId, msg, (resp) => {
        clearTimeout(timer)
        void rt.lastError // reading it silences "Unchecked runtime.lastError"
        resolve((resp as T) ?? null)
      })
    } catch {
      clearTimeout(timer)
      resolve(null)
    }
  })
}

/** The id of whichever connector build is installed (store or unpacked), or null. */
export async function findConnector(ids: string[]): Promise<string | null> {
  const answers = await Promise.all(
    ids.filter(Boolean).map(async (id) => ((await send<{ ok: boolean }>(id, { type: 'ping' }, 1500))?.ok ? id : null)),
  )
  return answers.find(Boolean) ?? null
}

export async function extensionInstalled(ids: string[]): Promise<boolean> {
  return (await findConnector(ids)) !== null
}

export type PartifulSession =
  | { ok: true; signedIn: false }
  | { ok: true; signedIn: true; uid: string; refreshToken: string; apiKey: string; displayName: string | null }
  | { ok: false; error: string }

export async function readPartifulSession(ids: string[]): Promise<PartifulSession> {
  const id = await findConnector(ids)
  if (!id) return { ok: false, error: 'The connector is not installed in this browser.' }
  const resp = await send<PartifulSession>(id, { type: 'getPartifulSession' })
  return resp ?? { ok: false, error: 'The connector did not answer. Reload this page and try again.' }
}

/** Connector ids from the app config, newest store build first. */
export const connectorIds = (c: { extensionId: string; extensionIds?: string[] }) =>
  c.extensionIds?.length ? c.extensionIds : [c.extensionId]
