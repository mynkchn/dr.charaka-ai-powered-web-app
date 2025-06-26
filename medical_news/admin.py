from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import NewsArticle, NewsCategory, UserReadingHistory

@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = [
        'title_truncated', 'source_name', 'category', 'published_at', 
        'view_count', 'is_trending', 'created_at'
    ]
    list_filter = ['category', 'source_name', 'is_trending', 'published_at', 'created_at']
    search_fields = ['title', 'description', 'author', 'source_name']
    readonly_fields = ['created_at', 'updated_at', 'view_count']
    list_editable = ['is_trending', 'category']
    list_per_page = 25
    date_hierarchy = 'published_at'
    
    fieldsets = (
        ('Article Information', {
            'fields': ('title', 'description', 'content', 'author')
        }),
        ('Links and Media', {
            'fields': ('url', 'url_to_image')
        }),
        ('Categorization', {
            'fields': ('category', 'source_name', 'is_trending')
        }),
        ('Dates and Stats', {
            'fields': ('published_at', 'view_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def title_truncated(self, obj):
        return obj.title[:50] + '...' if len(obj.title) > 50 else obj.title
    title_truncated.short_description = 'Title'
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related()
    
    actions = ['mark_as_trending', 'mark_as_not_trending', 'reset_view_count']
    
    def mark_as_trending(self, request, queryset):
        queryset.update(is_trending=True)
        self.message_user(request, f'{queryset.count()} articles marked as trending.')
    mark_as_trending.short_description = 'Mark selected articles as trending'
    
    def mark_as_not_trending(self, request, queryset):
        queryset.update(is_trending=False)
        self.message_user(request, f'{queryset.count()} articles unmarked as trending.')
    mark_as_not_trending.short_description = 'Remove trending status'
    
    def reset_view_count(self, request, queryset):
        queryset.update(view_count=0)
        self.message_user(request, f'View count reset for {queryset.count()} articles.')
    reset_view_count.short_description = 'Reset view count'


@admin.register(NewsCategory)
class NewsCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'icon', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['is_active']
    
    fieldsets = (
        ('Category Information', {
            'fields': ('name', 'slug', 'description')
        }),
        ('Display', {
            'fields': ('icon', 'is_active')
        }),
    )


@admin.register(UserReadingHistory)
class UserReadingHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'article_title', 'read_at', 'read_duration']
    list_filter = ['read_at', 'article__category']
    search_fields = ['user__username', 'article__title']
    readonly_fields = ['read_at']
    date_hierarchy = 'read_at'
    
    def article_title(self, obj):
        return obj.article.title[:50] + '...' if len(obj.article.title) > 50 else obj.article.title
    article_title.short_description = 'Article'
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('user', 'article')


# Custom admin site header
admin.site.site_header = 'Dr. Charaka Medical News Admin'
admin.site.site_title = 'Medical News Admin'
admin.site.index_title = 'Medical News Administration'