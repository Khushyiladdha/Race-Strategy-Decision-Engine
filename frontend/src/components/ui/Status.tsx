export function Loading({ label = 'Loading…' }: { label?: string }) {
  return <p className="font-body text-sm text-muted">{label}</p>
}

export function ErrorNote({ message }: { message: string }) {
  return (
    <div className="rounded-panel border border-loss/40 bg-loss/5 px-4 py-3">
      <p className="font-mono text-sm text-loss">{message}</p>
    </div>
  )
}
