from django.urls import path

from accounts import views

urlpatterns = [
    path('auth/register/', views.RegisterView.as_view(), name='register'),
    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('account/balance/', views.BalanceView.as_view(), name='balance'),
    path('account/transactions/', views.TransactionListView.as_view(), name='transactions'),
    path('transfers/', views.TransferView.as_view(), name='transfer'),
]
