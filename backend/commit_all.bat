@echo off
git add CodeNight.docx backend/docker-compose.yml backend/.gitignore
git commit -m "chore: update documentation, docker and gitignore configurations"

git add backend/app/main.py backend/app/core/ backend/app/api/ backend/app/schemas/ backend/app/__init__.py
git commit -m "build: setup FastAPI core structure and routing"

git add backend/app/db/
git commit -m "feat(db): configure async sqlalchemy engine and base class"

git add backend/app/models/
git commit -m "feat(models): implement phase 1 user, badge, friendship, metrics and goal models"

git add backend/alembic.ini backend/alembic/env.py backend/alembic/script.py.mako backend/alembic/versions/__init__.py
git commit -m "chore(db): configure alembic for database migrations"

git add backend/alembic/versions/
git commit -m "feat(db): auto-generate and apply initial database migration for phase 1"

git push origin main
