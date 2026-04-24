# SmartPantryAI — Project Structure

```
smartpantryai/
│
├── app.py                        # Entry point. Router ONLY.
│                                 # No business logic here.
│                                 # Reads session_state.page → imports + calls render()
│
├── .env                          # Local secrets (never committed)
├── .env.example                  # Template for onboarding
├── requirements.txt              # All Python dependencies
│
├── models/
│   └── food_yolo11/
│       └── best.pt               # Trained YOLOv11n weights (4.8MB)
│                                 # Trained on food ingredient dataset, 10 epochs
│
├── docs/                         # Architecture documentation
│   ├── HLD.md                    # High Level Design — system overview, tech choices
│   ├── LLD.md                    # Low Level Design — module interfaces, DB schema
│   ├── SYSTEM_FLOW.md            # Sequence diagrams for every user journey
│   └── PROJECT_STRUCTURE.md      # This file
│
├── auth/                         # Identity and session management
│   ├── __init__.py
│   ├── session.py                # st.session_state wrapper
│   │                             # init_session, login, logout, go(), is_authenticated
│   ├── password.py               # bcrypt hash_password / verify_password
│   ├── otp.py                    # generate_otp, send_otp, verify
│   └── email/
│       ├── __init__.py
│       ├── sender.py             # Gmail SMTP via SSL port 465
│       └── templates/
│           ├── base.html         # Shared layout (green header, footer)
│           ├── otp_verify.html   # Email verification OTP
│           ├── welcome.html      # Post-verification welcome
│           └── password_reset.html # Password reset OTP
│
├── db/                           # Data access layer — Supabase only
│   ├── __init__.py
│   ├── client.py                 # Supabase singleton + corporate SSL fix
│   ├── schema.sql                # DDL — run once in Supabase SQL Editor
│   ├── users.py                  # create_user, get_user_by_email, mark_verified, etc.
│   ├── preferences.py            # get_preferences, save_preferences
│   ├── history.py                # save_history, get_history, delete_history_entry
│   ├── favourites.py             # add_favourite, remove_favourite, get_favourites
│   └── otp_tokens.py             # store_otp, verify_otp
│
├── detection/                    # Computer vision — local inference
│   ├── __init__.py
│   ├── model.py                  # YOLODetector class — detect(), draw_boxes()
│   └── frame_processor.py        # OpenCV webcam capture + preprocessing
│
├── recipe_engine/                # LLM recipe generation
│   ├── __init__.py
│   ├── groq_client.py            # GroqRecipeClient (sync + async)
│   ├── prompt_builder.py         # build_prompt(ingredients, preferences)
│   └── recipe_parser.py          # parse_groq_response() → list[Recipe]
│
├── preference_engine/            # User preference schema (data only — no UI)
│   ├── __init__.py
│   └── schema.py                 # UserPreferences dataclass
│
├── pages/                        # UI pages — each exports render() only
│   ├── login.py                  # Email + password form
│   ├── register.py               # New account creation + OTP trigger
│   ├── verify_otp.py             # OTP entry (register + password reset)
│   ├── forgot_password.py        # Email input → OTP → new password
│   ├── dashboard.py              # Core: camera/upload → detect → recipes
│   ├── history.py                # Past detection sessions
│   └── favourites.py             # Saved recipes
│
├── ui/                           # Visual design system
│   ├── theme.py                  # inject() — CSS design tokens via st.markdown
│   ├── components.py             # Shared rendering helpers (badges, overlays, empty states)
│   └── preference_widget.py      # Preference sidebar widget (diet, health, cuisine, mood, time)
│
└── training/                     # Model training (separate concern, not in app path)
    ├── kaggle_train.py
    ├── kaggle_notebook.ipynb     # Kaggle kernel: YOLOv11n, 10 epochs, 480px
    └── colab_train.ipynb         # Google Colab alternative
```

---

## Layer Rules (enforced by convention)

```
pages/          ─── may import from ───►  auth/, db/, detection/,
                                          recipe_engine/, preference_engine/, ui/

auth/           ─── may import from ───►  db/

recipe_engine/  ─── may import from ───►  preference_engine/

db/             ─── may import from ───►  (nothing internal)

detection/      ─── may import from ───►  (nothing internal)

ui/             ─── may import from ───►  (nothing internal)

app.py          ─── may import from ───►  auth/session, ui/theme, pages/*
```

No cross-page imports. No page imports from other pages.
No db/ imports from recipe_engine/ or detection/.

---

## Dependency Graph

```
app.py
 ├── auth.session
 │    └── db.users
 │         └── db.client  ──► Supabase
 ├── ui.theme
 └── pages.*
      ├── auth.session
      ├── auth.otp
      │    ├── db.otp_tokens
      │    └── auth.email.sender
      ├── auth.password
      ├── db.users
      ├── db.preferences
      ├── db.history
      ├── db.favourites
      ├── detection.model  ──► YOLOv11n (local)
      └── recipe_engine.groq_client
           ├── recipe_engine.prompt_builder
           │    └── preference_engine.schema
           └── recipe_engine.recipe_parser  ──► Groq API
```

---

## Environment Setup

```bash
# 1. Clone and install
git clone https://github.com/SaiKrishnaMulukutla/SmartPantryAI.git
cd SmartPantryAI
pip install -r requirements.txt

# 2. Copy and fill env
cp .env.example .env

# 3. Corporate proxy only (CoinSwitch / Netskope)
cat ~/certs.pem >> $(python3.13 -c "import certifi; print(certifi.where())")

# 4. Create Supabase tables
# → Go to Supabase project → SQL Editor → paste db/schema.sql → Run

# 5. Run
streamlit run app.py
```

---

## Key Files Quick Reference

| What you want to change | File to edit |
|---|---|
| Add a new page | `pages/newpage.py` + add route in `app.py` |
| Change recipe prompt style | `recipe_engine/prompt_builder.py` |
| Add a new preference field | `preference_engine/schema.py` + `db/preferences.py` + `db/schema.sql` |
| Change YOLO confidence threshold | `detection/model.py` |
| Change email look | `auth/email/templates/` |
| Change colour scheme | `ui/theme.py` |
| Add a new DB table | `db/schema.sql` + new `db/tablename.py` module |
