import requests
from django.conf import settings
from django.utils.dateparse import parse_datetime
from datetime import datetime, timedelta
from .models import NewsArticle
import logging

logger = logging.getLogger(__name__)

class NewsAPIService:
    def __init__(self):
        self.api_key = getattr(settings, 'NEWS_API_KEY', 'e204dad0083f4b11b5d75b695dea5340')
        self.base_url = 'https://newsapi.org/v2'
        
        # Medical and health-related keywords
        self.medical_keywords = [
            'health', 'medical', 'medicine', 'hospital', 'doctor', 'patient',
            'disease', 'treatment', 'vaccine', 'pharmaceutical', 'healthcare',
            'wellness', 'mental health', 'public health', 'epidemic', 'pandemic',
            'surgery', 'therapy', 'diagnosis', 'clinical trial', 'FDA approval',
            'medical research', 'cancer', 'diabetes', 'heart disease', 'covid',
            'WHO', 'CDC', 'medical breakthrough', 'drug', 'prescription'
        ]
        
        # Trusted medical news sources
        self.medical_sources = [
            'medical-news-today', 'reuters', 'bbc-news', 'cnn', 
            'associated-press', 'the-washington-post', 'axios',
            'abc-news', 'cbs-news', 'nbc-news'
        ]
    
    def get_trending_medical_news(self, page=1, page_size=20):
        """Fetch trending medical news from NewsAPI"""
        try:
            # Get news from the last 7 days
            from_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            
            # Use 'everything' endpoint for better medical news coverage
            url = f"{self.base_url}/everything"
            params = {
                'apiKey': self.api_key,
                'q': 'health OR medical OR healthcare OR medicine',
                'sources': ','.join(self.medical_sources[:5]),  # Limit sources to avoid URL length issues
                'from': from_date,
                'sortBy': 'popularity',
                'language': 'en',
                'page': page,
                'pageSize': page_size
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data['status'] == 'ok':
                return self._process_articles(data['articles'])
            else:
                logger.error(f"NewsAPI error: {data.get('message', 'Unknown error')}")
                return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching news: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return []
    
    def search_medical_news(self, query, page=1, page_size=20):
        """Search for specific medical news"""
        try:
            from_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            
            url = f"{self.base_url}/everything"
            params = {
                'apiKey': self.api_key,
                'q': f"{query} AND (health OR medical OR healthcare)",
                'from': from_date,
                'sortBy': 'relevancy',
                'language': 'en',
                'page': page,
                'pageSize': page_size
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data['status'] == 'ok':
                return self._process_articles(data['articles'])
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error searching news: {str(e)}")
            return []
    
    def get_top_medical_headlines(self, country='us', page_size=20):
        """Get top medical headlines"""
        try:
            url = f"{self.base_url}/top-headlines"
            params = {
                'apiKey': self.api_key,
                'category': 'health',
                'country': country,
                'pageSize': page_size
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data['status'] == 'ok':
                return self._process_articles(data['articles'])
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error fetching headlines: {str(e)}")
            return []
    
    def _process_articles(self, articles):
        """Process and clean article data"""
        processed_articles = []
        
        for article in articles:
            # Skip articles without essential information
            if not article.get('title') or not article.get('url'):
                continue
                
            # Skip articles with [Removed] content
            if '[Removed]' in str(article.get('title', '')):
                continue
            
            try:
                # Parse publication date
                published_at = None
                if article.get('publishedAt'):
                    published_at = parse_datetime(article['publishedAt'])
                    if not published_at:
                        # Fallback parsing
                        published_at = datetime.fromisoformat(
                            article['publishedAt'].replace('Z', '+00:00')
                        )
                
                processed_article = {
                    'title': article.get('title', '').strip(),
                    'description': article.get('description', '').strip() if article.get('description') else None,
                    'content': article.get('content', '').strip() if article.get('content') else None,
                    'url': article.get('url'),
                    'url_to_image': article.get('urlToImage'),
                    'source_name': article.get('source', {}).get('name', 'Unknown'),
                    'author': article.get('author'),
                    'published_at': published_at or datetime.now(),
                    'category': self._categorize_article(article),
                }
                
                processed_articles.append(processed_article)
                
            except Exception as e:
                logger.error(f"Error processing article: {str(e)}")
                continue
        
        return processed_articles
    
    def _categorize_article(self, article):
        """Categorize article based on content"""
        title = article.get('title', '').lower()
        description = article.get('description', '').lower() if article.get('description') else ''
        
        content = f"{title} {description}"
        
        # Define categories and their keywords
        categories = {
            'covid': ['covid', 'coronavirus', 'pandemic', 'vaccine', 'omicron', 'delta'],
            'mental-health': ['mental health', 'depression', 'anxiety', 'therapy', 'psychology'],
            'cancer': ['cancer', 'tumor', 'oncology', 'chemotherapy', 'radiation'],
            'heart-disease': ['heart', 'cardiac', 'cardiovascular', 'blood pressure', 'cholesterol'],
            'diabetes': ['diabetes', 'insulin', 'blood sugar', 'glucose'],
            'public-health': ['public health', 'CDC', 'WHO', 'epidemic', 'outbreak'],
            'research': ['study', 'research', 'clinical trial', 'breakthrough', 'discovery'],
            'pharmaceuticals': ['drug', 'pharmaceutical', 'FDA', 'approval', 'medication'],
        }
        
        for category, keywords in categories.items():
            if any(keyword in content for keyword in keywords):
                return category
        
        return 'general'
    
    def save_articles_to_db(self, articles):
        """Save articles to database"""
        saved_count = 0
        
        for article_data in articles:
            try:
                article, created = NewsArticle.objects.get_or_create(
                    url=article_data['url'],
                    defaults=article_data
                )
                
                if created:
                    saved_count += 1
                    
            except Exception as e:
                logger.error(f"Error saving article to DB: {str(e)}")
                continue
        
        return saved_count