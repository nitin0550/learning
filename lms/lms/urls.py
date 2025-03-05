from django.contrib import admin
from django.urls import path,include
from django.contrib.auth import views as auth_views
#from .views import CustomLoginView
from. import views
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('student.urls')),
    path('expert/', include('expert.urls')),
    path('login/', views.CustomLoginView.as_view(template_name=views.CustomLoginView.template_name), name='login'),
    path('verify-activation/', views.verify_activation, name='verify_activation'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('request_otp/', views.forgot_password, name='request_otp'),
    path('verify_otp/', views.verify_otp, name='verify_otp'),
    path('reset_password/', views.reset_password, name='reset_password'),
    path('chat/', include('chat.urls')),  # Include chat app URLs
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
