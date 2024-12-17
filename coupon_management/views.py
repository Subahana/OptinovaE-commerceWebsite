from django.shortcuts import render, redirect, get_object_or_404
from .models import Coupon
from order_management.models import Order
from .forms import CouponForm
from django.contrib import messages
import json
from django.http import JsonResponse
from cart_management.models import Cart ,CartItem
from django.utils import timezone
from django.db.models import Q
import logging
from django.middleware.csrf import get_token

logger = logging.getLogger(__name__)

def create_coupon(request):
    if request.method == 'POST':
        form = CouponForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('coupon_list')
    else:
        form = CouponForm()
    return render(request, 'coupon/create_coupon.html', {'form': form})


def edit_coupon(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)  

    if request.method == 'POST':
        form = CouponForm(request.POST, instance=coupon)  
        if form.is_valid():
            form.save()  
            return redirect('coupon_list')  
    else:
        form = CouponForm(instance=coupon)  

    context = {
        'form': form,
    }
    return render(request, 'coupon/edit_coupon.html', context)


def coupon_list(request):
    coupons = Coupon.objects.all()  # Retrieve all coupons from the database
    for coupon in coupons:
        coupon.deactivate_if_expired()  # Check and deactivate if expired
    context = {
        'coupons': coupons,
    }
    return render(request, 'coupon/coupon_list.html', context)


def coupon_status(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)
    coupon.active = not coupon.active
    coupon.save()

    if coupon.active:
        messages.success(request, f'Coupon "{coupon.code}" has been activated.')
    else:
        messages.warning(request, f'Coupon "{coupon.code}" has been deactivated.')

    return redirect('coupon_list')
def apply_coupon(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method. Please use POST.'}, status=405)

    try:
        print('print',request.META.get('HTTP_X_CSRFTOKEN'))  # Log the received CSRF token

        # Parse JSON data from the request body
        data = json.loads(request.body)
        coupon_code = data.get('coupon_code', '').strip()
        if not coupon_code:
            return JsonResponse({'success': False, 'error': {'coupon_code': 'Coupon code is required.'}}, status=400)

        # Fetch the user's cart
        user_cart = get_object_or_404(Cart, user=request.user)
        cart_items = CartItem.objects.filter(cart=user_cart)

        if not cart_items.exists():
            return JsonResponse({'success': False, 'error': {'cart': 'Your cart is empty.'}}, status=400)

        # Calculate totals for the cart
        original_total = sum(item.variant.price * item.quantity for item in cart_items)
        offer_total = sum(
            (item.variant.get_discounted_price() or item.variant.price) * item.quantity for item in cart_items
        )
        offer_discount_amount = original_total - offer_total

        # Validate the coupon
        coupon = Coupon.objects.filter(code__iexact=coupon_code, active=True).first()
        print(coupon)
        if not coupon:
            return JsonResponse({'success': False, 'error': 'Invalid or expired coupon code.'}, status=400)

        order=Order.objects.filter(user=request.user).values('coupon')
        print(order)

        # Check if the user has already used this coupon (in any order, including uncompleted ones)
        if Order.objects.filter(user=request.user, coupon=coupon).exists():
            return JsonResponse({
                'success': False,
                'error': 'You have already used this coupon.'
            }, status=400)

        # Check coupon validity period
        current_time = timezone.now()
        if not (coupon.valid_from <= current_time <= coupon.valid_to):
            return JsonResponse({'success': False, 'error':  'Invalid or expired coupon code.'}, status=403)

        # Calculate the coupon discount and the final total
        coupon_discount_amount = coupon.get_discount_amount(offer_total)
        total_discount = coupon_discount_amount + offer_discount_amount
        coupon_discount_amount = min(coupon_discount_amount, offer_total)  # Cap discount at offer total
        final_total = offer_total - coupon_discount_amount

        # Save the applied coupon to the cart
        user_cart.coupon = coupon
        user_cart.total_discount = total_discount
        user_cart.final_price = final_total
        user_cart.save()

        # Return success response with updated totals
        return JsonResponse({
            'success': True,
            'original_total': float(original_total),
            'offer_total': float(offer_total),
            'final_total': float(final_total),
            'coupon_discount_amount': float(coupon_discount_amount),
            'offer_discount_amount': float(offer_discount_amount),
            'total_items': cart_items.count(),
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': {'data': 'Invalid data format. Please ensure your JSON is correctly formatted.'}}, status=400)
    except Exception as e:
        logger.error(f"Error applying coupon: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': {'system': 'An unexpected error occurred. Please try again later.'}}, status=500)

def remove_coupon(request):
    if request.method == 'POST':
        try:
            # Fetch the user's cart
            user_cart = get_object_or_404(Cart, user=request.user)

            # Check if a coupon is applied
            if user_cart.coupon:
                # Remove the coupon
                user_cart.coupon = None
                user_cart.save()

                # Recalculate totals without the discount
                original_total = user_cart.get_original_total()
                cart_items = CartItem.objects.filter(cart=user_cart)  # Fetch cart items
                offer_total = sum((item.variant.get_discounted_price() or item.variant.price) * item.quantity for item in cart_items)
                offer_discount_amount = original_total - offer_total

                # Since coupon is removed, final total is just the original total
                final_total = original_total  - offer_discount_amount
                total_items = sum(item.quantity for item in cart_items)

                # Return updated cart data
                return JsonResponse({
                    'success': True,
                    'original_total': original_total,
                    'offer_total': offer_total,
                    'offer_discount_amount': offer_discount_amount,
                    'final_total': final_total,
                    'coupon_discount_amount': 0,  
                    'total_items': total_items
                })

            return JsonResponse({'success': False, 'error': 'No coupon applied.'}, status=400)
        
        except Exception as e:
            print(f"Error removing coupon: {e}")
            return JsonResponse({'success': False, 'error': 'Failed to remove the coupon.'}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405)
