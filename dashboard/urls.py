from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home, name='home'),
    path('accounts/', views.accounts, name='accounts'),
    path('accounts/<int:account_id>/', views.account_detail, name='account_detail'),
    path('goals/', views.goals, name='goals'),
    path('goals/<int:goal_id>/', views.goal_detail, name='goal_detail'),
    path('settings/', views.settings_view, name='settings'),
]
