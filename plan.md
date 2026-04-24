# SmartPantryAI — Product Improvement Plan

## Vision
A professional, consumer-grade AI recipe app — clean UI, personalized per user,
works from camera or photo upload, remembers your history and favourites.

---

## Tech Stack Additions

| Layer | Tool | Why |
|---|---|---|
| Database | Supabase (Postgres) | Free tier, REST API, built-in row-level security |
| Auth sessions | `streamlit-authenticator` | Handles login state across reruns |
| Email / OTP | Gmail SMTP (`smtplib`) | Free, works on Streamlit Cloud with App Password |
| Password hashing | `bcrypt` | Industry standard, never store plain text |
| PDF export | `reportlab` | Generate shareable recipe PDFs |

---

## Phase 1 — Image Upload (Quick Win)

**Goal:** Let users upload a photo in addition to using the camera.

### Changes
- Add `st.file_uploader()` tab alongside `st.camera_input()`
- Use `st.tabs(["📷 Camera", "🖼️ Upload"])` for clean switching
- Same YOLO detection pipeline for both inputs
- Show a preview of the uploaded image before detection

### UI
- Tabs sit at the top of the left column
- Drag-and-drop zone styled with a dashed border
- Supported formats: JPG, PNG, WEBP

---

## Phase 2 — Database (Supabase)

**Goal:** Persist user accounts, preferences, recipe history, favourites.

### Schema

```sql
-- Users
create table users (
  id uuid primary key default gen_random_uuid(),
  email text unique not null,
  password_hash text not null,
  is_verified boolean default false,
  created_at timestamptz default now()
);

-- Preferences (one row per user, upserted on change)
create table preferences (
  user_id uuid primary key references users(id) on delete cascade,
  diet text default 'veg',
  health text default 'normal',
  cuisine text default 'north_indian',
  mood text default 'tired',
  time_minutes int default 30,
  updated_at timestamptz default now()
);

-- Recipe history
create table recipe_history (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  ingredients text[],
  recipes jsonb,
  created_at timestamptz default now()
);

-- Favourites
create table favourites (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  recipe_name text,
  recipe jsonb,
  saved_at timestamptz default now()
);
```

### New Env Vars
```
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
```

---

## Phase 3 — Auth (Login / Register / OTP)

**Goal:** Secure email + password auth with email OTP verification.

### Flow

```
Register → enter email + password
  → send 6-digit OTP via Gmail SMTP
  → verify OTP (expires in 10 min)
  → account activated → auto login

Login → email + password
  → bcrypt verify → session created
  → load preferences from Supabase

Forgot Password → email OTP → reset password
```

### Pages / Routes
```
/          → redirect to /login if not authenticated
/login     → email + password form + "Register" link
/register  → email + password + confirm password
/verify    → OTP input (6 boxes, auto-advance)
/app       → main app (protected)
```

### Session Management
- Store `user_id`, `email`, `is_authenticated` in `st.session_state`
- Add logout button in sidebar footer
- Session expires on browser close (no persistent cookies)

### Gmail SMTP Setup
```python
# .env
SMTP_EMAIL=yourapp@gmail.com
SMTP_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx  # Google App Password
```

### OTP UX
- 6 individual digit input boxes side by side
- Auto-focus next box on input
- Countdown timer shown (10:00 → 0:00)
- "Resend OTP" button appears after 60 seconds

---

## Phase 4 — Recipe History & Favourites

**Goal:** Every recipe generation is saved; users can favourite and revisit.

### History Page
- List of past sessions grouped by date
- Each entry shows: detected ingredients, timestamp, recipes generated
- Click to expand and view full recipe
- "Re-detect" button to rerun with same ingredients

### Favourites
- Heart icon on each recipe card (filled = saved)
- Dedicated "My Favourites" tab in sidebar
- Filter favourites by cuisine, cook time

---

## Phase 5 — Nutrition Info

**Goal:** Add macros to every recipe via Groq.

### Schema Addition to Recipe JSON
```json
{
  "name": "...",
  "nutrition_per_serving": {
    "calories": 320,
    "protein_g": 12,
    "carbs_g": 45,
    "fat_g": 8,
    "fibre_g": 6
  }
}
```

### UI
- Nutrition badge row below each recipe card
- Colour coded: green (protein), yellow (carbs), red (fat)
- "Per serving" disclaimer

---

## Phase 6 — Polish & Extra Features

| Feature | Detail |
|---|---|
| **Manual ingredient add** | Tag-style input — type an ingredient and press Enter |
| **Ingredient confidence** | Show YOLO confidence % next to each detected ingredient |
| **Share / Export PDF** | "Download Recipe" button → PDF with ingredients + steps |
| **Multi-language** | Dropdown: English / Hindi / Telugu — Groq translates steps |
| **Dark mode** | Streamlit theme toggle, CSS vars for all components |
| **Onboarding** | First-login walkthrough: 3-step tooltip tour |

---

## UI Design Principles

- **Colour palette:** Off-white background (`#FAFAF8`), deep green primary (`#2D6A4F`), warm amber accent (`#F4A261`)
- **Typography:** Inter (system font stack), 16px base, generous line height
- **Cards:** Subtle shadow (`box-shadow: 0 2px 12px rgba(0,0,0,0.06)`), 16px border radius, 24px padding
- **Spacing:** Consistent 8px grid — all margins/padding multiples of 8
- **Loading states:** Skeleton loaders (not spinners) for recipe cards
- **Empty states:** Illustrated placeholder with helpful CTA text
- **Responsive:** Single column on mobile, two columns on desktop
- **Sidebar:** Collapsible on mobile, always visible on desktop
- **Buttons:** Rounded pill style for primary CTAs, ghost style for secondary

---

## Implementation Order

```
Phase 1 — Image upload          (1 day)
Phase 2 — Supabase schema       (1 day)
Phase 3 — Auth + OTP            (2–3 days)
Phase 4 — History + Favourites  (1–2 days)
Phase 5 — Nutrition info        (half day)
Phase 6 — Polish                (ongoing)
```

---

## File Structure After All Phases

```
SmartPantryAI/
├── app.py                          # entry point + routing
├── pages/
│   ├── login.py
│   ├── register.py
│   ├── verify_otp.py
│   ├── history.py
│   └── favourites.py
├── auth/
│   ├── otp.py                      # generate, send, verify OTP
│   ├── password.py                 # bcrypt hash/verify
│   └── session.py                  # session state helpers
├── db/
│   ├── client.py                   # Supabase client singleton
│   ├── users.py                    # user CRUD
│   ├── preferences.py              # preferences CRUD
│   ├── history.py                  # recipe history CRUD
│   └── favourites.py               # favourites CRUD
├── detector/
├── recipe_engine/
├── preference_engine/
├── ui/
│   ├── components.py
│   ├── styles.css
│   └── theme.py                    # colour tokens, CSS injector
├── models/
├── training/
└── .env
```
