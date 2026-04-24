# SmartPantryAI — System Flows

## 1. Registration & Verification Flow

```
User                    Streamlit              Supabase           Gmail
 │                          │                     │                 │
 │  Fill register form       │                     │                 │
 │ ─────────────────────────►│                     │                 │
 │                          │ email_exists(email)  │                 │
 │                          │ ────────────────────►│                 │
 │                          │◄────────────────────│                 │
 │                          │                     │                 │
 │                          │ create_user(email,   │                 │
 │                          │   hash(password))    │                 │
 │                          │ ────────────────────►│                 │
 │                          │◄── user row created ─│                 │
 │                          │                     │                 │
 │                          │ store_otp(email, otp)│                 │
 │                          │ ────────────────────►│                 │
 │                          │                     │  send_email()   │
 │                          │ ───────────────────────────────────────►
 │                          │                     │                 │
 │  Redirect → verify_otp   │                     │                 │
 │◄─────────────────────────│                     │                 │
 │                          │                     │                 │
 │  Enter 6-digit OTP        │                     │                 │
 │ ─────────────────────────►│                     │                 │
 │                          │ verify_otp(email,otp)│                 │
 │                          │ ────────────────────►│                 │
 │                          │  check: exists,      │                 │
 │                          │  not used, not       │                 │
 │                          │  expired             │                 │
 │                          │◄── valid/invalid ────│                 │
 │                          │                     │                 │
 │                          │ mark_verified(email) │                 │
 │                          │ ────────────────────►│                 │
 │  login() → dashboard     │                     │                 │
 │◄─────────────────────────│                     │                 │
```

---

## 2. Login Flow

```
User                    Streamlit              Supabase
 │                          │                     │
 │  Email + Password         │                     │
 │ ─────────────────────────►│                     │
 │                          │ get_user_by_email()  │
 │                          │ ────────────────────►│
 │                          │◄── user row ─────────│
 │                          │                     │
 │                          │ verify_password()    │
 │                          │  (bcrypt compare)    │
 │                          │                     │
 │                          │ is_verified check    │
 │                          │  if False → go to    │
 │                          │  verify_otp page     │
 │                          │                     │
 │                          │ login(user_id, email)│
 │                          │  writes session state│
 │  Redirect → dashboard    │                     │
 │◄─────────────────────────│                     │
```

---

## 3. Ingredient Detection + Recipe Generation Flow

```
User                 Streamlit          YOLO Model         Groq API         Supabase
 │                       │                  │                  │                │
 │  Take photo /          │                  │                  │                │
 │  upload image          │                  │                  │                │
 │ ──────────────────────►│                  │                  │                │
 │                       │  run_inference()  │                  │                │
 │                       │ ─────────────────►│                  │                │
 │                       │  InferenceResult  │                  │                │
 │                       │◄─────────────────│                  │                │
 │                       │                  │                  │                │
 │  See annotated image  │                  │                  │                │
 │  + ingredient labels  │                  │                  │                │
 │◄──────────────────────│                  │                  │                │
 │                       │                  │                  │                │
 │  Click "Get Recipes"  │                  │                  │                │
 │ ──────────────────────►│                  │                  │                │
 │                       │ get_preferences() │                  │                │
 │                       │ ────────────────────────────────────────────────────►│
 │                       │◄────────────────────────────────────────────────────│
 │                       │                  │                  │                │
 │                       │ build_prompt(     │                  │                │
 │                       │  ingredients,     │                  │                │
 │                       │  preferences)     │                  │                │
 │                       │                  │                  │                │
 │                       │ groq_client.      │                  │                │
 │                       │ get_recipes_sync()│                  │                │
 │                       │ ─────────────────────────────────────►│               │
 │                       │                  │   LLM inference   │               │
 │                       │◄─────────────────────────────────────│               │
 │                       │ parse_groq_response()                │               │
 │                       │  → list[Recipe]                      │               │
 │                       │                  │                  │                │
 │  See recipe cards     │                  │                  │                │
 │◄──────────────────────│                  │                  │                │
 │                       │ save_history(     │                  │                │
 │                       │  user_id,         │                  │                │
 │                       │  ingredients,     │                  │                │
 │                       │  recipes)         │                  │                │
 │                       │ ────────────────────────────────────────────────────►│
```

---

## 4. Favourite / Unfavourite Flow

```
User                 Streamlit                          Supabase
 │                       │                                  │
 │  Click heart on recipe│                                  │
 │ ──────────────────────►│                                  │
 │                       │ is_favourite(user_id, name)       │
 │                       │ ─────────────────────────────────►│
 │                       │◄── bool ─────────────────────────│
 │                       │                                  │
 │                       │ if True:                          │
 │                       │   remove_favourite()              │
 │                       │ else:                             │
 │                       │   add_favourite()                 │
 │                       │ ─────────────────────────────────►│
 │  Button state updates │                                  │
 │◄──────────────────────│                                  │
```

---

## 5. Forgot Password Flow

```
User                 Streamlit              Supabase           Gmail
 │                       │                     │                 │
 │  Enter email           │                     │                 │
 │ ──────────────────────►│                     │                 │
 │                       │ (no email_exists     │                 │
 │                       │  check — security)   │                 │
 │                       │ send_otp(email,      │                 │
 │                       │   purpose="reset")   │                 │
 │                       │ ────────────────────►│  email sent     │
 │                       │                     │ ────────────────►
 │  "If your email exists,│                     │                 │
 │   check your inbox"   │                     │                 │
 │◄──────────────────────│                     │                 │
 │                       │                     │                 │
 │  Enter OTP + new pwd  │                     │                 │
 │ ──────────────────────►│                     │                 │
 │                       │ verify_otp()         │                 │
 │                       │ ────────────────────►│                 │
 │                       │◄── valid ────────────│                 │
 │                       │ update_password(     │                 │
 │                       │   email, hash(pwd))  │                 │
 │                       │ ────────────────────►│                 │
 │  Redirect → login     │                     │                 │
 │◄──────────────────────│                     │                 │
```

---

## 6. Session State Machine

```
          ┌──────────────┐
          │   not loaded  │
          └──────┬───────┘
                 │ app.py: init_session()
                 ▼
          ┌──────────────┐         register
          │    login     │◄────────────────────────────┐
          │   (default)  │                             │
          └──────┬───────┘                             │
                 │                            ┌────────┴───────┐
          login  │                            │    register    │
          success│                            └────────┬───────┘
                 │                                     │ submit form
                 │                            ┌────────▼───────┐
                 │                            │  verify_otp    │
                 │                            └────────┬───────┘
                 │                   OTP valid         │
                 │◄────────────────────────────────────┘
                 ▼
          ┌──────────────┐
          │  dashboard   │◄──────────────────────────────────────┐
          │ (authenticated│                                       │
          │    state)    │                                       │
          └──────┬───────┘                                       │
                 │                                               │
         ┌───────┼──────────────────────────────────────────┐   │
         │       ▼              ▼               ▼            │   │
         │  ┌─────────┐  ┌──────────┐  ┌────────────────┐  │   │
         │  │ history │  │favourites│  │ detect/recipes │  │   │
         │  └─────────┘  └──────────┘  └────────────────┘  │   │
         │       │              │               │            │   │
         └───────┴──────────────┴───────────────┴────────────┘   │
                                 sidebar nav                      │
                                    └────────────────────────────┘
                 │ sign out
                 ▼
          ┌──────────────┐
          │    login     │
          └──────────────┘
```

---

## 7. Data Flow: Image → Recipe (Condensed)

```
Camera / Upload
      │
      │ PIL.Image
      ▼
 YOLOv11n (local)
      │
      │ ["tomato", "onion", "garlic", ...]
      ▼
 UserPreferences (from Supabase)
  + Ingredient list
      │
      ▼
 Prompt Builder
  "Generate 3 recipes for a tired vegetarian
   with these ingredients in 30 minutes..."
      │
      │ structured prompt
      ▼
 Groq API (llama-3.3-70b-versatile)
      │
      │ JSON string
      ▼
 Recipe Parser
      │
      │ list[Recipe]
      ▼
 Streamlit UI (recipe cards)
      │
      ├──► Supabase (save to history)
      └──► Supabase (save to favourites, on click)
```
