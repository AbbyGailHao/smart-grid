import sqlite3
from database import get_connection

def fetch_all_households():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM households")
    rows = cursor.fetchall()
    conn.close()
    return rows

def fetch_all_readings():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.reading_id, h.account_number, h.homeowner_name, r.billing_period, 
               r.previous_reading, r.current_reading, r.consumption_kwh, 
               r.rate_per_kwh, r.estimated_cost, r.reading_date 
        FROM meter_readings r
        JOIN households h ON r.household_id = h.household_id
        ORDER BY r.reading_date DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows

def insert_household(account_number, homeowner_name, address, connection_type):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO households (account_number, homeowner_name, address, connection_type)
            VALUES (?, ?, ?, ?)
        """, (account_number, homeowner_name, address, connection_type))
        conn.commit()
        conn.close()
        return True, f"Success! Household '{homeowner_name}' added successfully."
    except sqlite3.IntegrityError:
        return False, "Error: Account number already exists or invalid data provided."

def insert_meter_reading(household_id, billing_period, previous_reading, current_reading, rate_per_kwh, reading_date):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO meter_readings (household_id, billing_period, previous_reading, current_reading, rate_per_kwh, reading_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (household_id, billing_period, previous_reading, current_reading, rate_per_kwh, reading_date))
        conn.commit()
        conn.close()
        return True, "Success! Meter reading recorded successfully."
    except sqlite3.Error as e:
        return False, f"Database error: {e}"

def search_account_records(acc_query):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT h.account_number, h.homeowner_name, h.address, h.connection_type,
               r.billing_period, r.previous_reading, r.current_reading, 
               r.consumption_kwh, r.rate_per_kwh, r.estimated_cost, r.reading_date
        FROM households h
        LEFT JOIN meter_readings r ON h.household_id = r.household_id
        WHERE h.account_number LIKE ?
    """, (f"%{acc_query}%",))
    rows = cursor.fetchall()
    conn.close()
    return rows

def filter_readings_by_type(ctype):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT h.account_number, h.homeowner_name, h.connection_type, 
               r.billing_period, r.consumption_kwh, r.estimated_cost
        FROM meter_readings r
        JOIN households h ON r.household_id = h.household_id
        WHERE h.connection_type = ?
        ORDER BY r.consumption_kwh DESC
    """, (ctype,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_highest_consumer():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT h.account_number, h.homeowner_name, h.address, h.connection_type, 
               SUM(r.consumption_kwh) as total_usage, SUM(r.estimated_cost) as total_cost
        FROM meter_readings r
        JOIN households h ON r.household_id = h.household_id
        GROUP BY h.household_id
        ORDER BY total_usage DESC
        LIMIT 1
    """)
    row = cursor.fetchone()
    conn.close()
    return row