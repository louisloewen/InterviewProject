import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useEffect, useState } from 'react'

import { authFetch, clearToken, getToken, UnauthorizedError } from '#/lib/auth'

export const Route = createFileRoute('/')({ component: Dashboard })

const PER_PAGE = 25
const SEARCH_DEBOUNCE_MS = 300

type Employee = {
  name: string
  email: string
  department: string
  role: string
  status: string
  annual_salary: number
  currency: string
  hire_date: string
}

type EmployeeStats = {
  active: number
  on_leave: number
  terminated: number
}

type EmployeePage = {
  data: Employee[]
  total: number
  page: number
  per_page: number
  stats: EmployeeStats
}

function formatSalary(amount: number, currency: string): string {
  return `${currency} ${amount.toLocaleString('en-US')}`
}

function Dashboard() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('') // debounced value actually queried
  const [status, setStatus] = useState('')
  const [department, setDepartment] = useState('')
  const [departments, setDepartments] = useState<string[]>([])
  const [result, setResult] = useState<EmployeePage | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // No token -> not logged in. Redirect to the login page (client-side only).
  useEffect(() => {
    if (!getToken()) navigate({ to: '/login' })
  }, [navigate])

  // Debounce the search box: commit the typed value (and reset to page 1) only
  // after the user pauses, so we don't fire a request per keystroke.
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput)
      setPage(1)
    }, SEARCH_DEBOUNCE_MS)
    return () => clearTimeout(timer)
  }, [searchInput])

  // Populate the department dropdown once from the full (unfiltered) set.
  useEffect(() => {
    authFetch('/departments')
      .then((res) => (res.ok ? (res.json() as Promise<string[]>) : []))
      .then(setDepartments)
      .catch(() => {
        // Non-critical; the main fetch handles auth redirects.
      })
  }, [])

  // Fetch the (filtered, paginated) page. authFetch attaches the bearer token;
  // a 401 throws UnauthorizedError, which bounces us back to login.
  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    const params = new URLSearchParams({ page: String(page), per_page: String(PER_PAGE) })
    if (search) params.set('search', search)
    if (status) params.set('status', status)
    if (department) params.set('department', department)

    authFetch(`/employees?${params.toString()}`)
      .then((res) => {
        if (!res.ok) throw new Error(`Proxy responded ${res.status}`)
        return res.json() as Promise<EmployeePage>
      })
      .then((body) => {
        if (!cancelled) setResult(body)
      })
      .catch((err) => {
        if (cancelled) return
        if (err instanceof UnauthorizedError) {
          navigate({ to: '/login' })
        } else {
          setError(err.message)
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [page, search, status, department, navigate])

  // Filter changes reset to page 1 so you never land past the filtered range.
  function onStatusChange(value: string) {
    setStatus(value)
    setPage(1)
  }
  function onDepartmentChange(value: string) {
    setDepartment(value)
    setPage(1)
  }

  function onLogout() {
    clearToken()
    navigate({ to: '/login' })
  }

  const total = result?.total ?? 0
  const totalPages = total > 0 ? Math.ceil(total / PER_PAGE) : 1
  const employees = result?.data ?? []
  const stats = result?.stats

  const cards = [
    { label: 'Total', value: total },
    { label: 'Active', value: stats?.active ?? 0 },
    { label: 'On Leave', value: stats?.on_leave ?? 0 },
    { label: 'Terminated', value: stats?.terminated ?? 0 },
  ]

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="mx-auto max-w-6xl">
        <header className="mb-6 flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Employee Aggregator</h1>
            <p className="text-sm text-gray-500">
              {total > 0 ? `${total.toLocaleString('en-US')} employees` : 'Loading…'}
            </p>
          </div>
          <button
            onClick={onLogout}
            className="rounded border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Log out
          </button>
        </header>

        {/* Summary stat cards (reflect the filtered set). */}
        <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
          {cards.map((c) => (
            <div key={c.label} className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
              <p className="text-xs uppercase tracking-wide text-gray-500">{c.label}</p>
              <p className="mt-1 text-2xl font-bold text-gray-900">
                {c.value.toLocaleString('en-US')}
              </p>
            </div>
          ))}
        </div>

        {/* Search + filters. */}
        <div className="mb-4 flex flex-col gap-3 sm:flex-row">
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search name or email…"
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-gray-500 focus:outline-none sm:flex-1"
          />
          <select
            value={status}
            onChange={(e) => onStatusChange(e.target.value)}
            className="rounded border border-gray-300 bg-white px-3 py-2 text-sm focus:border-gray-500 focus:outline-none"
          >
            <option value="">All statuses</option>
            <option value="active">Active</option>
            <option value="on_leave">On Leave</option>
            <option value="terminated">Terminated</option>
          </select>
          <select
            value={department}
            onChange={(e) => onDepartmentChange(e.target.value)}
            className="rounded border border-gray-300 bg-white px-3 py-2 text-sm focus:border-gray-500 focus:outline-none"
          >
            <option value="">All departments</option>
            {departments.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </div>

        {error && (
          <div className="mb-4 rounded border border-red-300 bg-red-50 p-3 text-sm text-red-700">
            Failed to load employees: {error}
          </div>
        )}

        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-gray-200 bg-gray-100 text-xs uppercase tracking-wide text-gray-600">
              <tr>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Email</th>
                <th className="px-4 py-3">Department</th>
                <th className="px-4 py-3">Role</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Salary</th>
                <th className="px-4 py-3">Hire Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-gray-400">
                    Loading…
                  </td>
                </tr>
              ) : employees.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-gray-400">
                    No employees found.
                  </td>
                </tr>
              ) : (
                employees.map((emp) => (
                  <tr key={emp.email} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-900">{emp.name}</td>
                    <td className="px-4 py-3 text-gray-600">{emp.email}</td>
                    <td className="px-4 py-3 text-gray-600">{emp.department}</td>
                    <td className="px-4 py-3 text-gray-600">{emp.role}</td>
                    <td className="px-4 py-3 text-gray-600">{emp.status}</td>
                    <td className="px-4 py-3 text-gray-600">
                      {formatSalary(emp.annual_salary, emp.currency)}
                    </td>
                    <td className="px-4 py-3 text-gray-600">{emp.hire_date}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="mt-4 flex items-center justify-between">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1 || loading}
            className="rounded border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Previous
          </button>
          <span className="text-sm text-gray-600">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages || loading}
            className="rounded border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  )
}
