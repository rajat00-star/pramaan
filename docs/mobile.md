# PraMaan Mobile App

One React Native + Expo + TypeScript application (`frontend/mobile/`) serving
**both** the Citizen and Inspector roles. There is no separate app per role —
after login, the backend-issued role (`citizen` / `inspector` /
`department_admin`) determines which navigator loads. Server-side RBAC
(`app/auth.require_roles`) remains authoritative everywhere; the app never
decides authorization on its own.

```
Mobile App (Expo)
  └─ Login (POST /api/auth/login, JWT)
       └─ role === 'citizen'      → Citizen navigator (Home / Scan / History / Profile)
       └─ role === 'inspector'    → Inspector navigator (Home / Review Queue / Case Detail / Profile)
       └─ role === 'department_admin' → same Inspector navigator (has the same
            review/dashboard permissions server-side; its primary surface is
            still the web Department Dashboard, not a third mobile UI)
```

No legal rule, OCR, or extraction logic exists in the mobile app — every
verdict comes from `POST /api/scans` on the same backend the website uses.
The app is a presentation layer over `src/api/*.ts`, which are thin, typed
wrappers around the real HTTP API (see `src/types/api.ts`, which mirrors
`backend/app/schemas.py` field-for-field).

## Project layout

```
frontend/mobile/
├── App.tsx                    # AuthProvider + RootNavigator
├── src/
│   ├── api/                   # client.ts, auth.ts, scans.ts, dashboard.ts, tokenStorage.ts
│   ├── components/            # Button, Card, VerdictBanner, StatusBadge, ScanDetailView, AuthenticatedImage, States
│   ├── contexts/AuthContext.tsx
│   ├── hooks/useScan.ts
│   ├── navigation/             # RootNavigator, CitizenNavigator, InspectorNavigator, types.ts
│   ├── screens/
│   │   ├── shared/             # LoginScreen, ProfileScreen
│   │   ├── citizen/            # CitizenHome, ScanCapture, ScanPreview, ScanProcessing, ScanResult, History, ScanDetail
│   │   └── inspector/          # InspectorHome, ReviewQueue, CaseDetail
│   ├── theme/colors.ts         # matches frontend/index.html's palette
│   └── types/api.ts
```

## Setup

```bash
cd frontend/mobile
npm install
cp .env.example .env
```

Edit `.env` to point at your backend — **never hardcode `localhost`** in
source; on a physical device "localhost" means the phone itself.

| Target | `EXPO_PUBLIC_API_URL` |
|---|---|
| iOS Simulator | `http://localhost:8000` (simulator shares the Mac's network stack) |
| Android Emulator | `http://10.0.2.2:8000` (emulator's alias for the host machine) |
| Physical iPhone/Android (same Wi-Fi as your Mac) | `http://<your-Mac-LAN-IP>:8000` — find it with `ipconfig getifaddr en0` |

Start the backend first (either works):

```bash
cd ../../backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000
# or, for the full Docker/PostgreSQL stack:
cd ../.. && docker compose up -d --build
```

Then start Expo:

```bash
cd frontend/mobile
npx expo start
```

Press `i` for iOS Simulator, `a` for Android Emulator, `w` for a web preview,
or scan the QR code with Expo Go on a physical device (make sure the phone
and your Mac are on the same Wi-Fi network, and that `EXPO_PUBLIC_API_URL`
is set to your Mac's LAN IP, not `localhost`).

## Demo accounts

Same accounts as the website (development/demo only — see the backend's
`.env.example`):

| Username | Password | Role |
|---|---|---|
| `citizen_demo` | `citizen123` | citizen |
| `inspector_demo` | `inspector123` | inspector |

(`admin_demo` / `admin123` is a `department_admin` account — it works on
mobile via the Inspector navigator, but its primary surface is the web
Department Dashboard.)

## Citizen walkthrough

1. Sign in as `citizen_demo`.
2. **Home** shows a greeting, a "Scan Product" button, and up to 3 recent scans (real data from `GET /api/scans`).
3. Tap **Scan Product** → **Take Photo** or **Choose From Gallery** (`expo-image-picker`, with real permission prompts).
4. **Review your photo** → **Analyze Product** uploads the real image to `POST /api/scans` and waits for the real pipeline result (no fabricated intermediate results — the "Analyzing…" stage labels are cosmetic UI only; the verdict shown is always the actual API response).
5. **Result** shows the actual uploaded image (fetched via the authenticated `GET /api/scans/{id}/image` endpoint), the real verdict banner, every field the backend actually extracted (never an invented value for a field that wasn't found), the legal evaluation per field with its clause citation, and the raw OCR text.
6. If the verdict is REVIEW, an explicit notice explains that human review is required — the app never silently upgrades REVIEW to COMPLIANT.
7. **History** tab lists every past scan for this citizen; tapping one reopens the same detail view.

## Inspector walkthrough

1. Sign in as `inspector_demo`.
2. **Home** shows real dashboard stats (Pending Reviews, Reviewed Today, Total Scans — from `GET /api/dashboard/summary`, which requires inspector/admin role server-side) and recent cases across **all** citizens (inspectors have cross-user visibility by design — see `routes/scan.py`'s IDOR comment).
3. **Review** tab lists every scan with `overall_verdict == REVIEW` (`GET /api/scans?verdict_filter=REVIEW`).
4. Opening a case shows the real image, every field/evaluation, and OCR text. Tapping **Correct this field** on any REVIEW-status field reveals an inline text input; **Save Correction** calls the real `POST /api/scans/{id}/review` endpoint — never a local-only state change.
5. On success, a "Correction saved · audit recorded" banner appears, the evaluation list re-renders from the fresh server response (field may now show PASS/FAIL), and **Correction History** shows the before/after/reviewer. **Load Audit Trail** fetches and displays the real `GET /api/scans/{id}/audit` event log.

## What was verified, and how (read this before claiming this app "works")

**No iOS Simulator or Android emulator was available in the environment this
was built in** — `xcode-select -p` resolves to Command Line Tools only (no
full Xcode.app), and there is no Android SDK/`adb`/`emulator` installed. This
is disclosed, not hidden. Verification instead used:

1. **TypeScript, strict mode**: `npx tsc --noEmit` — zero errors across the entire `src/` tree.
2. **Expo Metro bundling**: `npx expo start --web` bundled all ~600 modules with no errors.
3. **Live browser testing** (`expo start --web`, driven end-to-end against the real Dockerized backend at `http://127.0.0.1:8000`):
   - Citizen login → Home (real recent scans) → History → tapped into a real scan → full evidence rendered (real image, real fields, real evaluations, real OCR text, real scan metadata) → Profile → Sign out.
   - Inspector login → Home (real stats: pending reviews, reviewed today, total scans) → Review Queue (real REVIEW-verdict cases) → Case Detail (real image + evidence) → submitted a **real** field correction → confirmed the field flipped from REVIEW to PASS, the correction appeared in Correction History, and the exact `FIELD_CORRECTED` event appeared in a freshly-loaded Audit Trail.
4. Two real bugs were found and fixed **during this verification**, both disclosed here rather than silently patched:
   - `expo-secure-store` has no web implementation (`deleteValueWithKeyAsync is not a function`) — `src/api/tokenStorage.ts` now falls back to `localStorage` on `Platform.OS === 'web'` only; iOS/Android still use the real Keychain/Keystore via SecureStore.
   - React Native's `<Image source={{uri, headers}}>` header support is native-only — `react-native-web` maps `<Image>` to a plain `<img>` tag, which cannot carry a custom `Authorization` header at all, so the real product image never loaded on web. `src/components/AuthenticatedImage.tsx` now fetches the image via `fetch()` with the header and converts it to a data URI, which works identically on every platform (this is also what `frontend/index.html`'s new case-detail modal does, for the same reason).

**What was NOT verified because no device/simulator was available:**
- Real camera capture (`expo-image-picker`'s `launchCameraAsync`) on an actual camera.
- The native OS gallery/file picker (a native picker dialog is outside the DOM — driving it via browser automation risks hanging on an unclosable OS-level dialog, so it was deliberately not attempted).
- Any native iOS or Android build (`expo run:ios` / `expo run:android`), push notifications, or platform-specific permission-prompt UI.
- Physical-device networking end-to-end (the `.env` LAN-IP instructions above are correct in principle — Expo's documented behavior — but were not exercised against a real phone in this environment).

If you have a Mac with full Xcode installed, `npx expo run:ios` from
`frontend/mobile` should build and launch in the Simulator; the app code
itself does not assume any environment-specific behavior beyond what's
listed above.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| "Could not sign in. Check your connection…" on web preview | CORS: the backend's default `cors_allow_origins` doesn't include your Expo web dev port | Already includes `:8090` (the port these docs assume); if you use a different port, add it to `cors_allow_origins` in `backend/.env` or `app/config.py` |
| Login works but every screen shows a network error | `EXPO_PUBLIC_API_URL` doesn't match your target (see table above) | Fix `.env`, then fully restart `expo start` — Expo only reads `EXPO_PUBLIC_*` vars at startup |
| Product image never loads | You reverted `AuthenticatedImage.tsx` to a plain `<Image source={{uri}}>` | Authenticated images must be fetched manually (see above) — a plain `uri` has no way to attach the JWT |
| "Session expired" immediately after login | Backend `SECRET_KEY` changed (e.g. container restarted without an explicit `SECRET_KEY` env var) — see `backend/app/config.py`'s warning about the auto-generated dev key invalidating all prior tokens on restart | Set `SECRET_KEY` explicitly in `backend/.env` for a stable dev session |

## Known limitations

- Camera/gallery capture is unverified on real hardware in this environment (see above) — the code follows the standard, documented `expo-image-picker` API and permission flow, but "the button exists and calls the right function" is not the same claim as "verified working on a real camera."
- No offline support — every screen requires a live connection to the backend.
- No push notifications.
- The mobile app does not implement font-size-in-mm measurement, physical net-quantity verification, or any capability the backend itself doesn't already have — it is a client, not an independent compliance engine.
