// Afterparty Connector.
//
// Only Afterparty's own pages can talk to this extension: Chrome enforces the
// manifest's "externally_connectable" list, and every message's sender origin
// is checked again here. When Afterparty asks, the extension reads the Partiful
// sign-in your browser already holds and hands back what the Afterparty server
// needs to sync for you: your Partiful user id, the Firebase refresh token, and
// Partiful's public web API key. Nothing is stored here and nothing is read
// unless Afterparty asks.

const PARTIFUL = "https://partiful.com/";

/** Origins allowed to ask, straight from the manifest. The build an instance hands
 *  out (/afterparty-extension.zip) lists only that instance's own address. */
const ALLOWED = (chrome.runtime.getManifest().externally_connectable?.matches || []).map(
  (m) => m.replace(/\/\*$/, "")
);

function allowed(sender) {
  const origin = sender?.origin || (sender?.url ? new URL(sender.url).origin : "");
  return ALLOWED.some((a) => {
    if (origin === a) return true;
    // "http://localhost" in a match pattern covers every port (dev builds only).
    const u = new URL(a);
    try {
      const o = new URL(origin);
      return o.protocol === u.protocol && o.hostname === u.hostname && !u.port;
    } catch {
      return false;
    }
  });
}

chrome.runtime.onMessageExternal.addListener((msg, sender, reply) => {
  if (!allowed(sender)) {
    reply({ ok: false, error: "This page is not allowed to use the Afterparty Connector." });
    return false;
  }
  if (msg?.type === "ping") {
    reply({ ok: true, version: chrome.runtime.getManifest().version });
    return false;
  }
  if (msg?.type === "getPartifulSession") {
    getSession().then(reply, (err) => reply({ ok: false, error: String(err?.message || err) }));
    return true; // async reply
  }
  reply({ ok: false, error: "unknown request" });
  return false;
});

async function getSession() {
  const existing = await chrome.tabs.query({ url: "https://partiful.com/*" });
  // A loaded, not-discarded tab can answer at once; otherwise use a fresh one.
  let tab = existing.find((t) => t.status === "complete" && !t.discarded);
  let opened = false;
  try {
    if (!tab) {
      tab = await chrome.tabs.create({ url: PARTIFUL, active: false });
      opened = true;
      await waitForLoad(tab.id);
    }
    const [{ result }] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: readFirebaseUser,
    });
    return { ok: true, ...result };
  } finally {
    if (opened && tab) chrome.tabs.remove(tab.id).catch(() => {});
  }
}

function waitForLoad(tabId) {
  return new Promise((resolve, reject) => {
    const done = (fn, arg) => {
      clearTimeout(timer);
      chrome.tabs.onUpdated.removeListener(onUpdated);
      fn(arg);
    };
    const timer = setTimeout(() => done(reject, new Error("partiful.com took too long to load")), 20000);
    function onUpdated(id, info) {
      if (id === tabId && info.status === "complete") done(resolve);
    }
    chrome.tabs.onUpdated.addListener(onUpdated);
    // The tab may have finished loading before the listener was attached.
    chrome.tabs.get(tabId).then((t) => t.status === "complete" && done(resolve), () => {});
  });
}

// Runs inside the partiful.com tab. Firebase keeps the signed-in user in this
// IndexedDB store; it is the same record Partiful's own app uses.
async function readFirebaseUser() {
  const open = () =>
    new Promise((resolve, reject) => {
      const req = indexedDB.open("firebaseLocalStorageDb");
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
      req.onupgradeneeded = () => {
        req.transaction.abort();
        resolve(null);
      };
    });
  let db;
  try {
    db = await open();
  } catch {
    db = null;
  }
  if (!db || !db.objectStoreNames.contains("firebaseLocalStorage")) return { signedIn: false };
  const rows = await new Promise((resolve, reject) => {
    const req = db.transaction("firebaseLocalStorage").objectStore("firebaseLocalStorage").getAll();
    req.onsuccess = () => resolve(req.result || []);
    req.onerror = () => reject(req.error);
  });
  const row = rows.find((r) => String(r.fbase_key || "").startsWith("firebase:authUser:"));
  const user = row?.value;
  const refreshToken = user?.stsTokenManager?.refreshToken;
  if (!user?.uid || !refreshToken) return { signedIn: false };
  return {
    signedIn: true,
    uid: user.uid,
    refreshToken,
    apiKey: user.apiKey || String(row.fbase_key).split(":")[2],
    displayName: user.displayName || null,
  };
}
