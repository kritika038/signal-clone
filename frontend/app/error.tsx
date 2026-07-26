"use client";

import { useEffect } from "react";

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error("Signal web error boundary", error);
  }, [error]);

  return (
    <main className="grid min-h-screen place-items-center bg-slate-950 p-6 text-center text-white">
      <div className="max-w-md space-y-4 rounded-3xl border border-white/10 bg-white/5 p-8">
        <h1 className="text-xl font-semibold">Something went wrong</h1>
        <p className="text-sm text-slate-400">Your messages are safe. Please try loading Signal again.</p>
        <button className="rounded-xl bg-white px-4 py-2 text-sm font-medium text-slate-950" onClick={reset} type="button">
          Try again
        </button>
      </div>
    </main>
  );
}
