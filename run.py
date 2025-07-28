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


def run_api_server():
    """Run the FastAPI server"""
    print("Starting Trading Bot API server...")
    os.system("uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")


def run_celery_worker():
    """Run Celery worker"""
    print("Starting Celery worker...")
    os.system("celery -A app.tasks.daily_tasks worker --loglevel=info --concurrency=2")


def run_celery_beat():
    """Run Celery beat scheduler"""
    print("Starting Celery beat scheduler...")
    os.system("celery -A app.tasks.daily_tasks beat --loglevel=info")


def run_celery_flower():
    """Run Celery Flower monitoring"""
    print("Starting Celery Flower monitoring on http://localhost:5555")
    os.system("celery -A app.tasks.daily_tasks flower --port=5555")


def run_daily_analysis():
    """Run daily analysis manually"""
    print(f"Running daily analysis manually at {datetime.now()}")
    os.system("python -m app.tasks.daily_tasks daily")


def run_summary_report(days=30):
    """Generate summary report"""
    print(f"Generating summary report for last {days} days...")
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
                print(f"   - OpenSearch: {health_data.get('services', {}).get('opensearch', 'Unknown')}")
                print(f"   - Stable stocks: {health_data.get('configuration', {}).get('stable_stocks_count', 'Unknown')}")
                print(f"   - Risky stocks: {health_data.get('configuration', {}).get('risky_stocks_count', 'Unknown')}")
            else:
                print("❌ API Server: Unhealthy")
        except Exception as e:
            print(f"❌ API Server: Not accessible - {str(e)}")

        # Check OpenSearch
        try:
            response = requests.get("http://localhost:9201/_cluster/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                status = data.get('status', 'unknown')
                if status == 'green':
                    print("✅ OpenSearch: Healthy (Green)")
                elif status == 'yellow':
                    print("⚠️  OpenSearch: Warning (Yellow)")
                else:
                    print("❌ OpenSearch: Unhealthy (Red)")
            else:
                print("❌ OpenSearch: Not responding")
        except Exception as e:
            print(f"❌ OpenSearch: Not accessible - {str(e)}")

        # Check Redis
        try:
            import redis
            r = redis.Redis(host='localhost', port=6380, db=0)
            if r.ping():
                print("✅ Redis: Healthy")
            else:
                print("❌ Redis: Not responding")
        except Exception as e:
            print(f"❌ Redis: Not accessible - {str(e)}")

    except ImportError:
        print("❌ Required packages not installed. Run: pip install requests redis")


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
            "docker", "docker-dev", "stop", "logs", "health", "status"
        ],
        help="Command to execute"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days for summary report (default: 30)"
    )

    args = parser.parse_args()

    if args.command == "api":
        run_api_server()
    elif args.command == "worker":
        run_celery_worker()
    elif args.command == "beat":
        run_celery_beat()
    elif args.command == "flower":
        run_celery_flower()
    elif args.command == "analysis":
        run_daily_analysis()
    elif args.command == "summary":
        run_summary_report(args.days)
    elif args.command == "docker":
        run_docker()
    elif args.command == "docker-dev":
        run_docker_dev()
    elif args.command == "stop":
        stop_docker()
    elif args.command == "logs":
        show_logs()
    elif args.command == "health":
        check_health()
    elif args.command == "status":
        show_status()


if __name__ == "__main__":
    main()
