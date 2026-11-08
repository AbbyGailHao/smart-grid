from flask import Flask, render_template
import sqlite3

app = Flask(__name__)
DB_NAME = "electricity_monitor.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    conn = get_db_connection()
    households = conn.execute('SELECT * FROM households').fetchall()
    readings = conn.execute('''
        SELECT r.reading_id, h.account_number, h.homeowner_name, r.billing_period, 
               r.previous_reading, r.current_reading, r.consumption_kwh, 
               r.rate_per_kwh, r.estimated_cost, r.reading_date 
        FROM meter_readings r
        JOIN households h ON r.household_id = h.household_id
    ''').fetchall()
    conn.close()
    return render_template('index.html', households=households, readings=readings, db_name=DB_NAME)

if __name__ == '__main__':
    print("Starting Localhost server...")
    print("Open your web browser and go to: http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
