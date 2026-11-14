import type { ReactNode } from 'react'

export function Loading({ label = 'Loading…' }: { label?: string }) {
  return <p className="state">{label}</p>
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="state error" role="alert">
      <p>{message}</p>
      {onRetry && <button onClick={onRetry}>Try again</button>}
    </div>
  )
}

export function Empty({ text }: { text: string }) {
  return <p className="state">{text}</p>
}

export function Badge({ value }: { value: string }) {
  const cls = value.toLowerCase().replace(/_/g, '-')
  return <span className={`badge badge-${cls}`}>{value}</span>
}

export function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="card">
      <h2>{title}</h2>
      {children}
    </section>
  )
}