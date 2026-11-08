import sqlite3

DB_NAME = "electricity_monitor.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def initialize_database():
    conn = get_connection()
    cursor = conn.cursor()

    # Drop existing tables to avoid schema mismatches
    cursor.execute("DROP TABLE IF EXISTS meter_readings;")
    cursor.execute("DROP TABLE IF EXISTS households;")

    # Create Households Table (Parent)
    cursor.execute("""
    CREATE TABLE households (
        household_id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_number TEXT UNIQUE NOT NULL,
        homeowner_name TEXT NOT NULL,
        address TEXT NOT NULL,
        connection_type TEXT NOT NULL
    )
    """)

    # Create Meter Readings Table (Child) with SQLite Generated Columns
    cursor.execute("""
    CREATE TABLE meter_readings (
        reading_id INTEGER PRIMARY KEY AUTOINCREMENT,
        household_id INTEGER NOT NULL,
        billing_period TEXT NOT NULL,
        previous_reading REAL NOT NULL,
        current_reading REAL NOT NULL,
        consumption_kwh REAL GENERATED ALWAYS AS (current_reading - previous_reading) STORED,
        rate_per_kwh REAL NOT NULL,
        estimated_cost REAL GENERATED ALWAYS AS ((current_reading - previous_reading) * rate_per_kwh) STORED,
        reading_date TEXT NOT NULL,
        FOREIGN KEY (household_id) REFERENCES households (household_id) ON DELETE CASCADE
    )
    """)

    conn.commit()
    seed_expanded_data(cursor, conn)
    conn.close()

def seed_expanded_data(cursor, conn):
    households = [
        ("ACC-8001", "Maria Santos", "Brgy. Baluarte, Santiago City", "Residential"),
        ("ACC-8002", "Juan Dela Cruz", "Brgy. Echague Proper, Echague", "Residential"),
        ("ACC-8003", "Roberto Gomez", "Brgy. San Fabian, Echague", "Residential"),
        ("ACC-8004", "Elena Reyes", "Brgy. Malitao, Echague", "Commercial"),
        ("ACC-8005", "Carlos Aquino", "Brgy. Cabaruan, Santiago City", "Residential"),
        ("ACC-8006", "Ana Marie Ramos", "Brgy. San Antonio, Echague", "Residential"),
        ("ACC-8007", "Ruel Pascual", "Brgy. Cabagan, Echague", "Residential"),
        ("ACC-8008", "Greenfield Store", "Brgy. Alicia Road, Echague", "Commercial"),
        ("ACC-8009", "Loida Villanueva", "Brgy. Dammang, Echague", "Residential"),
        ("ACC-8010", "Echague Mini-Mart", "Brgy. Centro, Echague", "Commercial")
    ]
    cursor.executemany("""
        INSERT INTO households (account_number, homeowner_name, address, connection_type)
        VALUES (?, ?, ?, ?)
    """, households)

    readings = [
        (1, "2026-04", 800.0, 1020.0, 11.50, "2026-04-28"),
        (1, "2026-05", 1020.0, 1260.0, 11.60, "2026-05-27"),
        (1, "2026-06", 1260.0, 1250.0, 11.75, "2026-06-28"),
        (1, "2026-07", 1250.0, 1480.0, 11.85, "2026-07-28"),
        (1, "2026-08", 1480.0, 1715.0, 11.90, "2026-08-27"),
        (1, "2026-09", 1715.0, 1940.0, 11.95, "2026-09-26"),
        
        (2, "2026-04", 2600.0, 2850.0, 11.50, "2026-04-29"),
        (2, "2026-05", 2850.0, 3090.0, 11.60, "2026-05-28"),
        (2, "2026-06", 3090.0, 3100.0, 11.75, "2026-06-29"),
        (2, "2026-07", 3100.0, 3320.0, 11.85, "2026-07-29"),
        (2, "2026-08", 3320.0, 3580.0, 11.90, "2026-08-28"),
        (2, "2026-09", 3580.0, 3810.0, 11.95, "2026-09-27"),
        
        (3, "2026-04", 600.0, 720.0, 11.50, "2026-04-30"),
        (3, "2026-05", 720.0, 840.0, 11.60, "2026-05-29"),
        (3, "2026-06", 840.0, 850.0, 11.75, "2026-06-30"),
        (3, "2026-07", 850.0, 970.0, 11.85, "2026-07-30"),
        (3, "2026-08", 970.0, 1105.0, 11.90, "2026-08-29"),
        (3, "2026-09", 1105.0, 1230.0, 11.95, "2026-09-28"),
        
        (4, "2026-04", 4500.0, 5100.0, 12.90, "2026-04-25"),
        (4, "2026-05", 5100.0, 5750.0, 13.00, "2026-05-26"),
        (4, "2026-06", 5750.0, 5400.0, 13.10, "2026-06-25"),
        (4, "2026-07", 5400.0, 6150.0, 13.20, "2026-07-25"),
        (4, "2026-08", 6150.0, 6980.0, 13.25, "2026-08-26"),
        (4, "2026-09", 6980.0, 7750.0, 13.30, "2026-09-25"),
        
        (5, "2026-04", 1700.0, 1900.0, 11.50, "2026-04-30"),
        (5, "2026-05", 1900.0, 2090.0, 11.60, "2026-05-30"),
        (5, "2026-06", 2090.0, 2100.0, 11.75, "2026-06-30"),
        (5, "2026-07", 2100.0, 2290.0, 11.85, "2026-07-31"),
        (5, "2026-08", 2290.0, 2485.0, 11.90, "2026-08-30"),
        (5, "2026-09", 2485.0, 2690.0, 11.95, "2026-09-29")
    ]
    cursor.executemany("""
        INSERT INTO meter_readings (household_id, billing_period, previous_reading, current_reading, rate_per_kwh, reading_date)
        VALUES (?, ?, ?, ?, ?, ?)
    """, readings)
    conn.commit()