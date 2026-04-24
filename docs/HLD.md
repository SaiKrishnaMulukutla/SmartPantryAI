# SmartPantryAI — High Level Design

## 1. Problem Statement

Users don't know what to cook with what they have. SmartPantryAI lets users point their camera at their fridge or pantry, detects the ingredients automatically, and generates personalised recipe recommendations based on their dietary preferences, health goals, mood, and available time.

---

## 2. System Overview

```
                          ┌─────────────────────────────────────────┐
                          │              Browser (User)              │
                          │         Streamlit Web Interface          │
                          └────────────────┬────────────────────────┘
                                           │ HTTPS
                          ┌────────────────▼────────────────────────┐
                          │           Application Server            │
                          │              (Streamlit)                │
                          │                                          │
                          │  ┌──────────┐  ┌──────────────────────┐ │
                          │  │   Auth   │  │   Detection Engine   │ │
                          │  │  Module  │  │   (YOLOv11n local)   │ │
                          │  └────┬─────┘  └──────────┬───────────┘ │
                          │       │                    │             │
                          │  ┌────▼────────────────────▼──────────┐ │
                          │  │         Recipe Engine              │ │
                          │  │    (Prompt Builder + Parser)       │ │
                          │  └────────────────┬───────────────────┘ │
                          └───────────────────┼─────────────────────┘
                                              │
              ┌───────────────────────────────┼───────────────────────┐
              │                               │                       │
  ┌───────────▼──────────┐      ┌─────────────▼──────────┐  ┌────────▼───────┐
  │      Supabase        │      │       Groq API          │  │  Gmail SMTP   │
  │   (PostgreSQL DB)    │      │  llama-3.3-70b-versatile│  │  (OTP email)  │
  └──────────────────────┘      └─────────────────────────┘  └────────────────┘
```

---

## 3. Core Components

### 3.1 Auth Module
Handles the full identity lifecycle:
- **Registration**: email + password → bcrypt hash → OTP email → verified account
- **Login**: email + password verify → session token in Streamlit state
- **OTP Flow**: 6-digit code, 10-min TTL, stored in Supabase, invalidated on use
- **Forgot Password**: OTP-based reset, no security exposure (doesn't reveal if email exists)

### 3.2 Detection Engine
Runs entirely locally — no network call for inference:
- Loads `best.pt` (YOLOv11n trained on food ingredient dataset, 4.8MB)
- Accepts image from `st.camera_input()` or `st.file_uploader()`
- Returns a deduplicated list of detected ingredient labels with confidence scores
- No GPU required in production — nano model runs on CPU in ~100ms

### 3.3 Recipe Engine
Two sub-components:
- **Prompt Builder**: takes `(ingredients[], UserPreferences)` → crafts a structured LLM prompt requesting JSON output with name, ingredients+quantities, steps, cook time, health notes
- **Groq Client**: sends prompt to `llama-3.3-70b-versatile` (async), parses the JSON response into typed `Recipe` objects

### 3.4 Preference Engine
- Lightweight dataclass `UserPreferences` carrying: diet, health goal, cuisine, mood, time budget
- Loaded from Supabase on login, used to personalise every recipe prompt
- Editable from the dashboard; changes persist immediately

### 3.5 Data Layer (Supabase)
PostgreSQL hosted on Supabase. Five tables:

| Table | Purpose |
|---|---|
| `users` | Account credentials and verification status |
| `preferences` | One row per user, dietary and mood settings |
| `recipe_history` | Timestamped log of ingredient detections + generated recipes |
| `favourites` | User-saved individual recipes with full JSON |
| `otp_tokens` | Short-lived OTP codes for email flows |

---

## 4. Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| UI | Streamlit | Rapid ML app development, camera API, no frontend build step |
| Detection | YOLOv11n (Ultralytics) | Best-in-class food detection, runs on CPU, 4.8MB |
| LLM | Groq / llama-3.3-70b | Fast inference, free tier, structured JSON output |
| Database | Supabase (PostgreSQL) | Managed Postgres + REST API + auth-ready |
| Auth | Custom (bcrypt + OTP) | Full control, no vendor lock-in on auth |
| Email | Gmail SMTP (App Password) | Simple, reliable for transactional OTP emails |
| Hosting | Streamlit Cloud | One-click deploy, secrets management, free tier |

---

## 5. Key Design Decisions

### Local inference over API
YOLOv11n runs locally. No per-image API cost, no latency from network, no data privacy concerns (user's fridge images never leave the browser → server).

### Custom auth over Supabase Auth
Supabase Auth is JWTs. Streamlit doesn't natively understand JWT sessions. Building custom session state in `st.session_state` gives full control without fighting the framework.

### Supabase over raw Postgres
The PostgREST API layer means no ORM dependency. Simple `.table().select().execute()` calls are clear and testable.

### Single-process Streamlit architecture
For the current scale (demo / personal use), a single Streamlit process handles everything. If scale requires it, the Detection Engine and Recipe Engine can be extracted to separate FastAPI services.

---

## 6. Scalability Path

```
Current (MVP)                     Future (Product)
─────────────────────             ─────────────────────────────────────
Streamlit monolith          →     FastAPI backend + React/Next frontend
Local YOLO inference        →     Dedicated detection microservice
Groq direct call            →     Queue-based async with Redis
Supabase service key        →     Row Level Security (RLS) per user
bcrypt session state        →     Supabase Auth / JWT tokens
Gmail SMTP                  →     Resend / SendGrid transactional email
```
