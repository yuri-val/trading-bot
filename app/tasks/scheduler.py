from celery.schedules import crontab
from .daily_tasks import celery_app

# Configure beat schedule
celery_app.conf.beat_schedule = {
    # Daily analysis at 09:00 UTC (12:00 Kyiv time)
    'daily-stock-analysis': {
        'task': 'app.tasks.daily_tasks.daily_analysis_task',
        'schedule': crontab(hour=9, minute=0),
        'options': {
            'queue': 'analysis',
            'routing_key': 'analysis.daily'
        }
    },
    
    # Weekly summary report on Mondays at 10:00 UTC (13:00 Kyiv time)
    'weekly-summary-report': {
        'task': 'app.tasks.daily_tasks.generate_summary_report_task',
        'schedule': crontab(hour=10, minute=0, day_of_week=1),  # Monday
        'options': {
            'queue': 'reports',
            'routing_key': 'reports.summary'
        }
    },
    
    # Health check every hour
    'system-health-check': {
        'task': 'app.tasks.daily_tasks.health_check_task',
        'schedule': crontab(minute=0),  # Every hour at minute 0
        'options': {
            'queue': 'monitoring',
            'routing_key': 'monitoring.health'
        }
    },
    
    # Test task every 5 minutes (disable in production)
    'test-connectivity': {
        'task': 'app.tasks.daily_tasks.test_task',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
        'options': {
            'queue': 'testing',
            'routing_key': 'testing.connectivity'
        }
    }
}

# Set timezone
celery_app.conf.timezone = 'UTC'

# Additional Celery configuration
celery_app.conf.update(
    # Task execution settings
    task_soft_time_limit=1800,  # 30 minutes soft limit
    task_time_limit=2400,       # 40 minutes hard limit
    
    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=10,
    
    # Result backend settings
    result_expires=86400,  # 24 hours
    result_compression='gzip',
    
    # Queue routing
    task_default_queue='default',
    task_default_exchange='default',
    task_default_routing_key='default',
    
    # Queue definitions
    task_queues={
        'analysis': {
            'exchange': 'analysis',
            'routing_key': 'analysis.*',
        },
        'reports': {
            'exchange': 'reports', 
            'routing_key': 'reports.*',
        },
        'monitoring': {
            'exchange': 'monitoring',
            'routing_key': 'monitoring.*',
        },
        'testing': {
            'exchange': 'testing',
            'routing_key': 'testing.*',
        }
    },
    
    # Error handling
    task_reject_on_worker_lost=True,
    task_ignore_result=False,
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
)

# Custom schedule for different environments
def configure_schedule_for_environment(env: str = "development"):
    """Configure different schedules based on environment"""
    
    if env == "production":
        # Production schedule - strict timing
        celery_app.conf.beat_schedule = {
            'daily-stock-analysis': {
                'task': 'app.tasks.daily_tasks.daily_analysis_task',
                'schedule': crontab(hour=9, minute=0),  # 12:00 Kyiv
            },
            'weekly-summary-report': {
                'task': 'app.tasks.daily_tasks.generate_summary_report_task',
                'schedule': crontab(hour=10, minute=0, day_of_week=1),  # Monday 13:00 Kyiv
            },
            'system-health-check': {
                'task': 'app.tasks.daily_tasks.health_check_task',
                'schedule': crontab(minute=0),  # Every hour
            }
        }
        
    elif env == "development":
        # Development schedule - more frequent for testing
        celery_app.conf.beat_schedule.update({
            'dev-daily-analysis': {
                'task': 'app.tasks.daily_tasks.daily_analysis_task',
                'schedule': crontab(minute='*/30'),  # Every 30 minutes for testing
            },
            'dev-summary-report': {
                'task': 'app.tasks.daily_tasks.generate_summary_report_task', 
                'schedule': crontab(hour='*/4', minute=0),  # Every 4 hours
            }
        })
        
    elif env == "testing":
        # Testing schedule - very frequent
        celery_app.conf.beat_schedule = {
            'test-daily-analysis': {
                'task': 'app.tasks.daily_tasks.daily_analysis_task',
                'schedule': crontab(minute='*/5'),  # Every 5 minutes
            },
            'test-connectivity': {
                'task': 'app.tasks.daily_tasks.test_task',
                'schedule': crontab(minute='*/1'),  # Every minute
            }
        }


# Utility functions for manual scheduling
def run_daily_analysis_at_time(hour: int, minute: int = 0):
    """Set custom time for daily analysis"""
    celery_app.conf.beat_schedule['daily-stock-analysis']['schedule'] = crontab(
        hour=hour, minute=minute
    )


def run_summary_report_weekly(day_of_week: int, hour: int, minute: int = 0):
    """Set custom time for weekly summary (0=Sunday, 1=Monday, etc.)"""
    celery_app.conf.beat_schedule['weekly-summary-report']['schedule'] = crontab(
        hour=hour, minute=minute, day_of_week=day_of_week
    )


# Task monitoring and management
def get_active_tasks():
    """Get list of active tasks"""
    inspect = celery_app.control.inspect()
    return inspect.active()


def get_scheduled_tasks():
    """Get list of scheduled tasks"""
    inspect = celery_app.control.inspect()
    return inspect.scheduled()


def cancel_task(task_id: str):
    """Cancel a specific task"""
    celery_app.control.revoke(task_id, terminate=True)


def purge_queue(queue_name: str):
    """Purge all tasks from a specific queue"""
    celery_app.control.purge()


# Health monitoring
def check_celery_health():
    """Check overall Celery system health"""
    try:
        inspect = celery_app.control.inspect()
        
        # Check if workers are responding
        stats = inspect.stats()
        active = inspect.active()
        scheduled = inspect.scheduled()
        
        return {
            "workers_online": len(stats) if stats else 0,
            "active_tasks": sum(len(tasks) for tasks in active.values()) if active else 0,
            "scheduled_tasks": sum(len(tasks) for tasks in scheduled.values()) if scheduled else 0,
            "status": "healthy" if stats else "no_workers"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "health":
            health = check_celery_health()
            print(f"Celery Health: {health}")
            
        elif command == "active":
            active = get_active_tasks()
            print(f"Active Tasks: {active}")
            
        elif command == "scheduled":
            scheduled = get_scheduled_tasks()
            print(f"Scheduled Tasks: {scheduled}")
            
        elif command == "config":
            env = sys.argv[2] if len(sys.argv) > 2 else "development"
            configure_schedule_for_environment(env)
            print(f"Configured schedule for {env} environment")
            
    else:
        print("Usage: python scheduler.py [health|active|scheduled|config]")