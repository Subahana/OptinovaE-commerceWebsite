from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.contrib import messages
from .forms import UserProfileForm,AddressForm,CustomPasswordChangeForm,CancellationForm
from django.http import JsonResponse
from .models import Address
from products.models import ProductVariant
from order_management.models import Order,OrderItem
from django.contrib.auth import get_user_model
from django.contrib.auth import update_session_auth_hash
from django.middleware.csrf import get_token
from django.core.paginator import Paginator
from django.db.models import Q, Sum, F
from django.urls import reverse
from django.utils import timezone 

User = get_user_model()


# --------------Profile---------------#

@login_required(login_url='accounts:user_login_view')
def user_profile(request):
    user = request.user
    addresses = Address.objects.filter(user=request.user, is_deleted=False)
    orders = Order.objects.filter(user=user)

    if request.method == 'POST':
        profile_form = UserProfileForm(request.POST, instance=user)
        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, 'Your profile has been updated.')
            return redirect('user_profile')
    else:
        profile_form = UserProfileForm(instance=user)

    context = {
        'profile_form': profile_form,
        'addresses': addresses,
        'orders': orders,

    }
    return render(request, 'user_profile/user_profile_page.html', context)

@login_required(login_url='accounts:user_login_view')
def edit_profile(request):
    user = request.user  # Get the currently logged-in user

    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile was successfully updated!')
            return redirect('user_profile')  # Redirect to the profile page
        else:
            print(form.errors)
    else:
        form = UserProfileForm(instance=user)

    return render(request, 'user_profile/edit_profile_page.html', {
        'form': form,
        'profile': user,  # Pass the user instance directly to the template
    })


# --------------change_password---------------#

@login_required
def change_password(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True}, status=200)  # Respond with success

        # If form is invalid, send errors back in JSON format
        errors = {field: error[0] for field, error in form.errors.items()}
        return JsonResponse({'errors': errors}, status=400)
    
    # In case it's not a POST request, render the template
    form = CustomPasswordChangeForm(user=request.user)
    return render(request, 'user_profile/change_password.html', {'form': form})


# --------------Address---------------#

@login_required(login_url='accounts:user_login_view')
def add_address(request):
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            return redirect('user_profile') 
    else:
        form = AddressForm()
    return render(request, 'user_profile/add_address.html', {'form': form})

@login_required(login_url='accounts:user_login_view')
def edit_address(request, address_id):
    address = get_object_or_404(Address, id=address_id)
    if request.method == 'POST':
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            return redirect('user_profile')  # or wherever you want to redirect after editing the address
    else:
        form = AddressForm(instance=address)
    return render(request, 'user_profile/edit_address.html', {'form': form})

@login_required(login_url='accounts:user_login_view')
def delete_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user, is_deleted=False)
    if request.method == 'POST':
        address.soft_delete()  # Call the custom soft delete method
        messages.success(request, 'Address deleted successfully.')
        return redirect('user_profile')  # or wherever you want to redirect after deletion
    return redirect('user_profile')


# --------------Order---------------#

@login_required(login_url='accounts:user_login_view')
def my_orders(request):
    # Get the search query from the request (if any)
    query = request.GET.get('query', '')

    # Get orders for the logged-in user containing active product variants
    orders = Order.objects.filter(
        user=request.user,
        items__variant__is_active=True  # Filter orders that contain active variants
    ).distinct().order_by('id')

    # Calculate total price and total quantity for each order
    for order in orders:
        # Calculate the total price using price and quantity in OrderItem
        order.total_price = order.items.aggregate(
            total=Sum(F('price') * F('quantity'))
        )['total'] or 0
        
        # Calculate the total quantity of items in the order
        order.total_items = order.items.aggregate(
            total=Sum('quantity')
        )['total'] or 0
        
        # Add the payment method and payment status
        if order.payment_details:
            order.payment_method = order.payment_details.payment_method
            order.payment_status = order.payment_details.payment_status
            order.order_status = order.status.status
            if order.payment_details.payment_method == 'razorpay':
                order.razorpay_order_id = order.payment_details.razorpay_order_id
                order.razorpay_payment_id = order.payment_details.razorpay_payment_id
        else:
            order.payment_method = 'Not Provided'
            order.payment_status = 'Pending'
    first_item = order.items.first()  # Fetch the first item from the order
    print(first_item)
    # Pagination (5 orders per page)
    paginator = Paginator(orders, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'user_profile/my_orders.html', {
        'page_obj': page_obj,
        'first_item': first_item,
        'query': query
    })


@login_required(login_url='accounts:user_login_view')
def order_details(request, order_id):
    # Fetch the order for the logged-in user
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Calculate total price for all items in the order using the model's method
    total_price_order = order.final_price
    request.session['total_price_order'] = float(total_price_order)

    # Retrieve payment details or fallback to default values
    payment_status = order.payment_details.payment_status if order.payment_details else "N/A"
    payment_method = order.payment_details.payment_method if order.payment_details else "N/A"

    # Handle POST requests for canceling or returning the order
    if request.method == 'POST':
        # Cancel Order Logic
        if 'cancel_order' in request.POST:
            if order.status.lower() in ['pending', 'processing']:
                reason = request.POST.get('cancellation_reason', 'Cancelled by User')
                order.cancel_order(reason=reason)
                messages.success(request, "Order has been successfully canceled.")
                return redirect('my_orders')
            else:
                messages.error(request, "This order cannot be canceled.")
                return redirect('order_details', order_id=order.id)

        # Return Order Logic
        elif 'return_order' in request.POST:
            if order.status.lower() == 'delivered':
                order.return_order()
                messages.success(request, "Return request has been submitted.")
                return redirect('my_orders')
            else:
                messages.error(request, "This order cannot be returned.")
                return redirect('order_details', order_id=order.id)
        # Proceed to Payment Logic
        elif 'proceed_to_payment' in request.POST:
            return redirect('complete_payment', order_id=order.id)

    # Pass necessary data to the template
    return render(request, 'checkout/order_details.html', {
        'order': order,
        'total_price_order': total_price_order,
        'payment_status': payment_status,
        'payment_method': payment_method,
    })

