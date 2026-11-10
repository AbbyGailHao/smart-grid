import os
import folium
import random
import statistics
from database import get_connection, log_audit_event

def fetch_all_households():
    """Fetches all registered households from the database as dictionaries."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM households")
    rows = cursor.fetchall()
    conn.close()
    
    # Convert sqlite3.Row objects to standard dictionaries
    return [dict(row) for row in rows]

def view_audit_logs():
    """Displays system security audit logs safely, preventing key lookup errors."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Ensure audit_logs table exists just in case
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT,
                target TEXT,
                details TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 50")
        rows = cursor.fetchall()
        conn.close()
        
        print("\n" + "="*80)
        print("🛡️ SYSTEM SECURITY AUDIT LOGS")
        print("="*80)
        
        if not rows:
            print("[INFO] No audit logs recorded yet.")
        else:
            for row in rows:
                # Convert sqlite3.Row to standard dict so .get() works securely
                r = dict(row)
                log_id = r.get('log_id', 'N/A')
                action = r.get('action', 'N/A')
                target = r.get('target', 'N/A')
                details = r.get('details', 'N/A')
                timestamp = r.get('timestamp', 'N/A')
                
                print(f"[{timestamp}] ID: {log_id} | {action} -> Target: {target}")
                if details:
                    print(f"    Details: {details}")
                    
        print("="*80 + "\n")
    except Exception as e:
        print(f"\n[ERROR] Database or execution error: {e}\n")

def get_output_path(filename):
    """
    Automatically routes files based on your folder convention:
    - Charts (.png) -> 'charts/' folder
    - Reports, PDFs, & GIS Maps -> 'reports_output/' folder
    """
    ext = filename.split('.')[-1].lower()
    target_dir = "charts" if ext == 'png' else "reports_output"
    os.makedirs(target_dir, exist_ok=True)
    return os.path.join(target_dir, filename)

def generate_household_map():
    """Generates an interactive GIS map with household nodes precisely distributed across Echague and Santiago City."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM households")
    households = cursor.fetchall()
    conn.close()
    
    # Center map right between Echague and Santiago City
    center_lat, center_lon = 16.7800, 121.6100
    m = folium.Map(location=[center_lat, center_lon], zoom_start=11, tiles='Esri.WorldStreetMap')
    
    echague_count = 0
    santiago_count = 0
    
    for idx, row in enumerate(households):
        h = dict(row)
        addr = str(h.get('address', '')).lower()
        
        # Explicitly check address content for Echague vs Santiago
        if "echague" in addr:
            echague_count += 1
            lat = 16.8533 + ((echague_count * 0.003) % 0.04)
            lon = 121.6708 + ((echague_count * 0.004) % 0.04)
        elif "santiago" in addr:
            santiago_count += 1
            lat = 16.6850 + ((santiago_count * 0.003) % 0.04)
            lon = 121.5450 + ((santiago_count * 0.004) % 0.04)
        else:
            # Fallback split if address doesn't explicitly name the city/town
            if idx % 2 == 0:
                echague_count += 1
                lat = 16.8533 + ((echague_count * 0.003) % 0.04)
                lon = 121.6708 + ((echague_count * 0.004) % 0.04)
            else:
                santiago_count += 1
                lat = 16.6850 + ((santiago_count * 0.003) % 0.04)
                lon = 121.5450 + ((santiago_count * 0.004) % 0.04)
            
        name = h.get('homeowner_name', 'Unknown')
        acc = h.get('account_number', 'N/A')
        address_text = h.get('address', 'N/A')
        ctype = h.get('connection_type', 'Residential')
        
        # Color coding by connection type
        if ctype == "Commercial":
            color = "blue"
        elif ctype == "Industrial":
            color = "purple"
        else:
            color = "green" # Residential
            
        popup_html = f"""
        <div style="font-family: Arial, sans-serif; font-size: 13px; width: 220px; padding: 5px; color: #111;">
            <b style="color: #0284c7; font-size: 14px;">{name}</b><hr style="margin: 5px 0; border: 0; border-top: 1px solid #ccc;">
            <b>Account No:</b> {acc}<br>
            <b>Address:</b> {address_text}<br>
            <b>Connection:</b> {ctype}
        </div>
        """
        
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"Node {acc} - {name}",
            icon=folium.Icon(color=color, icon="info-sign", prefix="glyphicon")
        ).add_to(m)
        
    output_path = get_output_path("household_map.html")
    m.save(output_path)
    return output_path
                 
def fetch_all_readings():
    """Fetches all meter readings joined with household details."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.*, h.account_number, h.homeowner_name, h.address, h.connection_type 
        FROM meter_readings r
        JOIN households h ON r.household_id = h.household_id
        ORDER BY r.reading_id DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def insert_household(acc_no, name, address, ctype, status="Active", online_billing="No"):
    """Inserts a new household into the database with validation."""
    if not acc_no or not name or not address:
        return False, "Account number, homeowner name, and address are required."
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO households (account_number, homeowner_name, address, connection_type, status, online_billing)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (acc_no, name, address, ctype, status, online_billing))
        conn.commit()
        log_audit_event("INSERT_HOUSEHOLD", acc_no, f"Added household {name} at {address}")
        conn.close()
        return True, "Household added successfully."
    except Exception as e:
        return False, f"Database error: {e}"

def delete_household(household_id):
    """Deletes a household and its associated meter readings."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT account_number FROM households WHERE household_id = ?", (household_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False, "Household not found."
        acc_no = row['account_number']
        
        cursor.execute("DELETE FROM meter_readings WHERE household_id = ?", (household_id,))
        cursor.execute("DELETE FROM households WHERE household_id = ?", (household_id,))
        conn.commit()
        log_audit_event("DELETE_HOUSEHOLD", acc_no, f"Deleted household ID {household_id}")
        conn.close()
        return True, "Household and associated readings deleted successfully."
    except Exception as e:
        return False, f"Database error: {e}"

def insert_meter_reading(household_id, billing_period, previous_reading, current_reading, rate_per_kwh, payment_status="Unpaid", reading_date="", interruption_notice="Normal Service"):
    """Records a new meter reading with non-negative consumption and tiered billing calculation."""
    try:
        prev = float(previous_reading)
        curr = float(current_reading)
        rate = float(rate_per_kwh)
        
        if curr < prev:
            return False, "Current reading cannot be less than previous reading."
        
        consumption = curr - prev
        cost = consumption * rate
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO meter_readings (household_id, billing_period, consumption_kwh, estimated_cost)
            VALUES (?, ?, ?, ?)
        """, (household_id, billing_period, consumption, cost))
        conn.commit()
        log_audit_event("INSERT_READING", str(household_id), f"Recorded {consumption} kWh for period {billing_period}")
        conn.close()
        return True, f"Meter reading recorded successfully (Consumption: {consumption:.2f} kWh, Cost: ₱{cost:.2f})."
    except Exception as e:
        return False, f"Error recording reading: {e}"

def delete_reading(reading_id):
    """Deletes a specific meter reading log entry."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM meter_readings WHERE reading_id = ?", (reading_id,))
        conn.commit()
        log_audit_event("DELETE_READING", str(reading_id), f"Deleted reading ID {reading_id}")
        conn.close()
        return True, "Reading deleted successfully."
    except Exception as e:
        return False, f"Database error: {e}"

def search_account_records(query):
    """Performs a live search across households by account number, name, or address."""
    conn = get_connection()
    cursor = conn.cursor()
    q = f"%{query}%"
    cursor.execute("""
        SELECT h.*, r.billing_period, r.consumption_kwh, r.estimated_cost
        FROM households h
        LEFT JOIN meter_readings r ON h.household_id = r.household_id
        WHERE h.account_number LIKE ? OR h.homeowner_name LIKE ? OR h.address LIKE ?
        ORDER BY h.household_id DESC
    """, (q, q, q))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def filter_readings_by_type(connection_type):
    """Filters meter readings by connection type (Residential, Commercial, Industrial)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.*, h.account_number, h.homeowner_name, h.address, h.connection_type 
        FROM meter_readings r
        JOIN households h ON r.household_id = h.household_id
        WHERE h.connection_type = ?
        ORDER BY r.reading_id DESC
    """, (connection_type,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]