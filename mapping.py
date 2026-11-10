import folium
from database import get_connection

def generate_household_map():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT h.account_number, h.homeowner_name, h.address, h.status, h.connection_type,
               COALESCE(SUM(r.consumption_kwh), 0) as total_consumption
        FROM households h
        LEFT JOIN meter_readings r ON h.household_id = r.household_id
        GROUP BY h.household_id
    """)
    households = cursor.fetchall()

    cursor.execute("SELECT barangay, incident_type, severity_level, date_reported FROM disaster_incidents")
    disasters = cursor.fetchall()
    conn.close()

    santiago_center = [16.6908, 121.5478]
    m = folium.Map(location=santiago_center, zoom_start=13, tiles="Esri.WorldStreetMap")

    barangay_coords = {
        "Baluarte": [16.6850, 121.5520],
        "Centro": [16.6908, 121.5478],
        "Dubinan East": [16.6950, 121.5600],
        "Rizal": [16.6820, 121.5400],
        "National Highway": [16.6880, 121.5430],
        "Plaridel": [16.6750, 121.5350],
        "Victory Norte": [16.7000, 121.5500],
        "San Andres": [16.6680, 121.5250],
        "Villanueva": [16.7100, 121.5650],
        "Cabulay": [16.7200, 121.5800]
    }

    for row in households:
        addr = row['address']
        coords = santiago_center
        for bldg, loc in barangay_coords.items():
            if bldg.lower() in addr.lower():
                coords = loc
                break

        status = row['status']
        color = 'green' if status == 'Active' else ('orange' if status == 'Overdue' else 'red')

        popup_html = f"""
        <b>Account:</b> {row['account_number']}<br>
        <b>Name:</b> {row['homeowner_name']}<br>
        <b>Address:</b> {addr}<br>
        <b>Status:</b> {status}<br>
        <b>Total Usage:</b> {row['total_consumption']:,.2f} kWh
        """

        folium.Marker(
            location=coords,
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"{row['homeowner_name']} ({row['account_number']})",
            icon=folium.Icon(color=color, icon='bolt', prefix='fa')
        ).add_to(m)

    for d in disasters:
        bldg = d['barangay']
        coords = barangay_coords.get(bldg, [santiago_center[0] + 0.005, santiago_center[1] + 0.005])
        severity = d['severity_level']
        d_color = 'red' if severity == 'High' else ('orange' if severity == 'Medium' else 'beige')

        disaster_html = f"""
        <div style="color: darkred; font-weight: bold;">
        ⚠️ DISASTER / HAZARD ALERT ⚠️<br>
        <b>Barangay:</b> {bldg}<br>
        <b>Incident:</b> {d['incident_type']}<br>
        <b>Severity:</b> {severity}<br>
        <b>Reported:</b> {d['date_reported']}
        </div>
        """

        folium.Marker(
            location=coords,
            popup=folium.Popup(disaster_html, max_width=320),
            tooltip=f"Hazard Alert: {bldg} ({d['incident_type']})",
            icon=folium.Icon(color=d_color, icon='exclamation-triangle', prefix='fa')
        ).add_to(m)

    map_path = "household_map.html"
    m.save(map_path)
    return map_path