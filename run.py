#!/usr/bin/env python3
"""
Trading Bot - Main runner script
This script provides a convenient way to run different components of the trading bot system.
"""

import os
import sys
import argparse
import subprocess
from datetime import datetime


def check_docker_services():
    """Check if Docker services are running"""
    # Check if app service is running
    result = os.system("docker compose ps app --format json | grep -q 'running' 2>/dev/null")
    if result != 0:
        print("❌ Docker services are not running!")
        print("💡 Start the services first with: python run.py docker")
        print("💡 Or check service status with: docker compose ps")
        return False
    return True


def run_api_server():
    """Run the FastAPI server"""
    print("Starting Trading Bot API server...")
    os.system("uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")


def run_celery_worker(use_docker=False):
    """Run Celery worker"""
    print("Starting Celery worker...")
    if use_docker:
        if not check_docker_services():
            return
        print("Starting Celery worker in Docker container...")
        result = os.system("docker compose exec app celery -A app.tasks.daily_tasks worker --loglevel=info --concurrency=2")
        if result != 0:
            print("❌ Failed to start Celery worker in Docker container")
    else:
        os.system("celery -A app.tasks.daily_tasks worker --loglevel=info --concurrency=2")


def run_celery_beat(use_docker=False):
    """Run Celery beat scheduler"""
    print("Starting Celery beat scheduler...")
    if use_docker:
        if not check_docker_services():
            return
        print("Starting Celery beat scheduler in Docker container...")
        result = os.system("docker compose exec app celery -A app.tasks.daily_tasks beat --loglevel=info")
        if result != 0:
            print("❌ Failed to start Celery beat in Docker container")
    else:
        os.system("celery -A app.tasks.daily_tasks beat --loglevel=info")


def run_celery_flower(use_docker=False):
    """Run Celery Flower monitoring"""
    print("Starting Celery Flower monitoring on http://localhost:5555")
    if use_docker:
        if not check_docker_services():
            return
        print("Starting Celery Flower in Docker container...")
        result = os.system("docker compose exec app celery -A app.tasks.daily_tasks flower --port=5555 --address=0.0.0.0")
        if result != 0:
            print("❌ Failed to start Celery Flower in Docker container")
    else:
        os.system("celery -A app.tasks.daily_tasks flower --port=5555")


def run_daily_analysis(use_docker=False):
    """Run daily analysis manually"""
    print(f"Running daily analysis manually at {datetime.now()}")
    if use_docker:
        if not check_docker_services():
            return
        print("Running analysis in Docker container...")
        result = os.system("docker compose exec app python -m app.tasks.daily_tasks daily")
        if result != 0:
            print("❌ Failed to run analysis in Docker container")
    else:
        os.system("python -m app.tasks.daily_tasks daily")


def run_summary_report(days=30, use_docker=False):
    """Generate summary report"""
    print(f"Generating summary report for last {days} days...")
    if use_docker:
        if not check_docker_services():
            return
        print("Running summary report in Docker container...")
        result = os.system(f"docker compose exec app python -m app.tasks.daily_tasks summary {days}")
        if result != 0:
            print("❌ Failed to run summary report in Docker container")
    else:
        os.system(f"python -m app.tasks.daily_tasks summary {days}")


def run_docker():
    """Run the entire system using Docker Compose"""
    print("Starting Trading Bot system with Docker Compose...")
    os.system("docker compose up -d")


def run_docker_dev():
    """Run system in development mode"""
    print("Starting Trading Bot in development mode...")
    os.system("docker compose -f docker-compose.yml up")


def stop_docker():
    """Stop Docker Compose services"""
    print("Stopping Trading Bot services...")
    os.system("docker compose down")


def show_logs():
    """Show Docker Compose logs"""
    print("Showing system logs...")
    os.system("docker compose logs -f")


def show_containers():
    """Show Docker containers status"""
    print("Trading Bot Docker Containers Status")
    print("=" * 50)
    os.system("docker compose ps")
    print("\n" + "=" * 50)
    print("Container Details:")
    os.system("docker ps --filter 'name=trade_bot' --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'")


def check_task_status():
    """Check recent task execution status"""
    print("Trading Bot Task Status")
    print("=" * 40)

    # Check for today's files
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")

    print(f"Checking files for {today}:")

    # Check daily report
    report_file = f"data/reports/DR_{today}.json"
    if os.path.exists(report_file):
        stat = os.stat(report_file)
        mod_time = datetime.fromtimestamp(stat.st_mtime).strftime("%H:%M:%S")
        print(f"✅ Daily Report: Created at {mod_time}")
    else:
        print("❌ Daily Report: Not found")

    # Check stock data directory
    stock_files = []
    if os.path.exists("data/stocks"):
        stock_files = [f for f in os.listdir("data/stocks") if f.endswith('.json')]

    if stock_files:
        print(f"✅ Stock Data: {len(stock_files)} files")
        # Show newest stock file
        newest = max([os.path.join("data/stocks", f) for f in stock_files], key=os.path.getmtime)
        mod_time = datetime.fromtimestamp(os.path.getmtime(newest)).strftime("%H:%M:%S")
        print(f"   Latest: {os.path.basename(newest)} at {mod_time}")
    else:
        print("❌ Stock Data: No files found")

    # Check summary files
    summary_files = []
    if os.path.exists("data/summaries"):
        summary_files = [f for f in os.listdir("data/summaries") if f.endswith('.json')]

    if summary_files:
        print(f"📊 Summary Reports: {len(summary_files)} files")
        newest = max([os.path.join("data/summaries", f) for f in summary_files], key=os.path.getmtime)
        mod_time = datetime.fromtimestamp(os.path.getmtime(newest)).strftime("%H:%M:%S")
        print(f"   Latest: {os.path.basename(newest)} at {mod_time}")
    else:
        print("📊 Summary Reports: No files found")


def check_health():
    """Check system health"""
    print("Checking system health...")

    try:
        import requests

        # Check API health
        try:
            response = requests.get("http://localhost:8000/health", timeout=5)
            if response.status_code == 200:
                print("✅ API Server: Healthy")
                health_data = response.json()
                print(f"   - Database: {health_data.get('services', {}).get('database', 'Unknown')}")
                print(f"   - Stable stocks: {health_data.get('configuration', {}).get('stable_stocks_count', 'Unknown')}")
                print(f"   - Risky stocks: {health_data.get('configuration', {}).get('risky_stocks_count', 'Unknown')}")
            else:
                print("❌ API Server: Unhealthy")
        except Exception as e:
            print(f"❌ API Server: Not accessible - {str(e)}")

        # Check Redis using simple HTTP request (since redis module isn't installed locally)
        try:
            # Check if Redis container is responsive by checking if the port is open
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex(('localhost', 6380))
            sock.close()

            if result == 0:
                print("✅ Redis: Port 6380 is accessible")
            else:
                print("❌ Redis: Port 6380 is not accessible")
        except Exception as e:
            print(f"❌ Redis: Connection test failed - {str(e)}")

        # Check Flower
        try:
            response = requests.get("http://localhost:5555", timeout=5)
            if response.status_code == 200:
                print("✅ Flower: Web interface accessible")
            else:
                print("❌ Flower: Web interface not responding")
        except Exception as e:
            print(f"❌ Flower: Not accessible - {str(e)}")

        # Check Docker containers
        try:
            result = os.system("docker compose ps --format json >/dev/null 2>&1")
            if result == 0:
                print("✅ Docker Compose: Services are managed")
                # Count running containers
                container_count = os.popen("docker ps --filter 'name=trade_bot' --format '{{.Names}}' | wc -l").read().strip()
                print(f"   - Running containers: {container_count}")
            else:
                print("❌ Docker Compose: Not available or services not running")
        except Exception as e:
            print(f"❌ Docker: Check failed - {str(e)}")

    except ImportError:
        print("❌ Required packages not installed. Run: pip install requests")


def show_status():
    """Show system status"""
    print("Trading Bot System Status")
    print("=" * 40)

    try:
        import requests
        response = requests.get("http://localhost:8000/api/v1/status", timeout=5)
        if response.status_code == 200:
            status_data = response.json()

            print(f"System Time: {status_data.get('system_time', 'Unknown')}")
            print(f"Analysis Status:")
            analysis = status_data.get('analysis_status', {})
            print(f"  - Today's Report: {'✅' if analysis.get('todays_report_available') else '❌'}")
            print(f"  - Yesterday's Report: {'✅' if analysis.get('yesterdays_report_available') else '❌'}")
            print(f"  - Last Analysis: {analysis.get('last_analysis', 'Never')}")

            db_status = status_data.get('database_status', {})
            print(f"Database Status: {db_status.get('status', 'Unknown')}")

            config = status_data.get('api_configuration', {})
            print(f"Configuration:")
            print(f"  - Tracked Stocks: {config.get('total_tracked_stocks', 'Unknown')}")
            print(f"  - Investment Strategy: {config.get('investment_strategy', 'Unknown')}")

        else:
            print("❌ Could not retrieve system status")

    except Exception as e:
        print(f"❌ Error retrieving status: {str(e)}")


def main():
    parser = argparse.ArgumentParser(description="Trading Bot Management Script")
    parser.add_argument(
        "command",
        choices=[
            "api", "worker", "beat", "flower", "analysis", "summary",
            "docker", "docker-dev", "stop", "logs", "containers", "tasks", "health", "status"
        ],
        help="Command to execute"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days for summary report (default: 30)"
    )
    parser.add_argument(
        "--docker",
        action="store_true",
        help="Run the command inside Docker container (for analysis, summary, worker, beat, flower)"
    )

    args = parser.parse_args()

    if args.command == "api":
        run_api_server()
    elif args.command == "worker":
        run_celery_worker(args.docker)
    elif args.command == "beat":
        run_celery_beat(args.docker)
    elif args.command == "flower":
        run_celery_flower(args.docker)
    elif args.command == "analysis":
        run_daily_analysis(args.docker)
    elif args.command == "summary":
        run_summary_report(args.days, args.docker)
    elif args.command == "docker":
        run_docker()
    elif args.command == "docker-dev":
        run_docker_dev()
    elif args.command == "stop":
        stop_docker()
    elif args.command == "logs":
        show_logs()
    elif args.command == "containers":
        show_containers()
    elif args.command == "tasks":
        check_task_status()
    elif args.command == "health":
        check_health()
    elif args.command == "status":
        show_status()


if __name__ == "__main__":
    main()
