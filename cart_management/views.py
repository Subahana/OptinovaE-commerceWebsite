from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Cart, CartItem, Wishlist, Coupon  # Ensure you have a Coupon model
from products.models import ProductVariant
from django.contrib import messages
from django.middleware.csrf import get_token
import json
from decimal import Decimal
from offer_management.models import CategoryOffer
from django.views.decorators.cache import never_cache
from django.utils import timezone

# --------------Cart Management---------------#

@login_required(login_url='accounts:user_login_view')
def add_to_cart(request, variant_id):
    if request.method == "POST":
        quantity = request.POST.get('quantity')

        try:
            quantity = int(quantity)
            if quantity <= 0:
                return JsonResponse({'message': 'Quantity must be greater than 0', 'status': 'error'})
        except ValueError:
            return JsonResponse({'message': 'Invalid quantity', 'status': 'error'})

        variant = get_object_or_404(ProductVariant, id=variant_id)
        user = request.user  

        if variant.stock <= 0:
            return JsonResponse({'message': 'Out of stock', 'status': 'error'})

        cart, _ = Cart.objects.get_or_create(user=user)
        cart_item, created = CartItem.objects.get_or_create(cart=cart, variant=variant)

        new_quantity = cart_item.quantity + quantity if not created else quantity

        if new_quantity > variant.stock:
            return JsonResponse({
                'message': f'Only {variant.stock - cart_item.quantity} units are left to add to the cart',
                'status': 'error'
            })

        if new_quantity > 10:
            return JsonResponse({
                'message': 'You cannot add more than 10 units of this item',
                'status': 'error'
            })

        cart_item.quantity = new_quantity
        cart_item.save()

        return JsonResponse({'message': 'Item added to cart successfully', 'status': 'success'})
    else:
        return JsonResponse({'message': 'Invalid request method', 'status': 'error'})

@never_cache
@login_required(login_url='accounts:user_login_view')
def cart_detail(request):
    try:
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_items = CartItem.objects.filter(cart=cart)
        available_coupons = Coupon.objects.filter(active=True, valid_to__gte=timezone.now())

        if not request.GET.get('apply_coupon'):
            cart.coupon = None
            cart.save()

        # Initialize totals
        original_total = 0
        offer_total = 0
        offer_discount_amount = 0
        coupon_discount_amount = 0
        total_discount = 0
        final_total = 0

        cart_items_with_offers = []

        for item in cart_items:
            original_price = item.variant.price
            offer_price = item.variant.get_discounted_price() or original_price
            quantity = item.quantity

            # Calculate item total price based on quantity
            item_total_price = offer_price * quantity

            # Add to overall totals
            original_total += original_price * quantity
            offer_total += item_total_price

            # Store item details with item total price
            cart_items_with_offers.append({
                'item': item,
                'original_price': original_price,
                'discounted_price': offer_price,
                'item_total_price': item_total_price,
            })
        
        # Calculate offer discount amount
        offer_discount_amount = original_total - offer_total
        # Apply coupon discount if any
        if cart.coupon:
            discount_base = offer_total if offer_discount_amount > 0 else original_total
            coupon_discount_amount = cart.coupon.get_discount_amount(discount_base)

        total_discount = offer_discount_amount + coupon_discount_amount
        final_total = original_total - total_discount
        total_items = sum(item.quantity for item in cart_items)
        # Variants not in cart
        all_variants = ProductVariant.objects.all()
        in_cart_variants = cart_items.values_list('variant_id', flat=True)
        variants_not_in_cart = all_variants.exclude(id__in=in_cart_variants)
        cart.final_price = final_total
        cart.total_discount = total_discount
        cart.save()
        context = {
            'cart_items': cart_items,
            'cart_items_with_offers': cart_items_with_offers,
            'original_total': original_total,
            'offer_total': offer_total,
            'offer_discount_amount': offer_discount_amount,
            'coupon_discount_amount': coupon_discount_amount,
            'total_discount': total_discount,
            'final_total': final_total,
            'variants_not_in_cart': variants_not_in_cart,
            'total_items': total_items,
            'csrf_token': get_token(request),
            'available_coupons': available_coupons,
            'coupon_code': cart.coupon.code if cart.coupon else None
        }

        return render(request, 'cart_management/cart_detail.html', context)

    except Exception as e:
        import traceback
        error_message = traceback.format_exc()
        print(f"Error in cart_detail view: {error_message}")
        return JsonResponse({'error': 'An error occurred.'}, status=500)


@login_required(login_url='accounts:user_login_view')
def remove_from_cart(request, cart_item_id):
    cart_item = get_object_or_404(CartItem, id=cart_item_id)
    if cart_item.cart.user == request.user:
        cart_item.delete()
        return redirect('cart_detail')
    return JsonResponse({'error': 'You are not authorized to remove this item'}, status=403)


@login_required(login_url='accounts:user_login_view')
def update_cart_item_quantity(request, item_id):
    if request.method == 'POST':
        try:
            new_quantity = int(request.POST.get('quantity'))
            cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)

            # Check if the new quantity is valid
            if new_quantity < 1:
                return JsonResponse({'success': False, 'error': 'Quantity must be at least 1.'})

            # Check stock availability
            available_stock = cart_item.variant.stock
            if new_quantity > available_stock:
                return JsonResponse({
                    'success': False,
                    'error': f"Only {available_stock} items available in stock."
                })

            # Update quantity and save
            cart_item.quantity = new_quantity

            # Calculate item total price
            item_discounted_price = cart_item.variant.get_discounted_price()
            item_total_price = cart_item.variant.get_discounted_price() * cart_item.quantity if cart_item.variant.get_discounted_price() < cart_item.variant.price else cart_item.variant.price * cart_item.quantity
            cart_item.total_price = item_total_price
            print(cart_item.total_price)
            cart_item.save()

            # Calculate cart totals
            cart = cart_item.cart
            
            # Initialize totals
            original_total = sum(item.variant.price * item.quantity for item in cart.cartitem_set.all())
            offer_total = sum(item.variant.get_discounted_price() * item.quantity for item in cart.cartitem_set.all())
            offer_discount_amount = original_total - offer_total
            
            # Coupon discount calculation
            coupon_discount_amount = Decimal('0.00')
            if cart.coupon:
                discount_base = offer_total if offer_discount_amount > 0 else original_total
                coupon_discount_amount = cart.get_discount()

            # Final totals
            total_discount = offer_discount_amount + coupon_discount_amount
            final_total = original_total - total_discount
            total_items = sum(item.quantity for item in cart.cartitem_set.all())
            cart.final_price=final_total
            cart.save()
            # Return successful response with updated values
            return JsonResponse({
                'success': True,
                'item_quantity': cart_item.quantity,
                'item_total_price': item_total_price,
                'total_items': total_items,
                'original_total': original_total,
                'offer_total': offer_total,
                'offer_discount_amount': offer_discount_amount,
                'coupon_discount_amount': coupon_discount_amount,
                'total_discount': total_discount,
                'final_total': final_total
            })
        
        except CartItem.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Cart item not found.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request method.'})


# --------------Wishlist Management---------------#
@never_cache
@login_required(login_url='accounts:user_login_view')
def view_wishlist(request):
    wishlist = request.user.wishlist
    wishlist_items = wishlist.variants.all()
    is_empty = not wishlist_items.exists()

    context = {
        'wishlist_items': wishlist_items,
        'wishlist': wishlist,
        'is_empty': is_empty,
        'csrf_token': get_token(request) 
    }
    return render(request, 'cart_management/wishlist.html', context)


@login_required(login_url='accounts:user_login_view')
def add_to_wishlist(request, variant_id):
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'message': 'User not authenticated.'}, status=403)       
        try:
            variant = get_object_or_404(ProductVariant, id=variant_id)
            wishlist, created = Wishlist.objects.get_or_create(user=request.user)
            if variant in wishlist.variants.all():
                wishlist.variants.remove(variant)
                action = 'removed'
                message = 'Item removed from wishlist.'
            else:
                wishlist.variants.add(variant)
                action = 'added'
                message = 'Item added to wishlist.'
            return JsonResponse({'success': True, 'action': action, 'message': message})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error: {str(e)}'}, status=500)    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=400)

@login_required(login_url='accounts:user_login_view')
def remove_from_wishlist(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        selected_items = data.get('selected_items', [])

        if selected_items:
            wishlist = Wishlist.objects.get(user=request.user)
            for item_id in selected_items:
                variant = get_object_or_404(ProductVariant, id=item_id)
                wishlist.variants.remove(variant)

        return JsonResponse({'status': 'success'})
    else:
        return JsonResponse({'status': 'error'}, status=400)
