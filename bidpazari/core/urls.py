from django.contrib.auth.views import LoginView
from django.urls import include, path

from bidpazari.core import views

legacy_urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('signup/', views.SignupView.as_view(), name='signup',),
    path('login/', LoginView.as_view(template_name='core/login.html'), name='login',),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('account/', views.AccountDetailsView.as_view(), name='account-details',),
    path(
        'account/reset-password',
        views.PasswordResetView.as_view(),
        name='reset-password',
    ),
    path(
        'account/change-password',
        views.PasswordChangeView.as_view(),
        name='change-password',
    ),
    path('auctions/', views.AuctionsView.as_view(), name='auctions'),
    path(
        'auctions/<int:pk>/', views.AuctionDetailsView.as_view(), name='auction-details'
    ),
    path(
        'auctions/<int:pk>/start/',
        views.AuctionStartView.as_view(),
        name='auction-start',
    ),
    path(
        'auctions/<int:pk>/cancel/',
        views.AuctionCancelView.as_view(),
        name='auction-cancel',
    ),
    path(
        'auctions/<int:pk>/sell/', views.AuctionSellView.as_view(), name='auction-sell'
    ),
    path('auctions/<int:pk>/bid/', views.AuctionBidView.as_view(), name='auction-bid'),
    path('transactions/', views.TransactionsView.as_view(), name='transactions'),
    path('add-item/', views.AddItemView.as_view(), name='add-item'),
    path('edit-item/<int:pk>/', views.EditItemView.as_view(), name='edit-item'),
    path('add-balance/', views.AddBalanceView.as_view(), name='add-balance'),
    path(
        'create-auction/<int:pk>/',
        views.CreateAuctionStep1View.as_view(),
        name='create-auction',
    ),
    path(
        'create-auction/<int:pk>/confirm/',
        views.CreateAuctionStep2View.as_view(),
        name='create-auction-confirm',
    ),
]

ws_urlpatterns = [
    path("server/", views.WSServerView.as_view(), name='ws-server'),
    path("client/", views.WSClientView.as_view(), name='ws-client'),
]

urlpatterns = [
    path("ws/", include(ws_urlpatterns)),
    path("", include(legacy_urlpatterns)),
]
