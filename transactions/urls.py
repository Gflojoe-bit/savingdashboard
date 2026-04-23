from django.urls import path

from . import views

app_name = "transactions"

urlpatterns = [
    path("", views.list_view, name="list"),
    path("new/", views.new, name="new"),
]
