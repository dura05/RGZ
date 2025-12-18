from flask import Flask, request, jsonify
from migrate import run_migrations
from config import get_db_connection
from psycopg2 import sql
import json
from datetime import datetime, date

# 🔥 Запускаем мигратор ПЕРЕД созданием приложения
run_migrations()

app = Flask(__name__)

def log_audit(user_id, action, entity, entity_id=None, details=None):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO audit_log (user_id, action, entity, entity_id, details)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, action, entity, entity_id, json.dumps(details) if details else None))
        conn.commit()
    finally:
        conn.close()

# 1. Создание подписки
@app.route('/subscriptions', methods=['POST'])
def create_subscription():
    data = request.get_json(force=True)
    user_id = data.get('user_id')
    name = data.get('name')
    amount = data.get('amount')
    periodicity = data.get('periodicity')
    start_date_str = data.get('start_date')

    if not all([user_id, name, amount, periodicity, start_date_str]):
        return jsonify({"error": "Missing required fields"}), 400

    if periodicity not in ('monthly', 'yearly'):
        return jsonify({"error": "Periodicity must be 'monthly' or 'yearly'"}), 400

    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    # Рассчитываем next_charge_date (упрощённо)
    if periodicity == 'monthly':
        if start_date.month == 12:
            next_charge = date(start_date.year + 1, 1, start_date.day)
        else:
            next_charge = date(start_date.year, start_date.month + 1, start_date.day)
    else:  # yearly
        next_charge = date(start_date.year + 1, start_date.month, start_date.day)

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO subscriptions (user_id, name, amount, periodicity, start_date, next_charge_date)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
            """, (user_id, name, amount, periodicity, start_date, next_charge))
            sub_id = cur.fetchone()[0]
        conn.commit()
        log_audit(user_id, "create", "subscription", sub_id, {"name": name})
        return jsonify({"id": sub_id, "message": "Subscription created"}), 201
    finally:
        conn.close()

# 2. Просмотр подписок
@app.route('/subscriptions', methods=['GET'])
def get_subscriptions():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "user_id required"}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, amount, periodicity, start_date, next_charge_date
                FROM subscriptions WHERE user_id = %s
            """, (user_id,))
            rows = cur.fetchall()
        return jsonify([{
            "id": r[0],
            "name": r[1],
            "amount": float(r[2]),
            "periodicity": r[3],
            "start_date": str(r[4]),
            "next_charge_date": str(r[5])
        } for r in rows])
    finally:
        conn.close()

# 3. Редактирование подписки
@app.route('/subscriptions/<int:sub_id>', methods=['PUT'])
def update_subscription(sub_id):
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT user_id, start_date, periodicity FROM subscriptions WHERE id = %s
            """, (sub_id,))
            result = cur.fetchone()
            if not result:
                return jsonify({"error": "Subscription not found"}), 404
            user_id, start_date, old_periodicity = result

        # Собираем обновления
        updates = {}
        recalculate_date = False

        if 'amount' in data:
            updates['amount'] = float(data['amount'])

        if 'periodicity' in data:
            new_p = data['periodicity']
            if new_p not in ('monthly', 'yearly'):
                return jsonify({"error": "Invalid periodicity"}), 400
            updates['periodicity'] = new_p
            if new_p != old_periodicity:
                recalculate_date = True

        if 'next_charge_date' in data:
            try:
                updates['next_charge_date'] = datetime.strptime(data['next_charge_date'], "%Y-%m-%d").date()
                recalculate_date = False
            except ValueError:
                return jsonify({"error": "Invalid date format"}), 400

        if not updates:
            return jsonify({"error": "No fields to update"}), 400

        # Пересчёт даты
        if recalculate_date:
            if updates.get('periodicity', old_periodicity) == 'monthly':
                if start_date.month == 12:
                    next_date = date(start_date.year + 1, 1, start_date.day)
                else:
                    next_date = date(start_date.year, start_date.month + 1, start_date.day)
            else:
                next_date = date(start_date.year + 1, start_date.month, start_date.day)
            updates['next_charge_date'] = next_date

        # Безопасное формирование запроса
        set_parts = []
        for k in updates.keys():
            set_parts.append(sql.Identifier(k) + sql.SQL(" = %s"))
        set_clause = sql.SQL(", ").join(set_parts)
        query = sql.SQL("UPDATE subscriptions SET {} WHERE id = %s").format(set_clause)

        values = list(updates.values()) + [sub_id]

        cur.execute(query, values)

        # Логируем
        cur.execute("""
            INSERT INTO audit_log (user_id, action, entity, entity_id, details)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, "update", "subscription", sub_id, json.dumps(updates)))

        conn.commit()
        return jsonify({"message": "Updated"}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"error": "Internal error"}), 500
    finally:
        conn.close()

# 4. Удаление подписки
@app.route('/subscriptions/<int:sub_id>', methods=['DELETE'])
def delete_subscription(sub_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id FROM subscriptions WHERE id = %s", (sub_id,))
            result = cur.fetchone()
            if not result:
                return jsonify({"error": "Subscription not found"}), 404
            user_id = result[0]
            cur.execute("DELETE FROM subscriptions WHERE id = %s", (sub_id,))
        conn.commit()
        log_audit(user_id, "delete", "subscription", sub_id)
        return jsonify({"message": "Deleted"}), 200
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(debug=False)  # debug=False для безопасности