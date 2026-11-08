import os
import sys
from database import initialize_database
from functions import (
    fetch_all_households, fetch_all_readings, insert_household,
    insert_meter_reading, search_account_records, filter_readings_by_type,
    get_highest_consumer
)

from analytics import (
    get_summary_statistics, chart_monthly_trend, chart_connection_comparison,
    chart_consumption_cost_scatter, chart_consumption_distribution,
    chart_household_rankings, generate_all_charts, print_full_diagnostic_report
)

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

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def pause():
    input("\nPress Enter to continue...")

def print_header(title):
    clear_screen()
    print("=" * 75)
    print(f" {title.center(71)} ")
    print("=" * 75)

def display_menu():
    clear_screen()
    print("=" * 75)
    print(" HOUSEHOLD ELECTRICITY CONSUMPTION MONITOR (CLI) ".center(75))
    print("=" * 75)
    print(" [1] View All Registered Households")
    print(" [2] View All Meter Readings & Billing Logs")
    print(" [3] Add New Household Record")
    print(" [4] Record New Meter Reading")
    print(" [5] Search Records by Account Number (Continuous Loop)")
    print(" [6] View Advanced Statistical Summary")
    print(" [7] Filter Readings by Connection Type (Continuous Loop)")
    print(" [8] Identify Highest Consuming Household")
    print(" [9] Generate Diagnostic Report Charts (Choose & Export)")
    print(" [10] Exit Program")
    print("=" * 75)

def cli_view_households():
    print_header("REGISTERED HOUSEHOLDS")
    rows = fetch_all_households()
    if not rows:
        print("\n[INFO] No households found in the database.")
        pause()
        return
    
    header = f"{'ID':<4} | {'Account No.':<12} | {'Homeowner Name':<20} | {'Address':<30} | {'Type':<12}"
    print(header)
    print("-" * len(header))
    for r in rows:
        print(f"{r[0]:<4} | {r[1]:<12} | {r[2]:<20} | {r[3]:<30} | {r[4]:<12}")
    print("-" * len(header))
    pause()

def cli_view_readings():
    print_header("METER READINGS & BILLING LOGS")
    rows = fetch_all_readings()
    if not rows:
        print("\n[INFO] No meter readings found in the database.")
        pause()
        return

    for r in rows:
        print(f"Reading ID: {r[0]} | Account: {r[1]} ({r[2]})")
        print(f"  Billing Period: {r[3]} | Date: {r[9]}")
        print(f"  Previous: {r[4]} kWh | Current: {r[5]} kWh | Consumption: {r[6]:.1f} kWh")
        print(f"  Rate: ₱{r[7]:.2f}/kWh | Estimated Cost: ₱{r[8]:.2f}")
        print("-" * 60)
    pause()

def cli_add_household():
    print_header("ADD NEW HOUSEHOLD")
    try:
        account_number = input("Enter Account Number (e.g., ACC-8011): ").strip()
        homeowner_name = input("Enter Homeowner's Full Name: ").strip()
        address = input("Enter Address (e.g., Brgy. Baluarte, Santiago City): ").strip()
        connection_type = input("Enter Connection Type (Residential/Commercial): ").strip()

        if not all([account_number, homeowner_name, address, connection_type]):
            print("\n[ERROR] All fields are required.")
            pause()
            return

        success, msg = insert_household(account_number, homeowner_name, address, connection_type)
        print(f"\n[{'SUCCESS' if success else 'ERROR'}] {msg}")
    except Exception as e:
        print(f"\n[ERROR] {e}")
    pause()

def cli_add_meter_reading():
    print_header("RECORD NEW METER READING")
    households = fetch_all_households()
    if not households:
        print("\n[ERROR] Add a household first.")
        pause()
        return

    print(f"{'ID':<4} | {'Account No.':<12} | {'Homeowner Name':<20}")
    print("-" * 40)
    for h in households:
        print(f"{h[0]:<4} | {h[1]:<12} | {h[2]:<20}")
    print("-" * 40)

    try:
        household_id = int(input("\nEnter Household ID: ").strip())
        billing_period = input("Enter Billing Period (YYYY-MM): ").strip()
        previous_reading = float(input("Enter Previous Reading (kWh): ").strip())
        current_reading = float(input("Enter Current Reading (kWh): ").strip())
        rate_per_kwh = float(input("Enter Rate per kWh (₱): ").strip())
        reading_date = input("Enter Reading Date (YYYY-MM-DD): ").strip()

        success, msg = insert_meter_reading(household_id, billing_period, previous_reading, current_reading, rate_per_kwh, reading_date)
        print(f"\n[{'SUCCESS' if success else 'ERROR'}] {msg}")
    except ValueError:
        print("\n[ERROR] Invalid numerical input.")
    pause()

def cli_search_by_account():
    while True:
        print_header("SEARCH BY ACCOUNT NUMBER")
        acc_query = input("Enter Account Number (or type 'back'): ").strip()
        if acc_query.lower() in ['back', 'exit', '']: break

        rows = search_account_records(acc_query)
        if not rows:
            print(f"\n[INFO] No records found for '{acc_query}'\n")
        else:
            print(f"\nResults for '{acc_query}':")
            print("=" * 70)
            for r in rows:
                print(f"Homeowner: {r[1]} | Address: {r[2]} | Type: {r[3]}")
                if r[4]: print(f"  Period: {r[4]} | Usage: {r[7]:.1f} kWh | Cost: ₱{r[9]:.2f}")
                print("-" * 70)
        if input("\nSearch again? (y/n): ").strip().lower() != 'y': break

def cli_analytical_summary():
    print_header("ADVANCED STATISTICAL SUMMARY")
    stats = get_summary_statistics()
    if not stats:
        print("\n[INFO] No analytical data available.")
        pause()
        return

    print(f"Total Households          : {stats['total_households']}")
    print(f"Total Reading Logs        : {stats['total_readings']}")
    print("-" * 55)
    print(f"Total Cumulative Usage    : {stats['total_consumption']:,.2f} kWh")
    print(f"Mean Monthly Consumption  : {stats['mean_consumption']:,.2f} kWh")
    print(f"Median Monthly Consumption: {stats['median_consumption']:,.2f} kWh")
    print(f"Variance                  : {stats['variance_consumption']:,.2f}")
    print(f"Standard Deviation        : {stats['stdev_consumption']:,.2f} kWh")
    print(f"Min Consumption           : {stats['min_consumption']:,.2f} kWh")
    print(f"Max Consumption           : {stats['max_consumption']:,.2f} kWh")
    print(f"1st Quartile (Q1)         : {stats['q1']:,.2f} kWh")
    print(f"3rd Quartile (Q3)         : {stats['q3']:,.2f} kWh")
    print(f"Interquartile Range (IQR) : {stats['iqr']:,.2f} kWh")
    print(f"Distribution Skewness     : {stats['skewness']:.3f}")
    print("-" * 55)
    print(f"Average Electricity Rate  : ₱{stats['avg_rate']:.2f} / kWh")
    print(f"Mean Estimated Cost       : ₱{stats['mean_cost']:,.2f}")
    print(f"Total Projected Revenue   : ₱{stats['total_cost']:,.2f}")
    print("=" * 55)
    pause()

def cli_filter_by_connection_type():
    while True:
        print_header("FILTER READINGS BY CONNECTION TYPE")
        ctype = input("Enter Type ('Residential' or 'Commercial', or 'back'): ").strip().capitalize()
        if ctype.lower() in ['back', 'exit', '']: break
        if ctype not in ["Residential", "Commercial"]:
            print("\n[ERROR] Invalid type.\n")
            continue

        rows = filter_readings_by_type(ctype)
        if not rows: print(f"\n[INFO] No records found for {ctype}\n")
        else:
            print(f"\nReadings for {ctype}:")
            header = f"{'Account No.':<12} | {'Homeowner':<20} | {'Period':<10} | {'Usage (kWh)':<12} | {'Cost (₱)':<10}"
            print(header)
            print("-" * len(header))
            for r in rows:
                print(f"{r[0]:<12} | {r[1]:<20} | {r[3]:<10} | {r[4]:<12.1f} | ₱{r[5]:<10.2f}")
        if input("\nFilter again? (y/n): ").strip().lower() != 'y': break

def cli_highest_consuming_household():
    print_header("HIGHEST CONSUMING HOUSEHOLD")
    row = get_highest_consumer()
    if not row:
        print("\n[INFO] No reading data available.")
        pause()
        return
    print(f"Account Number  : {row[0]}")
    print(f"Homeowner Name  : {row[1]}")
    print(f"Address         : {row[2]}")
    print(f"Connection Type : {row[3]}")
    print(f"Total Usage     : {row[4]:,.2f} kWh")
    print(f"Total Cost      : ₱{row[5]:,.2f}")
    print("=" * 45)
    pause()

def cli_chart_menu():
    while True:
        print_header("DIAGNOSTIC REPORT CHARTS (SAVED TO /charts)")
        print(" [1] Monthly Consumption Trend")
        print(" [2] Connection Type Comparison")
        print(" [3] Consumption vs. Estimated Cost Scatter Plot")
        print(" [4] Consumption Frequency Histogram")
        print(" [5] Household Consumption Rankings (Horizontal Bar)")
        print(" [6] GENERATE ALL CHARTS")
        print(" [7] Return to Main Menu")
        print("-" * 50)
        
        choice = input("Select chart option (1-7): ").strip()
        success = False
        
        if choice == '1':
            success = chart_monthly_trend()
            name = "monthly_consumption_trend.png"
        elif choice == '2':
            success = chart_connection_comparison()
            name = "connection_type_comparison.png"
        elif choice == '3':
            success = chart_consumption_cost_scatter()
            name = "consumption_vs_cost_scatter.png"
        elif choice == '4':
            success = chart_consumption_distribution()
            name = "consumption_histogram.png"
        elif choice == '5':
            success = chart_household_ranking()
            name = "household_consumption_ranking.png"
        elif choice == '6':
            success = generate_all_charts()
            name = "All 5 charts"
        elif choice == '7':
            break
        else:
            print("\n[ERROR] Invalid selection.")
            pause()
            continue

        if success:
            print(f"\n[SUCCESS] Saved successfully to the 'charts/' folder: {name}")
        else:
            print("\n[ERROR] Failed to generate chart. Ensure database has valid reading records.")
        pause()

def main():
    initialize_database()
    while True:
        display_menu()
        choice = input("Enter your choice (1-10): ").strip()
        
        if choice == '1': cli_view_households()
        elif choice == '2': cli_view_readings()
        elif choice == '3': cli_add_household()
        elif choice == '4': cli_add_meter_reading()
        elif choice == '5': cli_search_by_account()
        elif choice == '6': cli_analytical_summary()
        elif choice == '7': cli_filter_by_connection_type()
        elif choice == '8': cli_highest_consuming_household()
        elif choice == '9': cli_chart_menu()
        elif choice == '10':
            clear_screen()
            print("Exiting program. Thank you!")
            sys.exit(0)
        else:
            print("\n[ERROR] Invalid choice.")
            pause()

if __name__ == "__main__":
    main()