import os
import django
import logging
import random
import string
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from django.core.mail import send_mail
from django.conf import settings
from asgiref.sync import sync_to_async

# Django setup
import sys
sys.path.append(r'D:\project_ai_hackathon')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mediai.settings')
django.setup()

# Import Django models
from accounts.models import Patient, User, Profile

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('medical_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Bot configuration
BOT_TOKEN = "7953046471:AAFi4pFiEm-_tVu30Ci81Pb3THkAdmYtKFY"
OTP_EXPIRY_MINUTES = 10
OTP_LENGTH = 6

# In-memory storage
otp_storage = {}
user_sessions = {}

class SimpleMedicalBot:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()
        logger.info("Simple Medical Bot Initialized")
    
    def setup_handlers(self):
        """Configure bot handlers"""
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
    
    # Database operations
    @sync_to_async
    def get_patient_by_email(self, email):
        """Get patient by email - handle multiple records"""
        try:
            patients = Patient.objects.filter(email=email.lower())
            if patients.exists():
                # Return the first patient if multiple exist
                return patients.first()
            return None
        except Exception as e:
            logger.error(f"Error getting patient by email: {e}")
            return None
    
    @sync_to_async
    def count_patients_by_email(self, email):
        """Count patients with same email"""
        try:
            return Patient.objects.filter(email=email.lower()).count()
        except Exception as e:
            logger.error(f"Error counting patients: {e}")
            return 0
    
    @sync_to_async
    def get_patient_doctor(self, patient):
        """Get patient's assigned doctor"""
        return patient.doctor if patient.doctor else None
    
    @sync_to_async
    def send_email_sync(self, subject, message, to_email):
        """Send email synchronously"""
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [to_email],
                fail_silently=False,
            )
            logger.info(f"Email sent successfully to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Email sending failed: {e}")
            return False
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command"""
        welcome_message = """
MEDICAL COMMUNICATION PORTAL

Available Services:
- Contact Your Doctor
- Book Appointment

Please select an option to begin:
        """
        
        keyboard = [
            [InlineKeyboardButton("Contact Doctor", callback_data="contact_doctor")],
            [InlineKeyboardButton("Book Appointment", callback_data="book_appointment")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_message, reply_markup=reply_markup)
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "contact_doctor":
            context.user_data['action'] = 'contact_doctor'
            await query.edit_message_text(
                "CONTACT DOCTOR\n\n"
                "Please enter your registered email address:"
            )
        elif query.data == "book_appointment":
            context.user_data['action'] = 'book_appointment'
            await query.edit_message_text(
                "BOOK APPOINTMENT\n\n"
                "Please enter your registered email address:"
            )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        user_id = update.effective_user.id
        message_text = update.message.text.strip()
        
        # Handle OTP verification
        if user_id in otp_storage and context.user_data.get('awaiting_otp'):
            await self.verify_otp(update, context, message_text)
            return
        
        # Handle doctor message composition
        if context.user_data.get('compose_message'):
            await self.send_doctor_message(update, context, message_text)
            return
        
        # Handle appointment booking
        if context.user_data.get('book_appointment_details'):
            await self.send_appointment_request(update, context, message_text)
            return
        
        # Handle email identification
        if context.user_data.get('action') and not context.user_data.get('patient_verified'):
            await self.process_email_identification(update, context, message_text)
            return
        
        await update.message.reply_text(
            "Please use /start to begin or select an option from the menu."
        )
    
    async def process_email_identification(self, update: Update, context: ContextTypes.DEFAULT_TYPE, email):
        """Process email identification"""
        try:
            # Validate email format
            if '@' not in email or '.' not in email:
                await update.message.reply_text(
                    "Invalid email format. Please enter a valid email address."
                )
                return
            
            patient = await self.get_patient_by_email(email)
            
            if not patient:
                await update.message.reply_text(
                    "Patient record not found. Please check your email address."
                )
                return
            
            # Check if multiple patients exist with same email
            patients_count = await self.count_patients_by_email(email)
            if patients_count > 1:
                await update.message.reply_text(
                    f"Multiple patient records found with this email.\n"
                    f"Using: {patient.first_name} {patient.last_name} (ID: {patient.id})\n\n"
                    f"If this is not correct, please contact support."
                )
            
            # Generate and send OTP
            otp = self.generate_otp()
            otp_storage[update.effective_user.id] = {
                'otp': otp,
                'patient': patient,
                'timestamp': datetime.now(),
                'action': context.user_data.get('action')
            }
            
            context.user_data['awaiting_otp'] = True
            
            # Send OTP via email
            email_sent = await self.send_otp_email(email, otp)
            
            if email_sent:
                await update.message.reply_text(
                    f"Patient found: {patient.first_name} {patient.last_name}\n"
                    f"Patient ID: {patient.id}\n\n"
                    f"OTP sent to: {email}\n"
                    f"Valid for {OTP_EXPIRY_MINUTES} minutes\n\n"
                    "Please enter the 6-digit OTP:"
                )
            else:
                await update.message.reply_text(
                    "Failed to send OTP email. Please try again later."
                )
                # Clean up
                if update.effective_user.id in otp_storage:
                    del otp_storage[update.effective_user.id]
                context.user_data.pop('awaiting_otp', None)
            
        except Exception as e:
            logger.error(f"Error in email identification: {e}")
            await update.message.reply_text(
                "Error processing your request. Please try again."
            )
    
    async def verify_otp(self, update: Update, context: ContextTypes.DEFAULT_TYPE, otp_input):
        """Verify OTP and proceed"""
        user_id = update.effective_user.id
        
        if user_id not in otp_storage:
            await update.message.reply_text("No OTP request found. Please start over.")
            return
        
        stored_data = otp_storage[user_id]
        
        # Check OTP expiry
        if datetime.now() - stored_data['timestamp'] > timedelta(minutes=OTP_EXPIRY_MINUTES):
            del otp_storage[user_id]
            context.user_data.pop('awaiting_otp', None)
            await update.message.reply_text("OTP expired. Please request a new one.")
            return
        
        # Verify OTP
        if otp_input.strip() != stored_data['otp']:
            await update.message.reply_text(
                "Invalid OTP. Please check and try again."
            )
            return
        
        # OTP verified successfully
        patient = stored_data['patient']
        action = stored_data['action']
        
        # Clean up
        del otp_storage[user_id]
        context.user_data.pop('awaiting_otp', None)
        context.user_data['patient_verified'] = True
        context.user_data['patient'] = patient
        
        # Check if doctor is assigned
        doctor = await self.get_patient_doctor(patient)
        if not doctor:
            await update.message.reply_text(
                "No doctor assigned to your profile. Please contact administration."
            )
            return
        
        context.user_data['doctor'] = doctor
        
        # Execute action
        if action == 'contact_doctor':
            await self.prompt_doctor_message(update, context, patient, doctor)
        elif action == 'book_appointment':
            await self.prompt_appointment_details(update, context, patient, doctor)
    
    async def prompt_doctor_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, patient, doctor):
        """Prompt for doctor message"""
        doctor_name = f"{doctor.first_name} {doctor.last_name}" if doctor.first_name else doctor.username
        
        context.user_data['compose_message'] = True
        
        await update.message.reply_text(
            f"CONTACT DOCTOR\n\n"
            f"Doctor: Dr. {doctor_name}\n\n"
            f"Please type your message to the doctor:"
        )
    
    async def send_doctor_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_text):
        """Send message to doctor"""
        try:
            patient = context.user_data['patient']
            doctor = context.user_data['doctor']
            
            doctor_name = f"{doctor.first_name} {doctor.last_name}" if doctor.first_name else doctor.username
            patient_name = f"{patient.first_name} {patient.last_name}"
            
            # Compose email to doctor
            subject = f"Patient Message - {patient_name}"
            email_message = f"""
PATIENT MESSAGE

Patient Details:
Name: {patient_name}
Email: {patient.email}
Phone: {patient.contact_number}
Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}

Message:
{message_text}

Please respond to the patient directly.

Medical Communication System
            """
            
            # Send email to doctor
            email_sent = await self.send_email_sync(subject, email_message, doctor.email)
            
            if email_sent:
                await update.message.reply_text(
                    f"MESSAGE SENT SUCCESSFULLY\n\n"
                    f"Your message has been sent to Dr. {doctor_name}\n"
                    f"The doctor will respond to your registered email.\n\n"
                    f"Sent at: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
                )
            else:
                await update.message.reply_text(
                    "Failed to send message. Please try again later."
                )
            
            # Reset context
            self.reset_user_context(context)
            
        except Exception as e:
            logger.error(f"Error sending doctor message: {e}")
            await update.message.reply_text(
                "Error sending message. Please try again."
            )
    
    async def prompt_appointment_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE, patient, doctor):
        """Prompt for appointment details"""
        doctor_name = f"{doctor.first_name} {doctor.last_name}" if doctor.first_name else doctor.username
        
        context.user_data['book_appointment_details'] = True
        
        await update.message.reply_text(
            f"BOOK APPOINTMENT\n\n"
            f"Doctor: Dr. {doctor_name}\n\n"
            f"Please provide appointment details:\n\n"
            f"Format:\n"
            f"Preferred Date: DD/MM/YYYY\n"
            f"Preferred Time: HH:MM AM/PM\n"
            f"Reason: Brief description\n"
            f"Urgency: Low/Medium/High\n\n"
            f"Example:\n"
            f"Preferred Date: 25/12/2024\n"
            f"Preferred Time: 02:00 PM\n"
            f"Reason: Follow-up consultation\n"
            f"Urgency: Medium"
        )
    
    async def send_appointment_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE, details):
        """Send appointment request to doctor"""
        try:
            patient = context.user_data['patient']
            doctor = context.user_data['doctor']
            
            doctor_name = f"{doctor.first_name} {doctor.last_name}" if doctor.first_name else doctor.username
            patient_name = f"{patient.first_name} {patient.last_name}"
            
            subject = f"Appointment Request - {patient_name}"
            email_message = f"""
APPOINTMENT REQUEST

Patient Details:
Name: {patient_name}
Email: {patient.email}
Phone: {patient.contact_number}
Request Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}

Appointment Details:
{details}

Please confirm the appointment with the patient.

Medical Communication System
            """
            
            email_sent = await self.send_email_sync(subject, email_message, doctor.email)
            
            if email_sent:
                await update.message.reply_text(
                    f"APPOINTMENT REQUEST SENT\n\n"
                    f"Your request has been sent to Dr. {doctor_name}\n"
                    f"The doctor will contact you to confirm.\n\n"
                    f"Sent at: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
                )
            else:
                await update.message.reply_text(
                    "Failed to send appointment request. Please try again later."
                )
            
            # Reset context
            self.reset_user_context(context)
            
        except Exception as e:
            logger.error(f"Error sending appointment request: {e}")
            await update.message.reply_text(
                "Error sending appointment request. Please try again."
            )
    
    def reset_user_context(self, context):
        """Reset user context data"""
        keys_to_remove = [
            'action', 'patient_verified', 'patient', 'doctor',
            'compose_message', 'book_appointment_details'
        ]
        for key in keys_to_remove:
            context.user_data.pop(key, None)
    
    def generate_otp(self):
        """Generate random OTP"""
        return ''.join(random.choices(string.digits, k=OTP_LENGTH))
    
    async def send_otp_email(self, email, otp):
        """Send OTP via email"""
        subject = "Medical Portal - OTP Verification"
        message = f"""
Medical Communication Portal
OTP Verification

Your One-Time Password (OTP) is: {otp}

This OTP is valid for {OTP_EXPIRY_MINUTES} minutes.
Do not share this OTP with anyone.

Medical Communication System
        """
        
        return await self.send_email_sync(subject, message, email)
    
    def run(self):
        """Start the bot"""
        logger.info("Starting Simple Medical Bot...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

# Main execution
if __name__ == "__main__":
    try:
        bot = SimpleMedicalBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}")
        raise