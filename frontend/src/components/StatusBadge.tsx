// Colored status pill: green = active, amber = on_leave, red = terminated.

const STYLES: Record<string, { label: string; cls: string }> = {
  active: { label: 'Active', cls: 'bg-emerald-100 text-emerald-800' },
  on_leave: { label: 'On Leave', cls: 'bg-amber-100 text-amber-800' },
  terminated: { label: 'Terminated', cls: 'bg-red-100 text-red-800' },
}

export function StatusBadge({ status }: { status: string }) {
  const style = STYLES[status] ?? { label: status, cls: 'bg-gray-100 text-gray-700' }
  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${style.cls}`}
    >
      {style.label}
    </span>
  )
}
