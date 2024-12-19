from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.contrib import messages
from .models import Order, OrderItem, PaymentDetails, PaymentStatus
from user_profile.models import Address
import razorpay
from django.conf import settings
from user_wallet.models import WalletTransaction
from user_wallet.wallet_utils import debit_wallet ,credit_wallet ,process_refund_to_wallet,ensure_wallet_exists



def handle_address_selection(form, user):
    """Handle address selection or creation."""
    address_id = form.cleaned_data.get('address')
    if address_id == 'add_new':
        return Address.objects.create(
            user=user,
            street=form.cleaned_data.get('new_street'),
            city=form.cleaned_data.get('new_city'),
            state=form.cleaned_data.get('new_state'),
            pin_code=form.cleaned_data.get('new_pin_code'),
            is_default=True
        )
    return get_object_or_404(Address, id=address_id)


def create_order_and_items(user, address, payment_details, cart_items, total_price, coupon, total_discount):
    """Create an order and associated order items."""
    with transaction.atomic():
        order = Order.objects.create(
            user=user,
            address=address,
            payment_details=payment_details,
            final_price=total_price,
            coupon=coupon
        )
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                variant=item.variant,
                quantity=item.quantity,
                price=item.variant.price
            )
        return order

# ----------------------- Payment Methods -----------------------

def handle_cod_payment(request, cart_items, address, total_price, coupon,total_discount):
    """Handle Cash on Delivery payment method."""
    payment_status = PaymentStatus.objects.filter(status="Pending").first()
    if not payment_status:
        payment_status = PaymentStatus.objects.create(status="Pending")
    
    payment_details = PaymentDetails.objects.create(
        payment_method="COD",
        payment_status=payment_status
    )
    order = create_order_and_items(request.user, address, payment_details, cart_items, total_price, coupon,total_discount)
    # Clear the cart
    cart_items.delete()

    # Render a success page or redirect to an order success URL
    messages.success(request, "Order placed successfully using Cash on Delivery!")
    return redirect('cod_order_success', order_id=order.id)  # Update with your success URL name


def handle_wallet_payment(request, cart_items, address, total_price, coupon,total_discount):
    """Handle wallet payment method."""
    wallet = ensure_wallet_exists(request.user)  # Helper function to get user's wallet

    if wallet.balance >= total_price:
        # Deduct amount from wallet
        debit_wallet(request.user, total_price, "Order Payment via Wallet")

        # Update payment status to Completed
        payment_status = PaymentStatus.objects.filter(status="Completed").first()
        if not payment_status:
            payment_status = PaymentStatus.objects.create(status="Completed")
        payment_details = PaymentDetails.objects.create(
            payment_method="Wallet",
            payment_status=payment_status
        )

        # Create order and items
        order = create_order_and_items(request.user, address, payment_details, cart_items, total_price, coupon,total_discount)

        # Clear the cart
        cart_items.delete()

        # Redirect to order success page
        messages.success(request, "Order placed successfully using Wallet!")
        return redirect('cod_order_success', order_id=order.id)  # Update with your success URL name

    # Insufficient wallet balance
    messages.error(request, "Insufficient wallet balance. Please select another payment method.",extra_tags="checkout")
    return redirect('checkout')  # Redirect back to the checkout page


def handle_razorpay_payment(request, cart_items, address, total_price, coupon,total_discount):
    """Handle Razorpay payment method."""
    payment_status = PaymentStatus.objects.filter(status="Pending").first()
    if not payment_status:
        payment_status = PaymentStatus.objects.create(status="Pending")
    payment_details = PaymentDetails.objects.create(
        payment_method="Razorpay",
        payment_status=payment_status
    )

    # Create order and items
    order = create_order_and_items(request.user, address, payment_details, cart_items, total_price, coupon,total_discount)

    # Integrate Razorpay payment initialization
    razorpay_client = razorpay.Client(auth=(settings.RAZOR_PAY_KEY_ID, settings.RAZOR_PAY_KEY_SECRET))
    razorpay_order = razorpay_client.order.create({
        "amount": int(total_price * 100),  # Amount in paise
        "currency": "INR",
        "payment_capture": 1
    })

    # Save Razorpay order ID to the order
    order.razorpay_order_id = razorpay_order['id']
    order.save()

    # Render Razorpay payment page
    return render(request, 'checkout/razorpay_payment.html', {
        'order': order,
        'razorpay_order_id': razorpay_order['id'],
        'razorpay_key': settings.RAZOR_PAY_KEY_ID,
        'total_price': total_price * 100,  # Razorpay expects price in paise
        'user_email': request.user.email,
        'user_name': request.user.get_full_name(),
    })


def complete_wallet_payment(request, order):
    """Handle wallet payment method for existing order."""
    wallet = ensure_wallet_exists(request.user)  # Helper function to get user's wallet

    if wallet.balance >= order.final_price:
        # Deduct amount from wallet
        debit_wallet(request.user, order.final_price, "Order Payment via Wallet")

        # Update payment status to Completed
        payment_status = PaymentStatus.objects.filter(status="Completed").first()
        if not payment_status:
            payment_status = PaymentStatus.objects.create(status="Completed")
        
        # Update payment details for the order
        order.payment_details.payment_status = payment_status
        order.payment_details.save()

        # Redirect to order success page
        messages.success(request, "Order placed successfully using Wallet!")
        return redirect('order_details', order_id=order.id)

    # Insufficient wallet balance
    messages.error(request, "Insufficient wallet balance. Please select another payment method.",extra_tags="complete")
    return redirect('complete_payment', order_id=order.id)  # Redirect back to payment selection page


def complete_razorpay_payment(request, order):
    """Handle Razorpay payment method for existing order."""
    # Initialize Razorpay client
    razorpay_client = razorpay.Client(auth=(settings.RAZOR_PAY_KEY_ID, settings.RAZOR_PAY_KEY_SECRET))
    
    # Create Razorpay order
    razorpay_order = razorpay_client.order.create({
        "amount": int(order.final_price * 100),  # Amount in paise
        "currency": "INR",
        "payment_capture": 1
    })

    # Update order with Razorpay order ID
    order.razorpay_order_id = razorpay_order['id']
    order.save()

    # Render Razorpay payment page
    return render(request, 'checkout/razorpay_payment.html', {
        'order': order,
        'razorpay_order_id': razorpay_order['id'],
        'razorpay_key': settings.RAZOR_PAY_KEY_ID,
        'total_price': order.final_price * 100,  # Razorpay expects price in paise
        'user_email': request.user.email,
        'user_name': request.user.get_full_name(),
    })