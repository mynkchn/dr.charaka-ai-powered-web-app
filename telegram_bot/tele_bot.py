import os
import django
import logging
import random
import string
from datetime import datetime, timedelta, time, date
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
from accounts.models import Patient, User, Profile, Appointment

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

# Available time slots (9 AM to 5 PM, 30-minute slots)
TIME_SLOTS = [
    "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
    "12:00", "12:30", "13:00", "13:30", "14:00", "14:30",
    "15:00", "15:30", "16:00", "16:30", "17:00"
]

# In-memory storage
otp_storage = {}
user_sessions = {}

class SimpleMedicalBot:
    def __init__(self):
        # Build application with v20.8 compatible syntax
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()
        logger.info("Medical Bot with Slot Management Initialized (v20.8)")
    
    def setup_handlers(self):
        """Configure bot handlers"""
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
    
    # Database operations
    @sync_to_async
    def get_patient_by_email(self, email):
        """Get patient by email"""
        try:
            patients = Patient.objects.filter(email=email.lower())
            return patients.first() if patients.exists() else None
        except Exception as e:
            logger.error(f"Error getting patient: {e}")
            return None
    
    @sync_to_async
    def get_patient_doctor(self, patient):
        """Get patient's doctor"""
        return patient.doctor if patient.doctor else None
    
    @sync_to_async
    def get_available_slots(self, doctor, selected_date):
        """Get available time slots for a doctor on a specific date"""
        try:
            # Get existing appointments for the date
            existing_appointments = Appointment.objects.filter(
                doctor=doctor,
                appointment_date=selected_date,
                status__in=['PENDING', 'CONFIRMED']
            ).values_list('appointment_time', flat=True)
            
            # Convert to string format for comparison
            booked_times = [apt.strftime('%H:%M') for apt in existing_appointments]
            
            # Return available slots
            available_slots = [slot for slot in TIME_SLOTS if slot not in booked_times]
            return available_slots
        except Exception as e:
            logger.error(f"Error getting available slots: {e}")
            return []
    
    @sync_to_async
    def create_appointment(self, doctor, patient, appointment_date, appointment_time, reason, urgency):
        """Create new appointment"""
        try:
            # Parse time string to time object
            time_obj = datetime.strptime(appointment_time, '%H:%M').time()
            
            # Check if slot is still available
            existing = Appointment.objects.filter(
                doctor=doctor,
                appointment_date=appointment_date,
                appointment_time=time_obj,
                status__in=['PENDING', 'CONFIRMED']
            ).exists()
            
            if existing:
                return None, "Slot no longer available"
            
            # Create appointment
            appointment = Appointment.objects.create(
                doctor=doctor,
                patient=patient,
                appointment_date=appointment_date,
                appointment_time=time_obj,
                reason=reason,
                urgency=urgency,
                status='PENDING'
            )
            return appointment, "Success"
        except Exception as e:
            logger.error(f"Error creating appointment: {e}")
            return None, str(e)
    
    @sync_to_async
    def send_email_sync(self, subject, message, to_email):
        """Send email"""
        try:
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [to_email], fail_silently=False)
            return True
        except Exception as e:
            logger.error(f"Email failed: {e}")
            return False
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Start command"""
        welcome_message = """🏥 MEDICAL COMMUNICATION PORTAL

Available Services:
• Contact Your Doctor
• Book Appointment

Please select an option:"""
        
        keyboard = [
            [InlineKeyboardButton("📧 Contact Doctor", callback_data="contact_doctor")],
            [InlineKeyboardButton("📅 Book Appointment", callback_data="book_appointment")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_message, reply_markup=reply_markup)
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "contact_doctor":
            context.user_data['action'] = 'contact_doctor'
            await query.edit_message_text("📧 CONTACT DOCTOR\n\nPlease enter your registered email address:")
        
        elif query.data == "book_appointment":
            context.user_data['action'] = 'book_appointment'
            await query.edit_message_text("📅 BOOK APPOINTMENT\n\nPlease enter your registered email address:")
        
        elif query.data.startswith("date_"):
            selected_date = query.data.replace("date_", "")
            await self.show_available_slots(update, context, selected_date)
        
        elif query.data.startswith("slot_"):
            slot_info = query.data.replace("slot_", "")
            await self.handle_slot_selection(update, context, slot_info)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle text messages"""
        user_id = update.effective_user.id
        message_text = update.message.text.strip()
        
        # Handle OTP verification
        if user_id in otp_storage and context.user_data.get('awaiting_otp'):
            await self.verify_otp(update, context, message_text)
            return
        
        # Handle doctor message
        if context.user_data.get('compose_message'):
            await self.send_doctor_message(update, context, message_text)
            return
        
        # Handle appointment reason
        if context.user_data.get('awaiting_reason'):
            await self.handle_appointment_reason(update, context, message_text)
            return
        
        # Handle email identification
        if context.user_data.get('action') and not context.user_data.get('patient_verified'):
            await self.process_email_identification(update, context, message_text)
            return
        
        await update.message.reply_text("Please use /start to begin using the medical portal.")
    
    async def process_email_identification(self, update: Update, context: ContextTypes.DEFAULT_TYPE, email: str) -> None:
        """Process email and send OTP"""
        try:
            # Basic email validation
            if '@' not in email or '.' not in email:
                await update.message.reply_text("❌ Invalid email format. Please enter a valid email address.")
                return
            
            # Look up patient
            patient = await self.get_patient_by_email(email)
            if not patient:
                await update.message.reply_text("❌ Patient not found with this email address.")
                return
            
            # Generate and store OTP
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
                    f"✅ Patient Found: {patient.first_name} {patient.last_name}\n"
                    f"📧 OTP sent to: {email}\n"
                    f"⏰ Valid for {OTP_EXPIRY_MINUTES} minutes\n\n"
                    f"🔢 Please enter the OTP:"
                )
            else:
                await update.message.reply_text("❌ Failed to send OTP. Please try again.")
                # Clean up on failure
                if update.effective_user.id in otp_storage:
                    del otp_storage[update.effective_user.id]
                context.user_data.pop('awaiting_otp', None)
            
        except Exception as e:
            logger.error(f"Email processing error: {e}")
            await update.message.reply_text("❌ Error processing your request. Please try again.")
    
    async def verify_otp(self, update: Update, context: ContextTypes.DEFAULT_TYPE, otp_input: str) -> None:
        """Verify OTP"""
        user_id = update.effective_user.id
        
        if user_id not in otp_storage:
            await update.message.reply_text("❌ No OTP found. Please start over with /start")
            return
        
        stored_data = otp_storage[user_id]
        
        # Check if OTP has expired
        if datetime.now() - stored_data['timestamp'] > timedelta(minutes=OTP_EXPIRY_MINUTES):
            del otp_storage[user_id]
            context.user_data.pop('awaiting_otp', None)
            await update.message.reply_text("⏰ OTP has expired. Please start over with /start")
            return
        
        # Verify OTP
        if otp_input.strip() != stored_data['otp']:
            await update.message.reply_text("❌ Invalid OTP. Please try again.")
            return
        
        # OTP verified successfully
        patient = stored_data['patient']
        action = stored_data['action']
        
        # Clean up OTP storage
        del otp_storage[user_id]
        context.user_data.pop('awaiting_otp', None)
        context.user_data['patient_verified'] = True
        context.user_data['patient'] = patient
        
        # Get patient's doctor
        doctor = await self.get_patient_doctor(patient)
        if not doctor:
            await update.message.reply_text("❌ No doctor assigned to your account. Please contact support.")
            return
        
        context.user_data['doctor'] = doctor
        
        # Execute the requested action
        if action == 'contact_doctor':
            await self.prompt_doctor_message(update, context, patient, doctor)
        elif action == 'book_appointment':
            await self.show_available_dates(update, context, patient, doctor)
    
    async def prompt_doctor_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, patient, doctor) -> None:
        """Prompt for doctor message"""
        doctor_name = f"{doctor.first_name} {doctor.last_name}" if doctor.first_name else doctor.username
        context.user_data['compose_message'] = True
        
        await update.message.reply_text(
            f"📧 CONTACT DOCTOR\n\n"
            f"👨‍⚕️ Doctor: Dr. {doctor_name}\n\n"
            f"✍️ Please type your message for the doctor:"
        )
    
    async def send_doctor_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str) -> None:
        """Send message to doctor"""
        try:
            patient = context.user_data['patient']
            doctor = context.user_data['doctor']
            
            # Prepare email
            subject = f"Patient Message - {patient.first_name} {patient.last_name}"
            email_message = f"""🏥 PATIENT MESSAGE

👤 Patient: {patient.first_name} {patient.last_name}
📧 Email: {patient.email}
📞 Phone: {patient.contact_number}
📅 Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}

💬 Message:
{message_text}

---
Medical Communication System"""
            
            # Send email to doctor
            email_sent = await self.send_email_sync(subject, email_message, doctor.email)
            
            if email_sent:
                await update.message.reply_text(
                    f"✅ MESSAGE SENT SUCCESSFULLY\n\n"
                    f"📤 Sent to: Dr. {doctor.first_name} {doctor.last_name}\n"
                    f"⏰ Time: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
                    f"The doctor will respond via email."
                )
            else:
                await update.message.reply_text("❌ Failed to send message. Please try again.")
            
            # Reset user context
            self.reset_user_context(context)
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            await update.message.reply_text("❌ Error sending message. Please try again.")
    
    async def show_available_dates(self, update: Update, context: ContextTypes.DEFAULT_TYPE, patient, doctor) -> None:
        """Show available dates for booking"""
        doctor_name = f"{doctor.first_name} {doctor.last_name}" if doctor.first_name else doctor.username
        
        # Generate next 7 days (excluding today)
        keyboard = []
        today = date.today()
        
        for i in range(7):
            booking_date = today + timedelta(days=i+1)  # Start from tomorrow
            date_str = booking_date.strftime('%Y-%m-%d')
            display_date = booking_date.strftime('%d/%m/%Y')
            day_name = booking_date.strftime('%A')
            
            keyboard.append([
                InlineKeyboardButton(
                    f"{day_name} - {display_date}", 
                    callback_data=f"date_{date_str}"
                )
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"📅 BOOK APPOINTMENT\n\n"
            f"👨‍⚕️ Doctor: Dr. {doctor_name}\n\n"
            f"📆 Please select an appointment date:",
            reply_markup=reply_markup
        )
    
    async def show_available_slots(self, update: Update, context: ContextTypes.DEFAULT_TYPE, selected_date: str) -> None:
        """Show available time slots"""
        query = update.callback_query
        doctor = context.user_data['doctor']
        
        # Convert string to date object
        appointment_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
        context.user_data['selected_date'] = appointment_date
        
        # Get available slots from database
        available_slots = await self.get_available_slots(doctor, appointment_date)
        
        if not available_slots:
            await query.edit_message_text(
                f"❌ No slots available on {appointment_date.strftime('%d/%m/%Y')}\n\n"
                f"Please select another date or contact the clinic directly."
            )
            return
        
        # Create slot buttons (2 per row for better layout)
        keyboard = []
        for i in range(0, len(available_slots), 2):
            row = []
            for j in range(2):
                if i + j < len(available_slots):
                    slot = available_slots[i + j]
                    # Convert to 12-hour format for display
                    time_obj = datetime.strptime(slot, '%H:%M').time()
                    display_time = time_obj.strftime('%I:%M %p')
                    
                    row.append(InlineKeyboardButton(
                        display_time, 
                        callback_data=f"slot_{slot}"
                    ))
            keyboard.append(row)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"⏰ Available slots on {appointment_date.strftime('%d/%m/%Y')}:\n\n"
            f"Please select a time:",
            reply_markup=reply_markup
        )
    
    async def handle_slot_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE, selected_slot: str) -> None:
        """Handle slot selection"""
        query = update.callback_query
        context.user_data['selected_slot'] = selected_slot
        context.user_data['awaiting_reason'] = True
        
        # Convert to display format
        time_obj = datetime.strptime(selected_slot, '%H:%M').time()
        display_time = time_obj.strftime('%I:%M %p')
        selected_date = context.user_data['selected_date']
        
        await query.edit_message_text(
            f"📝 APPOINTMENT DETAILS\n\n"
            f"📅 Date: {selected_date.strftime('%d/%m/%Y')}\n"
            f"⏰ Time: {display_time}\n\n"
            f"Please provide the following information:\n\n"
            f"Format:\n"
            f"Reason: [Your reason for the visit]\n"
            f"Urgency: Low/Medium/High\n\n"
            f"Example:\n"
            f"Reason: Regular checkup and blood pressure monitoring\n"
            f"Urgency: Low"
        )
    
    async def handle_appointment_reason(self, update: Update, context: ContextTypes.DEFAULT_TYPE, reason_text: str) -> None:
        """Handle appointment reason and create booking"""
        try:
            patient = context.user_data['patient']
            doctor = context.user_data['doctor']
            selected_date = context.user_data['selected_date']
            selected_slot = context.user_data['selected_slot']
            
            # Parse reason and urgency from input
            lines = reason_text.strip().split('\n')
            reason = ""
            urgency = "MEDIUM"  # Default urgency
            
            for line in lines:
                line = line.strip()
                if line.lower().startswith('reason:'):
                    reason = line.split(':', 1)[1].strip()
                elif line.lower().startswith('urgency:'):
                    urgency_input = line.split(':', 1)[1].strip().upper()
                    if urgency_input in ['LOW', 'MEDIUM', 'HIGH']:
                        urgency = urgency_input
            
            # If no structured format, use entire text as reason
            if not reason:
                reason = reason_text.strip()
            
            # Create appointment in database
            appointment, result_message = await self.create_appointment(
                doctor, patient, selected_date, selected_slot, reason, urgency
            )
            
            if appointment:
                # Send notification email to doctor
                await self.send_appointment_email(appointment)
                
                # Format time for display
                time_obj = datetime.strptime(selected_slot, '%H:%M').time()
                display_time = time_obj.strftime('%I:%M %p')
                
                await update.message.reply_text(
                    f"✅ APPOINTMENT BOOKED SUCCESSFULLY\n\n"
                    f"📅 Date: {selected_date.strftime('%d/%m/%Y')}\n"
                    f"⏰ Time: {display_time}\n"
                    f"👨‍⚕️ Doctor: Dr. {doctor.first_name} {doctor.last_name}\n"
                    f"📝 Reason: {reason}\n"
                    f"🚨 Urgency: {urgency}\n"
                    f"📊 Status: Pending confirmation\n\n"
                    f"📧 You will receive a confirmation email shortly.\n"
                    f"🆔 Booking ID: {appointment.id}"
                )
            else:
                await update.message.reply_text(f"❌ Booking failed: {result_message}")
            
            # Reset user context
            self.reset_user_context(context)
            
        except Exception as e:
            logger.error(f"Error handling appointment: {e}")
            await update.message.reply_text("❌ Error processing appointment. Please try again.")
    
    async def send_appointment_email(self, appointment) -> None:
        """Send appointment notification email to doctor"""
        try:
            subject = f"🏥 New Appointment Request - {appointment.patient.first_name} {appointment.patient.last_name}"
            message = f"""🏥 NEW APPOINTMENT REQUEST

👤 Patient Information:
Name: {appointment.patient.first_name} {appointment.patient.last_name}
Email: {appointment.patient.email}
Phone: {appointment.patient.contact_number}

📅 Appointment Details:
Date: {appointment.appointment_date.strftime('%d/%m/%Y')}
Time: {appointment.appointment_time.strftime('%I:%M %p')}
Reason: {appointment.reason}
Urgency Level: {appointment.urgency}

📊 Status: {appointment.status}
🆔 Booking ID: {appointment.id}

Please log into the medical portal to confirm or reschedule this appointment.

---
Medical Communication System
Automated Notification"""
            
            await self.send_email_sync(subject, message, appointment.doctor.email)
            logger.info(f"Appointment email sent for booking ID: {appointment.id}")
            
        except Exception as e:
            logger.error(f"Error sending appointment email: {e}")
    
    def reset_user_context(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Reset user context after completing an action"""
        keys_to_reset = [
            'action', 'patient_verified', 'patient', 'doctor',
            'compose_message', 'awaiting_reason', 'selected_date', 'selected_slot'
        ]
        for key in keys_to_reset:
            context.user_data.pop(key, None)
    
    def generate_otp(self) -> str:
        """Generate random OTP"""
        return ''.join(random.choices(string.digits, k=OTP_LENGTH))
    
    async def send_otp_email(self, email: str, otp: str) -> bool:
        """Send OTP verification email"""
        subject = "🏥 Medical Portal - OTP Verification"
        message = f"""🏥 Medical Communication Portal
🔐 OTP Verification

Your verification code: {otp}

⏰ This code is valid for {OTP_EXPIRY_MINUTES} minutes.

If you did not request this code, please ignore this email.

---
Medical Communication System
Security Team"""
        
        return await self.send_email_sync(subject, message, email)
    
    async def run(self) -> None:
        """Start the bot with proper v20.8 async handling"""
        logger.info("Starting Medical Bot with Slot Management (v20.8)...")
        
        # Initialize the bot
        await self.application.initialize()
        await self.application.start()
        
        # Start polling
        await self.application.updater.start_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
        
        # Keep the bot running
        await self.application.updater.idle()
    
    def run_bot(self) -> None:
        """Synchronous wrapper to run the async bot"""
        import asyncio
        try:
            asyncio.run(self.run())
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Bot error: {e}")
            raise
        finally:
            logger.info("Bot shutdown complete")

# Main execution
if __name__ == "__main__":
    try:
        bot = SimpleMedicalBot()
        bot.run_bot()
    except KeyboardInterrupt:
        logger.info("Bot stopped")
    except Exception as e:
        logger.error(f"Bot error: {e}")
        raise