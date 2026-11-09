import { CircleHelp, Monitor, Moon, Sun } from 'lucide-react'
import { Link, Outlet, useLocation } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { healthOptions, infoOptions } from '@/client/@tanstack/react-query.gen'
import { useTheme } from '@/lib/theme-context'
import { cn } from '@/lib/utils'

function ApiStatus() {
  const { data, isError } = useQuery({ ...healthOptions(), refetchInterval: 30_000 })
  const ok = data?.status === 'ok'
  return (
    <span className="flex items-center gap-2 text-xs text-fg-muted">
      <span className={cn('size-2 rounded-full', ok ? 'bg-ok' : isError ? 'bg-danger' : 'bg-fg-muted')} />
      {ok ? 'API connected' : isError ? 'API offline' : 'Connecting'}
    </span>
  )
}

function Model() {
  const { data } = useQuery({ ...infoOptions(), staleTime: Infinity })
  return data ? (
    <span className="text-xs text-fg-muted" title={`Analyzer ${data.analyzer_id}`}>
      Model <span className="font-medium text-fg">{data.model}</span>
    </span>
  ) : null
}

function ThemeToggle() {
  const { theme, setTheme } = useTheme()
  const next = { system: 'light', light: 'dark', dark: 'system' } as const
  const Icon = { system: Monitor, light: Sun, dark: Moon }[theme]
  return (
    <button
      className="btn-ghost p-1.5"
      onClick={() => setTheme(next[theme])}
      title={`Theme: ${theme}`}
      aria-label={`Theme: ${theme}`}
    >
      <Icon className="size-4" />
    </button>
  )
}

export function Shell() {
  const explaining = useLocation().pathname === '/how-it-works'
  return (
    <div className="flex h-full flex-col">
      <header className="flex h-14 shrink-0 items-center gap-3 border-b border-border bg-surface px-6">
        <Link to="/" className="font-semibold">
          Content Understanding Explorer
        </Link>
        <span className="ml-auto" />
        {/* a new tab: the explorer keeps its document and result */}
        {!explaining && (
          <a href="/how-it-works" target="_blank" rel="noreferrer" className="btn-ghost">
            <CircleHelp className="size-4" />
            How it works
          </a>
        )}
        <Model />
        <ApiStatus />
        <ThemeToggle />
      </header>
      <main className="min-h-0 flex-1">
        <Outlet />
      </main>
    </div>
  )
}
