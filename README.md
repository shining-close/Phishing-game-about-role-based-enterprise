# Phishing Game: Role‑Based Enterprise Anti‑Phishing Training Game
> Graduation Design Django Project: Role‑Hierarchy‑Based Enterprise Anti‑Phishing Training Game

## Project Overview
This is a web‑based anti‑phishing serious game.
Implement T0 baseline, T1 test, L1‑L3 multi‑level training system,
includes user register/login, four‑dimensional scoring system, behaviour log, questionnaire and ethics consent page.

Tech Stack:
- Backend: Django
- Frontend: HTML, CSS, JavaScript
- Database: SQLite3 (local development only)

## Local Development Setup
### 1. Clone repository
git clone https://github.com/shining-close/Phishing-game-about-role-based-enterprise.git
cd Phishing-game-about-role-based-enterprise

## 2. Create conda virtual environment
conda create -n phishing_game python=3.12
conda activate phishing_game

## 3. Install dependencies
pip install -r requirements.txt

## 4. Database migrate
python manage.py migrate

## 5. Run local development server
python manage.py runserver
Open browser: [http://127.0.0.1:8000]