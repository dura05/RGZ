# migrate.py
import yaml
from config import get_db_connection

def run_migrations():
    conn = get_db_connection()
    try:
        # Гарантируем, что таблица лога существует
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS migrations_log (
                    id SERIAL PRIMARY KEY,
                    migration_id INTEGER NOT NULL UNIQUE,
                    file_path VARCHAR(255) NOT NULL,
                    applied_at TIMESTAMP DEFAULT NOW()
                )
            """)
        conn.commit()

        # Читаем changelog
        with open("changelog.yaml", "r", encoding="utf-8") as f:
            changelog = yaml.safe_load(f)["migrations"]

        # Получаем уже применённые миграции
        with conn.cursor() as cur:
            cur.execute("SELECT migration_id, file_path FROM migrations_log")
            applied = {row[0]: row[1] for row in cur.fetchall()}

        # Обрабатываем каждую миграцию
        for migration in changelog:
            mid = migration["id"]
            path = migration["file_path"]

            if mid in applied:
                if applied[mid] != path:
                    raise RuntimeError(
                        f"❌ Несогласованность: миграция ID {mid} изменилась! "
                        f"Было: '{applied[mid]}', стало: '{path}'. "
                        "База данных в несогласованном состоянии."
                    )
                continue

            # Применяем новую миграцию
            with open(path, "r", encoding="utf-8") as f:
                sql = f.read()
            with conn.cursor() as cur:
                cur.execute(sql)
                cur.execute(
                    "INSERT INTO migrations_log (migration_id, file_path) VALUES (%s, %s)",
                    (mid, path)
                )
            conn.commit()
            print(f"✅ Миграция {mid} применена")

        print("🎉 Все миграции успешно применены.")
    finally:
        conn.close()