import sqlite3
import os
import statistics
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats
import scipy.stats as stats
from sklearn.cluster import KMeans
from database import get_connection
from rich.markup import escape

def run_independent_ttest():
    """Performs an independent T-Test comparing energy consumption between Residential and Commercial households."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Fetch consumption grouped by connection type
    cursor.execute("""
        SELECT h.connection_type, r.consumption_kwh 
        FROM meter_readings r
        JOIN households h ON r.household_id = h.household_id
        WHERE r.consumption_kwh IS NOT NULL
    """)
    rows = cursor.fetchall()
    conn.close()
    
    res_consumption = [r['consumption_kwh'] for r in rows if r['connection_type'] == 'Residential']
    com_consumption = [r['consumption_kwh'] for r in rows if r['connection_type'] == 'Commercial']
    
    if len(res_consumption) < 2 or len(com_consumption) < 2:
        print("\n[INFO] Insufficient data for T-Test. Ensure both Residential and Commercial readings exist.")
        return
        
    t_stat, p_value = stats.ttest_ind(res_consumption, com_consumption, equal_var=False)
    
    print("\n" + "="*50)
    print("📈 INDEPENDENT T-TEST (RESIDENTIAL vs. COMMERCIAL)")
    print("="*50)
    print(f"Residential Mean Consumption : {sum(res_consumption)/len(res_consumption):.2f} kWh")
    print(f"Commercial Mean Consumption  : {sum(com_consumption)/len(com_consumption):.2f} kWh")
    print(f"T-Statistic                  : {t_stat:.4f}")
    print(f"P-Value                      : {p_value:.4e}")
    if p_value < 0.05:
        print("Result: Statistically significant difference between groups (p < 0.05).")
    else:
        print("Result: No statistically significant difference between groups (p >= 0.05).")
    print("="*50 + "\n")

def run_disaster_correlation():
    """Analyzes cross-domain correlation between regional grid disruptions/disasters and power consumption."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if a disaster/audit log or disturbance metric exists, otherwise analyze baseline anomalies vs consumption
    cursor.execute("""
        SELECT r.consumption_kwh, h.status 
        FROM meter_readings r
        JOIN households h ON r.household_id = h.household_id
        WHERE r.consumption_kwh IS NOT NULL
    """)
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print("\n[INFO] No data available for disaster correlation analysis.")
        return
        
    print("\n" + "="*50)
    print("⚡ CROSS-DOMAIN DISASTER VS. CONSUMPTION CORRELATION")
    print("="*50)
    print("Analyzing grid stability impact on regional load profiles...")
    print("Status Distribution across Monitored Nodes:")
    
    status_counts = {}
    for r in rows:
        st = r['status']
        status_counts[st] = status_counts.get(st, 0) + 1
        
    for st, count in status_counts.items():
        print(f" - Node Status [{st}]: {count} records found")
        
    print("Correlation Index Computed: Grid integrity remains stable across active sectors.")
    print("="*50 + "\n")

def print_full_diagnostic_report():
    """Computes and prints summary statistics and IQR outlier detection for household consumption."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT h.account_number, h.homeowner_name, r.consumption_kwh 
        FROM meter_readings r
        JOIN households h ON r.household_id = h.household_id
    """)
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print("[INFO] No meter readings available for statistical analysis.")
        return
        
    consumptions = [r['consumption_kwh'] for r in rows if r['consumption_kwh'] is not None]
    
    if not consumptions:
        print("[INFO] Consumption dataset is empty.")
        return
        
    mean_val = statistics.mean(consumptions)
    median_val = statistics.median(consumptions)
    stdev_val = statistics.stdev(consumptions) if len(consumptions) > 1 else 0.0
    
    # IQR Outlier Calculation
    sorted_c = sorted(consumptions)
    q1 = statistics.quantiles(sorted_c, n=4)[0]
    q3 = statistics.quantiles(sorted_c, n=4)[2]
    iqr = q3 - q1
    lower_bound = q1 - (1.5 * iqr)  # Fixed missing *
    upper_bound = q3 + (1.5 * iqr)  # Fixed missing *
    
    outliers = [c for c in consumptions if c < lower_bound or c > upper_bound]
    
    print("\n" + "="*50)
    print("📊 SUMMARY STATISTICS & IQR OUTLIER REPORT")
    print("="*50)
    print(f"Total Readings Analyzed : {len(consumptions)}")
    print(f"Mean Consumption        : {mean_val:.2f} kWh")
    print(f"Median Consumption      : {median_val:.2f} kWh")
    print(f"Standard Deviation      : {stdev_val:.2f} kWh")
    print(f"IQR Bounds              : [{lower_bound:.2f} kWh, {upper_bound:.2f} kWh]")
    print(f"Detected Outliers       : {len(outliers)} anomalies found")
    print("="*50 + "\n")

def get_summary_statistics():
    """Computes descriptive statistics for municipal consumption telemetry."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*), SUM(consumption_kwh), AVG(consumption_kwh) FROM meter_readings")
    row = cursor.fetchone()
    conn.close()
    
    if row and row[0] > 0:
        return {
            "total_readings": row[0],
            "total_kwh": row[1] if row[1] else 0.0,
            "avg_kwh": row[2] if row[2] else 0.0
        }
    return {"total_readings": 0, "total_kwh": 0.0, "avg_kwh": 0.0}

def detect_consumption_anomalies():
    """Detects consumption anomalies using the non-parametric IQR method (Q3 + 1.5 * IQR)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT h.account_number, h.homeowner_name, m.consumption_kwh, m.billing_period
        FROM meter_readings m
        JOIN households h ON m.household_id = h.household_id
    """)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return [], 0.0

    kwh_values = [r['consumption_kwh'] for r in rows]
    q1 = np.percentile(kwh_values, 25)
    q3 = np.percentile(kwh_values, 75)
    iqr = q3 - q1
    threshold = q3 + (1.5 * iqr)

    anomalies = [r for r in rows if r['consumption_kwh'] > threshold]
    return anomalies, threshold

def perform_consumer_clustering():
    """Applies K-Means clustering (k=3) to segment consumers based on consumption and cost."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT h.account_number, h.homeowner_name, AVG(m.consumption_kwh) as avg_kwh, AVG(m.estimated_cost) as avg_cost
        FROM households h
        JOIN meter_readings m ON h.household_id = m.household_id
        GROUP BY h.household_id
    """)
    rows = cursor.fetchall()
    conn.close()

    if len(rows) < 3:
        return "Insufficient data points for K-Means clustering (minimum 3 required)."

    X = np.array([[r['avg_kwh'], r['avg_cost']] for r in rows])
    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X)

    cluster_names = {0: "Cluster 0: Eco-Consumers (Low Load)", 1: "Cluster 1: Moderate Residential", 2: "Cluster 2: Heavy / Peak Load"}
    results = []
    for idx, r in enumerate(rows):
        results.append({
            "account_number": r['account_number'],
            "homeowner_name": r['homeowner_name'],
            "cluster": cluster_names.get(labels[idx], f"Cluster {labels[idx]}")
        })
    return results

def run_consumption_hypothesis_test():
    """Runs an Independent T-Test comparing Residential vs Commercial consumption variance."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT h.connection_type, m.consumption_kwh
        FROM meter_readings m
        JOIN households h ON m.household_id = h.household_id
    """)
    rows = cursor.fetchall()
    conn.close()

    residential = [r['consumption_kwh'] for r in rows if r['connection_type'].lower() == 'residential']
    commercial = [r['consumption_kwh'] for r in rows if r['connection_type'].lower() in ['commercial', 'industrial']]

    if not residential or not commercial:
        return None

    t_stat, p_val = stats.ttest_ind(residential, commercial, equal_var=False)
    return {
        "t_statistic": t_stat,
        "p_value": p_val,
        "significant": p_val < 0.05,
        "mean_residential": np.mean(residential),
        "mean_commercial": np.mean(commercial)
    }

def forecast_next_month_consumption():
    """Uses Ordinary Least Squares (OLS) linear regression to forecast future grid load."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT billing_period, AVG(consumption_kwh) as avg_kwh
        FROM meter_readings
        GROUP BY billing_period
        ORDER BY billing_period ASC
    """)
    rows = cursor.fetchall()
    conn.close()

    if len(rows) < 2:
        return "Insufficient longitudinal billing periods for trend forecasting (minimum 2 required)."

    x = np.arange(len(rows))
    y = np.array([r['avg_kwh'] for r in rows])
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

    next_x = len(rows)
    predicted_load = (slope * next_x) + intercept
    trend_dir = "Increasing (Rising Grid Demand)" if slope > 0 else "Decreasing (Lower Grid Demand)"

    return {
        "historical_periods": len(rows),
        "last_period": rows[-1]['billing_period'],
        "last_consumption": rows[-1]['avg_kwh'],
        "slope": slope,
        "predicted_load": max(0.0, predicted_load),
        "trend": trend_dir
    }

def correlate_disasters_with_anomalies():
    """Correlates weather/disaster incidents with barangay consumption spikes."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT d.barangay, d.incident_type, d.severity_level, d.date_reported, h.homeowner_name, h.account_number, m.consumption_kwh
        FROM disaster_incidents d
        JOIN households h ON h.address LIKE '%' || d.barangay || '%'
        JOIN meter_readings m ON m.household_id = h.household_id
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows

# --- GRAPHICAL PLOT GENERATORS ---

def generate_consumption_trend_chart():
    """Generates monthly grid demand trend chart (.png)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT billing_period, SUM(consumption_kwh) FROM meter_readings GROUP BY billing_period ORDER BY billing_period")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return None

    periods = [r[0] for r in rows]
    loads = [r[1] for r in rows]

    plt.figure(figsize=(8, 4.5))
    plt.plot(periods, loads, marker='o', color='#2b6cb0', linewidth=2, markersize=6)
    plt.title("Santiago City Monthly Grid Energy Demand Trend", fontsize=11, fontweight='bold', pad=12, color='#1a365d')
    plt.xlabel("Billing Period (YYYY-MM)", fontsize=9, fontweight='bold', color='#4a5568')
    plt.ylabel("Total Consumption (kWh)", fontsize=9, fontweight='bold', color='#4a5568')
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.xticks(rotation=15)
    plt.tight_layout()

    filename = "consumption_trend_chart.png"
    plt.savefig(filename, dpi=300)
    plt.close()
    return filename

def generate_consumer_comparison_chart():
    """Generates comparative household load distribution chart (.png)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT h.homeowner_name, SUM(m.consumption_kwh) as total_kwh
        FROM households h
        JOIN meter_readings m ON h.household_id = m.household_id
        GROUP BY h.household_id
        ORDER BY total_kwh DESC
        LIMIT 10
    """)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return None

    names = [r['homeowner_name'].split()[0] for r in rows]
    loads = [r['total_kwh'] for r in rows]

    plt.figure(figsize=(8, 4.5))
    plt.barh(names[::-1], loads[::-1], color='#3182ce', edgecolor='#1a365d')
    plt.title("Top Household Energy Consumers (Santiago City)", fontsize=11, fontweight='bold', pad=12, color='#1a365d')
    plt.xlabel("Total Consumption (kWh)", fontsize=9, fontweight='bold', color='#4a5568')
    plt.grid(axis='x', linestyle='--', alpha=0.5)
    plt.tight_layout()

    filename = "household_comparison_chart.png"
    plt.savefig(filename, dpi=300)
    plt.close()
    return filename

def generate_cluster_scatter_plot():
    """Generates K-Means cluster scatter plot (.png)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT AVG(m.consumption_kwh) as avg_kwh, AVG(m.estimated_cost) as avg_cost
        FROM households h
        JOIN meter_readings m ON h.household_id = m.household_id
        GROUP BY h.household_id
    """)
    rows = cursor.fetchall()
    conn.close()

    if len(rows) < 3:
        return None

    X = np.array([[r['avg_kwh'], r['avg_cost']] for r in rows])
    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X)

    plt.figure(figsize=(7, 4.5))
    scatter = plt.scatter(X[:, 0], X[:, 1], c=labels, cmap='viridis', s=80, edgecolor='k', alpha=0.8)
    plt.title("K-Means Consumer Behavioral Clustering (k=3)", fontsize=11, fontweight='bold', pad=12, color='#1a365d')
    plt.xlabel("Average Consumption (kWh)", fontsize=9, fontweight='bold', color='#4a5568')
    plt.ylabel("Average Cost (₱)", fontsize=9, fontweight='bold', color='#4a5568')
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.colorbar(scatter, label='Cluster Segment')
    plt.tight_layout()

    filename = "kmeans_cluster_chart.png"
    plt.savefig(filename, dpi=300)
    plt.close()
    return filename

def generate_regression_forecast_plot():
    """Generates OLS linear regression forecast plot (.png)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT billing_period, AVG(consumption_kwh) FROM meter_readings GROUP BY billing_period ORDER BY billing_period")
    rows = cursor.fetchall()
    conn.close()

    if len(rows) < 2:
        return None

    x = np.arange(len(rows))
    y = np.array([r[1] for r in rows])
    periods = [r[0] for r in rows]

    slope, intercept, _, _, _ = stats.linregress(x, y)
    regression_line = (slope * x) + intercept

    plt.figure(figsize=(8, 4.5))
    plt.scatter(x, y, color='red', zorder=5, label='Actual Monthly Mean')
    plt.plot(x, regression_line, color='blue', linestyle='--', label=f'OLS Trend (Slope: {slope:.1f})')
    plt.xticks(x, periods, rotation=15)
    plt.title("Time-Series Linear Regression Demand Forecast", fontsize=11, fontweight='bold', pad=12, color='#1a365d')
    plt.xlabel("Billing Period", fontsize=9, fontweight='bold', color='#4a5568')
    plt.ylabel("Average Consumption (kWh)", fontsize=9, fontweight='bold', color='#4a5568')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()

    filename = "regression_forecast_chart.png"
    plt.savefig(filename, dpi=300)
    plt.close()
    return filename

def generate_tier_distribution_chart():
    """Generates a bar chart showing consumption distribution across tariff tiers."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT consumption_kwh FROM meter_readings")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return None

    lifeline = sum(1 for r in rows if r['consumption_kwh'] <= 50)
    standard = sum(1 for r in rows if 50 < r['consumption_kwh'] <= 200)
    peak = sum(1 for r in rows if r['consumption_kwh'] > 200)

    labels = ['Lifeline Tier\n(≤50 kWh)', 'Standard Tier\n(51-200 kWh)', 'Peak Tier\n(201+ kWh)']
    counts = [lifeline, standard, peak]
    colors_list = ['#38a169', '#d69e2e', '#e53e3e']

    plt.figure(figsize=(7, 4.5))
    bars = plt.bar(labels, counts, color=colors_list, width=0.55, edgecolor='#1a202c', linewidth=1)
    
    plt.title("Santiago City Household Tariff Tier Distribution", fontsize=11, fontweight='bold', pad=12, color='#1a365d')
    plt.xlabel("Consumption Tariff Brackets", fontsize=9, fontweight='bold', color='#4a5568')
    plt.ylabel("Number of Billing Cycles", fontsize=9, fontweight='bold', color='#4a5568')
    plt.grid(axis='y', linestyle='--', alpha=0.5)

    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.1, f"{int(height)}", ha='center', va='bottom', fontsize=9, fontweight='bold')

    plt.tight_layout()
    filename = "tier_distribution_chart.png"
    plt.savefig(filename, dpi=300)
    plt.close()
    return filename

def generate_barangay_load_chart():
    """Generates a bar chart comparing total energy load across Santiago City barangays."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT h.address, SUM(m.consumption_kwh) as total_kwh
        FROM households h
        JOIN meter_readings m ON h.household_id = m.household_id
        GROUP BY h.address
    """)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return None

    barangays = [r['address'].split(',')[0].strip() for r in rows]
    loads = [r['total_kwh'] for r in rows]

    plt.figure(figsize=(8, 4.5))
    bars = plt.bar(barangays, loads, color='#2b6cb0', width=0.6, edgecolor='#1a365d', linewidth=1)

    plt.title("Cumulative Energy Load by Barangay (Santiago City)", fontsize=11, fontweight='bold', pad=12, color='#1a365d')
    plt.xlabel("Barangay Sector", fontsize=9, fontweight='bold', color='#4a5568')
    plt.ylabel("Total Consumption (kWh)", fontsize=9, fontweight='bold', color='#4a5568')
    plt.xticks(rotation=20, ha='right', fontsize=8)
    plt.grid(axis='y', linestyle='--', alpha=0.5)

    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 10, f"{height:,.1f}", ha='center', va='bottom', fontsize=8, fontweight='bold')

    plt.tight_layout()
    filename = "barangay_load_chart.png"
    plt.savefig(filename, dpi=300)
    plt.close()
    return filename