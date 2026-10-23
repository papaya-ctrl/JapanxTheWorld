import { useState, useSyncExternalStore } from "react";
import { getApiConfiguration } from "../api/configuration";
import { getAuthSession, signIn, signOut, subscribeToAuth } from "../api/auth";
import type { ApiError } from "../types";

export function AccountAccess() {
  const session = useSyncExternalStore(subscribeToAuth, getAuthSession, () => null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  if (!getApiConfiguration().requireAuth) return null;
  return <section id="account-access" aria-label="Account access" className="mb-6 rounded-2xl bg-white p-5 ring-1 ring-slate-200">
    {session ? <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
      <p>Signed in as {session.user.username}. {!session.user.canAnalyzeDocuments && "Document analysis access has not been granted. Contact the administrator."}</p>
      <button className="font-semibold text-blue-700" disabled={busy} onClick={async () => {
        setBusy(true); const revoked = await signOut(); setBusy(false);
        setMessage(revoked ? "Signed out." : "Signed out on this browser. Server revocation could not be confirmed; the credential expires within one hour.");
      }}>Sign out</button>
    </div> : <form className="flex flex-wrap items-end gap-3" onSubmit={async event => {
      event.preventDefault(); if (busy) return; setBusy(true); setMessage("");
      try { await signIn(username, password); setUsername(""); }
      catch (error) { setMessage((error as ApiError).message); }
      finally { setPassword(""); setBusy(false); }
    }}>
      <p className="w-full text-sm text-slate-600">Sign in with an administrator-provided account to analyze documents and use your private checklist.</p>
      <label className="text-sm">Account name<input required autoComplete="username" maxLength={150} value={username} onChange={event => setUsername(event.target.value)} className="mt-1 block rounded-lg border border-slate-300 p-2" /></label>
      <label className="text-sm">Password<input required type="password" autoComplete="current-password" maxLength={1024} value={password} onChange={event => setPassword(event.target.value)} className="mt-1 block rounded-lg border border-slate-300 p-2" /></label>
      <button disabled={busy} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60">{busy ? "Signing in…" : "Sign in"}</button>
    </form>}
    {message && <p role="status" className="mt-3 text-sm text-slate-700">{message}</p>}
  </section>;
}
