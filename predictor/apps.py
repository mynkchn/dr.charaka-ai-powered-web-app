from django.apps import AppConfig
import threading
import time
import sys
import os
import asyncio

class PredictorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'predictor'
