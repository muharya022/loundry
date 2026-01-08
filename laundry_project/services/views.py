from .models import Service
from django.shortcuts import render, get_object_or_404
from .models import Service

def service_list(request):
    services = Service.objects.all().order_by('name')
    return render(request, 'services/list.html', {'services': services})


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.db.models import ProtectedError
from .forms import ServiceForm
from .models import Service

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
