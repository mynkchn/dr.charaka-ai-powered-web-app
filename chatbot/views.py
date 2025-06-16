from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import ChatSession, ChatMessage
from .serializers import ChatMessageSerializer, ChatSessionSerializer
from .services import GeminiService
import json
import uuid
import logging
from rest_framework.views import APIView

logger = logging.getLogger(__name__)

class ChatbotView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Render the chatbot page and return initial session data"""
        try:
            # Get or create a new session for the user
            session, created = ChatSession.objects.get_or_create(
                user=request.user,
                is_active=True
            )

            # Get existing messages
            messages = [msg.to_dict() for msg in session.get_messages()]

            return render(request, 'chatbot/chatbot.html', {
                'session_id': str(session.session_id),
                'messages': messages
            })
        except Exception as e:
            logger.error(f"Error in chatbot page view: {str(e)}")
            return render(request, 'chatbot/chatbot.html', {
                'error': 'Failed to load chat session'
            })

    def post(self, request):
        """Handle chat messages"""
        try:
            message = request.data.get('message', '').strip()
            session_id = request.data.get('session_id')

            if not message:
                return Response(
                    {'error': 'Message is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get or create chat session
            if session_id:
                try:
                    session = ChatSession.objects.get(
                        session_id=session_id, 
                        user=request.user,
                        is_active=True
                    )
                except ChatSession.DoesNotExist:
                    return Response(
                        {'error': 'Invalid session ID'}, 
                        status=status.HTTP_404_NOT_FOUND
                    )
            else:
                session = ChatSession.objects.create(user=request.user)

            # Save user message
            user_message = session.add_message(
                content=message,
                message_type='user'
            )

            # Get bot response
            try:
                gemini_service = GeminiService()
                response, tokens_used, response_time = gemini_service.get_response(message)
            except Exception as e:
                logger.error(f"Error getting response from Gemini: {str(e)}")
                return Response(
                    {'error': 'Failed to get response from AI service'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # Save bot response
            bot_message = session.add_message(
                content=response,
                message_type='bot',
                tokens_used=tokens_used,
                response_time=response_time
            )

            return Response({
                'response': response,
                'session_id': str(session.session_id),
                'message_id': str(bot_message.id),
                'tokens_used': tokens_used,
                'response_time': response_time
            })

        except Exception as e:
            logger.error(f"Unexpected error in chat_api: {str(e)}")
            return Response(
                {'error': 'Internal server error'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_chat_history(request, session_id):
    """Get chat history for a session"""
    logger.info(f"Get chat history view triggered for session: {session_id}")
    try:
        session = ChatSession.objects.get(session_id=session_id, user=request.user)
        messages = session.messages.all()
        serializer = ChatMessageSerializer(messages, many=True)
        return Response(serializer.data)
    except ChatSession.DoesNotExist:
        logger.warning(f"Session not found: {session_id}")
        return Response(
            {'error': 'Chat session not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error getting chat history: {str(e)}")
        return Response(
            {'error': 'Internal server error'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def clear_chat_history(request, session_id):
    """Clear chat history for a session"""
    logger.info(f"Clear chat history view triggered for session: {session_id}")
    try:
        session = ChatSession.objects.get(session_id=session_id, user=request.user)
        session.messages.all().delete()
        return Response({'message': 'Chat history cleared successfully'})
    except ChatSession.DoesNotExist:
        logger.warning(f"Session not found: {session_id}")
        return Response(
            {'error': 'Chat session not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error clearing chat history: {str(e)}")
        return Response(
            {'error': 'Internal server error'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

class ClearChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        """Clear chat history for a session"""
        try:
            session = ChatSession.objects.get(
                session_id=session_id,
                user=request.user,
                is_active=True
            )
            
            # Delete all messages in the session
            session.messages.all().delete()
            
            # Create a new session
            new_session = ChatSession.objects.create(user=request.user)
            
            return Response({
                'status': 'success',
                'new_session_id': str(new_session.session_id)
            })
            
        except ChatSession.DoesNotExist:
            return Response(
                {'error': 'Invalid session ID'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error clearing chat: {str(e)}")
            return Response(
                {'error': 'Failed to clear chat'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )