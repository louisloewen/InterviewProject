// Left navigation sidebar (Design B). Icon-only on small screens, icon + label
// on md+. Dashboard is active; other items are future-proof placeholders.

import { LayoutDashboard, LogOut, Settings, Users } from 'lucide-react'
import type { ComponentType } from 'react'

type NavItemProps = {
  icon: ComponentType<{ className?: string }>
  label: string
  active?: boolean
  disabled?: boolean
}

function NavItem({ icon: Icon, label, active, disabled }: NavItemProps) {
  const base =
    'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors'
  const state = active
    ? 'bg-emerald-50 text-emerald-700'
    : disabled
      ? 'cursor-not-allowed text-gray-300'
      : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
  return (
    <div className={`${base} ${state}`} aria-current={active ? 'page' : undefined}>
      <Icon className="h-5 w-5 shrink-0" />
      <span className="hidden md:inline">{label}</span>
    </div>
  )
}

export function Sidebar({ onLogout }: { onLogout: () => void }) {
  return (
    <aside className="flex w-16 shrink-0 flex-col border-r border-gray-200 bg-white md:w-56">
      <div className="flex items-center gap-2 px-4 py-5">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-emerald-600 text-sm font-bold text-white">
          EA
        </div>
        <span className="hidden text-base font-bold text-gray-900 md:inline">Aggregator</span>
      </div>

      <nav className="flex-1 space-y-1 px-2">
        <NavItem icon={LayoutDashboard} label="Dashboard" active />
        <NavItem icon={Users} label="Employees" disabled />
        <NavItem icon={Settings} label="Settings" disabled />
      </nav>

      <div className="p-2">
        <button
          onClick={onLogout}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-50 hover:text-gray-900"
        >
          <LogOut className="h-5 w-5 shrink-0" />
          <span className="hidden md:inline">Log out</span>
        </button>
      </div>
    </aside>
  )
}
