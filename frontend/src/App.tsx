import { useEffect, useMemo, useState } from 'react'
import './App.css'

type ApiStatus = 'idle' | 'loading' | 'ok' | 'error'

type Spot = {
  id: number
  bar_id: number
  name: string
}

type Bar = {
  id: number
  name: string
  timezone: string
}

type Bartender = {
  id: number
  bar_id: number
  name: string
  is_active: boolean
  temp_username?: string | null
  temp_password?: string | null
}

type ShiftCreate = {
  bar_id: number
  spot_id: number
  bartender_name: string
  shift_date: string
  personal_sales_volume: number
  total_bar_sales: number
  personal_tips: number
  hours_worked: number
  transactions_count?: number | null
}

type ShiftOut = ShiftCreate & {
  id: number
  pct_of_bar_sales: number
  tip_pct: number
  sales_per_hour: number
  score_total?: number | null
  score_version?: string | null
}

type LeaderboardEntry = {
  bartender_name: string
  avg_score: number
  shifts_count: number
  last_shift_date: string | null
}

type LeaderboardResponse = {
  bar_id: number
  start_date: string | null
  end_date: string | null
  entries: LeaderboardEntry[]
}

type AuthUser = {
  id: number
  bar_id: number
  email: string
  name: string
  role: 'owner' | 'employee'
  must_change_credentials: boolean
}

type TokenResponse = {
  access_token: string
  token_type: string
  must_change_credentials?: boolean
}

type ProvisionBartenderResponse = {
  bartender: Bartender
  temporary_username: string
  temporary_password: string
}

function withAuthHeaders(headers: HeadersInit | undefined, token: string | null): HeadersInit {
  return {
    ...(headers ?? {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

async function apiGet<T>(path: string, token: string | null = null): Promise<T> {
  const resp = await fetch(path, { headers: withAuthHeaders(undefined, token) })
  if (!resp.ok) {
    const detail = await safeReadErrorDetail(resp)
    throw new Error(`GET ${path} failed: ${resp.status}${detail ? ` — ${detail}` : ''}`)
  }
  return resp.json() as Promise<T>
}

async function apiPost<T>(path: string, body: unknown | undefined, token: string | null = null): Promise<T> {
  const init: RequestInit = { method: 'POST' }
  if (body !== undefined) {
    init.headers = withAuthHeaders({ 'Content-Type': 'application/json' }, token)
    init.body = JSON.stringify(body)
  } else {
    init.headers = withAuthHeaders(undefined, token)
  }

  const resp = await fetch(path, init)
  if (!resp.ok) {
    const detail = await safeReadErrorDetail(resp)
    throw new Error(`POST ${path} failed: ${resp.status}${detail ? ` — ${detail}` : ''}`)
  }
  return resp.json() as Promise<T>
}

async function apiPostForm<T>(path: string, form: Record<string, string>, token: string | null = null): Promise<T> {
  const body = new URLSearchParams()
  for (const [k, v] of Object.entries(form)) body.set(k, v)

  const resp = await fetch(path, {
    method: 'POST',
    headers: withAuthHeaders({ 'Content-Type': 'application/x-www-form-urlencoded' }, token),
    body,
  })

  if (!resp.ok) {
    const detail = await safeReadErrorDetail(resp)
    throw new Error(`POST ${path} failed: ${resp.status}${detail ? ` — ${detail}` : ''}`)
  }
  return resp.json() as Promise<T>
}

async function apiPatch<T>(path: string, body: unknown, token: string | null = null): Promise<T> {
  const resp = await fetch(path, {
    method: 'PATCH',
    headers: withAuthHeaders({ 'Content-Type': 'application/json' }, token),
    body: JSON.stringify(body),
  })
  if (!resp.ok) {
    const detail = await safeReadErrorDetail(resp)
    throw new Error(`PATCH ${path} failed: ${resp.status}${detail ? ` — ${detail}` : ''}`)
  }
  return resp.json() as Promise<T>
}

async function apiDelete<T>(path: string, token: string | null = null): Promise<T> {
  const resp = await fetch(path, { method: 'DELETE', headers: withAuthHeaders(undefined, token) })
  if (!resp.ok) {
    const detail = await safeReadErrorDetail(resp)
    throw new Error(`DELETE ${path} failed: ${resp.status}${detail ? ` — ${detail}` : ''}`)
  }
  return resp.json() as Promise<T>
}

async function safeReadErrorDetail(resp: Response): Promise<string | null> {
  try {
    const contentType = resp.headers.get('content-type') || ''
    if (contentType.includes('application/json')) {
      const data = (await resp.json()) as unknown
      if (data && typeof data === 'object' && 'detail' in data) {
        const detail = (data as { detail?: unknown }).detail
        if (typeof detail === 'string') return detail
        return JSON.stringify(detail)
      }
      return JSON.stringify(data)
    }
    const text = await resp.text()
    return text ? text.slice(0, 300) : null
  } catch {
    return null
  }
}

function App() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>('idle')
  const [view, setView] = useState<'dashboard' | 'settings'>('dashboard')

  const [token, setToken] = useState<string | null>(() => localStorage.getItem('shiftscore_token'))
  const [me, setMe] = useState<AuthUser | null>(null)
  const [authErrorText, setAuthErrorText] = useState<string | null>(null)
  const [isAuthBusy, setIsAuthBusy] = useState(false)

  const [loginEmail, setLoginEmail] = useState('')
  const [loginPassword, setLoginPassword] = useState('')

  const [bootstrapBarName, setBootstrapBarName] = useState('My Bar')
  const [bootstrapName, setBootstrapName] = useState('Owner')
  const [bootstrapEmail, setBootstrapEmail] = useState('')
  const [bootstrapPassword, setBootstrapPassword] = useState('')

  const [firstLoginEmail, setFirstLoginEmail] = useState('')
  const [firstLoginPassword, setFirstLoginPassword] = useState('')


  const [bars, setBars] = useState<Bar[]>([])
  const [barId, setBarId] = useState<number | null>(null)
  const [spots, setSpots] = useState<Spot[]>([])
  const [bartenders, setBartenders] = useState<Bartender[]>([])
  const [recentShifts, setRecentShifts] = useState<ShiftOut[]>([])
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([])
  const [errorText, setErrorText] = useState<string | null>(null)
  const [isSeeding, setIsSeeding] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [isLoadingLeaderboard, setIsLoadingLeaderboard] = useState(false)
  const [isLoadingBars, setIsLoadingBars] = useState(false)
  const [isLoadingSpots, setIsLoadingSpots] = useState(false)
  const [isLoadingBartenders, setIsLoadingBartenders] = useState(false)

  const [barEditName, setBarEditName] = useState('')
  const [barEditTimezone, setBarEditTimezone] = useState('America/New_York')

  const [newSpotName, setNewSpotName] = useState('')
  const [newBartenderName, setNewBartenderName] = useState('')
  const [selectedBartenderId, setSelectedBartenderId] = useState<number>(0)

  const defaultShiftDate = useMemo(() => {
    const d = new Date()
    const yyyy = d.getFullYear()
    const mm = String(d.getMonth() + 1).padStart(2, '0')
    const dd = String(d.getDate()).padStart(2, '0')
    return `${yyyy}-${mm}-${dd}`
  }, [])

  const [form, setForm] = useState<ShiftCreate>({
    bar_id: 0,
    spot_id: 0,
    bartender_name: '',
    shift_date: defaultShiftDate,
    personal_sales_volume: 0,
    total_bar_sales: 0,
    personal_tips: 0,
    hours_worked: 6,
    transactions_count: null,
  })

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setApiStatus('loading')
      setErrorText(null)
      try {
        await apiGet<{ status: string }>('/api/health')
        if (cancelled) return
        setApiStatus('ok')
      } catch (e) {
        if (cancelled) return
        setApiStatus('error')
        setErrorText(e instanceof Error ? e.message : 'Failed to reach API')
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      if (!token) {
        setMe(null)
        return
      }
      setIsAuthBusy(true)
      setAuthErrorText(null)
      try {
        const user = await apiGet<AuthUser>('/api/auth/me', token)
        if (cancelled) return
        setMe(user)

        if (user.must_change_credentials) {
          setFirstLoginEmail('')
          setFirstLoginPassword('')
        }

        // Load initial bar context once authenticated.
        const existingBars = await loadBars(token)
        if (cancelled) return
        if (barId === null && existingBars.length > 0) {
          const first = existingBars[0]
          setBarId(first.id)
          setBarEditName(first.name)
          setBarEditTimezone(first.timezone)
          void loadBarContext(first.id, token)
        }
      } catch (e) {
        if (cancelled) return
        setMe(null)
        setAuthErrorText(e instanceof Error ? e.message : 'Authentication failed')
        localStorage.removeItem('shiftscore_token')
        setToken(null)
      } finally {
        if (!cancelled) setIsAuthBusy(false)
      }
    })()
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  const isOwner = me?.role === 'owner'

  function logout() {
    localStorage.removeItem('shiftscore_token')
    setToken(null)
    setMe(null)
    setView('dashboard')
  }

  async function submitFirstLogin(e: React.FormEvent) {
    e.preventDefault()
    if (!token) return
    setIsAuthBusy(true)
    setAuthErrorText(null)
    try {
      const resp = await apiPost<TokenResponse>(
        '/api/auth/first-login',
        { login: firstLoginEmail, password: firstLoginPassword },
        token
      )
      localStorage.setItem('shiftscore_token', resp.access_token)
      setToken(resp.access_token)
      setFirstLoginPassword('')
    } catch (e) {
      setAuthErrorText(e instanceof Error ? e.message : 'Failed to update credentials')
    } finally {
      setIsAuthBusy(false)
    }
  }

  async function doLogin(e: React.FormEvent) {
    e.preventDefault()
    setIsAuthBusy(true)
    setAuthErrorText(null)
    try {
      const resp = await apiPostForm<TokenResponse>('/api/auth/login', {
        username: loginEmail,
        password: loginPassword,
      })
      localStorage.setItem('shiftscore_token', resp.access_token)
      setToken(resp.access_token)
      setLoginPassword('')
    } catch (e) {
      setAuthErrorText(e instanceof Error ? e.message : 'Login failed')
    } finally {
      setIsAuthBusy(false)
    }
  }

  async function doBootstrap(e: React.FormEvent) {
    e.preventDefault()
    setIsAuthBusy(true)
    setAuthErrorText(null)
    try {
      const resp = await apiPost<TokenResponse>(
        '/api/auth/bootstrap',
        {
          bar_name: bootstrapBarName,
          owner_name: bootstrapName,
          owner_login: bootstrapEmail,
          owner_password: bootstrapPassword,
        },
        null
      )
      localStorage.setItem('shiftscore_token', resp.access_token)
      setToken(resp.access_token)
      setBootstrapPassword('')
    } catch (e) {
      setAuthErrorText(e instanceof Error ? e.message : 'Bootstrap failed')
    } finally {
      setIsAuthBusy(false)
    }
  }

  async function loadBars(authToken: string | null = token) {
    setIsLoadingBars(true)
    try {
      const data = await apiGet<Bar[]>('/api/bars', authToken)
      setBars(data)
      return data
    } catch (e) {
      setErrorText(e instanceof Error ? e.message : 'Failed to load bars')
      return []
    } finally {
      setIsLoadingBars(false)
    }
  }

  async function loadBarContext(targetBarId: number, authToken: string | null = token) {
    setErrorText(null)
    setIsLoadingSpots(true)
    setIsLoadingBartenders(true)
    try {
      const [loadedSpots, loadedBartenders] = await Promise.all([
        apiGet<Spot[]>(`/api/spots?bar_id=${targetBarId}`, authToken),
        apiGet<Bartender[]>(`/api/bartenders?bar_id=${targetBarId}`, authToken),
      ])
      setSpots(loadedSpots)
      setBartenders(loadedBartenders)
      setSelectedBartenderId(0)

      setForm((f) => ({
        ...f,
        bar_id: targetBarId,
        spot_id: loadedSpots[0]?.id ?? 0,
      }))

      const shifts = await apiGet<ShiftOut[]>(`/api/shifts?bar_id=${targetBarId}&limit=25`, authToken)
      setRecentShifts(shifts)

      const lb = await apiGet<LeaderboardResponse>(`/api/leaderboard?limit=10`, authToken)
      setLeaderboard(lb.entries)
    } catch (e) {
      setErrorText(e instanceof Error ? e.message : 'Failed to load bar data')
    } finally {
      setIsLoadingSpots(false)
      setIsLoadingBartenders(false)
    }
  }

  async function seedAndLoad() {
    setErrorText(null)
    setIsSeeding(true)
    try {
      const seed = await apiPost<{ bar_id: number }>('/api/dev/seed', undefined, token)
      setBarId(seed.bar_id)

      const updatedBars = await loadBars()
      const seededBar = updatedBars.find((b) => b.id === seed.bar_id)
      if (seededBar) {
        setBarEditName(seededBar.name)
        setBarEditTimezone(seededBar.timezone)
      }
      await loadBarContext(seed.bar_id)
    } catch (e) {
      setErrorText(e instanceof Error ? e.message : 'Seed failed')
    } finally {
      setIsSeeding(false)
    }
  }

  async function refreshLeaderboard() {
    if (!token) return
    setErrorText(null)
    setIsLoadingLeaderboard(true)
    try {
      const lb = await apiGet<LeaderboardResponse>(`/api/leaderboard?limit=10`, token)
      setLeaderboard(lb.entries)
    } catch (e) {
      setErrorText(e instanceof Error ? e.message : 'Failed to load leaderboard')
    } finally {
      setIsLoadingLeaderboard(false)
    }
  }

  async function refreshBarsAndSelect(nextBarId: number) {
    const updatedBars = await loadBars()
    const selected = updatedBars.find((b) => b.id === nextBarId)
    if (selected) {
      setBarEditName(selected.name)
      setBarEditTimezone(selected.timezone)
    }
  }

  async function saveBarSettings() {
    if (!barId) return
    setErrorText(null)
    try {
      const updated = await apiPatch<Bar>(`/api/bars/${barId}`, { name: barEditName, timezone: barEditTimezone }, token)
      await refreshBarsAndSelect(updated.id)
    } catch (e) {
      setErrorText(e instanceof Error ? e.message : 'Failed to update bar')
    }
  }

  async function addSpot() {
    if (!barId) return
    setErrorText(null)
    try {
      const created = await apiPost<Spot>('/api/spots', { bar_id: barId, name: newSpotName }, token)
      setSpots((prev) => [...prev, created])
      setNewSpotName('')
      setForm((f) => ({
        ...f,
        bar_id: barId,
        spot_id: f.spot_id || created.id,
      }))
    } catch (e) {
      setErrorText(e instanceof Error ? e.message : 'Failed to add spot')
    }
  }

  async function removeSpot(spot_id: number) {
    setErrorText(null)
    try {
      await apiDelete<{ status: string }>(`/api/spots/${spot_id}`, token)
      setSpots((prev) => prev.filter((s) => s.id !== spot_id))
      setForm((f) => ({ ...f, spot_id: f.spot_id === spot_id ? 0 : f.spot_id }))
    } catch (e) {
      setErrorText(e instanceof Error ? e.message : 'Failed to delete spot')
    }
  }

  async function addBartender() {
    if (!barId) return
    setErrorText(null)
    try {
      const created = await apiPost<ProvisionBartenderResponse>('/api/bartenders/provision', { name: newBartenderName }, token)
      setBartenders((prev) => [
        ...prev,
        {
          ...created.bartender,
          temp_username: created.temporary_username,
          temp_password: created.temporary_password,
        },
      ])
      setNewBartenderName('')
    } catch (e) {
      setErrorText(e instanceof Error ? e.message : 'Failed to add bartender')
    }
  }

  async function toggleBartenderActive(bartender: Bartender) {
    setErrorText(null)
    try {
      const updated = await apiPatch<Bartender>(
        `/api/bartenders/${bartender.id}`,
        { is_active: !bartender.is_active },
        token
      )
      setBartenders((prev) => prev.map((b) => (b.id === updated.id ? updated : b)))
    } catch (e) {
      setErrorText(e instanceof Error ? e.message : 'Failed to update bartender')
    }
  }

  async function deleteBartenderProfile(bartender: Bartender) {
    if (!isOwner) return
    if (!barId) return

    const confirmDelete = window.confirm(`Delete bartender profile for "${bartender.name}"?`)
    if (!confirmDelete) return

    const clearSales = window.confirm(
      `Also clear ALL saved sales/shift data currently linked to "${bartender.name}"?\n\nOK = clear sales data\nCancel = keep sales data (only remove the login/profile).`
    )

    setErrorText(null)
    try {
      await apiDelete<{ status: string }>(`/api/bartenders/${bartender.id}?clear_sales=${clearSales ? 'true' : 'false'}`, token)
      setBartenders((prev) => prev.filter((b) => b.id !== bartender.id))

      if (selectedBartenderId === bartender.id) {
        setSelectedBartenderId(0)
        setForm((f) => ({ ...f, bartender_name: '' }))
      }

      // If we cleared sales data, refresh dashboard lists/leaderboard.
      if (clearSales) {
        void loadBarContext(barId, token)
      }
    } catch (e) {
      setErrorText(e instanceof Error ? e.message : 'Failed to delete bartender')
    }
  }

  async function submitShift(e: React.FormEvent) {
    e.preventDefault()
    if (!isOwner) {
      setErrorText('Employees cannot enter shifts. Ask an owner.')
      return
    }
    setErrorText(null)
    setIsSubmitting(true)
    try {
      const created = await apiPost<ShiftOut>('/api/shifts', {
        ...form,
        transactions_count: form.transactions_count ?? null,
      }, token)
      setRecentShifts((prev) => [created, ...prev].slice(0, 25))
      setForm((f) => ({
        ...f,
        bartender_name: '',
        personal_sales_volume: 0,
        total_bar_sales: 0,
        personal_tips: 0,
        hours_worked: f.hours_worked,
        transactions_count: null,
      }))
    } catch (err) {
      setErrorText(err instanceof Error ? err.message : 'Failed to create shift')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (apiStatus !== 'ok') {
    return (
      <div className="shell">
        <header className="topbar">
          <div className="brand">
            <div className="brand-mark">SS</div>
            <div>
              <div className="brand-title">ShiftScore</div>
              <div className="brand-subtitle">MVP • shift entry + scoring</div>
            </div>
          </div>

          <div className="status">
            <span className={`pill ${apiStatus}`}>API: {apiStatus}</span>
          </div>
        </header>

        {errorText && <div className="alert">{errorText}</div>}
      </div>
    )
  }

  if (!me) {
    return (
      <div className="shell">
        <header className="topbar">
          <div className="brand">
            <div className="brand-mark">SS</div>
            <div>
              <div className="brand-title">ShiftScore</div>
              <div className="brand-subtitle">Login required</div>
            </div>
          </div>
          <div className="status">
            <span className="pill ok">API: ok</span>
          </div>
        </header>

        {authErrorText && <div className="alert">{authErrorText}</div>}

        <main className="grid">
          <section className="panel">
            <h2>Login</h2>
            <form className="form" onSubmit={doLogin}>
              <label>
                Username or email
                <input value={loginEmail} onChange={(e) => setLoginEmail(e.target.value)} placeholder="jay or owner@bar.com" />
              </label>
              <label>
                Password
                <input type="password" value={loginPassword} onChange={(e) => setLoginPassword(e.target.value)} />
              </label>
              <div className="actions">
                <button className="btn primary" type="submit" disabled={isAuthBusy || !loginEmail || !loginPassword}>
                  {isAuthBusy ? 'Working…' : 'Login'}
                </button>
              </div>
            </form>
          </section>

          <section className="panel">
            <h2>Bootstrap first owner</h2>
            <p className="muted">Only works if no owner exists yet.</p>
            <form className="form" onSubmit={doBootstrap}>
              <label>
                Bar name
                <input value={bootstrapBarName} onChange={(e) => setBootstrapBarName(e.target.value)} />
              </label>
              <label>
                Owner name
                <input value={bootstrapName} onChange={(e) => setBootstrapName(e.target.value)} />
              </label>
              <label>
                Owner username or email
                <input value={bootstrapEmail} onChange={(e) => setBootstrapEmail(e.target.value)} placeholder="jay or owner@bar.com" />
              </label>
              <label>
                Owner password
                <input
                  type="password"
                  value={bootstrapPassword}
                  onChange={(e) => setBootstrapPassword(e.target.value)}
                />
              </label>
              <div className="actions">
                <button
                  className="btn"
                  type="submit"
                  disabled={isAuthBusy || !bootstrapEmail || !bootstrapPassword || !bootstrapBarName.trim()}
                >
                  {isAuthBusy ? 'Working…' : 'Create owner + bar'}
                </button>
              </div>
            </form>
          </section>
        </main>
      </div>
    )
  }

  if (me.must_change_credentials) {
    return (
      <div className="shell">
        <header className="topbar">
          <div className="brand">
            <div className="brand-mark">SS</div>
            <div>
              <div className="brand-title">ShiftScore</div>
              <div className="brand-subtitle">First login setup</div>
            </div>
          </div>
          <div className="status">
            <span className="pill ok">{me.role}</span>
            <button className="btn" onClick={logout}>
              Logout
            </button>
          </div>
        </header>

        {authErrorText && <div className="alert">{authErrorText}</div>}

        <main className="grid">
          <section className="panel">
            <h2>Set your username + password</h2>
            <p className="muted">You’re logged in with temporary credentials. Choose your real login email + a new password.</p>

            <form className="form" onSubmit={submitFirstLogin}>
              <label>
                New username or email
                <input value={firstLoginEmail} onChange={(e) => setFirstLoginEmail(e.target.value)} placeholder="liliabarnet or lilia@icloud.com" />
              </label>
              <label>
                New password
                <input type="password" value={firstLoginPassword} onChange={(e) => setFirstLoginPassword(e.target.value)} />
              </label>
              <div className="actions">
                <button className="btn primary" type="submit" disabled={isAuthBusy || !firstLoginEmail || !firstLoginPassword}>
                  {isAuthBusy ? 'Working…' : 'Save credentials'}
                </button>
              </div>
            </form>
          </section>
        </main>
      </div>
    )
  }

  return (
    <>
      <div className="shell">
        <header className="topbar">
          <div className="brand">
            <div className="brand-mark">SS</div>
            <div>
              <div className="brand-title">ShiftScore</div>
              <div className="brand-subtitle">MVP • shift entry + scoring</div>
            </div>
          </div>

          <nav className="nav">
            <button className={`tab ${view === 'dashboard' ? 'active' : ''}`} onClick={() => setView('dashboard')}>
              Dashboard
            </button>
            {isOwner && (
              <button className={`tab ${view === 'settings' ? 'active' : ''}`} onClick={() => setView('settings')}>
                Settings
              </button>
            )}
          </nav>

          <div className="status">
            <span className={`pill ${apiStatus}`}>API: {apiStatus}</span>
            <span className="pill ok">{me.role}</span>
            {isOwner && (
              <button className="btn" onClick={seedAndLoad} disabled={apiStatus !== 'ok' || isSeeding}>
                {isSeeding ? 'Seeding…' : 'Seed demo data'}
              </button>
            )}
            <button className="btn" onClick={logout}>
              Logout
            </button>
          </div>
        </header>

        {errorText && <div className="alert">{errorText}</div>}

        {view === 'settings' ? (
          <main className="grid">
            <section className="panel">
              <h2>Bar setup</h2>
              <p className="muted">Create and manage bars, spots, and bartender profiles.</p>

              <div className="form">
                <div className="row">
                  <label>
                    Select bar
                    <select
                      value={barId ?? ''}
                      onChange={async (e) => {
                        const next = Number(e.target.value)
                        setBarId(next)
                        const selected = bars.find((b) => b.id === next)
                        if (selected) {
                          setBarEditName(selected.name)
                          setBarEditTimezone(selected.timezone)
                        }
                        await loadBarContext(next)
                      }}
                      disabled={isLoadingBars || bars.length === 0}
                    >
                      {bars.length === 0 ? (
                        <option value="">No bars yet</option>
                      ) : (
                        bars.map((b) => (
                          <option key={b.id} value={b.id}>
                            {b.name} (#{b.id})
                          </option>
                        ))
                      )}
                    </select>
                  </label>
                  <label>
                    Bars
                    <button className="btn" type="button" onClick={() => void loadBars()} disabled={isLoadingBars}>
                      {isLoadingBars ? 'Loading…' : 'Refresh bars'}
                    </button>
                  </label>
                </div>

                <h3 className="h3">Bars</h3>
                <p className="muted">Bar creation happens during Bootstrap. Multi-bar support can be added later.</p>

                <h3 className="h3">Basic bar settings</h3>
                <div className="row">
                  <label>
                    Name
                    <input value={barEditName} onChange={(e) => setBarEditName(e.target.value)} disabled={!barId} />
                  </label>
                  <label>
                    Timezone
                    <input value={barEditTimezone} onChange={(e) => setBarEditTimezone(e.target.value)} disabled={!barId} />
                  </label>
                </div>
                <div className="actions">
                  <button className="btn" type="button" onClick={saveBarSettings} disabled={!barId || !isOwner}>
                    Save settings
                  </button>
                </div>
              </div>
            </section>

            <section className="panel">
              <div className="panel-header">
                <h2>Spots</h2>
                <span className="muted">{isLoadingSpots ? 'Loading…' : `${spots.length} spots`}</span>
              </div>

              {!barId ? (
                <p className="muted">Select or create a bar first.</p>
              ) : (
                <>
                  <div className="form">
                    <div className="row">
                      <label>
                        New spot name
                        <input value={newSpotName} onChange={(e) => setNewSpotName(e.target.value)} placeholder="e.g. Main Well" />
                      </label>
                      <label>
                        
                        <button className="btn primary" type="button" onClick={addSpot} disabled={!newSpotName.trim() || !isOwner}>
                          Add spot
                        </button>
                      </label>
                    </div>
                  </div>

                  {spots.length === 0 ? (
                    <p className="muted">No spots yet.</p>
                  ) : (
                    <div className="list">
                      {spots.map((s) => (
                        <div key={s.id} className="list-row">
                          <div>
                            <strong>{s.name}</strong>
                            <div className="muted">Spot #{s.id}</div>
                          </div>
                          <button className="btn danger" type="button" onClick={() => removeSpot(s.id)} disabled={!isOwner}>
                            Delete
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </section>

            <section className="panel">
              <div className="panel-header">
                <h2>Bartenders</h2>
                <span className="muted">{isLoadingBartenders ? 'Loading…' : `${bartenders.length} profiles`}</span>
              </div>

              {!barId ? (
                <p className="muted">Select or create a bar first.</p>
              ) : (
                <>
                  <div className="form">
                    <div className="row">
                      <label>
                        New bartender name
                        <input value={newBartenderName} onChange={(e) => setNewBartenderName(e.target.value)} placeholder="e.g. Jay" />
                      </label>
                      <label>
                        
                        <button
                          className="btn primary"
                          type="button"
                          onClick={addBartender}
                          disabled={!newBartenderName.trim() || !isOwner}
                        >
                          Add bartender
                        </button>
                      </label>
                    </div>
                  </div>

                  {bartenders.length === 0 ? (
                    <p className="muted">No bartender profiles yet.</p>
                  ) : (
                    <div className="list">
                      {bartenders.map((b) => (
                        <div key={b.id} className="list-row">
                          <div>
                            <strong>{b.name}</strong>
                            <div className="muted">
                              #{b.id} • {b.is_active ? 'Active' : 'Inactive'}
                            </div>
                            {b.temp_username && b.temp_password && (
                              <div className="muted">
                                Temp login: <strong>{b.temp_username}</strong> / <strong>{b.temp_password}</strong>
                              </div>
                            )}
                          </div>
                          <div className="actions">
                            <button className="btn" type="button" onClick={() => toggleBartenderActive(b)} disabled={!isOwner}>
                              {b.is_active ? 'Deactivate' : 'Activate'}
                            </button>
                            <button className="btn danger" type="button" onClick={() => void deleteBartenderProfile(b)} disabled={!isOwner}>
                              Delete
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </section>
          </main>
        ) : (
          <main className="grid">
          <section className="panel">
            <h2>Enter a shift</h2>
            <p className="muted">
              Start by clicking <strong>Seed demo data</strong>. Then enter the shift metrics below.
            </p>

            {!isOwner && <p className="muted">Employees can view stats but cannot enter shifts.</p>}

            <form className="form" onSubmit={submitShift}>
              <div className="row">
                <label>
                  Date
                  <input
                    type="date"
                    value={form.shift_date}
                    onChange={(e) => setForm((f) => ({ ...f, shift_date: e.target.value }))}
                    required
                  />
                </label>
                <label>
                  Spot
                  <select
                    value={form.spot_id}
                    onChange={(e) => setForm((f) => ({ ...f, spot_id: Number(e.target.value) }))}
                    disabled={spots.length === 0}
                    required
                  >
                    {spots.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <label>
                Bartender profile (optional)
                <select
                  value={selectedBartenderId}
                  onChange={(e) => {
                    const nextId = Number(e.target.value)
                    setSelectedBartenderId(nextId)
                    const selected = bartenders.find((b) => b.id === nextId)
                    if (selected) {
                      setForm((f) => ({ ...f, bartender_name: selected.name }))
                    }
                    if (nextId === 0) {
                      setForm((f) => ({ ...f, bartender_name: '' }))
                    }
                  }}
                  disabled={!barId || bartenders.length === 0}
                >
                  <option value={0}>Custom / type below</option>
                  {bartenders
                    .filter((b) => b.is_active)
                    .map((b) => (
                      <option key={b.id} value={b.id}>
                        {b.name}
                      </option>
                    ))}
                </select>
              </label>

              <label>
                Bartender name
                <input
                  value={form.bartender_name}
                  onChange={(e) => setForm((f) => ({ ...f, bartender_name: e.target.value }))}
                  placeholder="e.g. Jay"
                  required
                  disabled={selectedBartenderId !== 0}
                />
              </label>

              <div className="row">
                <label>
                  Personal sales ($)
                  <input
                    type="number"
                    min={0}
                    step={0.01}
                    value={form.personal_sales_volume}
                    onChange={(e) => setForm((f) => ({ ...f, personal_sales_volume: Number(e.target.value) }))}
                    required
                  />
                </label>
                <label>
                  Total bar sales ($)
                  <input
                    type="number"
                    min={0}
                    step={0.01}
                    value={form.total_bar_sales}
                    onChange={(e) => setForm((f) => ({ ...f, total_bar_sales: Number(e.target.value) }))}
                    required
                  />
                </label>
              </div>

              <div className="row">
                <label>
                  Personal tips ($)
                  <input
                    type="number"
                    min={0}
                    step={0.01}
                    value={form.personal_tips}
                    onChange={(e) => setForm((f) => ({ ...f, personal_tips: Number(e.target.value) }))}
                    required
                  />
                </label>
                <label>
                  Hours worked
                  <input
                    type="number"
                    min={0}
                    step={0.25}
                    value={form.hours_worked}
                    onChange={(e) => setForm((f) => ({ ...f, hours_worked: Number(e.target.value) }))}
                    required
                  />
                </label>
              </div>

              <label>
                Transactions (optional)
                <input
                  type="number"
                  min={0}
                  step={1}
                  value={form.transactions_count ?? ''}
                  onChange={(e) =>
                    setForm((f) => ({
                      ...f,
                      transactions_count: e.target.value === '' ? null : Number(e.target.value),
                    }))
                  }
                  placeholder="(optional)"
                />
              </label>

              <div className="actions">
                <button
                  className="btn primary"
                  type="submit"
                  disabled={apiStatus !== 'ok' || !barId || isSubmitting || spots.length === 0 || !isOwner}
                >
                  {isSubmitting ? 'Saving…' : 'Calculate + Save'}
                </button>
              </div>
            </form>
          </section>

          <section className="panel">
            <div className="panel-header">
              <h2>Recent shifts</h2>
              {barId && (
                <button
                  className="btn"
                  onClick={async () => {
                    setIsRefreshing(true)
                    setErrorText(null)
                    try {
                        const shifts = await apiGet<ShiftOut[]>(`/api/shifts?bar_id=${barId}&limit=25`, token)
                      setRecentShifts(shifts)
                    } catch (e) {
                      setErrorText(e instanceof Error ? e.message : 'Failed to refresh')
                    } finally {
                      setIsRefreshing(false)
                    }
                  }}
                  disabled={isRefreshing}
                >
                  {isRefreshing ? 'Refreshing…' : 'Refresh'}
                </button>
              )}
            </div>

            {recentShifts.length === 0 ? (
              <p className="muted">No shifts yet.</p>
            ) : (
              <div className="table">
                <div className="thead">
                  <div>Date</div>
                  <div>Spot</div>
                  <div>Bartender</div>
                  <div className="num">Score</div>
                </div>
                {recentShifts.map((s) => (
                  <div key={s.id} className="trow">
                    <div>{s.shift_date}</div>
                    <div>{spots.find((sp) => sp.id === s.spot_id)?.name ?? `#${s.spot_id}`}</div>
                    <div>{s.bartender_name}</div>
                    <div className="num">
                      <span className="score">{s.score_total?.toFixed(1) ?? '—'}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="panel">
            <div className="panel-header">
              <h2>Leaderboard (avg score)</h2>
              {barId && (
                <button className="btn" onClick={refreshLeaderboard} disabled={isLoadingLeaderboard}>
                  {isLoadingLeaderboard ? 'Loading…' : 'Refresh'}
                </button>
              )}
            </div>

            {!barId ? (
              <p className="muted">Seed demo data to view the leaderboard.</p>
            ) : leaderboard.length === 0 ? (
              <p className="muted">No leaderboard data yet.</p>
            ) : (
              <div className="table leaderboard">
                <div className="thead">
                  <div>Bartender</div>
                  <div className="num">Avg</div>
                  <div className="num">Shifts</div>
                  <div>Last</div>
                </div>
                {leaderboard.map((e) => (
                  <div key={e.bartender_name} className="trow">
                    <div>{e.bartender_name}</div>
                    <div className="num">
                      <span className="score">{e.avg_score.toFixed(1)}</span>
                    </div>
                    <div className="num">{e.shifts_count}</div>
                    <div>{e.last_shift_date ?? '—'}</div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </main>
        )}
      </div>
    </>
  )
}

export default App
