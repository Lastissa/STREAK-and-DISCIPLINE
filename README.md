# Discipline & Streak

A Django-based habit and commitment tracker. Users create "commitments" (habits/goals), log daily entries, build streaks, track progress on a heat map, compete on a leaderboard, and can pair up with a partner or friends for accountability.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Site Map](#site-map)
  - [Public Pages](#public-pages)
  - [Authentication](#authentication)
  - [Dashboard (Authenticated)](#dashboard-authenticated)
  - [Community & Partnering](#community--partnering)
  - [Staff Panel](#staff-panel)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Environment Variables](#environment-variables)
  - [Database & Static Files](#database--static-files)
  - [Running the App](#running-the-app)
- [Project Structure](#project-structure)
- [Background Jobs](#background-jobs)
- [License](#license)

---

## Overview

Discipline & Streak helps users stay consistent with their goals. Each user can define one or more **commitments**, check in daily, and watch their **streak** grow. Progress is visualized through a heat map and analytics reports, and users can opt into a **leaderboard** or pair with a **partner** for shared accountability.

## Features

- 🔐 Email/password authentication plus Google & Facebook social login
- ✅ Create, track, and archive personal commitments/habits
- 🔥 Daily check-ins with streak tracking and a GitHub-style heat map
- 📊 Weekly/analytical reports on progress
- 🏆 Opt-in leaderboard with weekly rankings
- 🤝 Friend requests and partner pairing for shared accountability
- 🔔 Web push notifications for check-in reminders
- 📰 In-app blog/news feed
- 🖼️ Profile customization (picture, theme, username) with Cloudinary-backed image storage
- 🛠️ Internal staff panel for user and content management
- 📤 Data export and account management (deactivation, reactivation, deletion)

## Tech Stack

| Layer            | Technology                                   |
|-------------------|-----------------------------------------------|
| Framework         | Django                                        |
| Database          | PostgreSQL                                    |
| Caching           | Redis (`django-redis`)                        |
| Auth              | Django auth + `social-auth-app-django` (Google, Facebook) |
| Static files      | WhiteNoise                                    |
| Media storage     | Cloudinary                                    |
| Email             | SMTP (Gmail) / Resend                         |
| Push notifications| Web Push (VAPID)                              |
| App server        | Gunicorn                                      |
| Load testing      | Locust                                        |

---

## Site Map

Below is the app's user-facing navigation. This lists the pages people actually move through in the product — internal API/JSON endpoints and implementation details are intentionally left out.

### Public Pages

| Page | Path |
|---|---|
| Landing / Home | `/` |
| Blog & Updates | `/v1/blog/` |
| Blog Post Detail | `/v1/blog/<id>/` |
| Privacy & Policies | linked from footer |
| "Still in Progress" placeholder | `/v1/in-progress/` |

### Authentication

| Page | Path |
|---|---|
| Log In | `/v1/login/` |
| Sign Up | `/v1/signup/` |
| Onboarding | `/v1/onboarding/` |
| Forgot Password | `/v1/password-reset/` |
| Reactivate Account | try to log in and you will be shown the process |

### Dashboard (Authenticated)

| Page | Path |
|---|---|
| Dashboard (home) | `/v1/dashboard/` |
| Account Settings | `/v1/dashboard/settings/` |
| Commitments (all) | `/v1/dashboard/commitment/` |
| Commitment Detail | `/v1/dashboard/commitment/<key>/` |
| Commitment Settings | `/v1/dashboard/commitment/<key>/settings/` |
| Profile | `/v1/dashboard/profile/` |
| Reports & Analytics | `/v1/dashboard/reports/` |
| Weekly Analysis | `/v1/weekly-analysis/` |
| Leaderboard | `/v1/leaderboard/` |

### Community & Partnering

| Page | Path |
|---|---|
| Relationships (friends & partner) | `/v1/dashboard/relationship/` |
| Partner Dashboard | `/v1/dashboard/relationship/partner/<user_id>/` |
| Find a Friend | search from Relationships page |

### Staff Panel

Internal, staff-only tools for managing users and content.

| Page | Path |
|---|---|
| Staff Home | `/v1/staff/home/` |
| Staff Sign Up | `/v1/staff/signup/` |
| Manage Users | `/v1/staff/users/` |
| Publish News/Blog Post | `/v1/staff/create_blog/` |
| Edit News Post | `/v1/staff/news/<id>/edit/` |
| Active Sessions | `/v1/staff/sessions/` |

---

## Getting Started

### Prerequisites

- Python 3.x
- get in touch with me for others @ lastissa11@gmail.com
### Installation

```bash
git clone <repository-url>
cd DISCIPLINEandSTREAK
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the project root:

```GET IN TOUCH WITH ME @LASTISSA11:GMAIL.COM FOR THE ENV SETUP
HIDDEN
```

### Database & Static Files

```GET IN TOUCH WITH ME @LASTISSA11:GMAIL.COM FOR THE DATABASE AND STATIC SETUP
HIDDEN
```

### Running the App

```bash
python manage.py runserver
```

The app will be available at `http://127.0.0.1:8000/`.

---

## Project Structure

```
DISCIPLINEandSTREAK/
├── DISCIPLINEandSTREAK/   # Project settings, root URLs, WSGI/ASGI entry points
├── origin/                # Main application (models, templates, static assets)
├── utility/                # Shared helpers (email, push notifications, reminders, config)
├── manage.py
├── requirements.txt       # The dependency my project use to function fully
└── runtime.txt            # For render hosting (additional information not important)
```

## Background Jobs

Reminder and maintenance jobs (e.g. check-in reminders) are triggered via authenticated HTTP calls from an external scheduler (cron), rather than an in-process worker- Reason because i cannot have a render background taska and i found a workaround

## License
MIT
