from django.urls import path

from . import views

app_name = "goals"

urlpatterns = [
    path("", views.list_view, name="list"),
    path("new/", views.new, name="new"),
    path("basket/", views.basket, name="basket"),
    path("<int:goal_id>/", views.detail, name="detail"),
]
