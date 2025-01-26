from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

def custom_404(request, exception):
    return JsonResponse({'error': 'Not found'}, status=404)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
]

handler404 = custom_404
