import { useEffect, useState } from 'react'

export interface AsyncState<T> {
  data: T | null
  error: string | null
  loading: boolean
  reload: () => void
}

// Loads data and reports loading, error and success. Reloads when `key` changes.
export function useAsync<T>(load: () => Promise<T>, key: string): AsyncState<T> {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [tick, setTick] = useState(0)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    load()
      .then((result) => {
        if (!cancelled) {
          setData(result)
          setLoading(false)
        }
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : 'Unknown error')
          setLoading(false)
        }
      })
    return () => {
      cancelled = true
    }
    // `load` is a new function on every render, so only key and tick trigger a reload.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, tick])

  return { data, error, loading, reload: () => setTick((t) => t + 1) }
}