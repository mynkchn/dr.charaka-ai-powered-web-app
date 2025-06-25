from django.apps import AppConfig
import threading
import time
import sys
import os
import asyncio

class PredictorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'predictor'

    def ready(self):
        if os.environ.get('RUN_MAIN') != 'true':
            return

        def start_bot():
            time.sleep(3)  # Give Django time to fully load

            try:
                sys.path.append(r"D:\project_ai_hackathon\telegram_bot")
                from tele_bot import SimpleMedicalBot

                asyncio.set_event_loop(asyncio.new_event_loop())  # <-- FIX

                bot = SimpleMedicalBot()
                bot.run()
            except Exception as e:
                print(f"Error starting Telegram bot: {e}")

        bot_thread = threading.Thread(target=start_bot)
        bot_thread.daemon = True
        bot_thread.start()
