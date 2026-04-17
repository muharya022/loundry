from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.db.models import ProtectedError
from .forms import ServiceForm
from .models import Service
from django.db.models import Q

def service_list(request):
    services = Service.objects.all()
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        services = services.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Filter by type (Jenis Layanan)
    filter_type = request.GET.get('type', '')
    if filter_type:
        services = services.filter(type=filter_type)
    
    # Filter by duration (Durasi)
    filter_duration = request.GET.get('duration', '')
    if filter_duration:
        services = services.filter(duration=filter_duration)
    
    # Sort functionality
    sort_by = request.GET.get('sort', 'name_asc')
    if sort_by == 'name_asc':
        services = services.order_by('name')
    elif sort_by == 'name_desc':
        services = services.order_by('-name')
    elif sort_by == 'price_asc':
        services = services.order_by('price')
    elif sort_by == 'price_desc':
        services = services.order_by('-price')
    elif sort_by == 'newest':
        services = services.order_by('-created_at')
    elif sort_by == 'oldest':
        services = services.order_by('created_at')
    elif sort_by == 'duration_asc':
        services = services.order_by('duration')
    else:
        services = services.order_by('name')
    
    # Pagination
    paginator = Paginator(services, 9)
    page_number = request.GET.get('page')
    services_page = paginator.get_page(page_number)
    
    context = {
        'services': services_page,
        'search_query': search_query,
        'filter_type': filter_type,
        'filter_duration': filter_duration,
        'sort_by': sort_by,
    }
    
    return render(request, 'services/list.html', context)

def is_admin(user):
    return user.is_staff or user.is_superuser

@user_passes_test(is_admin)
def add_service(request):
    if request.method == 'POST':
        form = ServiceForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Layanan berhasil ditambahkan ✅")
            return redirect('services:list')
        else:
            messages.error(request, "Terjadi kesalahan, periksa kembali form.")
    else:
        form = ServiceForm()
    return render(request, 'services/add_service.html', {'form': form})

@user_passes_test(is_admin)
def edit_service(request, pk):
    service = get_object_or_404(Service, pk=pk)
    if request.method == 'POST':
        form = ServiceForm(request.POST, request.FILES, instance=service)
        if form.is_valid():
            form.save()
            messages.success(request, f"Layanan '{service.name}' berhasil diperbarui ✅")
            return redirect('services:list')
        else:
            messages.error(request, "Perubahan gagal disimpan. Periksa kembali input.")
    else:
        form = ServiceForm(instance=service)
    return render(request, 'services/edit_service.html', {'form': form, 'service': service})

@user_passes_test(is_admin)
def delete_service(request, pk):
    service = get_object_or_404(Service, pk=pk)
    try:
        service.delete()
        messages.success(request, f"Layanan '{service.name}' berhasil dihapus 🗑️")
    except ProtectedError:
        messages.error(request, f"Layanan '{service.name}' tidak dapat dihapus karena masih digunakan dalam pesanan.")
    return redirect('services:list')
