from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django.views.generic import ListView, DetailView
from django.db.models import Q
from .models import NewsArticle, NewsCategory
from .services import NewsAPIService
import logging

logger = logging.getLogger(__name__)

class NewsListView(ListView):
    model = NewsArticle
    template_name = 'medical_news/news_list.html'
    context_object_name = 'articles'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = NewsArticle.objects.all()
        
        # Search functionality
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(content__icontains=search_query)
            )
        
        # Category filter
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        return queryset.order_by('-published_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_category'] = self.request.GET.get('category', '')
        
        # Get available categories
        categories = NewsArticle.objects.values_list('category', flat=True).distinct()
        context['categories'] = [cat for cat in categories if cat]
        
        # Get trending articles for sidebar
        context['trending_articles'] = NewsArticle.objects.filter(
            is_trending=True
        )[:5]
        
        return context


class NewsDetailView(DetailView):
    model = NewsArticle
    template_name = 'medical_news/news_detail.html'
    context_object_name = 'article'
    
    def get_object(self):
        article = super().get_object()
        # Increment view count
        article.increment_views()
        
        # Add to user's reading history if authenticated
        if self.request.user.is_authenticated:
            from .models import UserReadingHistory
            UserReadingHistory.objects.get_or_create(
                user=self.request.user,
                article=article
            )
        
        return article
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get related articles (same category)
        context['related_articles'] = NewsArticle.objects.filter(
            category=self.object.category
        ).exclude(pk=self.object.pk)[:4]
        
        return context


@cache_page(60 * 5)  # Cache for 5 minutes
def fetch_latest_news(request):
    """Fetch latest news from API and save to database"""
    if request.method == 'POST':
        try:
            news_service = NewsAPIService()
            
            # Fetch trending medical news
            articles = news_service.get_trending_medical_news(page_size=30)
            
            if articles:
                saved_count = news_service.save_articles_to_db(articles)
                messages.success(
                    request, 
                    f'Successfully fetched and saved {saved_count} new articles!'
                )
            else:
                messages.warning(request, 'No new articles found.')
                
        except Exception as e:
            logger.error(f"Error fetching news: {str(e)}")
            messages.error(request, 'Error fetching latest news. Please try again.')
    
    return JsonResponse({'status': 'success'})


def search_news(request):
    """AJAX search for news articles"""
    query = request.GET.get('q', '')
    
    if len(query) < 3:
        return JsonResponse({'articles': []})
    
    try:
        # Search in database first
        articles = NewsArticle.objects.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query)
        )[:10]
        
        # If no results in DB, try API search
        if not articles:
            news_service = NewsAPIService()
            api_articles = news_service.search_medical_news(query, page_size=10)
            
            if api_articles:
                # Save to DB and get saved articles
                saved_count = news_service.save_articles_to_db(api_articles)
                articles = NewsArticle.objects.filter(
                    Q(title__icontains=query) |
                    Q(description__icontains=query)
                )[:10]
        
        # Serialize articles for JSON response
        articles_data = []
        for article in articles:
            articles_data.append({
                'id': article.pk,
                'title': article.title,
                'description': article.short_description,
                'url': article.get_absolute_url(),
                'image': article.url_to_image,
                'source': article.source_name,
                'published_at': article.time_since_published,
            })
        
        return JsonResponse({'articles': articles_data})
        
    except Exception as e:
        logger.error(f"Error in search: {str(e)}")
        return JsonResponse({'error': 'Search failed'}, status=500)


def news_by_category(request, category):
    """Display news filtered by category"""
    articles = NewsArticle.objects.filter(category=category).order_by('-published_at')
    
    # Pagination
    paginator = Paginator(articles, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'articles': page_obj,
        'category': category,
        'category_display': category.replace('-', ' ').title(),
        'page_obj': page_obj,
    }
    
    return render(request, 'medical_news/category_news.html', context)


def trending_news(request):
    """Display trending news"""
    # Mark most viewed articles as trending
    trending_articles = NewsArticle.objects.filter(
        view_count__gte=5
    ).order_by('-view_count', '-published_at')[:20]
    
    # Update trending status
    NewsArticle.objects.update(is_trending=False)
    for article in trending_articles:
        article.is_trending = True
        article.save(update_fields=['is_trending'])
    
    # Pagination
    paginator = Paginator(trending_articles, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'articles': page_obj,
        'page_obj': page_obj,
        'is_trending_page': True,
    }
    
    return render(request, 'medical_news/trending_news.html', context)


def dashboard_stats(request):
    """Get dashboard statistics for admin"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    from django.db.models import Count
    from datetime import datetime, timedelta
    
    # Calculate statistics
    total_articles = NewsArticle.objects.count()
    today = datetime.now().date()
    articles_today = NewsArticle.objects.filter(created_at__date=today).count()
    
    # Articles by category
    category_stats = NewsArticle.objects.values('category').annotate(
        count=Count('category')
    ).order_by('-count')[:5]
    
    # Most viewed articles
    popular_articles = NewsArticle.objects.order_by('-view_count')[:5]
    
    stats = {
        'total_articles': total_articles,
        'articles_today': articles_today,
        'category_stats': list(category_stats),
        'popular_articles': [
            {
                'title': article.title,
                'views': article.view_count,
                'url': article.get_absolute_url()
            }
            for article in popular_articles
        ]
    }
    
    return JsonResponse(stats)