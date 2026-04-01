# Dr. Charaka — AI-Powered Medical Web Application

Dr. Charaka is an AI-driven medical assistant web application built with Django. It combines large language model (LLM) capabilities with practical clinical tools to help users understand symptoms, check drug interactions, receive AI-generated medical guidance, and stay informed with the latest medical news — all within a single, unified platform.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Environment Variables](#environment-variables)
  - [Running the Application](#running-the-application)
- [Usage](#usage)
- [Disclaimer](#disclaimer)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

Dr. Charaka is named after the ancient Indian physician and is designed to make preliminary medical information more accessible. The application integrates a conversational AI interface, a disease predictor, a drug interaction checker, a community forum, and a medical news aggregator into one cohesive Django-based web platform.

This project is intended for educational and informational purposes and does not replace professional medical advice.

---

## Features

### AI Medical Chat (Conversation)
A conversational interface powered by an LLM backend that answers general medical questions, explains symptoms, and provides guidance in natural language.

### Disease Predictor
A machine learning-based symptom checker that predicts possible conditions based on user-provided symptoms, using trained models stored in the `ml_models` directory.

### Drug Interaction Checker
Users can input multiple medications to check for known drug interactions, helping flag potential contraindications before consulting a physician.

### Medical News Feed
An aggregated feed of the latest medical and health news, keeping users informed on current developments in medicine and healthcare.

### Community Forum
A peer-to-peer discussion space where users can post questions, share experiences, and engage with others on health-related topics.

### User Accounts
Full user authentication system supporting registration, login, profile management, and conversation history.

### Media & Image Support
Support for uploading and processing medical images as part of AI interactions.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend Framework | Django (Python) |
| Frontend | HTML, CSS, JavaScript (Django Templates) |
| AI / LLM Integration | LLM module (configured via environment) |
| Machine Learning | Scikit-learn / custom ML models |
| Database | SQLite (default); configurable for PostgreSQL |
| Static Files | Django staticfiles |

---

## Project Structure

```
dr.charaka-ai-powered-web-app/
|
|-- accounts/           # User authentication, registration, profiles
|-- community/          # Community forum and discussion threads
|-- conversation/       # AI chat interface and conversation history
|-- core/               # Project settings, URLs, WSGI/ASGI config
|-- drug_interaction/   # Drug interaction checker module
|-- llm/                # LLM integration and prompt handling
|-- media/              # User-uploaded media files
|-- mediai/             # Core AI utility functions
|-- medical_news/       # Medical news aggregation
|-- ml_models/          # Trained machine learning model files
|-- predictor/          # Disease prediction logic and views
|-- static/             # CSS, JS, and static assets
|-- templates/          # HTML templates
|-- utils/              # Shared utility functions
|-- manage.py           # Django management script
|-- requirements.txt    # Python dependencies
```

---

## Getting Started

### Prerequisites

- Python 3.9 or higher
- pip
- Git
- A virtual environment tool (venv or conda)

### Installation

1. Clone the repository:

```bash
git clone https://github.com/mynkchn/dr.charaka-ai-powered-web-app.git
cd dr.charaka-ai-powered-web-app
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate        # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Apply database migrations:

```bash
python manage.py migrate
```

5. Collect static files:

```bash
python manage.py collectstatic
```

### Environment Variables

Create a `.env` file in the root directory and configure the following variables:

```env
SECRET_KEY=your_django_secret_key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# LLM API Key (e.g., Groq, OpenAI, or other provider)
LLM_API_KEY=your_llm_api_key

# News API Key (for medical news aggregation)
NEWS_API_KEY=your_news_api_key
```

> Do not commit your `.env` file to version control. Add it to `.gitignore`.

### Running the Application

```bash
python manage.py runserver
```

The application will be available at `http://127.0.0.1:8000/`.

---

## Usage

1. Register for an account or log in.
2. Use the chat interface to ask medical questions in plain language.
3. Navigate to the Disease Predictor to enter symptoms and receive possible condition matches.
4. Open the Drug Interaction Checker and enter medication names to check for conflicts.
5. Browse the Medical News section for curated health and medical updates.
6. Participate in the Community forum to discuss health topics with other users.

---

## Disclaimer

Dr. Charaka is an informational tool and is not a substitute for professional medical advice, diagnosis, or treatment. Always consult a qualified healthcare provider regarding any medical condition or treatment. The AI responses are generated by a language model and may not be accurate, complete, or appropriate for individual medical situations.

---

## Contributing

Contributions are welcome. To contribute:

1. Fork the repository.
2. Create a new branch: `git checkout -b feature/your-feature-name`
3. Commit your changes: `git commit -m "Add your feature"`
4. Push to your branch: `git push origin feature/your-feature-name`
5. Open a pull request.

Please ensure your code follows existing style conventions and that any new features are documented.

---

## License

This project is open source. Please refer to the repository for licensing details or contact the author for clarification.

---

Built by [mynkchn](https://github.com/mynkchn)
