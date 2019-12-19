from django.contrib.auth.views import LoginView
from django.urls import include, path
from django.views.generic import TemplateView

from bidpazari.core import views

legacy_urlpatterns = [
    path('', views.LegacyView.as_view(), name='legacy-index'),
    path(
        'login/',
        LoginView.as_view(template_name='core/legacy/login.html'),
        name='legacy-login',
    ),
    path('logout/', views.LogoutView.as_view(), name='legacy-logout'),
    path('dashboard/', views.DashboardView.as_view(), name='legacy-dashboard'),
    path('add-item/', views.AddItemView.as_view(), name='legacy-add-item'),
    path('edit-item/<int:pk>', views.EditItemView.as_view(), name='legacy-edit-item'),
    path('add-balance/', views.AddBalanceView.as_view(), name='legacy-add-balance'),
    path(
        'create-auction/<int:pk>',
        views.CreateAuctionStep1View.as_view(),
        name='legacy-create-auction',
    ),
    path(
        'create-auction/<int:pk>/confirm',
        views.CreateAuctionStep2View.as_view(),
        name='legacy-create-auction-confirm',
    ),
]

urlpatterns = [
    path('', TemplateView.as_view(template_name='core/index.html'), name='index'),
    path("ws_server/", views.WSServerView.as_view(), name='ws-server'),
    path("ws_client/", views.WSClientView.as_view(), name='ws-client'),
    path("legacy/", include(legacy_urlpatterns)),
]
