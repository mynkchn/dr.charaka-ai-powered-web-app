from django.db import models
from django.utils import timezone
from django.urls import reverse
from django.conf import settings

class NewsArticle(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    content = models.TextField(blank=True, null=True)
    url = models.URLField(unique=True)
    url_to_image = models.URLField(blank=True, null=True)
    source_name = models.CharField(max_length=100)
    author = models.CharField(max_length=100, blank=True, null=True)
    published_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Medical categorization
    category = models.CharField(max_length=50, default='general')
    is_trending = models.BooleanField(default=False)
    view_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-published_at']
        verbose_name = 'News Article'
        verbose_name_plural = 'News Articles'
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('medical_news:detail', kwargs={'pk': self.pk})
    
    def increment_views(self):
        self.view_count += 1
        self.save(update_fields=['view_count'])
    
    @property
    def short_description(self):
        if self.description:
            return self.description[:150] + '...' if len(self.description) > 150 else self.description
        return "No description available"
    
    @property
    def time_since_published(self):
        now = timezone.now()
        diff = now - self.published_at
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return f"Just now"


class NewsCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=50, default='fas fa-newspaper')  # FontAwesome icon
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'News Category'
        verbose_name_plural = 'News Categories'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class UserReadingHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reading_history')
    article = models.ForeignKey(NewsArticle, on_delete=models.CASCADE)
    read_at = models.DateTimeField(auto_now_add=True)
    read_duration = models.PositiveIntegerField(default=0)  # in seconds
    
    class Meta:
        unique_together = ['user', 'article']
        ordering = ['-read_at']
    
    def __str__(self):
        return f"{self.user.username} read {self.article.title}"