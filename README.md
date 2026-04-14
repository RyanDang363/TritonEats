# TritonEats - built for TransferHacks 2026

**TritonEats** is a UC San Diego campus dining companion: students set dietary preferences and fitness goals, see dining halls on a map, and get personalized food recommendations based on nutrition, allergies, walking distance, and optional cravings.

This repo contains the **TritonEats** mobile app and its **Python API**.

## Stack

| Layer | Technologies |
|--------|----------------|
| Mobile app | [Expo](https://expo.dev/) (SDK 54), [React Native](https://reactnative.dev/), [expo-router](https://docs.expo.dev/router/introduction/), TypeScript |
| Maps & location | `react-native-maps`, `expo-location` |
| Auth & data | [Supabase](https://supabase.com/) (Auth, Postgres, Row Level Security) |
| API | [FastAPI](https://fastapi.tiangolo.com/), [Uvicorn](https://www.uvicorn.org/), [Pydantic](https://docs.pydantic.dev/) v2 |
| Integrations | OpenAI (menu ranking / reasons), Google Routes API (walking times), Supabase Python client |

Environment variables are loaded from a root `.env` (API) and `triton-eats/.env` (Expo public keys). See `triton-eats/.env.example`.

## Prerequisites

- Node.js 18+ and npm  
- Python 3.11+ (3.12+ recommended)  
- Supabase project with `user_profiles`, `dining_halls`, `stations`, `menu_items`, `favorites` (see `misc/` for migration helpers)  
- API keys: OpenAI, Google Routes, Supabase URL + keys (service role on the server for profile reads if RLS blocks anon)

## How to run TritonEats

Run the **API** and **Expo app** in two terminals from the repo root.

### 1. API (FastAPI)

```bash
cd api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `../.env` at the **repo root** (next to `api/`) with at least:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` (and optionally `SUPABASE_SERVICE_ROLE_KEY` for server-side profile access)
- `OPENAI_API_KEY`
- `GOOGLE_ROUTES_API_KEY`

Start the server (use `0.0.0.0` so a **physical phone** on the same Wi‑Fi can reach your Mac):

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Health check: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### 2. TritonEats app (Expo)

```bash
cd triton-eats
cp .env.example .env
```

Edit `.env`: set `EXPO_PUBLIC_SUPABASE_URL`, `EXPO_PUBLIC_SUPABASE_ANON_KEY`, and `EXPO_PUBLIC_API_URL` (e.g. `http://localhost:8000` for iOS Simulator, or `http://<your-mac-LAN-ip>:8000` for a real device if needed).

```bash
npm install
npx expo start
```

Open in **Expo Go** (scan QR) or press `i` / `a` for simulator / emulator. After changing `.env`, restart Metro (`npx expo start --clear`).

---

**TritonEats** — find your next meal on campus.
