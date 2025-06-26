from django.urls import path
from . import views

app_name = 'medical_news'

urlpatterns = [
    # Main news pages
    path('', views.NewsListView.as_view(), name='list'),
    path('article/<int:pk>/', views.NewsDetailView.as_view(), name='detail'),
    
    # Category and trending
    path('category/<str:category>/', views.news_by_category, name='category'),
    path('trending/', views.trending_news, name='trending'),
    
    # AJAX endpoints
    path('fetch-latest/', views.fetch_latest_news, name='fetch_latest'),
    path('search/', views.search_news, name='search'),
    path('stats/', views.dashboard_stats, name='stats'),
]