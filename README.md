# TritonEats - built for TransferHacks 2026 (Honorable Mention)

**TritonEats** is a UC San Diego campus dining companion: students set dietary preferences and fitness goals, see dining halls on a map, and get personalized food recommendations based on nutrition, allergies, walking distance, and optional cravings.

This repo contains the **TritonEats** mobile app and its **Python API**.

## Stack

| Layer           | Technologies                                                                                                                                        |
| --------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| Mobile app      | [Expo](https://expo.dev/) (SDK 54), [React Native](https://reactnative.dev/), [expo-router](https://docs.expo.dev/router/introduction/), TypeScript |
| Maps & location | `react-native-maps`, `expo-location`                                                                                                                |
| Auth & data     | [Supabase](https://supabase.com/) (Auth, Postgres, Row Level Security)                                                                              |
| API             | [FastAPI](https://fastapi.tiangolo.com/), [Uvicorn](https://www.uvicorn.org/), [Pydantic](https://docs.pydantic.dev/) v2                            |
| Integrations    | OpenAI (menu ranking / reasons), Google Routes API (walking times), Supabase Python client                                                          |

Environment variables are loaded from a **repo root** `.env` (API, via `load_dotenv` in `api/main.py`) and `triton-eats/.env` (Expo). Use the same **`EXPO_PUBLIC_`** names in both. See **`triton-eats/.env.example`** for the Expo-side template; create the root `.env` with the same keys (plus `OPENAI_API_KEY`, `GOOGLE_ROUTES_API_KEY`, and optionally `SUPABASE_SERVICE_ROLE_KEY`).

## Prerequisites

- Node.js 18+ and npm
- Python 3.11+ (3.12+ recommended)
- Supabase project with `user_profiles`, `dining_halls`, `stations`, `menu_items`, `favorites` (see `misc/` for migration helpers)
- API keys: OpenAI, Google Routes, Supabase URL + keys (service role on the server for profile reads if RLS blocks anon)

## How to run TritonEats

### Step 1 — API (do this first)

From the **repo root**, create `.env` next to the `api/` folder (not inside `api/`) with at least:

- `EXPO_PUBLIC_SUPABASE_URL`
- `EXPO_PUBLIC_SUPABASE_ANON_KEY` (same value as in the Expo app; and optionally `SUPABASE_SERVICE_ROLE_KEY` for server-side profile access)
- `OPENAI_API_KEY`
- `GOOGLE_ROUTES_API_KEY`

Use the **same** `EXPO_PUBLIC_SUPABASE_*` values in `triton-eats/.env`, or from `triton-eats` run `ln -sf ../.env .env` so one file serves both. (The API still accepts legacy `NEXT_PUBLIC_SUPABASE_*` names if the new ones are unset.)

Then in a terminal:

```bash
cd api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Use `--host 0.0.0.0` so a **physical phone** on the same Wi‑Fi can reach your Mac. Leave this terminal running.

Confirm the API is up: open [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health) in a browser (should return `{"status":"ok"}`).

### Step 2 — TritonEats app (after the API is running)

In a **second** terminal:

```bash
cd triton-eats
cp .env.example .env
```

Edit `triton-eats/.env`:

- `EXPO_PUBLIC_SUPABASE_URL` and `EXPO_PUBLIC_SUPABASE_ANON_KEY` — from your Supabase project
- `EXPO_PUBLIC_API_URL` — where the app will reach the API: `http://localhost:8000` for **iOS Simulator** on the same Mac; `http://<your-mac-LAN-ip>:8000` for **Expo Go on a physical device** (same Wi‑Fi as your computer); **Android emulator** often needs `http://10.0.2.2:8000` instead of `localhost`

Then:

```bash
npm install
npx expo start
```

Open **Expo Go** and scan the QR code, or press **`i`** (iOS Simulator) / **`a`** (Android emulator) in the terminal.

---

**TritonEats** — find your next meal on campus.
