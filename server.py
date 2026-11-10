from flask import Flask, render_template, request, jsonify, redirect, url_for
from database import get_connection, init_db
from analytics import get_summary_statistics
from functions import (
    fetch_all_households, fetch_all_readings, insert_household,
    delete_household, insert_meter_reading, delete_reading,
    search_account_records, filter_readings_by_type
)

app = Flask(__name__)

# Ensure tables and expanded dataset (~450+ records across Echague & Santiago) are initialized on web server boot
init_db()

@app.route('/')
def index():
    """Main dashboard rendering household tables and analytical summaries."""
    households = fetch_all_households()
    readings = fetch_all_readings()
    stats = get_summary_statistics()
    return render_template('index.html', households=households, readings=readings, stats=stats)

@app.route('/api/stats', methods=['GET'])
def api_stats():
    """API endpoint returning analytical statistics as JSON."""
    stats = get_summary_statistics()
    return jsonify(stats if stats else {"error": "No data available"})

@app.route('/api/households', methods=['GET', 'POST'])
def handle_households():
    """API endpoint to fetch or add households with strict formatting validation."""
    if request.method == 'POST':
        data = request.json or {}
        acc_no = data.get('account_number', '').strip()
        name = data.get('homeowner_name', '').strip()
        address = data.get('address', '').strip()
        ctype = data.get('connection_type', '').strip()
        status = data.get('status', 'Active').strip().capitalize()
        online_billing = data.get('online_billing', 'No').strip().capitalize()
        
        success, message = insert_household(acc_no, name, address, ctype, status, online_billing)
        status_code = 201 if success else 400
        return jsonify({"success": success, "message": message}), status_code

    households = fetch_all_households()
    return jsonify(households)

@app.route('/api/households/delete/<int:household_id>', methods=['DELETE', 'POST'])
def api_delete_household(household_id):
    """API endpoint to delete a household record."""
    success, message = delete_household(household_id)
    status_code = 200 if success else 400
    return jsonify({"success": success, "message": message}), status_code

@app.route('/api/readings', methods=['GET', 'POST'])
def handle_readings():
    """API endpoint to fetch or record new meter readings with high usage detection."""
    if request.method == 'POST':
        data = request.json or {}
        try:
            hid = int(data.get('household_id'))
            period = data.get('billing_period', '').strip()
            prev = float(data.get('previous_reading'))
            curr = float(data.get('current_reading'))
            rate = float(data.get('rate_per_kwh'))
            status = data.get('payment_status', 'Unpaid').strip().capitalize()
            date_str = data.get('reading_date', '').strip()
            notice = data.get('interruption_notice', 'Normal Service').strip()
            
            success, message = insert_meter_reading(hid, period, prev, curr, rate, status, date_str, notice)
            status_code = 201 if success else 400
            
            # High consumption flag for web UI notification
            high_consumption_flag = (curr - prev) > 300.0
            
            return jsonify({
                "success": success, 
                "message": message,
                "high_consumption_warning": high_consumption_flag
            }), status_code
        except (ValueError, TypeError) as e:
            return jsonify({"success": False, "message": f"Invalid payload parameter: {e}"}), 400

    readings = fetch_all_readings()
    return jsonify(readings)

@app.route('/api/readings/delete/<int:reading_id>', methods=['DELETE', 'POST'])
def api_delete_reading(reading_id):
    """API endpoint to delete a reading entry."""
    success, message = delete_reading(reading_id)
    status_code = 200 if success else 400
    return jsonify({"success": success, "message": message}), status_code

@app.route('/api/search', methods=['GET'])
def api_search():
    """API endpoint for live filtering households and meter logs."""
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])
    results = search_account_records(query)
    return jsonify(results)

if __name__ == '__main__':
    # Runs web server on port 5000 in debug mode for development
    app.run(host='127.0.0.1', port=5000, debug=True)