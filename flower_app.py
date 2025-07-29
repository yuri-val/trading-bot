#!/usr/bin/env python3
"""
Standalone Flower monitoring app that doesn't import the main application.
This avoids the Pydantic validation issues with environment variables.
"""

import os
from celery import Celery

# Simple Celery app configuration for flower monitoring
flower_celery = Celery('flower_monitor')

# Configure Celery for monitoring only
flower_celery.conf.update(
    broker_url=f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', '6379')}/0",
    result_backend=f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', '6379')}/0",
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

if __name__ == '__main__':
    print("Starting Flower monitoring...")
    print(f"Broker: redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', '6379')}/0")