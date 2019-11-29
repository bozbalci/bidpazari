from django.urls import path

from bidpazari.core.views import TCPClientView

urlpatterns = [
    path("tcp_client/", TCPClientView.as_view()),
]
