# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Langue

Ce projet est en francais. Les commentaires, messages de commit, et communications doivent etre en francais. Les identifiants de code restent en anglais.

## Commandes

```bash
# Activer le venv
cd nba-dashboard && source venv/Scripts/activate   # Windows/Git Bash
cd nba-dashboard && source venv/bin/activate        # Linux/Mac

# Installer les dependances
pip install -r requirements.txt

# Lancer le serveur (depuis nba-dashboard/)
uvicorn main:app --reload

# Lancer les tests
pytest tests/

# Lancer un test specifique
pytest tests/test_database.py -v
```

## Architecture

Monolithe FastAPI dans `nba-dashboard/`. Un seul process gere tout : collecte de donnees NBA, stockage SQLite, API REST, et service du frontend statique.

**Flux de donnees :** APScheduler (cron 8h00) -> `nba_service.py` (appels HTTP stats.nba.com + cdn.nba.com) -> `database.py` (SQLite `nba.db`) -> API REST -> Frontend JS

### Fichiers backend

- `main.py` — Point d'entree FastAPI. Definit les routes `/api/games`, `/api/standings`, `/api/refresh`. Monte les fichiers statiques sur `/`. Gere le lifecycle (init DB + scheduler au demarrage).
- `database.py` — Schema SQLite (3 tables : `games`, `player_stats`, `standings`), fonctions CRUD, purge des donnees > 30 jours. Utilise `sqlite3.Row` comme row_factory.
- `nba_service.py` — Collecte via HTTP direct (pas le package `nba_api` malgre la dependance). Utilise ScoreboardV3 pour les matchs et le CDN NBA pour les box scores. Necessite des headers specifiques (`NBA_HEADERS`).
- `scheduler.py` — Configure APScheduler avec `BackgroundScheduler`. `daily_collect()` est aussi appelee par `POST /api/refresh`.

### Frontend

Fichiers statiques dans `nba-dashboard/static/` (HTML/CSS/JS vanilla), servis par FastAPI. Theme sombre, responsive.

### Base de donnees

SQLite local (`nba.db`, cree au demarrage). 3 tables avec retention de 30 jours. WAL mode et foreign keys actives.

## Design spec

La spec complete du projet est dans `docs/superpowers/specs/2026-04-09-nba-daily-dashboard-design.md` — contient le schema de donnees detaille, les formats de reponse API, et les specs du frontend.
