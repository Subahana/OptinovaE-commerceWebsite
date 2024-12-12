from .models import CartItem

def cart_count(request):
    if request.user.is_authenticated:
        cart_items_count = CartItem.objects.filter(cart__user=request.user).count()
    else:
        cart_items_count = 0
    return {'cart_items_count': cart_items_count}
