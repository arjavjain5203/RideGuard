# Frontend

The frontend is a Next.js 16 App Router application under `frontend/`. It is a thin client over the backend API and keeps almost all business state on the server.

## Frontend Structure

| Path | Responsibility |
| --- | --- |
| `frontend/src/app/` | route-level pages |
| `frontend/src/components/` | shared layout and UI primitives |
| `frontend/src/context/` | auth state and toast state |
| `frontend/src/services/api.js` | Axios client, token storage, and API calls |
| `frontend/src/app/globals.css` | global Tailwind styles |

## Shared Runtime Pieces

### App shell

- `RootLayout` renders `AppShell` for every page.
- `AppShell` provides `AuthProvider`, `ToastProvider`, the navbar, and the page container.

### Auth state

- `AuthContext` reads the access token from `localStorage` under `rideguard_access_token`.
- On load, it calls `fetchCurrentUser()` if a token exists.
- The Axios response interceptor clears the token on `401` and dispatches a `rideguard:unauthorized` browser event.
- Logout clears local storage and redirects based on the current role.

### Common UI components

- `Navbar` switches between public links, rider dashboard links, and admin entry points based on auth state.
- `Sidebar` is used only on rider pages.
- `Card` and `Loader` are reusable display primitives.
- `ToastContext` provides success, error, and custom notifications.

## Route Inventory

| Route | Audience | Main responsibility | Main API usage |
| --- | --- | --- | --- |
| `/` | public | landing page and entry points to login/register | none |
| `/register` | public rider signup | create rider and auto-login | `registerUser`, `loginUser` |
| `/login` | rider | rider login | `loginUser` |
| `/admin/login` | admin | admin login using the same backend login endpoint | `loginUser` |
| `/onboarding` | rider | show seeded earnings summary after signup | `fetchEarnings` |
| `/policy` | rider | choose coverage modules, quote premium, create policy | `listCoverageModules`, `calculatePremium`, `createPolicy`, `fetchPolicies` |
| `/dashboard` | rider | show policy, URTS, earnings, and simulate a rain trigger | `fetchPolicies`, `fetchScore`, `fetchEarnings`, `triggerEvent` |
| `/claims` | rider | show claim history | `fetchClaims` |
| `/payout` | rider | show payout history and latest AI explanation | `fetchPayouts`, `getClaimDetails`, `explainClaim` |
| `/admin` | admin | show metrics, recent claims, and fraud alerts | `fetchAdminMetrics`, `fetchAdminClaims`, `fetchAdminFraudAlerts` |

## Route Guard Behavior

- Rider pages redirect unauthenticated users to `/login`.
- Rider pages redirect authenticated admins or missing rider profiles to `/admin`.
- The admin login page rejects non-admin users after a successful shared login response.
- The admin dashboard redirects unauthenticated users to `/admin/login` and non-admin users to `/dashboard`.

These are browser-side guards. The backend still enforces authorization independently.

## Rider Flow In The UI

### Registration and onboarding

1. The rider submits the registration form.
2. The frontend calls `POST /api/riders/`.
3. On success, it immediately logs the rider in through `POST /api/auth/login`.
4. The rider is redirected to `/onboarding` to review generated earnings data.

### Policy selection

1. The page checks for an existing active policy first.
2. If none exists, it loads coverage modules.
3. Module selection changes trigger premium recomputation.
4. Policy creation redirects back to the dashboard.

### Dashboard, claims, and payouts

- The dashboard loads the current policy, URTS, and earnings summary in parallel.
- If an active policy exists, the dashboard exposes a single-click rain-trigger simulation.
- Claims and payouts pages are read-only history views.
- The payout page requests an LLM explanation for the latest payout only.

## Admin Flow In The UI

- Admin users authenticate through the same `/api/auth/login` backend endpoint as riders.
- The admin dashboard is currently observational only.
- Fraud alerts are derived from low effective-URTS claims rather than a separate alert system.

## Current Frontend Limitations

- Access tokens are stored in `localStorage`, not secure cookies.
- There is no refresh-token flow.
- Route guards are client-side only and rely on redirect effects after page load.
- The registration form exposes only a subset of the zones configured in the backend.
- The dashboard's built-in simulation button only simulates rain, even though the backend supports other trigger types.
- There are no frontend unit, integration, or end-to-end tests in the repo today.
