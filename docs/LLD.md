# SmartPantryAI — Low Level Design

## 1. Module Map

```
smartpantryai/
├── app.py                        # Router only — no business logic
├── auth/
│   ├── session.py                # st.session_state wrapper
│   ├── password.py               # bcrypt hash/verify
│   ├── otp.py                    # OTP generate, send, verify
│   └── email/
│       ├── sender.py             # Gmail SMTP transport
│       └── templates/            # HTML email templates
├── db/
│   ├── client.py                 # Supabase singleton (truststore injected for corporate proxy)
│   ├── schema.sql                # DDL for all tables
│   ├── users.py                  # User CRUD
│   ├── preferences.py            # Preferences upsert/read
│   ├── history.py                # Recipe history CRUD
│   ├── favourites.py             # Favourites CRUD
│   └── otp_tokens.py             # OTP token store/verify
├── detection/
│   ├── model.py                  # YOLODetector, InferenceResult, run_inference()
│   └── frame_processor.py        # OpenCV webcam capture + preprocessing
├── recipe_engine/
│   ├── groq_client.py            # Groq API wrapper (sync + async)
│   ├── prompt_builder.py         # Build structured LLM prompt
│   └── recipe_parser.py          # Parse JSON → Recipe dataclass
├── preference_engine/
│   └── schema.py                 # UserPreferences dataclass
├── pages/
│   ├── login.py
│   ├── register.py
│   ├── verify_otp.py
│   ├── forgot_password.py
│   ├── dashboard.py              # Main app: detect + recipes
│   ├── history.py
│   └── favourites.py
└── ui/
    ├── theme.py                  # Inject CSS design tokens
    ├── components.py             # Shared rendering helpers (badges, overlays, empty states)
    └── preference_widget.py      # Preference sidebar widget
```

---

## 2. Module Interfaces

### 2.1 auth/session.py

```python
def init_session() -> None
    # Initialise all session keys with defaults on first load

def is_authenticated() -> bool
    # True if session has a valid user_id

def login(user_id: str, email: str) -> None
    # Write user_id + email into session state

def logout() -> None
    # Clear all session state keys

def go(page: str) -> None
    # Set session_state.page and trigger st.rerun()

def current_user_id() -> str | None
def current_email() -> str | None
```

### 2.2 auth/password.py

```python
def hash_password(plain: str) -> str
    # bcrypt hash, returns string for DB storage

def verify_password(plain: str, hashed: str) -> bool
    # Constant-time compare
```

### 2.3 auth/otp.py

```python
def generate_otp() -> str
    # 6-digit zero-padded string

def send_otp(email: str, purpose: Literal["register", "reset_password"]) -> None
    # Generates OTP → stores in DB → sends email

def verify(email: str, otp: str) -> bool
    # Checks DB: valid, not used, not expired
```

### 2.4 detection/model.py

```python
@dataclass
class Detection:
    label: str
    confidence: float
    bbox: tuple[int, int, int, int]   # (x1, y1, x2, y2)

@dataclass
class InferenceResult:
    labels: list[str]            # Deduplicated ingredient names
    annotated_image: np.ndarray  # RGB frame with bounding boxes drawn
    raw_boxes: list[dict]        # [{label, confidence, bbox}]

class YOLODetector:
    def __init__(self, model_path: str, confidence: float = 0.5) -> None
    def detect(self, frame: np.ndarray) -> list[Detection]
    def draw_boxes(self, frame: np.ndarray, detections: list[Detection]) -> np.ndarray
    def unique_labels(self, detections: list[Detection]) -> list[str]

def run_inference(detector: YOLODetector, frame_bgr: np.ndarray) -> InferenceResult
    # Runs detect + draw_boxes + colour conversion in one call
    # Returns fully-typed InferenceResult — pages never touch raw Detection objects
```

### 2.5 preference_engine/schema.py

```python
class UserPreferences(BaseModel):   # Pydantic — validation + serialisation built-in
    diet:         Literal["veg", "non_veg", "eggetarian"]          = "veg"
    health:       Literal["normal", "diabetic", "low_bp", "high_bp"] = "normal"
    cuisine:      Literal["north_indian", "south_indian", "chinese",
                          "mediterranean", "japanese"]              = "north_indian"
    mood:         Literal["party", "tired", "romantic", "quick_bite"] = "tired"
    time_minutes: Literal[10, 20, 30, 40]                           = 30

    @classmethod
    def from_dict(cls, d: dict) -> "UserPreferences"
        # wraps model_validate(d)

    def to_dict(self) -> dict
        # wraps model_dump(include={...5 fields...})

    def summary(self) -> str
        # Human-readable label string for sidebar display
```

### 2.6 recipe_engine/prompt_builder.py

```python
def build_prompt(
    ingredients: list[str],
    preferences: UserPreferences,
    n_recipes: int = 3,
) -> str
    # Returns the full system+user prompt string
    # Output spec embedded in prompt: JSON array of Recipe objects
```

### 2.7 recipe_engine/recipe_parser.py

```python
@dataclass
class Recipe:
    name: str
    cuisine: str
    cook_time_minutes: int
    ingredients: list[str]      # With quantities: ["2 cups rice", ...]
    steps: list[str]            # Numbered, detailed
    health_notes: str

def parse_groq_response(raw: str) -> list[Recipe]
    # Extract JSON block from LLM response, validate, return typed list
```

### 2.8 recipe_engine/groq_client.py

```python
class GroqRecipeClient:
    def __init__(self, api_key: str | None = None, model: str = ..., ...) -> None

    async def get_recipes(
        self, ingredients: list[str], preferences: UserPreferences
    ) -> list[Recipe]

    def get_recipes_sync(
        self, ingredients: list[str], preferences: UserPreferences
    ) -> list[Recipe]
    # Wraps async in asyncio.run() for Streamlit compatibility
```

---

## 3. Database Schema

```sql
-- users: core identity
users (
  id            uuid PK default gen_random_uuid()
  email         text UNIQUE NOT NULL
  password_hash text NOT NULL
  is_verified   boolean default false
  created_at    timestamptz default now()
)

-- preferences: one row per user, upserted on save
preferences (
  user_id       uuid PK FK → users.id ON DELETE CASCADE
  diet          text default 'veg'
  health        text default 'normal'
  cuisine       text default 'north_indian'
  mood          text default 'tired'
  time_minutes  int  default 30
  updated_at    timestamptz default now()
)

-- recipe_history: full session log
recipe_history (
  id            uuid PK default gen_random_uuid()
  user_id       uuid FK → users.id ON DELETE CASCADE
  ingredients   text[]     -- detected labels
  recipes       jsonb      -- array of Recipe objects
  created_at    timestamptz default now()
)

-- favourites: individually saved recipes
favourites (
  id            uuid PK default gen_random_uuid()
  user_id       uuid FK → users.id ON DELETE CASCADE
  recipe_name   text NOT NULL
  recipe        jsonb      -- single Recipe object
  saved_at      timestamptz default now()
)

-- otp_tokens: short-lived verification codes
otp_tokens (
  id            uuid PK default gen_random_uuid()
  email         text NOT NULL
  otp           text NOT NULL
  expires_at    timestamptz NOT NULL
  used          boolean default false
  created_at    timestamptz default now()

  INDEX (email, expires_at)
)
```

**Entity Relationships:**
```
users ──< preferences    (1:1, cascade delete)
users ──< recipe_history (1:N, cascade delete)
users ──< favourites     (1:N, cascade delete)
email ──< otp_tokens     (not FK, email is the key)
```

---

## 4. Page Contracts

Each page module exports exactly one function:

```python
def render() -> None
```

Pages do **not**:
- Import from each other
- Access `st.session_state` directly for user_id (use `auth.session`)
- Call Supabase directly (use `db.*` modules)
- Build prompts or call Groq directly (use `recipe_engine`)

---

## 5. Config / Environment Variables

| Variable | Used by | Description |
|---|---|---|
| `SUPABASE_URL` | db/client.py | Project URL |
| `SUPABASE_SERVICE_KEY` | db/client.py | Service role key (bypasses RLS) |
| `GROQ_API_KEY` | recipe_engine/groq_client.py | Groq API key |
| `SMTP_EMAIL` | auth/email/sender.py | Gmail sender address |
| `SMTP_APP_PASSWORD` | auth/email/sender.py | Gmail App Password (no spaces) |
| `REQUESTS_CA_BUNDLE` | db/client.py | Set by Netskope on corporate machines; presence signals corporate proxy environment |

---

## 6. Error Handling Strategy

| Layer | Approach |
|---|---|
| DB layer | Return `None` / `[]` on not-found; let callers decide meaning |
| Auth layer | Raise `ValueError` with user-facing message |
| Detection | Return empty `InferenceResult` on model failure; surface in UI |
| Recipe engine | Return `[]` on parse failure; show error in UI with retry option |
| Pages | `st.error()` / `st.warning()` for user-facing errors; never crash |
