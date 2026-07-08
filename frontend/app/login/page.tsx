import Link from "next/link";

export default function LoginPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-surface px-6">
      <section className="w-full max-w-sm rounded-md border border-line bg-white p-6">
        <h1 className="text-xl font-semibold text-ink">Vision Event Dashboard</h1>
        <p className="mt-2 text-sm text-muted">Sign in to continue.</p>

        <div className="mt-6 space-y-4">
          <label className="block">
            <span className="text-sm font-medium text-slate-700">Email</span>
            <input
              className="mt-1 w-full rounded-md border border-line px-3 py-2 text-sm outline-none focus:border-accent"
              placeholder="admin@example.com"
              type="email"
            />
          </label>
          <label className="block">
            <span className="text-sm font-medium text-slate-700">Password</span>
            <input
              className="mt-1 w-full rounded-md border border-line px-3 py-2 text-sm outline-none focus:border-accent"
              placeholder="password"
              type="password"
            />
          </label>
        </div>

        <Link
          href="/dashboard"
          className="mt-6 block rounded-md bg-accent px-4 py-2 text-center text-sm font-semibold text-white"
        >
          Continue
        </Link>
      </section>
    </main>
  );
}
