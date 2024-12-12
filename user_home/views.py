from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from products.models import Product, Category,ProductVariant
from offer_management.models import CategoryOffer
from cart_management.models import Wishlist,CartItem
from brand_management.models import Brand
from products.forms import ProductVariantForm
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Prefetch, F, Q
from django.contrib.auth import logout
from django.middleware.csrf import get_token
from django.db.models import Prefetch,Exists, OuterRef,Subquery,F
from django.http import JsonResponse
from django.utils import timezone
from user_wallet.models import Wallet
from itertools import chain



@login_required(login_url='accounts:user_login_view')
def user_product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if not product.is_active:
        messages.warning(request, 'This product is inactive. Redirecting to the shop.')
        return redirect('shop')

    if not product.category.is_active:
        messages.warning(request, 'The category of this product is not active. Redirecting to the shop.')
        return redirect('shop')

    main_variant = product.variants.first()  # Fetch the main variant

    # Get active offers for the product's category
    active_offers = CategoryOffer.objects.filter(
        category=product.category,
        is_active=True
    )

    # Fetch related products
    related_products = Product.objects.filter(
        category=product.category,
        is_active=True
    ).exclude(id=product.id).prefetch_related(
        Prefetch('variants', queryset=ProductVariant.objects.filter(is_active=True))
    ).order_by('?')[:4]

    categories = Category.objects.filter(is_active=True)

    # Prepare variant data with original and discounted prices
    variant_prices = []
    for variant in product.variants.filter(is_active=True):
        original_price = variant.price
        discounted_price = variant.get_discounted_price()  # Get the discounted price
        variant_prices.append({
            'variant': variant,
            'original_price': original_price,
            'discounted_price': discounted_price,
        })
        
    context = {
        'product': product,
        'main_variant': main_variant,
        'variant_prices': variant_prices,  # Pass variant prices to the template
        'related_products': related_products,
        'active_offers': active_offers,
        'categories': categories,
    }

    return render(request, 'user_home/shop_details.html', context)

@login_required(login_url='accounts:user_login_view')
def shop(request):
    # Fetch categories, products, brands, and active offers
    category_id = request.GET.get('category')
    brand_id = request.GET.get('brand')
    query = request.GET.get('q', '')
    sort_option = request.GET.get('sort')

    categories = Category.objects.filter(is_active=True)
    brands = Brand.objects.filter(is_active=True)
    active_offers = CategoryOffer.objects.filter(is_active=True)
    user_wishlist = Wishlist.objects.filter(user=request.user).values_list('variants__id', flat=True)

    # Fetch products and prefetch related fields for optimization
    products = Product.objects.filter(is_active=True).prefetch_related('category', 'variants')
    
    # Apply search filter
    if query:
        products = products.filter(name__icontains=query)
    
    # Apply category filter if valid
    if category_id and category_id != 'all':
        try:
            category_id = int(category_id)
            products = products.filter(category_id=category_id)
        except ValueError:
            pass  # Ignore invalid category_id

    # Apply brand filter if valid
    if brand_id and brand_id != 'all':
        try:
            brand_id = int(brand_id)
            products = products.filter(brand_id=brand_id)
        except ValueError:
            pass  # Ignore invalid brand_id

      # Sorting functionality based on main_variant price
    if sort_option == 'price_low':
        products = sorted(products, key=lambda p: p.main_variant.price if p.main_variant else p.base_price)
    elif sort_option == 'price_high':
        products = sorted(products, key=lambda p: p.main_variant.price if p.main_variant else p.base_price, reverse=True)
    elif sort_option == 'a_to_z':
        products = products.order_by('name')  # Alphabetical
    elif sort_option == 'z_to_a':
        products = products.order_by('-name')  # Reverse Alphabetical

    # Pagination logic
    per_page = 6
    paginator = Paginator(products, per_page)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Add discounted price for each product
    for product in page_obj:
        main_variant = product.main_variant  # Assuming main_variant is a method/property
        product.discounted_price = main_variant.get_discounted_price() if main_variant else product.price

    # Prepare context for rendering
    context = {
        'products': page_obj,
        'categories': categories,
        'brands': brands,
        'user_wishlist': user_wishlist,
        'page_obj': page_obj,
    }

    return render(request, 'user_home/shop.html', context)


@login_required(login_url='accounts:user_login_view')
def user_home(request):

    if request.user.is_superuser:
        messages.error(request, 'Admin users are not allowed to access the user home page.')
        return redirect('admin_page')  

    categories = Category.objects.filter(is_active=True)
    brands = Brand.objects.filter(is_active=True)
    active_offers = CategoryOffer.objects.filter(is_active=True)
    user_wishlist = Wishlist.objects.filter(user=request.user).values_list('variants__id', flat=True)

    # Fetch products and prefetch related fields for optimization
    products = Product.objects.filter(is_active=True).prefetch_related('category', 'variants')
    paginator = Paginator(products, 3)  # Show 6 products per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    # Add discounted price for each product
    for product in page_obj:
        main_variant = product.main_variant  # Assuming main_variant is a method/property
        product.discounted_price = main_variant.get_discounted_price() if main_variant else product.price

    context = {
        'products': products,
        'active_offers': active_offers,
        'page_obj': page_obj,
    }
    return render(request, 'user_home/index.html', context)


# View to handle user logout
@login_required(login_url='accounts:user_login_view')
def logout_view(request):
    if request.user.is_authenticated:
        logout(request)
    # Redirect to a specific page after logout or default to home
    return redirect(request.GET.get('next', 'accounts:first_page'))
