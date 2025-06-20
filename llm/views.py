from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile
from django.conf import settings
import json
import base64
import requests
from groq import Groq
from .models import ChatSession, ChatMessage
import os
from PIL import Image
import io
from datetime import datetime
from django.utils.dateparse import parse_datetime
import re

# Initialize Groq client
groq_client = Groq(api_key=settings.GROQ_API_KEY)

def encode_image_to_base64(image_file):
    """Convert uploaded image file to base64 string"""
    try:
        # If it's a Django UploadedFile, read it properly
        if hasattr(image_file, 'read'):
            image_file.seek(0)  # Reset to beginning
            image_data = image_file.read()
            image_file.seek(0)  # Reset again for potential reuse
        else:
            # If it's already bytes
            image_data = image_file
        
        # Encode to base64
        base64_image = base64.b64encode(image_data).decode('utf-8')
        print(f"Successfully encoded image, base64 length: {len(base64_image)}")
        return base64_image
    except Exception as e:
        print(f"Error encoding image: {str(e)}")
        return None

def clean_ai_response(response_text):
    """Clean AI response by removing markdown formatting and unnecessary symbols"""
    if not response_text:
        return response_text
    
    # Remove markdown bold/italic formatting
    cleaned = re.sub(r'\*\*([^*]+)\*\*', r'\1', response_text)  # Remove **bold**
    cleaned = re.sub(r'\*([^*]+)\*', r'\1', cleaned)  # Remove *italic*
    cleaned = re.sub(r'__([^_]+)__', r'\1', cleaned)  # Remove __bold__
    cleaned = re.sub(r'_([^_]+)_', r'\1', cleaned)  # Remove _italic_
    
    # Remove extra whitespace and line breaks
    cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned)  # Multiple line breaks to double
    cleaned = cleaned.strip()
    
    return cleaned

@login_required
def chat_interface(request):
    """Main chat interface"""
    sessions = ChatSession.objects.filter(user=request.user, is_active=True)[:10]
    active_session = sessions.first() if sessions.exists() else None
    
    context = {
        'sessions': sessions,
        'active_session': active_session,
        'messages': active_session.messages.all() if active_session else []
    }
    return render(request, 'llm/chat.html', context)

@login_required
def new_chat_session(request):
    """Create new chat session"""
    session = ChatSession.objects.create(
        user=request.user,
        title="Medical Consultation"
    )
    return redirect('llm:chat_session', session_id=session.id)

@login_required
def chat_session(request, session_id):
    """Load specific chat session"""
    session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    sessions = ChatSession.objects.filter(user=request.user, is_active=True)[:10]
    
    context = {
        'sessions': sessions,
        'active_session': session,
        'messages': session.messages.all()
    }
    return render(request, 'llm/chat.html', context)

@csrf_exempt
@login_required
def send_message(request):
    """Handle message sending"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        session_id = request.POST.get('session_id')
        content = request.POST.get('content', '')
        message_type = request.POST.get('message_type', 'text')
        
        # Get or create session
        if session_id:
            session = get_object_or_404(ChatSession, id=session_id, user=request.user)
        else:
            session = ChatSession.objects.create(
                user=request.user,
                title=content[:50] if content else "Medical Chat"
            )
        
        # Create user message
        user_message = ChatMessage.objects.create(
            session=session,
            sender='user',
            message_type=message_type,
            content=content
        )
        
        # Handle image upload
        uploaded_image = None
        if 'image' in request.FILES:
            uploaded_image = request.FILES['image']
            user_message.image = uploaded_image
            user_message.message_type = 'image' if not content else 'mixed'
            user_message.save()
            print(f"Image uploaded: {uploaded_image.name}, size: {uploaded_image.size}")
        
        # Generate AI response
        ai_response = generate_ai_response(user_message, uploaded_image)
        
        # Create assistant message
        assistant_message = ChatMessage.objects.create(
            session=session,
            sender='assistant',
            message_type='text',
            content=ai_response,
            is_processed=True
        )
        
        # Safely update session.updated_at with proper type checking
        ts = assistant_message.timestamp
        if isinstance(ts, str):
            parsed_ts = parse_datetime(ts)
            session.updated_at = parsed_ts if parsed_ts else datetime.now()
        elif isinstance(ts, datetime):
            session.updated_at = ts
        else:
            session.updated_at = datetime.now()  # fallback
        
        # Update session title if default or empty
        if not session.title or session.title == "New Chat":
            session.title = content[:50] if content else "Medical Consultation"
        session.save()
        
        return JsonResponse({
            'success': True,
            'session_id': str(session.id),
            'user_message': {
                'id': str(user_message.id),
                'content': user_message.content,
                'timestamp': user_message.timestamp.isoformat(),
                'image_url': user_message.image.url if user_message.image else None
            },
            'assistant_message': {
                'id': str(assistant_message.id),
                'content': assistant_message.content,
                'timestamp': assistant_message.timestamp.isoformat()
            }
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def generate_ai_response(user_message, uploaded_image=None):
    """Generate AI response using Groq with image support"""
    try:
        # Prepare system prompt for medical AI
        system_prompt = """You are Dr. Charaka, an advanced AI medical assistant with vision capabilities. You can analyze medical images including X-rays, CT scans, MRIs, lab reports, skin conditions, and other medical imagery.

When an image is provided:
- Analyze it thoroughly and describe what you observe
- Provide relevant medical insights and observations
- Suggest possible conditions or findings based on the image
- Always remind that this is AI analysis and professional medical review is essential

For text queries, provide evidence-based medical information and recommendations."""
        
        # Prepare messages for API
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add conversation history (last 6 messages for context)
        previous_messages = ChatMessage.objects.filter(
            session=user_message.session
        ).order_by('-timestamp')[:6]
        
        for msg in reversed(previous_messages):
            if msg.id != user_message.id:  # Don't include current message
                role = "user" if msg.sender == "user" else "assistant"
                messages.append({
                    "role": role,
                    "content": msg.content
                })
        
        # Prepare current user message content
        has_image = uploaded_image is not None
        print(f"Processing message - Has image: {has_image}")
        
        if has_image:
            # Handle image message
            base64_image = encode_image_to_base64(uploaded_image)
            print(f"Base64 encoding result: {'Success' if base64_image else 'Failed'}")
            
            if base64_image:
                # Create multimodal message with image
                user_content = []
                
                # Add text if present
                if user_message.content and user_message.content.strip():
                    user_content.append({
                        "type": "text", 
                        "text": user_message.content
                    })
                else:
                    user_content.append({
                        "type": "text", 
                        "text": "Please analyze this medical image and provide your professional insights."
                    })
                
                # Add image
                user_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    }
                })
                
                messages.append({
                    "role": "user",
                    "content": user_content
                })
                
                print("Multimodal message created successfully")
            else:
                # Fallback if image encoding fails
                messages.append({
                    "role": "user",
                    "content": "I uploaded an image but there was an issue processing it. Could you help me with general medical guidance instead?"
                })
                print("Image encoding failed, using fallback message")
        else:
            # Text-only message
            messages.append({
                "role": "user",
                "content": user_message.content or "Hello, I need medical assistance."
            })
            print("Text-only message created")
        
        print(f"Sending {len(messages)} messages to Groq API")
        
        # Call Groq API
        response = groq_client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=messages,
            max_tokens=1500,
            temperature=0.3  # Lower temperature for more consistent medical responses
        )
        
        # Get and clean the response
        raw_response = response.choices[0].message.content
        print(f"Raw response length: {len(raw_response)}")
        cleaned_response = clean_ai_response(raw_response)
        
        return cleaned_response
        
    except Exception as e:
        print(f"Error in generate_ai_response: {str(e)}")
        error_msg = f"I apologize, but I'm experiencing technical difficulties. Please try again. Error details: {str(e)}"
        return clean_ai_response(error_msg)

@login_required
def delete_session(request, session_id):
    """Delete chat session"""
    if request.method == 'POST':
        session = get_object_or_404(ChatSession, id=session_id, user=request.user)
        session.is_active = False
        session.save()
        return JsonResponse({'success': True})
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required
def chat_history(request):
    """View all chat sessions"""
    sessions = ChatSession.objects.filter(user=request.user, is_active=True)
    return render(request, 'llm/history.html', {'sessions': sessions})