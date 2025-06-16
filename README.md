# MediAI - Smart Healthcare Assistant

A machine learning-powered assistant for doctors at JBT Hospital, facilitating diagnosis through AI predictions and natural language interaction.

## Features

- Symptom-based illness prediction
- Report-based disease prediction (breast cancer, diabetes, heart disease, liver disease)
- OpenAI-powered chatbot for conversational interaction
- Role-based access (Doctors only)
- WhatsApp and Email report delivery
- Admin panel for model management and user administration

## Project Structure

```
mediai/
├── accounts/           # User authentication and management
├── chatbot/           # OpenAI integration and chat interface
├── core/              # Core functionality and shared components
├── predictor/         # ML models and prediction logic
├── static/            # Static files (CSS, JS, images)
├── media/             # User-uploaded files
├── templates/         # HTML templates
└── manage.py          # Django management script
```

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
Create a `.env` file with:
```
DEBUG=True
SECRET_KEY=your-secret-key
OPENAI_API_KEY=your-openai-key
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
```

4. Run migrations:
```bash
python manage.py migrate
```

5. Create superuser:
```bash
python manage.py createsuperuser
```

6. Run development server:
```bash
python manage.py runserver
```

## License

This project is proprietary and confidential. 