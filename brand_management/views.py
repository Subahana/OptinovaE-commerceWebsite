from django.shortcuts import render, redirect, get_object_or_404
from .models import Brand
from .forms import BrandForm

def brand_list(request):
    brands = Brand.objects.all()
    return render(request, 'brands/brand_list.html', {'brands': brands})

def brand_create(request):
    if request.method == 'POST':
        form = BrandForm(request.POST, request.FILES)
        if form.is_valid():
            brand = form.save(commit=False)
            brand.is_active = True  
            brand.save()
            return redirect('brand_list')
        else:
            return render(request, 'brands/brand_add.html', {'form': form})
    else:
        form = BrandForm()
    return render(request, 'brands/brand_add.html', {'form': form})


def brand_edit(request, pk):
    brand = get_object_or_404(Brand, pk=pk)
    if request.method == 'POST':
        form = BrandForm(request.POST, request.FILES, instance=brand)
        if form.is_valid():
            form.save()
            return redirect('brand_list')
    else:
        form = BrandForm(instance=brand)
    return render(request, 'brands/brand_edit.html', {'form': form})

def brand_activate(request, pk):
    brand = get_object_or_404(Brand, pk=pk)
    if not brand.is_active:
        brand.is_active = True
        brand.save()
    return redirect('brand_list')

def brand_deactivate(request, pk):
    brand = get_object_or_404(Brand, pk=pk)
    if brand.is_active:
        brand.is_active = False
        brand.save()
    return redirect('brand_list')
