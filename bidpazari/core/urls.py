from django.urls import path

from bidpazari.core.views import WSClientView

urlpatterns = [
    path("ws_client/", WSClientView.as_view()),
]
