# Glow AU Demo

Glow AU is a Django prototype for an Australia-focused beauty community. It combines artist discovery, lightweight artist onboarding, community posting, booking flow, and in-app messaging in a single demo app.

## Stable Demo Scope

- Dual login entry: users can enter as `client` or `makeup artist`.
- Artist onboarding flow: city selection, price range, style tags, optional social link.
- Community feed with artist posts, request-style posts, and non-bookable content.
- Artist profile page with visible booking form for signed-in users.
- Booking lifecycle: request, accept, deposit, complete, final payment.
- Artist dashboard: appointments, portfolio items, payment toggle, schedule, work notes.
- Private and booking-related message threads.
- Local Google login demo route for presentations without real OAuth.

## Demo Walkthrough

Recommended order for a GitHub reviewer or live demo:

1. Open home page and community feed.
2. Log in as an artist from `/login/`.
3. Complete artist registration from `/dashboard/portfolio/new/`.
4. Create or edit portfolio content.
5. Open an artist profile and show the booking form.
6. Show dashboard status, messages, and artist schedule.

## Fast Local Start

Requirements:

- Python 3.12+
- `Django`
- `Pillow`

Run locally:

```bash
python -m pip install django pillow
python manage.py migrate
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

## Demo Login Shortcuts

For local demos, use the built-in prototype login route instead of real Google OAuth:

```text
/login/google-demo/?role=artist&email=artist@example.com
/login/google-demo/?role=client&email=client@example.com
```

Notes:

- `role=artist` shows the session as logged in as a makeup artist, even before registration is completed.
- Real Google OAuth can still be configured through `.env`, but it is not required for demo use.

## Seeded Demo Data

This project includes a repeatable seed command:

```bash
python manage.py seed_demo
```

It prepares sample users, artist portfolios, availability, a booking, and message items for faster walkthroughs.

Sample seeded identities:

- `ava_artist`
- `amanda_client`
- `mia_chen`
- `jisoo_park`

## Key Routes

- `/` home
- `/community/` community feed
- `/community/create/` create community post
- `/login/` login role chooser
- `/dashboard/` account dashboard
- `/dashboard/portfolio/new/` artist registration / portfolio entry
- `/dashboard/messages/` messages
- `/dashboard/schedule/` artist schedule

## Environment Variables

Optional `.env` values:

```env
GOOGLE_OAUTH_CLIENT_ID=
GOOGLE_OAUTH_CLIENT_SECRET=
GOOGLE_OAUTH_REDIRECT_URI=http://127.0.0.1:8000/login/google/callback/
GOOGLE_MAPS_API_KEY=
```

## Current Notes

- SQLite is used for local demo simplicity.
- The app is currently optimized for prototype/demo usage, not production deployment.
- Tests currently cover core post creation, artist registration, and artist-entry login labeling.

Run tests:

```bash
python manage.py test core
```
