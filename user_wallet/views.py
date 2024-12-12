from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from .wallet_utils import credit_wallet, debit_wallet, ensure_wallet_exists
from .models import WalletTransaction
from order_management.models import Order

@login_required(login_url='accounts:user_login_view')
def wallet(request):
    wallet = ensure_wallet_exists(request.user)  
    transactions = WalletTransaction.objects.filter(wallet__user=request.user).order_by('-date')
    print(transactions,wallet)
    context = {
        'wallet': wallet,
        'transactions': transactions,
    }
    return render(request, 'wallet/wallet_display.html', context)



