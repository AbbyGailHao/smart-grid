import os
import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.linear_model import LinearRegression
from database import get_connection

def generate_consumption_trend_chart():
    """
    Generates a graphical Matplotlib line chart showing total consumption across billing periods.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT billing_period, SUM(consumption_kwh) as total_kwh
        FROM meter_readings
        GROUP BY billing_period
        ORDER BY billing_period ASC
    """)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return None

    periods = [r['billing_period'] for r in rows]
    kwh_values = [r['total_kwh'] for r in rows]

    plt.figure(figsize=(8, 5))
    plt.plot(periods, kwh_values, marker='o', color='#1f77b4', linewidth=2.5, markersize=8)
    plt.title('Monthly Grid Electricity Consumption Trend', fontsize=14, fontweight='bold', pad=15)
    plt.xlabel('Billing Period (YYYY-MM)', fontsize=11)
    plt.ylabel('Total Consumption (kWh)', fontsize=11)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()

    chart_path = 'consumption_trend_chart.png'
    plt.savefig(chart_path, dpi=300)
    plt.close()
    return chart_path

def generate_consumer_comparison_chart():
    """
    Generates a graphical Matplotlib bar chart comparing total consumption across household accounts.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT h.account_number, COALESCE(SUM(r.consumption_kwh), 0) as total_kwh
        FROM households h
        LEFT JOIN meter_readings r ON h.household_id = r.household_id
        GROUP BY h.household_id
    """)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return None

    accounts = [r['account_number'] for r in rows]
    kwh_values = [r['total_kwh'] for r in rows]

    plt.figure(figsize=(8, 5))
    plt.bar(accounts, kwh_values, color='#2ca02c', width=0.5)
    plt.title('Total Consumption by Household Account', fontsize=14, fontweight='bold', pad=15)
    plt.xlabel('Account Number', fontsize=11)
    plt.ylabel('Total Consumption (kWh)', fontsize=11)
    plt.grid(axis='y', linestyle='--', alpha=0.6)
    plt.tight_layout()

    chart_path = 'household_comparison_chart.png'
    plt.savefig(chart_path, dpi=300)
    plt.close()
    return chart_path

def generate_cluster_scatter_plot():
    """
    Generates an unsupervised K-Means clustering scatter plot segmenting households 
    by average consumption and estimated cost.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT h.account_number, AVG(r.consumption_kwh) as avg_consumption, AVG(r.estimated_cost) as avg_cost
        FROM households h
        JOIN meter_readings r ON h.household_id = r.household_id
        GROUP BY h.household_id
    """)
    rows = cursor.fetchall()
    conn.close()

    if len(rows) < 3:
        return None

    X = np.array([[row['avg_consumption'], row['avg_cost']] for row in rows])
    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X)

    plt.figure(figsize=(8, 5))
    scatter = plt.scatter(X[:, 0], X[:, 1], c=labels, cmap='viridis', s=120, edgecolors='k')
    plt.title('K-Means Consumer Behavioral Segmentation', fontsize=14, fontweight='bold', pad=15)
    plt.xlabel('Average Consumption (kWh)', fontsize=11)
    plt.ylabel('Average Estimated Cost (₱)', fontsize=11)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.colorbar(scatter, label='Behavioral Tier')
    plt.tight_layout()

    chart_path = 'kmeans_cluster_chart.png'
    plt.savefig(chart_path, dpi=300)
    plt.close()
    return chart_path

def generate_regression_forecast_plot():
    """
    Generates a Time-Series Linear Regression plot showing historical data fit 
    and the projected next-month demand forecast.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT billing_period, SUM(consumption_kwh) as total_consumption
        FROM meter_readings
        GROUP BY billing_period
        ORDER BY billing_period ASC
    """)
    rows = cursor.fetchall()
    conn.close()

    if len(rows) < 2:
        return None

    X = np.array(range(len(rows))).reshape(-1, 1)
    y = np.array([row['total_consumption'] for row in rows])

    model = LinearRegression()
    model.fit(X, y)

    next_x = np.array([[len(rows)]])
    pred_y = model.predict(next_x)[0]

    all_X = np.append(X, next_x).reshape(-1, 1)
    all_y_pred = model.predict(all_X)

    periods = [r['billing_period'] for r in rows] + ['Next (Proj)']

    plt.figure(figsize=(8, 5))
    plt.scatter(range(len(rows)), y, color='blue', s=100, label='Historical Data', zorder=5)
    plt.scatter(len(rows), pred_y, color='red', s=140, marker='*', label=f'Forecast: {pred_y:.1f} kWh', zorder=5)
    plt.plot(all_X.flatten(), all_y_pred, color='orange', linestyle='--', linewidth=2, label='Linear Trend Fit')
    plt.xticks(range(len(periods)), periods, rotation=15)
    plt.title('Time-Series Linear Regression Demand Forecast', fontsize=14, fontweight='bold', pad=15)
    plt.xlabel('Billing Period', fontsize=11)
    plt.ylabel('Total Consumption (kWh)', fontsize=11)
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()

    chart_path = 'regression_forecast_chart.png'
    plt.savefig(chart_path, dpi=300)
    plt.close()
    return chart_path

def print_ascii_bar_chart():
    """
    Renders an ASCII bar chart directly in the terminal for instant CLI visualization.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT h.account_number, h.homeowner_name, COALESCE(SUM(r.consumption_kwh), 0) as total_kwh
        FROM households h
        LEFT JOIN meter_readings r ON h.household_id = r.household_id
        GROUP BY h.household_id
    """)
    rows = cursor.fetchall()
    conn.close()

    print("\n" + "=" * 65)
    print(" ASCII HOUSEHOLD CONSUMPTION COMPARISON CHART ".center(65, "="))
    if not rows:
        print(" No data available for charting.")
    else:
        max_kwh = max([r['total_kwh'] for r in rows]) if rows else 1
        max_bar_length = 30

        for r in rows:
            kwh = r['total_kwh']
            bar_len = int((kwh / max_kwh) * max_bar_length) if max_bar_length > 0 else 0
            bar = '█' * bar_len
            print(f" {r['account_number']} ({r['homeowner_name'][:12]:<12}) | {bar} {kwh:,.1f} kWh")
    print("=" * 65)