# community/urls.py
from django.urls import path
from . import views


urlpatterns = [
    path('', views.community_home, name='community_home'),
    path('cases/', views.case_list, name='case_list'),
    path('case/<int:case_id>/', views.case_detail, name='case_detail'),
    path('submit/', views.submit_case, name='submit_case'),
    path('my-cases/', views.my_cases, name='my_cases'),
    path('vote/', views.vote_response, name='vote_response'),
    path('resolve/<int:case_id>/', views.resolve_case, name='resolve_case'),
    path('reopen/<int:case_id>/', views.reopen_case, name='reopen_case'),
    #  path('toggle-status/<int:case_id>/', views.toggle_case_status, name='toggle_case_status'),
]