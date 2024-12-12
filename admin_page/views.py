from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model, authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from user_profile.models import Address
from datetime import datetime, timedelta
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth, TruncDay
from dateutil.relativedelta import relativedelta
from order_management.models import Order,OrderItem
from products.models import Product, Category, Brand  
from django.utils.safestring import mark_safe
import json

# Create your views here.

User = get_user_model()

@login_required(login_url='accounts:admin_login')  
@never_cache
def user_management_page(request):
    status = request.GET.get('status')
    search_query = request.GET.get('search', '')
    
    # Start with filtering by status and exclude superusers
    if status == 'active':
        users = User.objects.filter(is_active=True, is_superuser=False)
    elif status == 'inactive':
        users = User.objects.filter(is_active=False, is_superuser=False)
    else:
        users = User.objects.filter(is_superuser=False)
    
    # Apply search filter
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) | 
            Q(email__icontains=search_query) | 
            Q(first_name__icontains=search_query) | 
            Q(last_name__icontains=search_query)
        )
    
    context = {
        'users': users,
        'search_query': search_query,
        'status': status,
    }
    return render(request, 'admin_page/user_management_page.html', context)

@login_required(login_url='accounts:admin_login')  
@never_cache
def permanent_delete_user(request, id):
    user = get_object_or_404(User, id=id)
    if request.method == "POST":
        # Ensure user is not a superuser before deleting
        if not user.is_superuser:
            user.delete()
            messages.success(request, 'User has been deleted permanently.')
        else:
            messages.error(request, 'Superuser cannot be deleted.')
    return redirect('user_management_page')

@login_required(login_url='accounts:admin_login')  
@never_cache
def block_user(request, id):
    user = get_object_or_404(User, id=id)
    if request.method == "POST":
        if not user.is_superuser:
            user.is_active = False
            user.save()
            messages.success(request, f"User {user.username} has been blocked.")
        else:
            messages.error(request, 'Superuser cannot be blocked.')
    return redirect('user_details_page', id=id)  # Redirect back to the user's detail page

@login_required(login_url='accounts:admin_login')  
def unblock_user(request, id):
    user = get_object_or_404(User, id=id)
    if request.method == "POST":
        if not user.is_superuser:
            user.is_active = True
            user.save()
            messages.success(request, f"User {user.username} has been unblocked.")
        else:
            messages.error(request, 'Superuser cannot be unblocked.')
    return redirect('user_details_page', id=id)  # Redirect back to the user's detail page

@login_required(login_url='accounts:admin_login')  
def user_details_page(request, id):
    user = get_object_or_404(User, id=id)  # Adjust User to your actual model
    addresses = Address.objects.filter(user=user)  # Fetch all addresses related to the user
    context = {
        'user': user,
        'addresses' : addresses,
    }
    return render(request, 'admin_page/user_details_page.html', context)

@login_required(login_url='accounts:admin_login')  
def admin_page(request):
    print('hi')
    filter_option = request.GET.get('filter', 'yearly')
    today = datetime.today()

    if filter_option == 'yearly':
        start_date = today.replace(month=1, day=1)
        end_date = today.replace(month=12, day=31)
        truncate = TruncMonth  # Monthly breakdown
    elif filter_option == 'monthly':
        start_date = today.replace(day=1)
        end_date = (start_date + relativedelta(months=1)) - timedelta(days=1)
        truncate = TruncDay  # Daily breakdown
    elif filter_option == 'weekly':
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)
        truncate = TruncDay  # Daily breakdown
    else:
        start_date = today.replace(month=1, day=1)
        end_date = today.replace(month=12, day=31)
        truncate = TruncMonth

    # Debugging filter dates
    print(f"Filter Option: {filter_option}")
    print(f"Start Date: {start_date}, End Date: {end_date}")

    # Filter orders by date range
    orders = Order.objects.filter(created_at__range=(start_date, end_date))

    # Debugging orders fetched
    print(f"Total Orders: {orders.count()}")
    for order in orders:
        print(f"Order ID: {order.id}, Created At: {order.created_at}, Total Price: {order.final_price}")

    # Group data based on truncation (e.g., months, days)
    sales_data = (
        orders
        .annotate(period=truncate('created_at'))
        .values('period')
        .annotate(total_sales=Sum('final_price'), total_orders=Count('id'))
        .order_by('period')
    )
    for item in sales_data:
        print(f"Period: {item['period']}, Total Sales: {item['total_sales']}, Total Orders: {item['total_orders']}")

    # Debugging grouped data
    print("Sales Data:")
    for data in sales_data:
        print(data)

    # Prepare data for the chart
    labels = [
        data['period'].strftime('%b %d, %Y') if isinstance(data['period'], datetime) else str(data['period'])
        for data in sales_data
    ]
    sales = [float(data['total_sales']) for data in sales_data]  # Convert Decimal to float
    orders_count = [data['total_orders'] for data in sales_data]

    # Debugging chart data
    print("Labels:", labels)
    print("Sales:", sales)
    print("Orders Count:", orders_count)


    # Best Selling Product
    best_selling_products = (
        OrderItem.objects.filter(order__in=orders)
        .values('variant__product__name')  # Use variant__product to reach the Product
        .annotate(total_quantity=Sum('quantity'))
        .order_by('-total_quantity')[:5]  # Top 5 products
    )

    # Best Selling Category
    best_selling_categories = (
        OrderItem.objects.filter(order__in=orders)
        .values('variant__product__category__name')  # Use variant__product__category
        .annotate(total_quantity=Sum('quantity'))
        .order_by('-total_quantity')[:5]  # Top 5 categories
    )

    # Best Selling Brand
    best_selling_brands = (
        OrderItem.objects.filter(order__in=orders)
        .values('variant__product__brand__name')  # Use variant__product__brand
        .annotate(total_quantity=Sum('quantity'))
        .order_by('-total_quantity')[:5]  # Top 5 brands
    )


    context = {
        'labels': mark_safe(json.dumps(labels)),
        'sales': mark_safe(json.dumps(sales)),
        'orders_count': mark_safe(json.dumps(orders_count)),
        'filter_option': filter_option,
        'sales_data':sales_data,
        'best_selling_products': best_selling_products,
        'best_selling_categories': best_selling_categories,
        'best_selling_brands': best_selling_brands,
    }
    return render(request, 'admin_page/index.html', context)

@login_required(login_url='accounts:admin_login')  
def admin_logout_view(request):
    if request.user.is_authenticated:
        logout(request)
    return redirect('accounts:admin_login')
