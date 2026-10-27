<div align="center">

<img src="favicon.svg" alt="GetRank Logo" width="80" height="80" />

**The Ultimate Leaderboard & Ranking Platform**

# GetRank.fun

### getrank.fun

**Create leaderboards, submit entries, vote for the best, and climb the ranks.**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=flat-square&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/SQLite-3.40+-003B57?style=flat-square&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![License MIT](https://img.shields.io/badge/license-MIT-f4c430?style=flat-square)](LICENSE)

[Quick Start](#quick-start) · [Features](#features) · [API Reference](#api-reference)

<br />

</div>

## Features

- 🏆 **Create Leaderboards** — Start competitions across gaming, music, art, photography, technology & more
- 🗳️ **Community Voting** — Upvote/downvote entries in real-time
- 📊 **Live Stats** — Track leaderboard counts, entries, and votes
- 🔍 **Category Filters** — Browse by category
- 👤 **Auth System** — Register, login, and personalized leaderboards

## Quick Start

```bash
cd backend
pip install -r requirements.txt
python3 server.py
```

The server runs on `http://localhost:5002`.

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/leaderboards` | List all leaderboards |
| `POST` | `/api/leaderboards` | Create a leaderboard |
| `GET` | `/api/leaderboards/<id>` | Get leaderboard detail + entries |
| `POST` | `/api/leaderboards/<id>/entries` | Submit an entry |
| `POST` | `/api/entries/<id>/vote` | Vote on an entry |
| `GET` | `/api/stats` | Platform stats |
| `POST` | `/api/auth/register` | Register a user |
| `POST` | `/api/auth/login` | Login |

## Architecture

```
getrank/
├── backend/
│   ├── server.py          # Flask API server
│   ├── requirements.txt
│   └── getrank.db         # SQLite database
└── frontend/
    ├── index.html         # Single-page app
    ├── css/styles.css
    └── js/app.js
```

## License

MIT
