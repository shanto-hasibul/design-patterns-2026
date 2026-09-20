import { NavLink, Outlet } from 'react-router-dom'
import HealthStatus from './HealthStatus'

export default function AppLayout() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-4">
          <div>
            <h1 className="text-xl font-bold">Smart Greenhouse</h1>
            <p className="text-sm text-slate-500">
              Monitoring and Control Dashboard
            </p>
          </div>

          <HealthStatus />
        </div>

        <nav className="mx-auto flex max-w-6xl gap-6 px-6 pb-4">
          <NavLink
            to="/"
            className={({ isActive }) =>
              isActive
                ? 'font-medium text-green-700'
                : 'text-slate-600 hover:text-slate-900'
            }
          >
            Home
          </NavLink>

          <NavLink
            to="/dashboard"
            className={({ isActive }) =>
              isActive
                ? 'font-medium text-green-700'
                : 'text-slate-600 hover:text-slate-900'
            }
          >
            Dashboard
          </NavLink>
        </nav>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8">
        <Outlet />
      </main>
    </div>
  )
}