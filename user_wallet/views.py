from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from .wallet_utils import credit_wallet, debit_wallet, ensure_wallet_exists
from .models import WalletTransaction
from order_management.models import Order
from django.core.paginator import Paginator


@login_required(login_url='accounts:user_login_view')
def wallet(request):
    wallet = ensure_wallet_exists(request.user)
    transactions = WalletTransaction.objects.filter(wallet__user=request.user).order_by('-date')

    # Add pagination
    paginator = Paginator(transactions, 10)  # Show 10 transactions per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'wallet': wallet,
        'transactions': page_obj,  # Pass the paginated transactions
    }
    return render(request, 'wallet/wallet_display.html', context)


