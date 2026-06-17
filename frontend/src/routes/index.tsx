import { createFileRoute } from '@tanstack/react-router'
import { useEffect, useState } from 'react'

export const Route = createFileRoute('/')({ component: Dashboard })

// BFF base URL. The proxy shields the upstream providers + their credentials.
const PROXY_URL = 'http://localhost:8000'
const PER_PAGE = 25

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

type EmployeePage = {
  data: Employee[]
  total: number
  page: number
  per_page: number
}

function formatSalary(amount: number, currency: string): string {
  return `${currency} ${amount.toLocaleString('en-US')}`
}

function Dashboard() {
  const [page, setPage] = useState(1)
  const [result, setResult] = useState<EmployeePage | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Fetch runs client-side (useEffect) so we hit the proxy from the browser,
  // not during SSR.
  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    fetch(`${PROXY_URL}/employees?page=${page}&per_page=${PER_PAGE}`)
      .then((res) => {
        if (!res.ok) throw new Error(`Proxy responded ${res.status}`)
        return res.json() as Promise<EmployeePage>
      })
      .then((body) => {
        if (!cancelled) setResult(body)
      })
      .catch((err) => {
        if (!cancelled) setError(err.message)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [page])

  const total = result?.total ?? 0
  const totalPages = total > 0 ? Math.ceil(total / PER_PAGE) : 1
  const employees = result?.data ?? []

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="mx-auto max-w-6xl">
        <header className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Employee Aggregator</h1>
          <p className="text-sm text-gray-500">
            {total > 0 ? `${total.toLocaleString('en-US')} employees` : 'Loading…'}
          </p>
        </header>

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
