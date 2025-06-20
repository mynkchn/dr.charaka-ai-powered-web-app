# # models.py
# from django.db import models
# from django.conf import settings
# import uuid

# class ChatSession(models.Model):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
#     session_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#     is_active = models.BooleanField(default=True)

#     class Meta:
#         indexes = [
#             models.Index(fields=['session_id']),
#             models.Index(fields=['user', 'created_at']),
#         ]
#         ordering = ['-created_at']

#     def __str__(self):
#         return f"Chat Session {self.session_id}"

#     def save(self, *args, **kwargs):
#         if not self.session_id:
#             self.session_id = uuid.uuid4()
#         super().save(*args, **kwargs)

#     def get_messages(self):
#         """Get all messages for this session"""
#         return self.messages.all()

#     def add_message(self, content, message_type='user', tokens_used=0, response_time=None):
#         """Add a new message to this session"""
#         return self.messages.create(
#             content=content,
#             message_type=message_type,
#             tokens_used=tokens_used,
#             response_time=response_time
#         )

# class ChatMessage(models.Model):
#     MESSAGE_TYPES = [
#         ('user', 'User'),
#         ('bot', 'Bot'),
#         ('system', 'System'),
#     ]
    
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
#     message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES)
#     content = models.TextField()
#     timestamp = models.DateTimeField(auto_now_add=True)
#     tokens_used = models.IntegerField(default=0)
#     response_time = models.FloatField(null=True, blank=True)

#     class Meta:
#         indexes = [
#             models.Index(fields=['session', 'timestamp']),
#             models.Index(fields=['message_type']),
#         ]
#         ordering = ['timestamp']

#     def __str__(self):
#         return f"{self.message_type}: {self.content[:50]}..."

#     def clean(self):
#         if self.message_type == 'bot' and self.tokens_used < 0:
#             raise models.ValidationError("Tokens used cannot be negative for bot messages")
#         if self.response_time is not None and self.response_time < 0:
#             raise models.ValidationError("Response time cannot be negative")

#     def to_dict(self):
#         """Convert message to dictionary format"""
#         return {
#             'id': str(self.id),
#             'type': self.message_type,
#             'content': self.content,
#             'timestamp': self.timestamp.isoformat(),
#             'tokens_used': self.tokens_used,
#             'response_time': self.response_time
#         }