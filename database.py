import sqlite3
import json
from config import Config

def get_db_connection():
    conn = sqlite3.connect(Config.DATABASE)
    conn.row_factory = sqlite3.Row
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_db_connection()
    with open('schema.sql', 'r') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()

# --- PROFILE CRUD OPERATIONS ---

def get_profiles():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM profiles ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_profile(profile_id):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def create_profile(name, age, gender, height_cm, weight_kg, activity_level, diet_type, allergies,
                   target_calories=2000, target_protein=60, target_carbs=250, target_fat=65):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO profiles (name, age, gender, height_cm, weight_kg, activity_level, diet_type, allergies,
                              target_calories, target_protein, target_carbs, target_fat)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, age, gender, height_cm, weight_kg, activity_level, diet_type, allergies,
          target_calories, target_protein, target_carbs, target_fat))
    profile_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return profile_id

def update_profile(profile_id, name, age, gender, height_cm, weight_kg, activity_level, diet_type, allergies,
                   target_calories, target_protein, target_carbs, target_fat):
    conn = get_db_connection()
    conn.execute("""
        UPDATE profiles
        SET name = ?, age = ?, gender = ?, height_cm = ?, weight_kg = ?, activity_level = ?,
            diet_type = ?, allergies = ?, target_calories = ?, target_protein = ?, target_carbs = ?, target_fat = ?
        WHERE id = ?
    """, (name, age, gender, height_cm, weight_kg, activity_level, diet_type, allergies,
          target_calories, target_protein, target_carbs, target_fat, profile_id))
    conn.commit()
    conn.close()
    return True

def delete_profile(profile_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
    conn.commit()
    conn.close()
    return True

# --- CHAT HISTORY OPERATIONS ---

def get_chat_history(profile_id, limit=30):
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT role, message, timestamp FROM chat_history
        WHERE profile_id = ?
        ORDER BY id ASC
    """, (profile_id,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]

def add_chat_message(profile_id, role, message):
    conn = get_db_connection()
    conn.execute("""
        INSERT INTO chat_history (profile_id, role, message)
        VALUES (?, ?, ?)
    """, (profile_id, role, message))
    conn.commit()
    conn.close()

def clear_chat_history(profile_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM chat_history WHERE profile_id = ?", (profile_id,))
    conn.commit()
    conn.close()

# --- MEAL PLANS OPERATIONS ---

def get_meal_plans(profile_id):
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT id, goal, duration, plan_data, created_at FROM meal_plans
        WHERE profile_id = ?
        ORDER BY id DESC
    """, (profile_id,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]

def add_meal_plan(profile_id, goal, duration, plan_data):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO meal_plans (profile_id, goal, duration, plan_data)
        VALUES (?, ?, ?, ?)
    """, (profile_id, goal, duration, plan_data))
    plan_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return plan_id

# --- NUTRITION LOGS OPERATIONS ---

def get_nutrition_logs(profile_id, limit=7):
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT date, calories, protein, carbs, fat FROM nutrition_logs
        WHERE profile_id = ?
        ORDER BY date DESC
        LIMIT ?
    """, (profile_id, limit)).fetchall()
    conn.close()
    # Reverse to return in chronological order
    return [dict(row) for row in reversed(rows)]

def add_nutrition_log(profile_id, calories, protein, carbs, fat, date):
    conn = get_db_connection()
    try:
        conn.execute("""
            INSERT INTO nutrition_logs (profile_id, calories, protein, carbs, fat, date)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(profile_id, date) DO UPDATE SET
                calories = excluded.calories,
                protein = excluded.protein,
                carbs = excluded.carbs,
                fat = excluded.fat
        """, (profile_id, calories, protein, carbs, fat, date))
        conn.commit()
        success = True
    except sqlite3.Error:
        success = False
    finally:
        conn.close()
    return success
