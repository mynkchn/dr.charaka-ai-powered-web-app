# serializers.py  
from rest_framework import serializers
from .models import ChatMessage, ChatSession
from django.utils import timezone

class ChatMessageSerializer(serializers.ModelSerializer):
    formatted_timestamp = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatMessage
        fields = ['id', 'message_type', 'content', 'timestamp', 
                 'formatted_timestamp', 'tokens_used', 'response_time']
        read_only_fields = ['id', 'timestamp', 'tokens_used', 'response_time']

    def get_formatted_timestamp(self, obj):
        return obj.timestamp.strftime('%Y-%m-%d %H:%M:%S')

    def validate(self, data):
        if data.get('message_type') == 'bot' and data.get('tokens_used', 0) < 0:
            raise serializers.ValidationError(
                "Tokens used cannot be negative for bot messages"
            )
        if data.get('response_time') is not None and data.get('response_time') < 0:
            raise serializers.ValidationError("Response time cannot be negative")
        return data


class ChatSessionSerializer(serializers.ModelSerializer):
    message_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatSession
        fields = ['id', 'session_id', 'created_at', 'updated_at', 
                 'is_active', 'message_count', 'last_message']
        read_only_fields = ['id', 'session_id', 'created_at', 'updated_at']

    def get_message_count(self, obj):
        return obj.messages.count()

    def get_last_message(self, obj):
        last_message = obj.messages.order_by('-timestamp').first()
        if last_message:
            return {
                'content': last_message.content,
                'timestamp': last_message.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'type': last_message.message_type
            }
        return None

    def validate(self, data):
        if data.get('is_active') is False and self.instance and self.instance.messages.exists():
            raise serializers.ValidationError(
                "Cannot deactivate session with existing messages"
            )
        return data

