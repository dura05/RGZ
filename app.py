# app.py
import os
import sys
import yaml
from flask import Flask, request, jsonify
import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/subs_db")

def run_migrations():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS migrations_log (
            id INTEGER PRIMARY KEY,
            file_path TEXT NOT NULL,
            applied_at TIMESTAMP DEFAULT NOW()
        )
    """)
    conn.commit()

    with open("changelog.yaml") as f:
        changelog = yaml.safe_load(f)

    cur.execute("SELECT id, file_path FROM migrations_log")
    applied = {row[0]: row[1] for row in cur.fetchall()}

    for entry in changelog:
        mid = entry["id"]
        path = entry["file_path"]

        if mid in applied:
            if applied[mid] != path:
                print(f"❌ ОШИБКА СОГЛАСОВАННОСТИ: миграция {mid}")
                sys.exit(1)
            else:
                print(f"⏭️ Миграция {mid} уже применена")
        else:
            print(f"🚀 Применяю миграцию {mid}: {path}")
            with open(path, encoding="utf-8") as sql_file:
                cur.execute(sql_file.read())
            cur.execute("INSERT INTO migrations_log (id, file_path) VALUES (%s, %s)", (mid, path))
            conn.commit()

    cur.close()
    conn.close()
    print("✅ Миграции завершены")

# === Flask app создаётся всегда ===
app = Flask(__name__)

def get_db():
    return psycopg2.connect(DATABASE_URL)

# ... (твои маршруты: @app.route ...)

# === МИГРАТОР ЗАПУСКАЕТСЯ ТОЛЬКО ПРИ ПРЯМОМ ЗАПУСКЕ ===
if __name__ == '__main__':
    run_migrations()
    app.run(debug=True)