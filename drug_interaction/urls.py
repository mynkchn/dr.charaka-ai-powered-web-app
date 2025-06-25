
# drug_checker/urls.py
from django.urls import path
from . import views

app_name = 'drug_checker'

urlpatterns = [
    path('', views.drug_checker_home, name='home'),
    path('check/', views.check_interactions, name='check'),
    path('drug-info/', views.drug_info, name='drug_info'),
    path('history/', views.interaction_history, name='history'),
]
