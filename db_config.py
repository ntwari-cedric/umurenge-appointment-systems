# db_config.py
import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Your Supabase PostgreSQL connection URL
# IMPORTANT: Replace YOUR-ACTUAL-PASSWORD with your real Supabase password
DATABASE_URL = "postgresql://postgres:YOUR-ACTUAL-PASSWORD@db.fpmqugcjvhidrjdgiijz.supabase.co:5432/postgres"

def get_db_connection():
    """Create and return a PostgreSQL database connection"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        raise

def init_postgres_tables():
    """Create all tables in PostgreSQL (matching your SQLite schema)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)
    
    # Create services table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS services (
            id SERIAL PRIMARY KEY,
            service_name TEXT NOT NULL UNIQUE
        )
    """)
    
    # Create appointments table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id SERIAL PRIMARY KEY,
            user_email TEXT NOT NULL,
            office_email TEXT NOT NULL,
            service_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            office_comment TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_email) REFERENCES users(email),
            FOREIGN KEY (office_email) REFERENCES users(email),
            FOREIGN KEY (service_id) REFERENCES services(id)
        )
    """)
    
    conn.commit()
    cursor.close()
    conn.close()
    print("✅ PostgreSQL tables created successfully!")

def migrate_data_from_sqlite():
    """Copy data from your existing SQLite database to PostgreSQL"""
    import sqlite3
    
    # Connect to SQLite
    sqlite_conn = sqlite3.connect('database.db')
    sqlite_cursor = sqlite_conn.cursor()
    
    # Connect to PostgreSQL
    pg_conn = get_db_connection()
    pg_cursor = pg_conn.cursor()
    
    # Migrate users
    sqlite_cursor.execute("SELECT * FROM users")
    users = sqlite_cursor.fetchall()
    for user in users:
        try:
            pg_cursor.execute(
                "INSERT INTO users (email, name, password, role) VALUES (%s, %s, %s, %s)",
                (user[0], user[1], user[2], user[3])
            )
        except Exception as e:
            print(f"User {user[0]} already exists or error: {e}")
    
    # Migrate services
    sqlite_cursor.execute("SELECT * FROM services")
    services = sqlite_cursor.fetchall()
    for service in services:
        try:
            pg_cursor.execute(
                "INSERT INTO services (id, service_name) VALUES (%s, %s)",
                (service[0], service[1])
            )
        except Exception as e:
            print(f"Service {service[1]} already exists or error: {e}")
    
    # Migrate appointments
    sqlite_cursor.execute("SELECT * FROM appointments")
    appointments = sqlite_cursor.fetchall()
    for apt in appointments:
        try:
            pg_cursor.execute("""
                INSERT INTO appointments (id, user_email, office_email, service_id, date, 
                                        description, status, office_comment, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (apt[0], apt[1], apt[2], apt[3], apt[4], apt[5], apt[6], apt[7], apt[8]))
        except Exception as e:
            print(f"Appointment {apt[0]} error: {e}")
    
    pg_conn.commit()
    pg_cursor.close()
    pg_conn.close()
    sqlite_conn.close()
    
    print("✅ Data migration completed!")
    