import sqlite3
import matplotlib.pyplot as plt
import statistics
import os

DB_NAME = "electricity_monitor.db"
CHARTS_DIR = "charts"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def ensure_charts_dir():
    """Ensures the output charts directory exists."""
    if not os.path.exists(CHARTS_DIR):
        os.makedirs(CHARTS_DIR)

def get_summary_statistics():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            COUNT(DISTINCT h.household_id) as total_households,
            COUNT(r.reading_id) as total_readings,
            SUM(r.consumption_kwh) as total_consumption,
            AVG(r.consumption_kwh) as mean_consumption,
            MIN(r.consumption_kwh) as min_consumption,
            MAX(r.consumption_kwh) as max_consumption,
            SUM(r.estimated_cost) as total_cost,
            AVG(r.rate_per_kwh) as avg_rate
        FROM households h
        LEFT JOIN meter_readings r ON h.household_id = r.household_id
    """)
    row = cursor.fetchone()
    
    cursor.execute("SELECT consumption_kwh FROM meter_readings WHERE consumption_kwh IS NOT NULL")
    consumptions = sorted([r[0] for r in cursor.fetchall()])
    
    cursor.execute("SELECT estimated_cost FROM meter_readings WHERE estimated_cost IS NOT NULL")
    costs = sorted([r[0] for r in cursor.fetchall()])
    conn.close()

    if not row or row[0] == 0 or not consumptions:
        return None

    n = len(consumptions)
    median_consumption = statistics.median(consumptions)
    variance_consumption = statistics.variance(consumptions) if n > 1 else 0.0
    stdev_consumption = statistics.stdev(consumptions) if n > 1 else 0.0
    
    # Quartiles
    q1 = consumptions[n // 4]
    q3 = consumptions[(3 * n) // 4]
    iqr = q3 - q1

    # Skewness approximation (Pearson's median skewness: 3 * (mean - median) / stdev)
    skewness = (3 * (row[3] - median_consumption) / stdev_consumption) if stdev_consumption > 0 else 0.0

    return {
        "total_households": row[0],
        "total_readings": row[1],
        "total_consumption": row[2] or 0.0,
        "mean_consumption": row[3] or 0.0,
        "median_consumption": median_consumption,
        "variance_consumption": variance_consumption,
        "stdev_consumption": stdev_consumption,
        "min_consumption": row[4] or 0.0,
        "max_consumption": row[5] or 0.0,
        "q1": q1,
        "q3": q3,
        "iqr": iqr,
        "skewness": skewness,
        "total_cost": row[6] or 0.0,
        "avg_rate": row[7] or 0.0,
        "mean_cost": statistics.mean(costs) if costs else 0.0
    }

def chart_monthly_trend():
    ensure_charts_dir()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT billing_period, SUM(consumption_kwh)
        FROM meter_readings GROUP BY billing_period ORDER BY billing_period ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    if not rows: return False

    plt.figure(figsize=(8, 5))
    plt.plot([r[0] for r in rows], [r[1] for r in rows], marker='o', color='#2980b9', linewidth=2.5)
    plt.title("System-Wide Monthly Consumption Trend", fontweight='bold')
    plt.xlabel("Billing Period")
    plt.ylabel("Total Consumption (kWh)")
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    plt.savefig(os.path.join(CHARTS_DIR, "monthly_consumption_trend.png"), dpi=300)
    plt.close()
    return True

def chart_connection_comparison():
    ensure_charts_dir()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT h.connection_type, SUM(r.consumption_kwh)
        FROM meter_readings r JOIN households h ON r.household_id = h.household_id
        GROUP BY h.connection_type
    """)
    rows = cursor.fetchall()
    conn.close()
    if not rows: return False

    plt.figure(figsize=(6, 5))
    bars = plt.bar([r[0] for r in rows], [r[1] for r in rows], color=['#27ae60', '#e74c3c'], width=0.4)
    plt.title("Consumption by Connection Type", fontweight='bold')
    plt.xlabel("Connection Type")
    plt.ylabel("Total kWh")
    plt.grid(axis='y', linestyle='--', alpha=0.6)
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2.0, yval + 50, f"{yval:,.1f}", ha='center', va='bottom')
    plt.tight_layout()
    plt.savefig(os.path.join(CHARTS_DIR, "connection_type_comparison.png"), dpi=300)
    plt.close()
    return True

def chart_consumption_cost_scatter():
    ensure_charts_dir()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT consumption_kwh, estimated_cost FROM meter_readings")
    rows = cursor.fetchall()
    conn.close()
    if not rows: return False

    plt.figure(figsize=(7, 5))
    plt.scatter([r[0] for r in rows], [r[1] for r in rows], color='#8e44ad', alpha=0.7, edgecolors='k', s=70)
    plt.title("Consumption (kWh) vs. Estimated Cost (₱)", fontweight='bold')
    plt.xlabel("Consumption (kWh)")
    plt.ylabel("Cost (₱)")
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    plt.savefig(os.path.join(CHARTS_DIR, "consumption_vs_cost_scatter.png"), dpi=300)
    plt.close()
    return True

def chart_consumption_distribution():
    ensure_charts_dir()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT consumption_kwh FROM meter_readings")
    rows = [r[0] for r in cursor.fetchall()]
    conn.close()
    if not rows: return False

    plt.figure(figsize=(7, 5))
    plt.hist(rows, bins=8, color='#e67e22', edgecolor='black', alpha=0.8)
    plt.title("Distribution of Household Monthly Consumption", fontweight='bold')
    plt.xlabel("Consumption (kWh)")
    plt.ylabel("Frequency")
    plt.grid(axis='y', linestyle='--', alpha=0.6)
    plt.tight_layout()
    plt.savefig(os.path.join(CHARTS_DIR, "consumption_histogram.png"), dpi=300)
    plt.close()
    return True

def chart_household_rankings():
    ensure_charts_dir()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT h.account_number, SUM(r.consumption_kwh) as total_usage
        FROM meter_readings r JOIN households h ON r.household_id = h.household_id
        GROUP BY h.household_id ORDER BY total_usage ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    if not rows: return False

    plt.figure(figsize=(8, 5))
    plt.barh([r[0] for r in rows], [r[1] for r in rows], color='#34495e')
    plt.title("Total Consumption Ranking per Account", fontweight='bold')
    plt.xlabel("Total Consumption (kWh)")
    plt.ylabel("Account Number")
    plt.grid(axis='x', linestyle='--', alpha=0.6)
    plt.tight_layout()
    plt.savefig(os.path.join(CHARTS_DIR, "household_consumption_ranking.png"), dpi=300)
    plt.close()
    return True

def generate_all_charts():
    results = [
        chart_monthly_trend(),
        chart_connection_comparison(),
        chart_consumption_cost_scatter(),
        chart_consumption_distribution(),
        chart_household_rankings()
    ]
    return all(results)

def print_full_diagnostic_report():
    """Prints a complete text-based diagnostic summary report."""
    stats = get_summary_statistics()
    if not stats:
        print("\n[INFO] No analytical data available to print.")
        return False

    print("\n" + "=" * 65)
    print(" HOUSEHOLD ELECTRICITY CONSUMPTION - FULL DIAGNOSTIC REPORT ".center(65))
    print("=" * 65)
    print(f" Dataset Scope")
    print(f" - Registered Households      : {stats['total_households']}")
    print(f" - Total Meter Reading Logs   : {stats['total_readings']}")
    print("-" * 65)
    print(f" Consumption Statistics (kWh)")
    print(f" - Cumulative Consumption     : {stats['total_consumption']:,.2f} kWh")
    print(f" - Mean (Average) Usage       : {stats['mean_consumption']:,.2f} kWh")
    print(f" - Median Usage               : {stats['median_consumption']:,.2f} kWh")
    print(f" - Variance                   : {stats['variance_consumption']:,.2f}")
    print(f" - Standard Deviation         : {stats['stdev_consumption']:,.2f} kWh")
    print(f" - Minimum Usage              : {stats['min_consumption']:,.2f} kWh")
    print(f" - Maximum Usage              : {stats['max_consumption']:,.2f} kWh")
    print(f" - 1st Quartile (Q1)          : {stats['q1']:,.2f} kWh")
    print(f" - 3rd Quartile (Q3)          : {stats['q3']:,.2f} kWh")
    print(f" - Interquartile Range (IQR)  : {stats['iqr']:,.2f} kWh")
    print(f" - Distribution Skewness      : {stats['skewness']:.3f}")
    print("-" * 65)
    print(f" Financial Metrics")
    print(f" - Average Electricity Rate   : ₱{stats['avg_rate']:.2f} / kWh")
    print(f" - Mean Estimated Cost        : ₱{stats['mean_cost']:,.2f}")
    print(f" - Total Projected Revenue    : ₱{stats['total_cost']:,.2f}")
    print("=" * 65)
    return True