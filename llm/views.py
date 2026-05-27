from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json
import base64
import re
import uuid
from .models import ChatSession, ChatMessage
import google.generativeai as genai

# ── Configure Gemini ──────────────────────────────────────────────────────────
genai.configure(api_key=settings.GEMINI_API_KEY)
gemini_model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",           # fast + supports vision
    system_instruction="""You are Dr. Charaka, an advanced AI medical assistant with vision \
capabilities. You can analyze medical images including X-rays, CT scans, MRIs, lab reports, \
skin conditions, and other medical imagery.

When an image is provided:
- Analyze it thoroughly and describe what you observe
- Provide relevant medical insights and observations
- Suggest possible conditions or findings based on the image
- Always remind that this is AI analysis and professional medical review is essential

For text queries, provide evidence-based medical information and recommendations.
Format your response using these section headers where relevant: ASSESSMENT:, \
RECOMMENDATIONS:, NOTE:, DISCLAIMER:"""
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def clean_ai_response(text):
    """Strip markdown bold/italic so the frontend renders plain text."""
    if not text:
        return text
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*',     r'\1', text)
    text = re.sub(r'__([^_]+)__',     r'\1', text)
    text = re.sub(r'_([^_]+)_',       r'\1', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def build_history_for_gemini(session, current_message_id):
    """Return Gemini-compatible chat history (excludes the current message)."""
    previous = (
        ChatMessage.objects
        .filter(session=session)
        .exclude(id=current_message_id)
        .order_by('timestamp')[:10]          # last 10 turns for context
    )
    history = []
    for msg in previous:
        role = "user" if msg.sender == "user" else "model"
        history.append({"role": role, "parts": [msg.content or ""]})
    return history


# ── Views ─────────────────────────────────────────────────────────────────────

@login_required
def chat_interface(request):
    """Render the main chat page."""
    sessions = ChatSession.objects.filter(user=request.user, is_active=True)[:10]
    active_session = sessions.first() if sessions.exists() else None
    session_id = str(active_session.id) if active_session else str(uuid.uuid4())

    context = {
        'sessions': sessions,
        'active_session': active_session,
        'session_id': session_id,
        'messages': active_session.messages.all() if active_session else [],
    }
    return render(request, 'llm/chat.html', context)


@login_required
def new_chat_session(request):
    session = ChatSession.objects.create(user=request.user, title="Medical Consultation")
    return redirect('llm:chat_session', session_id=session.id)


@login_required
def chat_session_view(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    sessions = ChatSession.objects.filter(user=request.user, is_active=True)[:10]
    context = {
        'sessions': sessions,
        'active_session': session,
        'session_id': str(session.id),
        'messages': session.messages.all(),
    }
    return render(request, 'llm/chat.html', context)


# ── Main API endpoint (called by the frontend JS) ─────────────────────────────
@csrf_exempt
@login_required
def api_chat(request):
    """
    POST /llm/api/chat/
    Accepts JSON:  { "message": "...", "session_id": "..." }
    Also accepts multipart/form-data when an image is attached.
    Returns JSON:  { "response": "...", "session_id": "..." }
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        # ── Parse body ───────────────────────────────────────────────────────
        content_type = request.content_type or ''

        if 'multipart/form-data' in content_type:
            # Image upload path
            content    = request.POST.get('message', '')
            session_id = request.POST.get('session_id', '')
            image_file = request.FILES.get('image')
        else:
            # Plain JSON path (used by the standalone HTML frontend)
            body       = json.loads(request.body)
            content    = body.get('message', '')
            session_id = body.get('session_id', '')
            image_file = None

        if not content and not image_file:
            return JsonResponse({'error': 'Empty message'}, status=400)

        # ── Get or create session ────────────────────────────────────────────
        session = None
        if session_id:
            try:
                session = ChatSession.objects.get(id=session_id, user=request.user)
            except (ChatSession.DoesNotExist, ValueError):
                pass          # UUID might be a temp client-side ID → create new

        if session is None:
            session = ChatSession.objects.create(
                user=request.user,
                title=(content[:50] if content else "Medical Consultation"),
            )

        # ── Save user message ────────────────────────────────────────────────
        msg_type = 'text'
        if image_file and content:
            msg_type = 'mixed'
        elif image_file:
            msg_type = 'image'

        user_msg = ChatMessage.objects.create(
            session=session,
            sender='user',
            message_type=msg_type,
            content=content,
        )
        if image_file:
            user_msg.image = image_file
            user_msg.save()

        # ── Generate Gemini response ─────────────────────────────────────────
        ai_text = generate_gemini_response(user_msg, image_file, session)

        # ── Save assistant message ───────────────────────────────────────────
        assistant_msg = ChatMessage.objects.create(
            session=session,
            sender='assistant',
            message_type='text',
            content=ai_text,
            is_processed=True,
        )

        # Update session title on first real message
        if session.title in ("New Chat", "Medical Consultation", ""):
            session.title = content[:50] if content else "Medical Consultation"
        session.save()

        return JsonResponse({
            'response':   ai_text,
            'session_id': str(session.id),
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


# ── Clear / new-chat endpoint (called by the "New chat" button) ───────────────
@csrf_exempt
@login_required
def api_clear_session(request, session_id):
    """
    POST /llm/api/chat/<session_id>/clear/
    Marks the session inactive and returns a new session id.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        session = ChatSession.objects.get(id=session_id, user=request.user)
        session.is_active = False
        session.save()
    except (ChatSession.DoesNotExist, ValueError):
        pass   # fine — just create a new one below

    new_session = ChatSession.objects.create(
        user=request.user,
        title="Medical Consultation",
    )
    return JsonResponse({'new_session_id': str(new_session.id)})


# ── Gemini response generator ─────────────────────────────────────────────────

def generate_gemini_response(user_msg, image_file=None, session=None):
    """Call Gemini (with optional image) and return cleaned response text."""
    try:
        # Build chat history for multi-turn context
        history = build_history_for_gemini(session, user_msg.id) if session else []

        chat = gemini_model.start_chat(history=history)

        # Build the message parts
        parts = []

        if image_file:
            image_file.seek(0)
            image_bytes = image_file.read()
            image_file.seek(0)

            # Detect MIME type
            name = getattr(image_file, 'name', '').lower()
            if name.endswith('.png'):
                mime = 'image/png'
            elif name.endswith('.gif'):
                mime = 'image/gif'
            elif name.endswith('.webp'):
                mime = 'image/webp'
            else:
                mime = 'image/jpeg'

            parts.append({"mime_type": mime, "data": image_bytes})

        parts.append(user_msg.content or "Please analyze this medical image.")

        response = chat.send_message(parts)
        return clean_ai_response(response.text)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return clean_ai_response(
            f"I apologize, but I encountered an error generating a response. "
            f"Please try again. (Error: {str(e)})"
        )


# ── Other views ───────────────────────────────────────────────────────────────

@login_required
def delete_session(request, session_id):
    if request.method == 'POST':
        session = get_object_or_404(ChatSession, id=session_id, user=request.user)
        session.is_active = False
        session.save()
        return JsonResponse({'success': True})
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def chat_history(request):
    sessions = ChatSession.objects.filter(user=request.user, is_active=True)
    return render(request, 'llm/history.html', {'sessions': sessions})