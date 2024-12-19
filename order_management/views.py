from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from django.conf import settings
from django.middleware.csrf import get_token
from django.http import JsonResponse, HttpResponseForbidden
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .models import Order, OrderItem ,PaymentDetails, PaymentStatus, OrderStatus
from user_profile.models import Address
from cart_management.models import Cart, CartItem
from .forms import OrderForm
import razorpay
from razorpay import Client
import logging
from urllib.parse import parse_qs
from user_wallet.models import WalletTransaction
from user_wallet.wallet_utils import debit_wallet ,credit_wallet ,process_refund_to_wallet,ensure_wallet_exists
from .checkout_utils import handle_cod_payment, handle_wallet_payment, handle_razorpay_payment, handle_address_selection,complete_razorpay_payment,complete_wallet_payment
from sales_report.sales_utils import send_invoice_email
import uuid
from django.contrib.auth import login, get_backends
from django.core.paginator import Paginator
from decimal import Decimal
from django.urls import reverse
import json
from urllib.parse import unquote, parse_qs
from django.http import Http404

logger = logging.getLogger(__name__)

@login_required(login_url='accounts:user_login_view')
def checkout(request):
    cart = Cart.objects.get(user=request.user)
    coupon = cart.coupon
    addresses = Address.objects.filter(user=request.user)
    total_price = cart.final_price
    total_discount = cart.total_discount

    if request.method == 'POST':
        form = OrderForm(request.POST, user=request.user)
        if form.is_valid():
            address = handle_address_selection(form, request.user)
            payment_method = form.cleaned_data['payment_method']
            cart_items = CartItem.objects.filter(cart=cart)

            if not cart_items.exists():
                messages.error(request, "Your cart is empty.")
                return redirect('cart_detail')

            # Handle specific payment methods
            if payment_method.lower() == "cod":
                return handle_cod_payment(request, cart_items, address, total_price, coupon, total_discount)

            elif payment_method.lower() == "wallet":
                return handle_wallet_payment(request, cart_items, address, total_price, coupon, total_discount)

            elif payment_method.lower() == "razorpay":
                return handle_razorpay_payment(request, cart_items, address, total_price, coupon, total_discount)

            else:
                messages.error(request, "Invalid payment method selected.")
                return redirect('checkout')

    else:
        form = OrderForm(user=request.user)

    return render(request, 'checkout/checkout.html', {
        'form': form,
        'addresses': addresses,
        'cart_items': CartItem.objects.filter(cart=cart),
        'total_price': total_price, 
        'total_discount': total_discount,
        'coupon' : coupon,
        'csrf_token': get_token(request),
    })

@method_decorator(csrf_exempt, name='dispatch')
class VerifyRazorpayPayment(View):
    def post(self, request, order_id):
        # Decode request body
        decoded_body = request.body.decode('utf-8')
        data = parse_qs(decoded_body)
        data = {k: v[0] for k, v in data.items()}

        # Handle payment failure
        if 'error[code]' in data:
            self._handle_payment_failure(data, order_id)
            return redirect('handle_payment_failure', order_id=order_id)

        # Handle payment success
        payment_id = data.get('razorpay_payment_id')
        razorpay_order_id = data.get('razorpay_order_id')
        signature = data.get('razorpay_signature')

        if not all([payment_id, razorpay_order_id, signature]):
            logger.error("Missing required payment data.")
            return JsonResponse({'error': 'Missing payment ID, order ID, or signature'}, status=400)

        try:
            # Verify payment signature
            razorpay_client = razorpay.Client(auth=(settings.RAZOR_PAY_KEY_ID, settings.RAZOR_PAY_KEY_SECRET))
            razorpay_client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            })

            # Update order status to completed
            self._handle_payment_success(order_id, payment_id)
            return redirect('razorpay_order_success', order_id=order_id)

        except razorpay.errors.SignatureVerificationError:
            logger.error("Payment verification failed: signature mismatch.")
            return JsonResponse({'error': 'Signature verification failed'}, status=400)

        except Exception as e:
            logger.error(f"Error verifying payment: {str(e)}", exc_info=True)
            return JsonResponse({'error': 'An error occurred while verifying payment'}, status=500)

    def _handle_payment_failure(self, data, order_id):
        """Handles payment failure and updates order status."""
        error_code = data.get('error[code]', 'Unknown Code')
        error_description = data.get('error[description]', 'Unknown Description')
        error_reason = data.get('error[reason]', 'Unknown Reason')

        # Parse metadata for payment details
        raw_metadata = data.get('error[metadata]', '{}')
        try:
            metadata = json.loads(unquote(raw_metadata))
            payment_id = metadata.get('payment_id', 'N/A')
            razorpay_order_id = metadata.get('order_id', 'N/A')
        except json.JSONDecodeError:
            payment_id = 'N/A'
            razorpay_order_id = 'N/A'

        logger.error(f"Payment Failed: {error_description} (Reason: {error_reason})")
        logger.error(f"Payment ID: {payment_id}, Razorpay Order ID: {razorpay_order_id}")

        # Update order payment status
        order = get_object_or_404(Order, id=order_id)
        payment_failed_status, _ = PaymentStatus.objects.get_or_create(status='Failed')
        order.payment_details.payment_status = payment_failed_status
        order.payment_details.save()
        order.save()

    def _handle_payment_success(self, order_id, payment_id):
        """Handles successful payment and updates order details."""
        order = get_object_or_404(Order, id=order_id)

        # Update order statuses
        processing_status, _ = OrderStatus.objects.get_or_create(status='Processing')
        completed_payment_status, _ = PaymentStatus.objects.get_or_create(status='Completed')

        order.status = processing_status
        order.payment_details.payment_status = completed_payment_status
        order.payment_details.razorpay_payment_id = payment_id
        order.payment_details.save()
        order.save()

        # Clear the cart for the user
        CartItem.objects.filter(cart__user=order.user).delete()

        # Automatically log in the user if needed
        user = order.user
        if user.is_active:
            backend = 'django.contrib.auth.backends.ModelBackend'
            login(self.request, user, backend=backend)

@login_required(login_url='accounts:user_login_view')
def razorpay_order_success(request, order_id):
    try:
        order = get_object_or_404(Order, id=order_id)
        user = order.user
        # Calculate the total price using the `total_amount` method
        total_price = order.final_price
        # Set the order status to 'Processing'
        processing_status = OrderStatus.objects.get(status="Processing")
        order.status = processing_status
        order.payment_details.payment_status = PaymentStatus.objects.get(status="Completed")
        order.payment_details.save()
        order.payment_date = timezone.now()
        order.save()

        # Clear the user's cart
        CartItem.objects.filter(cart__user=user).delete()

        # Render the success page
        return render(request, 'checkout/razorpay_order_success.html', {
            'order': order,
            'total_price': total_price,
            'payment_status': "Paid via Razorpay",
        })
    except Order.DoesNotExist:
        logger.error(f"No Order matches the given query for order_id: {order_id}")
        return JsonResponse({'error': 'Order not found'}, status=404)

@login_required(login_url='accounts:user_login_view')
def handle_payment_failure(request, order_id):
    try:
        # Retrieve the order by ID
        order = get_object_or_404(Order, id=order_id)
        user = order.user
        total_price = order.final_price

        # Update order payment date or status as needed
        order.payment_date = timezone.now()
        order.save()

        # Clear the user's cart
        CartItem.objects.filter(cart__user=user).delete()

        # Render the payment error page
        return render(request, 'checkout/razorpay_order_success.html', {
            'order': order,
            'total_price': total_price,
            'error_message': "Your payment was not successful. Please try again.",
        })

    except Order.DoesNotExist:
        # Handle cases where the order does not exist
        return render(request, 'checkout/payment_error.html', {
            'error_message': "Order not found. Please try again.",
        })

@login_required(login_url='accounts:user_login_view')
def complete_payment(request, order_id):
    """Complete payment after user selects a payment method (Wallet or Razorpay)."""  
    # Fetch the order based on order_id
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        messages.error(request, "Order not found!")
        return redirect('order_list')  # Redirect to orders list page
    
    # Check if the payment status is already completed
    if order.payment_details.payment_status.status == 'Completed':
        messages.info(request, "This order has already been paid.")
        return redirect('order_details', order_id=order_id)  # Redirect to order details page

    # Fetch payment status
    payment_status = PaymentStatus.objects.filter(status="Pending").first()
    
    # Handle POST request (when user selects payment method)
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')  # Get selected payment method (wallet or razorpay)

        if payment_method == 'wallet':
            return complete_wallet_payment(request, order)

        elif payment_method == 'razorpay':
            return complete_razorpay_payment(request, order)

    # Render the payment method selection page (if GET request)
    return render(request, 'checkout/complete_payment.html', {
        'order': order,
        'total_price': order.final_price,
    })

@login_required(login_url='accounts:user_login_view')
def cod_order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order.order_date = timezone.now()
    send_invoice_email(order)
    order.save()

    CartItem.objects.filter(cart__user=request.user).delete()
    final_price = order.final_price  # Assuming final_price is a field in your Order model

    return render(request, 'checkout/razorpay_order_success.html', {
        'order': order,
        'total_price':final_price,
        'payment_status': "Cash on Delivery",
    })

def list_orders(request):
    orders = Order.objects.filter(items__variant__is_active=True).distinct()

    # Search filter
    search_query = request.GET.get('search', '')
    if search_query:
        orders = orders.filter(user__username__icontains=search_query)

    # Status filter
    status_filter = request.GET.get('status_filter', '')
    if status_filter:
        try:
            # Find the OrderStatus object by status name and use its ID for filtering
            status_obj = OrderStatus.objects.get(status=status_filter)
            orders = orders.filter(status=status_obj)
        except OrderStatus.DoesNotExist:
            # Handle the case where the status does not exist
            orders = orders.none()

    # Sorting options
    sort_option = request.GET.get('sort', '')
    if sort_option == 'date_asc':
        orders = orders.order_by('created_at')
    elif sort_option == 'date_desc':
        orders = orders.order_by('-created_at')
    elif sort_option == 'status_asc':
        orders = orders.order_by('status')
    elif sort_option == 'status_desc':
        orders = orders.order_by('-status')

    # Pagination
    paginator = Paginator(orders,6)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'checkout/list_orders.html', {'orders': orders, 'page_obj': page_obj})

def update_order_status(request, order_id):
    """
    Update the status of an order to 'Delivered' or 'Cancelled' using a pop-up for cancellation reason.
    """
    order = get_object_or_404(Order, id=order_id)

    if request.method == "POST":
        new_status = request.POST.get("status")
        try:
            if new_status == "Delivered":
                # Handle 'Delivered' status
                delivered_status = OrderStatus.objects.filter(status="Delivered").first()
                order.status = delivered_status
                                # Update payment status to 'Complete'
                if order.payment_details:
                    complete_status= PaymentStatus.objects.filter(status="Completed").first()
                    order.payment_details.payment_status = complete_status
                    order.payment_details.save()

                send_invoice_email(order)
                order.save()
                messages.success(request, f"Order #{order.order_id} status updated to 'Delivered'.")
            
            elif new_status == "Cancelled":
                # Handle 'Cancelled' status
                complete_status = PaymentStatus.objects.filter(status="Complete").first()
                order.status = cancelled_status
                order.is_cancelled = True
                order.cancelled_at = timezone.now()
                order.cancellation_reason = 'Cancelled by admin.'

                # Check if payment is completed before processing the refund
                if order.payment_details and order.payment_details.payment_status.status == "Completed":
                    process_refund_to_wallet(order)

                    # Update payment status to 'Refund' and process refund
                    refund_status = PaymentStatus.objects.filter(status="Refunded").first()
                    order.payment_details.payment_status = refund_status
                    order.payment_details.save()

                    # Process refund logic
                else:
                    pass
                order.save()


                messages.success(
                    request,
                    f"Order #{order.order_id} has been canceled and a refund of ₹{refund_amount} processed."
                )
            else:
                messages.error(request, "Invalid status update request.")
        except Exception as e:
            messages.error(request, f"Failed to update order status: {str(e)}")

    return redirect("list_orders")

def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    print(order)
    # Debugging: Log the current order status
    logger.debug(f"Order ID: {order.id}, Current Status: {order.status.status}")

    # Ensure cancellation is allowed based on status
    if order.status.status.lower() in ["pending", "processing"] and \
       (not order.payment_details or order.payment_details.payment_status.status.lower() in [ "pending","failed"]):
        if request.method == "POST":
            cancellation_reason = request.POST.get("cancel_reason")
            print(cancellation_reason)
            logger.debug(f"Cancellation Reason: {cancellation_reason}")  # Log the cancellation reason

            if not cancellation_reason:
                messages.error(request, "Cancellation reason is required.")
                return redirect('order_details', order_id=order.id)

            # Proceed with cancellation
            try:
                order.is_cancelled = True
                order.canceled_by = request.user
                order.cancelled_at = timezone.now()
                order.cancellation_reason = cancellation_reason

                # Update order status to 'Cancelled'
                cancelled_status, _ = OrderStatus.objects.get_or_create(status="Cancelled")
                order.status = cancelled_status
                 # Retain stock
                for item in order.items.all():
                    item.variant.stock += item.quantity
                    item.variant.save()
                # Debugging: Log order details after changes
                logger.debug(f"Order Updated - ID: {order.id}, Status: {order.status.status}, is_cancelled: {order.is_cancelled}")

                # Save order
                order.save()

                messages.success(request, "Your order has been successfully canceled.")
                return redirect('my_orders')

            except Exception as e:
                logger.error(f"Error saving order cancellation: {e}")
                messages.error(request, "There was an error processing the cancellation.")
                return redirect('order_details', order_id=order.id)

    else:
        messages.error(request, "You cannot cancel this order at this stage.")
        return redirect('order_details', order_id=order.id)

def cancel_order_with_refund(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    # Debugging: Log current status and payment status
    logger.debug(f"Order ID: {order.id}, Current Status: {order.status.status}, Payment Status: {order.payment_details.payment_status.status if order.payment_details else 'No Payment Details'}")

    if order.status.status.lower() in ["pending", "processing"] and order.payment_details.payment_status.status.lower() == "completed":
        if request.method == "POST":
            cancellation_reason = request.POST.get("cancel_reason")
            logger.debug(f"Cancellation Reason: {cancellation_reason}")

            if not cancellation_reason:
                messages.error(request, "Cancellation reason is required.")
                return redirect('order_details', order_id=order.id)

            try:
                # Update order details
                order.is_cancelled = True
                order.canceled_by = request.user
                order.cancelled_at = timezone.now()
                order.cancellation_reason = cancellation_reason
                cancelled_status, _ = OrderStatus.objects.get_or_create(status="Cancelled")
                order.status = cancelled_status

                # Log the order cancellation
                logger.debug(f"Order Updated - ID: {order.id}, Status: {order.status.status}, is_cancelled: {order.is_cancelled}")
                # Retain stock
                for item in order.items.all():
                    item.variant.stock += item.quantity
                    item.variant.save()
                process_refund_to_wallet(order)
                # Update the payment status to 'Refund'
                if order.payment_details:
                    returned_status, _ = PaymentStatus.objects.get_or_create(status='Refund')
                    order.payment_details.payment_status = returned_status
                    order.payment_details.save()
                #Refund Process

                order.save()

                messages.success(request, "Your order has been successfully canceled with a refund.")
                return redirect('my_orders')

            except Exception as e:
                logger.error(f"Error processing refund: {e}")
                messages.error(request, f"Refund failed: {str(e)}")
                return redirect('order_details', order_id=order.id)
    else:
        messages.error(request, "You cannot cancel this order at this stage.")
        return redirect('order_details', order_id=order.id)

def return_order_with_refund(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    # Debugging: Log the current order status and payment status
    logger.debug(f"Order ID: {order.id}, Current Status: {order.status.status}, Payment Status: {order.payment_details.payment_status.status if order.payment_details else 'No Payment Details'}")
    print('befor')
    # Ensure return is allowed based on order status
    if order.status.status.lower() == "delivered" and order.payment_details.payment_status.status.lower() == "complete":
        print('yes')

        if request.method == "POST":
            return_reason = request.POST.get("return_reason")
            logger.debug(f"Return Reason: {return_reason}")  # Log the return reason

            if not return_reason:
                messages.error(request, "Return reason is required.")
                return redirect('order_details', order_id=order.id)

            # Proceed with return and refund in a transaction
            try:
                order.is_returned = True
                order.return_reason = return_reason
                order.returned_at = timezone.now()

                # Debugging: Log order details after return
                logger.debug(f"Order Updated - ID: {order.id}, is_returned: {order.is_returned}")
                # Retain stock
                for item in order.items.all():
                    item.variant.stock += item.quantity
                    item.variant.save()
                # Process the refund to wallet (assuming this is a defined method)
                process_refund_to_wallet(order)
                if order.payment_details:
                    returned_status, _ = PaymentStatus.objects.get_or_create(status='Refund to Wallet')
                    order.payment_details.payment_status = returned_status
                    order.payment_details.save()
                # Save order
                order.save()

                messages.success(request, "Your order has been successfully returned with a refund.")
                return redirect('my_orders')

            except Exception as e:
                logger.error(f"Error processing return with refund: {e}")
                messages.error(request, f"Refund failed: {str(e)}")
                return redirect('order_details', order_id=order.id)

    else:
        messages.error(request, "You cannot return this order at this stage.")
        return redirect('order_details', order_id=order.id)

