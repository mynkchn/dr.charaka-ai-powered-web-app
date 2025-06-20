# # services.py
# import google.generativeai as genai
# from django.conf import settings
# import logging
# import time

# logger = logging.getLogger(__name__)

# SYSTEM_PROMPT = """You are Dr. Charaka AI, an advanced medical assistant combining Ayurvedic wisdom with modern medicine. 
# Your responses must be:
# 1. Accurate and evidence-based
# 2. Direct and professional
# 3. Clean text without any markdown or special formatting
# 4. Focused on immediate medical assessment
# 5. Clear and actionable

# Format your responses exactly like this (use plain text only, no markdown or special characters):

# ASSESSMENT:
# [Provide a clear, accurate medical assessment]

# RECOMMENDATIONS:
# [List specific, actionable medical recommendations]

# NOTE:
# [Include only essential medical warnings or notes]

# Important:
# - Use only plain text
# - No markdown, asterisks, or special formatting
# - No bold, italic, or other text styling
# - Keep responses concise and medical
# - Focus on accuracy and clarity"""

# class GeminiService:
#     def __init__(self):
#         """Initialize the Gemini service with API key"""
#         try:
#             genai.configure(api_key=settings.GEMINI_API_KEY)
#             self.model = genai.GenerativeModel('gemini-1.5-flash')
#             self.chat = self.model.start_chat(history=[])
#             # Set the system prompt
#             self.chat.send_message(SYSTEM_PROMPT)
#             logger.info("Dr. Charaka AI initialized successfully")
#         except Exception as e:
#             logger.error(f"Failed to initialize Dr. Charaka AI: {str(e)}")
#             raise

#     def get_response(self, message):
#         """
#         Get a response from Dr. Charaka AI
        
#         Args:
#             message (str): The user's medical query
            
#         Returns:
#             tuple: (response_text, tokens_used, response_time)
#         """
#         try:
#             start_time = time.time()
            
#             # Send message and get response
#             response = self.chat.send_message(message)
#             response_text = response.text
            
#             # Calculate response time
#             response_time = time.time() - start_time
            
#             # Estimate tokens (rough approximation)
#             tokens_used = len(message.split()) + len(response_text.split())
            
#             logger.info(f"Generated medical response in {response_time:.2f}s using {tokens_used} tokens")
            
#             return response_text, tokens_used, response_time
            
#         except Exception as e:
#             logger.error(f"Error getting response from Dr. Charaka AI: {str(e)}")
#             raise

#     def reset_chat(self):
#         """Reset the chat history"""
#         try:
#             self.chat = self.model.start_chat(history=[])
#             # Reset the system prompt
#             self.chat.send_message(SYSTEM_PROMPT)
#             logger.info("Dr. Charaka AI chat history reset successfully")
#         except Exception as e:
#             logger.error(f"Error resetting chat: {str(e)}")
#             raise