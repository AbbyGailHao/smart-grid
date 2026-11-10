print("CURRENTLY RUNNING FILE:", __file__)
import os
import sys
import webbrowser
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text
from rich.markup import escape

from database import get_connection, init_db, log_audit_event
from analytics import (
    get_summary_statistics, 
    detect_consumption_anomalies, 
    perform_consumer_clustering, 
    run_consumption_hypothesis_test, 
    forecast_next_month_consumption,
    correlate_disasters_with_anomalies,
    generate_consumption_trend_chart,
    generate_consumer_comparison_chart,
    generate_cluster_scatter_plot,
    generate_regression_forecast_plot,
    generate_tier_distribution_chart,
    generate_barangay_load_chart,
    print_full_diagnostic_report,
    run_independent_ttest,
    run_disaster_correlation
)
from mapping import generate_household_map
from visualizer import (
    generate_consumption_trend_chart, 
    generate_consumer_comparison_chart, 
    generate_cluster_scatter_plot,
    generate_regression_forecast_plot,
    print_ascii_bar_chart
)
from reporter import compile_executive_report
from utils import clear_screen, pause, get_secure_choice
from functions import generate_household_map

console = Console()

def seed_sample_data_if_empty():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM households")
    if cursor.fetchone()[0] == 0:
        sample_households = [
            ("ACC-1001", "Jessica Lagmay", "Baluarte, Santiago City", "Residential"),
            ("ACC-1002", "Aldwyn Delmendo", "Centro, Santiago City", "Commercial"),
            ("ACC-1003", "Abegail Domingo", "Dubinan East, Santiago City", "Residential"),
            ("ACC-1004", "Kristine De Vera", "Rizal, Santiago City", "Residential"),
        ]
        cursor.executemany("""
            INSERT INTO households (account_number, homeowner_name, address, connection_type, status, online_billing)
            VALUES (?, ?, ?, ?, 'Active', 1)
        """, sample_households)
        
        cursor.execute("SELECT household_id FROM households")
        h_ids = [row[0] for row in cursor.fetchall()]
        
        sample_readings = [
            (h_ids[0], "2026-08", 145.5, calculate_tiered_cost(145.5, "Residential")),
            (h_ids[0], "2026-09", 160.0, calculate_tiered_cost(160.0, "Residential")),
            (h_ids[0], "2026-10", 215.2, calculate_tiered_cost(215.2, "Residential")),
            (h_ids[1], "2026-08", 450.0, calculate_tiered_cost(450.0, "Commercial")),
            (h_ids[1], "2026-09", 480.0, calculate_tiered_cost(480.0, "Commercial")),
            (h_ids[2], "2026-09", 42.0, calculate_tiered_cost(42.0, "Residential")), # Lifeline tier test
            (h_ids[3], "2026-09", 110.0, calculate_tiered_cost(110.0, "Residential")),
        ]
        cursor.executemany("""
            INSERT INTO meter_readings (household_id, billing_period, consumption_kwh, estimated_cost)
            VALUES (?, ?, ?, ?)
        """, sample_readings)

        cursor.execute("""
            INSERT INTO disaster_incidents (barangay, incident_type, severity_level, date_reported)
            VALUES ('Baluarte', 'Flash Flood / Severe Storm', 'High', '2026-10-15')
        """)
        conn.commit()
        log_audit_event("SYSTEM_INIT", "SYSTEM", "Database seeded with default enterprise benchmarks and audit logs.")
    conn.close()

def manage_households_crud():
    while True:
        clear_screen()
        console.print(Panel("[bold cyan]HOUSEHOLD RECORD MANAGEMENT (CRUD & AUDIT TRAIL)[/bold cyan]", expand=False))
        console.print(" [1] Add New Household Record (Create)")
        console.print(" [2] View & Search All Household Records (Read)")
        console.print(" [3] Update Existing Household Record (Update)")
        console.print(" [4] Delete Household Record (Delete with Confirmation)")
        console.print(" [5] View Immutable Audit Logs")
        console.print(" [6] Back to Admin Panel")
        
        choice = get_secure_choice("Select option (1-6): ", 1, 6)
        conn = get_connection()
        cursor = conn.cursor()
        
        if choice == 1:
            console.print("\n[bold green]--- ADD NEW HOUSEHOLD ---[/bold green]")
            acc_no = Prompt.ask("Enter Account Number (e.g., ACC-1005)").strip()
            name = Prompt.ask("Enter Homeowner Name").strip()
            address = Prompt.ask("Enter Address / Barangay").strip()
            ctype = Prompt.ask("Enter Connection Type", choices=["Residential", "Commercial"], default="Residential")
            
            try:
                cursor.execute("""
                    INSERT INTO households (account_number, homeowner_name, address, connection_type, status, online_billing)
                    VALUES (?, ?, ?, ?, 'Active', 1)
                """, (acc_no, name, address, ctype))
                conn.commit()
                log_audit_event("CREATE_HOUSEHOLD", acc_no, f"Added household {name} in {address}")
                console.print("\n[bold green][SUCCESS] New household record added & audit logged![/bold green]")
            except Exception as e:
                console.print(f"\n[bold red][ERROR] Failed: {e}[/bold red]")
            pause()
            
        elif choice == 2:
            cursor.execute("SELECT * FROM households")
            rows = cursor.fetchall()
            table = Table(title="Registered Household Registry")
            table.add_column("ID", style="dim")
            table.add_column("Account", style="cyan")
            table.add_column("Name", style="bold")
            table.add_column("Address")
            table.add_column("Type", style="magenta")
            table.add_column("Status", style="green")
            
            for r in rows:
                table.add_row(str(r['household_id']), r['account_number'], r['homeowner_name'], r['address'], r['connection_type'], r['status'])
            console.print(table)
            pause()
            
        elif choice == 3:
            acc_no = Prompt.ask("Enter Account Number to update").strip()
            cursor.execute("SELECT * FROM households WHERE account_number = ?", (acc_no,))
            hh = cursor.fetchone()
            if not hh:
                console.print(f"\n[bold red][ERROR] Account '{acc_no}' not found.[/bold red]")
            else:
                new_name = Prompt.ask(f"Enter new name [{hh['homeowner_name']}]", default=hh['homeowner_name']).strip()
                new_addr = Prompt.ask(f"Enter new address [{hh['address']}]", default=hh['address']).strip()
                new_status = Prompt.ask(f"Enter status", choices=["Active", "Inactive", "Overdue"], default=hh['status']).strip()
                
                cursor.execute("""
                    UPDATE households SET homeowner_name = ?, address = ?, status = ?
                    WHERE account_number = ?
                """, (new_name, new_addr, new_status, acc_no))
                conn.commit()
                log_audit_event("UPDATE_HOUSEHOLD", acc_no, f"Updated record for {new_name}")
                console.print("\n[bold green][SUCCESS] Record updated & audit logged![/bold green]")
            pause()
            
        elif choice == 4:
            acc_no = Prompt.ask("Enter Account Number to delete").strip()
            cursor.execute("SELECT * FROM households WHERE account_number = ?", (acc_no,))
            hh = cursor.fetchone()
            if not hh:
                console.print(f"\n[bold red][ERROR] Account not found.[/bold red]")
            else:
                confirm = Prompt.ask(f"Delete {hh['homeowner_name']} ({acc_no})? Cascades all readings.", choices=["y", "n"], default="n")
                if confirm == 'y':
                    cursor.execute("DELETE FROM households WHERE account_number = ?", (acc_no,))
                    conn.commit()
                    log_audit_event("DELETE_HOUSEHOLD", acc_no, f"Deleted household {hh['homeowner_name']}")
                    console.print("\n[bold green][SUCCESS] Record deleted & audit logged.[/bold green]")
                else:
                    console.print("\n[yellow]Deletion cancelled.[/yellow]")
            pause()
            
        elif choice == 5:
                cursor.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 15")
                logs = cursor.fetchall()
                table = Table(title="Immutable Administrative Audit Trail")
                table.add_column("Log ID", style="dim")
                table.add_column("Timestamp", style="cyan")
                table.add_column("Action", style="bold magenta")
                table.add_column("Target", style="yellow")
                table.add_column("Details")
                
                for l in logs:
                    # Convert sqlite3.Row to dict safely to use .get()
                    row_dict = dict(l)
                    
                    log_id = str(row_dict.get('log_id', 'N/A'))
                    timestamp = str(row_dict.get('timestamp', 'N/A'))
                    
                    # Check for either operator_action or action column names
                    action = str(row_dict.get('operator_action') or row_dict.get('action') or 'N/A')
                    
                    # Check for either target_account or target column names
                    target = str(row_dict.get('target_account') or row_dict.get('target') or 'SYS')
                    
                    details = str(row_dict.get('details', 'N/A'))
                    
                    table.add_row(log_id, timestamp, action, target, details)
                    
                console.print(table)
                pause()
            
        elif choice == 6:
            conn.close()
            break
        conn.close()

def admin_panel():
    while True:
        try:
            clear_screen()
            console.print(Panel("[bold yellow]ADMINISTRATOR / GRID OPERATOR CONTROL CENTER[/bold yellow]", expand=False))
            console.print(" [1] Live Grid Health & Status Dashboard")
            console.print(" [2] Household Management & Audit Trail (CRUD & Logs)")
            console.print(" [3] Telemetry Ingestion & Tiered Billing Engine")
            console.print(" [4] Analytics, Machine Learning & Statistical Diagnostics")
            console.print(" [5] Geospatial GIS Mapping & Disaster Resilience (DRRM)")
            console.print(" [6] Data Visualization & Executive Report Compilers")
            console.print(" [7] Return to Main Menu")
            
            choice = get_secure_choice("Select option (1-7): ", 1, 7)
            
            if choice == 1:
                clear_screen()
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM households")
                h_count = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM meter_readings")
                r_count = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM disaster_incidents")
                d_count = cursor.fetchone()[0]
                cursor.execute("SELECT COALESCE(SUM(estimated_cost), 0) FROM meter_readings")
                total_revenue = cursor.fetchone()[0]
                conn.close()

                console.print(Panel("[bold green]SANTIAGO CITY SMART-GRID HEALTH MONITOR[/bold green]", expand=False))
                console.print(f" • Registered Grid Households : [cyan]{h_count}[/cyan]")
                console.print(f" • Total Telemetry Readings   : [cyan]{r_count}[/cyan]")
                console.print(f" • Active Disaster / Hazards  : [red]{d_count} reported[/red]")
                console.print(f" • Cumulative Billed Revenue  : [green]₱{total_revenue:,.2f}[/green]")
                console.print(" • System Core Integrity      : [bold green]OPTIMAL (100% Secure Audit Trail Active)[/bold green]")
                pause()

            elif choice == 2:
                manage_households_crud()
                
            elif choice == 3:
                clear_screen()
                console.print("[bold cyan]--- TELEMETRY & TIERED TARIFF INGESTION ---[/bold cyan]")
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT household_id, account_number, homeowner_name, connection_type FROM households")
                hs = cursor.fetchall()
                
                if not hs:
                    console.print("[yellow]No households available. Please register households first.[/yellow]")
                    conn.close()
                    pause()
                    continue
                    
                for h in hs:
                    console.print(f" ID: {h['household_id']} | Acc: {h['account_number']} | Name: {h['homeowner_name']} ({h['connection_type']})")
                
                try:
                    h_id = int(Prompt.ask("\nEnter Household ID").strip())
                    period = Prompt.ask("Enter Billing Period (YYYY-MM)").strip()
                    kwh = float(Prompt.ask("Enter Consumption (kWh)").strip())
                    
                    if kwh < 0:
                        raise ValueError("Consumption cannot be negative.")
                    
                    cursor.execute("SELECT connection_type FROM households WHERE household_id = ?", (h_id,))
                    ctype_row = cursor.fetchone()
                    if not ctype_row:
                        raise ValueError("Invalid Household ID selected.")
                    ctype = ctype_row[0]
                    
                    cost = calculate_tiered_cost(kwh, ctype)
                    cursor.execute("""
                        INSERT INTO meter_readings (household_id, billing_period, consumption_kwh, estimated_cost)
                        VALUES (?, ?, ?, ?)
                    """, (h_id, period, kwh, cost))
                    conn.commit()
                    log_audit_event("RECORD_TELEMETRY", str(h_id), f"Recorded {kwh} kWh for {period} (Tiered Cost: ₱{cost})")
                    console.print(f"\n[bold green][SUCCESS] Telemetry saved! Tiered Cost: ₱{cost:,.2f}[/bold green]")
                except Exception as e:
                    console.print(f"\n[bold red][ERROR] Telemetry ingestion failed: {e}[/bold red]")
                conn.close()
                pause()
                
            elif choice == 4:
                while True:
                    clear_screen()
                    console.print(Panel("[bold magenta]--- ANALYTICS, ML & STATISTICAL DIAGNOSTICS ---[/bold magenta]", expand=False))
                    console.print(" [1] Print Summary Statistics & IQR Outlier Report")
                    console.print(" [2] Run Anomaly / Tampering Detection")
                    console.print(" [3] Run K-Means Behavioral Clustering")
                    console.print(" [4] Run Independent T-Test (Residential vs. Commercial)")
                    console.print(" [5] Run Time-Series Linear Regression Forecast")
                    console.print(" [6] Cross-Domain Disaster vs. Consumption Correlation")
                    console.print(" [7] Back to Admin Menu")
                    
                    sub = get_secure_choice("Select option (1-7): ", 1, 7)
                    if sub == 1:
                        try:
                            print_full_diagnostic_report()
                        except Exception as e:
                            console.print(f"[bold red][ERROR] {e}[/bold red]")
                        pause()
                    elif sub == 2:
                        try:
                            anomalies, threshold = detect_consumption_anomalies()
                            console.print(f"\n[bold yellow]Threshold: {threshold:,.2f} kWh | Flagged Anomalies: {len(anomalies)}[/bold yellow]")
                            if anomalies:
                                table = Table(title="Detected Consumption Outliers")
                                table.add_column("Account", style="cyan")
                                table.add_column("Homeowner", style="bold")
                                table.add_column("Consumption", justify="right", style="red")
                                for a in anomalies:
                                    table.add_row(a['account_number'], a['homeowner_name'], f"{a['consumption_kwh']:,.2f} kWh")
                                console.print(table)
                            else:
                                console.print("[green]No anomalies detected within current threshold.[/green]")
                        except Exception as e:
                            console.print(f"[bold red][ERROR] {e}[/bold red]")
                        pause()
                    elif sub == 3:
                        try:
                            clusters = perform_consumer_clustering()
                            if isinstance(clusters, str):
                                console.print(f"[yellow]{clusters}[/yellow]")
                            else:
                                table = Table(title="K-Means Behavioral Segmentation (k=3)")
                                table.add_column("Account", style="cyan")
                                table.add_column("Homeowner", style="bold")
                                table.add_column("Cluster Assignment", justify="center", style="magenta")
                                for c in clusters:
                                    table.add_row(c['account_number'], c['homeowner_name'], c['cluster'])
                                console.print(table)
                        except Exception as e:
                            console.print(f"[bold red][ERROR] {e}[/bold red]")
                        pause()
                    elif sub == 4:
                        try:
                            res = run_independent_ttest()
                            if res:
                                console.print(Panel(f"[bold cyan]INFERENTIAL STATISTICS: INDEPENDENT T-TEST[/bold cyan]\n"
                                                    f" • T-Statistic : {res['t_statistic']:.4f}\n"
                                                    f" • P-Value     : {res['p_value']:.5f}\n"
                                                    f" • Significant : [bold {'green' if res['significant'] else 'yellow'}]{res['significant']}[/bold]", expand=False))
                            else:
                                console.print("[yellow]Insufficient data for hypothesis testing.[/yellow]")
                        except Exception as e:
                            console.print(f"[bold red][ERROR] {e}[/bold red]")
                        pause()
                    elif sub == 5:
                        try:
                            forecast = forecast_next_month_consumption()
                            if isinstance(forecast, dict):
                                console.print(Panel(f"[bold green]TIME-SERIES LINEAR REGRESSION FORECAST[/bold green]\n"
                                                    f" • Historical Periods : {forecast['historical_periods']}\n"
                                                    f" • Last Period Usage  : {forecast['last_consumption']:,.2f} kWh\n"
                                                    f" • Trend Slope        : +{forecast['slope']:.2f} kWh/period\n"
                                                    f" • Projected Demand   : [bold cyan]{forecast['predicted_load']:,.2f} kWh[/bold cyan] ({forecast['trend']})", expand=False))
                            else:
                                console.print(f"[yellow]{forecast}[/yellow]")
                        except Exception as e:
                            console.print(f"[bold red][ERROR] {e}[/bold red]")
                        pause()
                    elif sub == 6:
                        try:
                            correlations = run_disaster_correlation()
                            if correlations:
                                table = Table(title="Disaster & Consumption Correlation Feed")
                                table.add_column("Barangay", style="cyan")
                                table.add_column("Incident", style="red")
                                table.add_column("Severity", justify="center")
                                table.add_column("Homeowner", style="bold")
                                table.add_column("Usage", justify="right")
                                for c in correlations:
                                    table.add_row(c['barangay'], c['incident'], c['severity'], c['homeowner'], f"{c['consumption']:,.1f} kWh")
                                console.print(table)
                            else:
                                console.print("[yellow]No cross-domain correlations found.[/yellow]")
                        except Exception as e:
                            console.print(f"[bold red][ERROR] {e}[/bold red]")
                        pause()
                    elif sub == 7:
                        break
                        
            elif choice == 5:
                while True:
                    clear_screen()
                    console.print(Panel("[bold blue]--- GEOSPATIAL GIS & DISASTER MANAGEMENT ---[/bold blue]", expand=False))
                    console.print(" [1] Generate & Open Interactive Santiago City GIS Map (`household_map.html`)")
                    console.print(" [2] Log New Weather / Disaster Incident")
                    console.print(" [3] Back to Admin Menu")
                    
                    sub = get_secure_choice("Select option (1-3): ", 1, 3)
                    if sub == 1:
                        print("\n[INFO] Generating dynamic regional GIS map for Echague & Santiago...")
                        map_path = generate_household_map()
                        print(f"[SUCCESS] Map generated successfully at: {map_path}")
                        
                        # Automatically open the map in your default browser
                        try:
                            os.startfile(os.path.abspath(map_path))
                        except Exception as e:
                            print(f"[NOTE] Map saved, but could not auto-open: {e}")
                        pause()
                    elif sub == 2:
                        try:
                            bldg = Prompt.ask("Enter Barangay (e.g., Baluarte)").strip()
                            if not bldg:
                                raise ValueError("Barangay name cannot be blank.")
                            itype = Prompt.ask("Enter Incident Type (e.g., Flash Flood)").strip()
                            if not itype:
                                raise ValueError("Incident type cannot be blank.")
                            sev = Prompt.ask("Severity Level", choices=["High", "Medium", "Low"], default="High").strip()
                            
                            from datetime import datetime
                            default_date = datetime.now().strftime("%Y-%m-%d")
                            date_rep = Prompt.ask("Date Reported (YYYY-MM-DD)", default=default_date).strip()
                            datetime.strptime(date_rep, "%Y-%m-%d")
                            
                            conn = get_connection()
                            cursor = conn.cursor()
                            cursor.execute("INSERT INTO disaster_incidents (barangay, incident_type, severity_level, date_reported) VALUES (?, ?, ?, ?)", (bldg, itype, sev, date_rep))
                            conn.commit()
                            log_audit_event("LOG_DISASTER", bldg, f"Logged {itype} ({sev}) on {date_rep}")
                            conn.close()
                            console.print("[bold green][SUCCESS] Disaster logged & audit tracked![/bold green]")
                        except Exception as e:
                            console.print(f"\n[bold red][ERROR] Failed to log disaster: {e}[/bold red]")
                        pause()
                    elif sub == 3:
                        break
                        
            elif choice == 6:
                while True:
                    clear_screen()
                    console.print(Panel("[bold green]--- VISUALIZATIONS & EXECUTIVE REPORTS (UPDATED) ---[/bold green]", expand=False)) 
                    console.print(" [2] Generate Monthly Trend Chart (.png)")
                    console.print(" [3] Generate Household Comparison Chart (.png)")
                    console.print(" [4] Generate K-Means Cluster Scatter Plot (.png)")
                    console.print(" [5] Generate Linear Regression Forecast Plot (.png)")
                    console.print(" [6] Generate Tariff Tier Distribution Chart (.png)")
                    console.print(" [7] Cumulative Energy Load by Barangay Chart (.png)")
                    console.print(" [8] Compile Executive Markdown Report (`executive_summary.md`)")
                    console.print(" [9] Compile Consolidated Executive PDF Deliverable (`Smart_Grid_Executive_Report.pdf`)")
                    console.print(" [10] Back to Admin Menu")
                    
                    sub = get_secure_choice("Select option (1-10): ", 1, 10)
                    try:
                        if sub == 1:
                            print_ascii_bar_chart()
                            pause()
                        elif sub == 2:
                            p = generate_consumption_trend_chart()
                            if p: os.startfile(os.path.abspath(p))
                            pause()
                        elif sub == 3:
                            p = generate_consumer_comparison_chart()
                            if p: os.startfile(os.path.abspath(p))
                            pause()
                        elif sub == 4:
                            p = generate_cluster_scatter_plot()
                            if p: os.startfile(os.path.abspath(p))
                            pause()
                        elif sub == 5:
                            p = generate_regression_forecast_plot()
                            if p: os.startfile(os.path.abspath(p))
                            pause()
                        elif sub == 6:
                            p = generate_tier_distribution_chart()
                            if p: 
                                console.print(f"\n[bold green][SUCCESS] Tariff tier chart saved to: {os.path.abspath(p)}[/bold green]")
                                os.startfile(os.path.abspath(p))
                            else:
                                console.print("[yellow]Insufficient data for tier chart.[/yellow]")
                            pause()
                        elif sub == 7:
                            p = generate_barangay_load_chart()
                            if p: 
                                console.print(f"\n[bold green][SUCCESS] Barangay load chart saved to: {os.path.abspath(p)}[/bold green]")
                                os.startfile(os.path.abspath(p))
                            else:
                                console.print("[yellow]Insufficient data for barangay chart.[/yellow]")
                            pause()
                        elif sub == 8:
                            path = compile_executive_report()
                            console.print(f"\n[bold green][SUCCESS] Markdown report saved to: {path}[/bold green]")
                            os.startfile(path)
                            pause()
                        elif sub == 9:
                            from pdf_generator import generate_consolidated_pdf
                            pdf_path = generate_consolidated_pdf()
                            console.print(f"\n[bold green][SUCCESS] Consolidated PDF generated with all charts & tables![/bold green]\nSaved to: {pdf_path}")
                            os.startfile(pdf_path)
                            pause()
                        elif sub == 10:
                            break
                    except Exception as e:
                        console.print(f"\n[bold red][ERROR] Execution failed: {e}[/bold red]")
                        pause()
                        
            elif choice == 7:
                break
        except Exception as e:
            console.print(f"\n[bold red][ERROR] Admin panel exception: {escape(str(e))}[/bold red]")
        pause()

def manage_households_crud():
    while True:
        try:
            clear_screen()
            console.print(Panel("[bold yellow]--- HOUSEHOLD MANAGEMENT & AUDIT TRAIL ---[/bold yellow]", expand=False))
            console.print(" [1] View All Registered Households")
            console.print(" [2] Register New Household")
            console.print(" [3] Update Household Status / Details")
            console.print(" [4] Delete Household Node")
            console.print(" [5] View System Security Audit Logs")
            console.print(" [6] Return to Admin Menu")
            
            choice = get_secure_choice("Select option (1-6): ", 1, 6)
            
            conn = get_connection()
            cursor = conn.cursor()
            
            if choice == 1:
                cursor.execute("SELECT * FROM households")
                rows = cursor.fetchall()
                
                table = Table(title="Registered Grid Households")
                table.add_column("ID", justify="center", style="dim")
                table.add_column("Account No.", style="cyan")
                table.add_column("Homeowner Name", style="bold")
                table.add_column("Address / Barangay")
                table.add_column("Type", justify="center")
                table.add_column("Status", justify="center", style="green")
                
                if rows:
                    for r in rows:
                        table.add_row(
                            str(r['household_id']),
                            r['account_number'],
                            r['homeowner_name'],
                            r['address'],
                            r['connection_type'],
                            r['status']
                        )
                    console.print(table)
                else:
                    console.print("[yellow]No households registered in the database.[/yellow]")
                pause()
                
            elif choice == 2:
                console.print("[bold cyan]--- REGISTER NEW HOUSEHOLD ---[/bold cyan]")
                acc = Prompt.ask("Enter Account Number (e.g., ACC-1016)").strip()
                name = Prompt.ask("Enter Homeowner Name").strip()
                addr = Prompt.ask("Enter Address / Barangay (e.g., Baluarte, Santiago City)").strip()
                ctype = Prompt.ask("Connection Type", choices=["Residential", "Commercial", "Industrial"], default="Residential").strip()
                
                if not acc or not name or not addr:
                    console.print("[bold red][ERROR] All fields are required.[/bold red]")
                    pause()
                    continue
                    
                cursor.execute("""
                    INSERT INTO households (account_number, homeowner_name, address, connection_type, status)
                    VALUES (?, ?, ?, ?, 'Active')
                """, (acc, name, addr, ctype))
                conn.commit()
                log_audit_event("REGISTER_HOUSEHOLD", acc, f"Registered new household for {name} in {addr}")
                console.print(f"\n[bold green][SUCCESS] Household {acc} registered successfully![/bold green]")
                pause()
                
            elif choice == 3:
                h_id = int(Prompt.ask("Enter Household ID to update").strip())
                cursor.execute("SELECT * FROM households WHERE household_id = ?", (h_id,))
                h = cursor.fetchone()
                if not h:
                    console.print("[bold red][ERROR] Household ID not found.[/bold red]")
                    pause()
                    continue
                
                new_status = Prompt.ask("New Status", choices=["Active", "Disconnected", "Suspended"], default="Active").strip()
                cursor.execute("UPDATE households SET status = ? WHERE household_id = ?", (new_status, h_id))
                conn.commit()
                log_audit_event("UPDATE_HOUSEHOLD", h['account_number'], f"Updated status to {new_status}")
                console.print(f"\n[bold green][SUCCESS] Household ID {h_id} updated![/bold green]")
                pause()
                
            elif choice == 4:
                h_id = int(Prompt.ask("Enter Household ID to delete").strip())
                cursor.execute("SELECT account_number FROM households WHERE household_id = ?", (h_id,))
                h = cursor.fetchone()
                if not h:
                    console.print("[bold red][ERROR] Household ID not found.[/bold red]")
                    pause()
                    continue
                    
                confirm = Prompt.ask(f"Are you sure you want to delete account {h['account_number']}?", choices=["y", "n"], default="n")
                if confirm == 'y':
                    cursor.execute("DELETE FROM households WHERE household_id = ?", (h_id,))
                    conn.commit()
                    log_audit_event("DELETE_HOUSEHOLD", h['account_number'], "Deleted household node and associated telemetry")
                    console.print("\n[bold green][SUCCESS] Household deleted successfully.[/bold green]")
                pause()
                
            elif choice == 5:
                        cursor.execute("SELECT * FROM audit_logs ORDER BY log_id DESC LIMIT 50")
                        logs = cursor.fetchall()
                        
                        table = Table(title="System Security Audit Trail (Last 50 Actions)")
                        table.add_column("Log ID", justify="center", style="dim")
                        table.add_column("Timestamp", justify="center", style="cyan")
                        table.add_column("Action", style="bold yellow")
                        table.add_column("Target", style="magenta")
                        table.add_column("Details")
                        
                        if logs:
                            for l in logs:
                                # Safely convert to dict to handle column name differences
                                r = dict(l)
                                
                                log_id = str(r.get('log_id', 'N/A'))
                                timestamp = str(r.get('timestamp', 'N/A'))
                                action = str(r.get('operator_action') or r.get('action') or 'N/A')
                                target = str(r.get('target_account') or r.get('target') or 'SYSTEM')
                                details = str(r.get('details', 'N/A'))
                                
                                table.add_row(log_id, timestamp, action, target, details)
                                
                            console.print(table)
                        else:
                            console.print("[yellow]No audit logs recorded yet.[/yellow]")
                        pause()

            elif choice == 6:
                conn.close()
                break
                
            conn.close()
        except Exception as e:
            console.print(f"\n[bold red][ERROR] Database or execution error: {e}[/bold red]")
            pause()


def resident_portal():
    clear_screen()
    console.print(Panel("[bold cyan]RESIDENT & HOMEOWNER SECURE LOGIN[/bold cyan]", expand=False))
    
    try:
        acc_no = Prompt.ask("Enter your Account Number (e.g., ACC-1001)").strip()
        if not acc_no:
            console.print("[bold red][ERROR] Account number cannot be blank.[/bold red]")
            pause()
            return
            
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM households WHERE account_number = ?", (acc_no,))
        household = cursor.fetchone()
        conn.close()
        
        if not household:
            console.print(f"\n[bold red][ERROR] Account '{acc_no}' not found in registry.[/bold red]")
            pause()
            return
    except Exception as e:
        console.print(f"\n[bold red][ERROR] Authentication failed: {e}[/bold red]")
        pause()
        return

    while DateLoop := True:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT reading_id, billing_period, consumption_kwh, estimated_cost 
                FROM meter_readings WHERE household_id = ? 
                ORDER BY billing_period DESC
            """, (household['household_id'],))
            readings = cursor.fetchall()

            cursor.execute("SELECT AVG(consumption_kwh) FROM meter_readings")
            avg_row = cursor.fetchone()
            sector_avg = avg_row[0] if avg_row and avg_row[0] else 0.0

            resident_barangay = household['address'].split(',')[0].strip()
            cursor.execute("""
                SELECT incident_type, severity_level, date_reported 
                FROM disaster_incidents 
                WHERE barangay LIKE ?
            """, (f"%{resident_barangay}%",))
            local_disasters = cursor.fetchall()
            conn.close()
        except Exception as e:
            console.print(f"\n[bold red][ERROR] Database sync failed: {e}[/bold red]")
            pause()
            break

        clear_screen()
        console.print(Panel(f"[bold green]HOMEOWNER DASHBOARD: {household['homeowner_name'].upper()}[/bold green]\nAddress: {household['address']} | Status: [bold cyan]{household['status']}[/bold cyan]", expand=False))
        
        if local_disasters:
            console.print("[bold red]⚠️ ACTIVE BARANGAY GRID ADVISORY & FAULTS:[/bold red]")
            for d in local_disasters:
                console.print(f" • [yellow]{d['incident_type']}[/yellow] (Severity: [bold red]{d['severity_level']}[/bold red]) reported on {d['date_reported']}.")
            console.print("")

        console.print(" [1] Billing, Payments & Statement Receipts")
        console.print(" [2] Consumption Analytics, Projections & Sustainability")
        console.print(" [3] Grid Safety, Outages & Emergency Reporting")
        console.print(" [4] Logout")
        
        choice = get_secure_choice("Select option (1-4): ", 1, 4)
        
        if choice == 1:
            # --- CATEGORY 1: BILLING & FINANCIALS ---
            while True:
                clear_screen()
                console.print(Panel("[bold cyan]--- BILLING, PAYMENTS & STATEMENT RECEIPTS ---[/bold cyan]", expand=False))
                console.print(" [1] View Billing History & Community Benchmarking Table")
                console.print(" [2] Simulate Digital Bill Payment (GCash / Maya / Bank)")
                console.print(" [3] Export Individual Statement Receipt (.txt)")
                console.print(" [4] Return to Main Resident Menu")
                
                sub = get_secure_choice("Select option (1-4): ", 1, 4)
                if sub == 1:
                    table = Table(title=f"Billing Statements for {household['account_number']}")
                    table.add_column("Period", style="cyan", justify="center")
                    table.add_column("Consumption", justify="right", style="bold")
                    table.add_column("Tiered Cost (₱)", justify="right", style="green")
                    table.add_column("Sector Variance", justify="right")
                    
                    if readings:
                        for r in readings:
                            kwh = r['consumption_kwh']
                            diff = kwh - sector_avg
                            diff_str = f"[green]{diff:+.1f} kWh vs avg[/green]" if diff <= 0 else f"[red]{diff:+.1f} kWh vs avg[/red]"
                            table.add_row(r['billing_period'], f"{kwh:,.2f} kWh", f"₱{r['estimated_cost']:,.2f}", diff_str)
                        console.print(table)
                        console.print(f"\n[dim]Santiago City Sector Average: {sector_avg:,.2f} kWh per cycle.[/dim]")
                    else:
                        console.print("[yellow]No billing statements recorded.[/yellow]")
                    pause()
                    
                elif sub == 2:
                    if not readings:
                        console.print("\n[yellow]No billing statements available for payment.[/yellow]")
                        pause()
                        continue
                        
                    table = Table(title="Select Statement to Pay")
                    table.add_column("#", style="dim", justify="center")
                    table.add_column("Period", style="cyan")
                    table.add_column("Amount Due", style="green", justify="right")
                    for idx, r in enumerate(readings, 1):
                        table.add_row(str(idx), r['billing_period'], f"₱{r['estimated_cost']:,.2f}")
                    console.print(table)
                    
                    try:
                        pay_idx = int(Prompt.ask("Select bill number to pay").strip()) - 1
                        if 0 <= pay_idx < len(readings):
                            target_bill = readings[pay_idx]
                            console.print("\n[bold cyan]Select Payment Gateway:[/bold cyan]")
                            console.print(" [1] GCash Mobile Wallet")
                            console.print(" [2] Maya Digital Wallet")
                            console.print(" [3] Direct Bank Transfer")
                            gateway = get_secure_choice("Choose gateway (1-3): ", 1, 3)
                            gw_name = ["GCash", "Maya", "Bank Transfer"][gateway - 1]
                            
                            conn = get_connection()
                            cursor = conn.cursor()
                            cursor.execute("UPDATE households SET status = 'Active' WHERE household_id = ?", (household['household_id'],))
                            conn.commit()
                            log_audit_event("ONLINE_PAYMENT", acc_no, f"Paid ₱{target_bill['estimated_cost']} via {gw_name}")
                            conn.close()
                            console.print(f"\n[bold green][SUCCESS] Payment of ₱{target_bill['estimated_cost']:,.2f} processed via {gw_name}![/bold green]")
                        else:
                            console.print("[bold red][ERROR] Invalid selection index.[/bold red]")
                    except Exception as e:
                        console.print(f"\n[bold red][ERROR] Payment processing failed: {e}[/bold red]")
                    pause()
                    
                elif sub == 3:
                    if not readings:
                        console.print("\n[yellow]No statements available to export.[/yellow]")
                        pause()
                        continue
                    try:
                        filename = f"Statement_{household['account_number']}.txt"
                        receipt_content = f"""==================================================
 SANTIAGO CITY SMART-GRID UTILITY STATEMENT
==================================================
 Account Number : {household['account_number']}
 Homeowner Name : {household['homeowner_name']}
 Service Address: {household['address']}
 Connection Type: {household['connection_type']}
 Status         : {household['status']}
--------------------------------------------------
 BILLING HISTORY:
"""
                        for r in readings:
                            receipt_content += f" - Period: {r['billing_period']} | Usage: {r['consumption_kwh']:,.2f} kWh | Cost: ₱{r['estimated_cost']:,.2f}\n"
                        receipt_content += "==================================================\n"

                        with open(filename, "w", encoding="utf-8") as f:
                            f.write(receipt_content)
                        
                        console.print(f"\n[bold green][SUCCESS] Statement exported to: {os.path.abspath(filename)}[/bold green]")
                        os.startfile(os.path.abspath(filename))
                    except Exception as e:
                        console.print(f"\n[bold red][ERROR] Export failed: {e}[/bold red]")
                    pause()
                elif sub == 4:
                    break

        elif choice == 2:
            # --- CATEGORY 2: ANALYTICS, PROJECTIONS & SUSTAINABILITY ---
            while True:
                clear_screen()
                console.print(Panel("[bold magenta]--- ANALYTICS, PROJECTIONS & SUSTAINABILITY ---[/bold magenta]", expand=False))
                console.print(" [1] Predictive Bill & Tier Simulator")
                console.print(" [2] Carbon Footprint & Eco-Impact Metrics")
                console.print(" [3] Appliance Load Disaggregation Profile")
                console.print(" [4] Return to Main Resident Menu")
                
                sub = get_secure_choice("Select option (1-4): ", 1, 4)
                if sub == 1:
                    clear_screen()
                    console.print(Panel("[bold yellow]PREDICTIVE BILL & TIER SIMULATOR[/bold yellow]", expand=False))
                    try:
                        sim_kwh = float(Prompt.ask("Enter projected consumption (kWh)").strip())
                        if sim_kwh < 0:
                            raise ValueError("Consumption cannot be negative.")
                        sim_cost = calculate_tiered_cost(sim_kwh, household['connection_type'])
                        
                        console.print(f"\n[bold green]--- SIMULATION RESULTS ---[/bold green]")
                        console.print(f" • Projected Usage : [cyan]{sim_kwh:,.2f} kWh[/cyan]")
                        console.print(f" • Estimated Cost  : [bold green]₱{sim_cost:,.2f}[/bold green]")
                        if sim_kwh <= 50:
                            console.print(" • Tariff Tier     : [green]Lifeline Subsidized Rate (₱8.50/kWh)[/green]")
                        elif sim_kwh <= 200:
                            console.print(" • Tariff Tier     : [yellow]Standard Utility Rate (₱11.20/kWh)[/yellow]")
                        else:
                            console.print(" • Tariff Tier     : [red]Peak / Heavy Load Rate (₱14.50/kWh)[/red]")
                    except Exception as e:
                        console.print(f"[bold red][ERROR] Invalid input: {e}[/bold red]")
                    pause()
                    
                elif sub == 2:
                    console.print(Panel("[bold green]CARBON FOOTPRINT & SUSTAINABILITY METRICS[/bold green]", expand=False))
                    if readings:
                        total_kwh_all = sum([r['consumption_kwh'] for r in readings])
                        total_co2_kg = total_kwh_all * 0.707
                        trees_needed = total_co2_kg / 21.0
                        console.print(f" • Cumulative Historical Consumption: [cyan]{total_kwh_all:,.2f} kWh[/cyan]")
                        console.print(f" • Estimated Carbon Emission ($CO_2$): [bold red]{total_co2_kg:,.2f} kg[/bold red]")
                        console.print(f" • Offset Required: Equivalent to ~[bold green]{max(1, int(trees_needed))}[/bold green] mature trees.")
                    else:
                        console.print("[yellow]No consumption data available.[/yellow]")
                    pause()
                    
                elif sub == 3:
                    console.print(Panel("[bold magenta]APPLIANCE LOAD DISAGGREGATION PROFILE[/bold magenta]", expand=False))
                    if readings:
                        latest_kwh = readings[0]['consumption_kwh']
                        table = Table(title="Estimated Energy Distribution")
                        table.add_column("Appliance Category", style="cyan")
                        table.add_column("Estimated Share", justify="right")
                        table.add_column("Estimated kWh", justify="right", style="green")
                        table.add_row("Air Conditioning / Cooling", "45%", f"{latest_kwh * 0.45:,.2f} kWh")
                        table.add_row("Refrigeration & Cooling", "25%", f"{latest_kwh * 0.25:,.2f} kWh")
                        table.add_row("Lighting & Ceiling Fans", "15%", f"{latest_kwh * 0.15:,.2f} kWh")
                        table.add_row("Entertainment & Electronics", "10%", f"{latest_kwh * 0.10:,.2f} kWh")
                        table.add_row("Other Appliances (Cooking/Laundry)", "5%", f"{latest_kwh * 0.05:,.2f} kWh")
                        console.print(table)
                    else:
                        console.print("[yellow]No consumption data available.[/yellow]")
                    pause()
                elif sub == 4:
                    break

        elif choice == 3:
            # --- CATEGORY 3: GRID SAFETY, OUTAGES & EMERGENCY ---
            while True:
                clear_screen()
                console.print(Panel("[bold red]--- GRID SAFETY, OUTAGES & EMERGENCY REPORTING ---[/bold red]", expand=False))
                console.print(" [1] View Active Grid Outages & Barangay Hazard Status")
                console.print(" [2] Report Emergency Outage / Electrical Hazard to Grid Ops")
                console.print(" [3] Return to Main Resident Menu")
                
                sub = get_secure_choice("Select option (1-3): ", 1, 3)
                if sub == 1:
                    clear_screen()
                    console.print(Panel(f"[bold cyan]LIVE GRID OUTAGES & HAZARD STATUS: {resident_barangay.upper()}[/bold cyan]", expand=False))
                    try:
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute("SELECT barangay, incident_type, severity_level, date_reported FROM disaster_incidents ORDER BY date_reported DESC")
                        all_incidents = cursor.fetchall()
                        conn.close()

                        if all_incidents:
                            table = Table(title="Santiago City Grid Resilience & Incident Feed")
                            table.add_column("Barangay", style="cyan")
                            table.add_column("Incident / Hazard", style="red")
                            table.add_column("Severity", style="bold", justify="center")
                            table.add_column("Date Reported", justify="center")
                            
                            for inc in all_incidents:
                                is_local = resident_barangay.lower() in inc['barangay'].lower()
                                b_styled = f"[bold yellow]{inc['barangay']} (YOUR AREA)[/bold yellow]" if is_local else inc['barangay']
                                table.add_row(b_styled, inc['incident_type'], inc['severity_level'], inc['date_reported'])
                            console.print(table)
                        else:
                            console.print("[green]All grid sectors in Santiago City are operating normally. No active outages reported.[/green]")
                    except Exception as e:
                        console.print(f"[bold red][ERROR] Failed to load outages: {e}[/bold red]")
                    pause()
                    
                elif sub == 2:
                    clear_screen()
                    console.print(Panel("[bold red]REPORT EMERGENCY / ELECTRICAL HAZARD[/bold red]", expand=False))
                    console.print(f"Reporting location locked to your registered address: [cyan]{household['address']}[/cyan]\n")
                    
                    console.print("Select Emergency Issue Type:")
                    console.print(" [1] Transformer Spark / Explosion")
                    console.print(" [2] Total Power Outage / Blackout")
                    console.print(" [3] Downed Power Line / Cable Hazard")
                    console.print(" [4] Severe Weather / Storm Grid Damage")
                    console.print(" [5] Meter Tampering / Suspected Illegal Tap Notice")
                    
                    try:
                        issue_choice = get_secure_choice("Select issue (1-5): ", 1, 5)
                        issue_types = [
                            "Transformer Spark / Explosion",
                            "Total Power Outage / Blackout",
                            "Downed Power Line / Cable Hazard",
                            "Severe Weather / Storm Grid Damage",
                            "Suspected Meter Tampering / Fault"
                        ]
                        selected_issue = issue_types[issue_choice - 1]
                        severity = Prompt.ask("Select Severity Level", choices=["High", "Medium", "Low"], default="High").strip()
                        details = Prompt.ask("Provide brief details or landmark").strip()
                        
                        from datetime import datetime
                        today_str = datetime.now().strftime("%Y-%m-%d")

                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO disaster_incidents (barangay, incident_type, severity_level, date_reported)
                            VALUES (?, ?, ?, ?)
                        """, (resident_barangay, f"{selected_issue} (Reported by {household['homeowner_name']}: {details})", severity, today_str))
                        conn.commit()
                        log_audit_event("RESIDENT_EMERGENCY_REPORT", acc_no, f"Reported {selected_issue} in {resident_barangay}")
                        conn.close()

                        console.print("\n[bold green][SUCCESS] Emergency report transmitted to Grid Operations & GIS Map![/bold green]")
                        console.print("[dim]The central dispatch and hazard database have been updated instantly.[/dim]")
                    except Exception as e:
                        console.print(f"\n[bold red][ERROR] Emergency report submission failed: {e}[/bold red]")
                    pause()
                elif sub == 3:
                    break

        elif choice == 4:
            break

def main():
    init_db(reset=False)
    seed_sample_data_if_empty()
    
    while True:
        clear_screen()
        console.print(Panel("[bold white on blue] SMART-GRID INTELLIGENCE & UTILITY PLATFORM [/bold white on blue]\n[italic]Santiago City, Isabela — Terminal-First Architecture[/italic]", expand=False))
        console.print(" [1] Administrator / Grid Operator Portal")
        console.print(" [2] Resident / Homeowner Portal")
        console.print(" [3] Exit System")
        
        choice = get_secure_choice("Select option (1-3): ", 1, 3)
        if choice == 1:
            admin_panel()
        elif choice == 2:
            resident_portal()
        elif choice == 3:
            console.print("[bold yellow]Exiting Smart-Grid Intelligence Platform. Goodbye![/bold yellow]")
            sys.exit(0)

if __name__ == "__main__":
    main()