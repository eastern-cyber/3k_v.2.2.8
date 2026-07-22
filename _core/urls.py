from django.contrib import admin
from django.urls import path, include, reverse_lazy
from django.conf import settings
from django.conf.urls.static import static
from allauth.account.views import PasswordChangeView
from a_posts.views import *
from a_users.views import profile_view, index_view, signup_otp_view  # Add this import

urlpatterns = [
    path('', home_view, name="home"),
    path('admin/', admin.site.urls),
    path("accounts/password/change/", PasswordChangeView.as_view(success_url=reverse_lazy("settings")), name="account_change_password"),
    
    # Use function-based view for signup with OTP
    path('accounts/signup/', signup_otp_view, name='account_signup'),
    
    # Keep allauth URLs for other features
    path('accounts/', include('allauth.urls')),
    
    path('login/', index_view, name="index"),
    path('@<username>/', profile_view, name="profile"),
    path('explore/', explore_view, name="explore"),
    path('upload/', upload_view, name="upload"),
    path('post/', include("a_posts.urls")),
    path('profile/', include('a_users.urls', namespace='a_users')),
    path('following/', include("a_network.urls")),
    path('search/', include("a_search.urls")),
    path('notifications/', include("a_notifications.urls")),
    path('messages/', include("a_messages.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += [
        path("__reload__/", include("django_browser_reload.urls")),
    ]
else:
    from django.views.static import serve
    urlpatterns += [
        path("media/<path:path>/", serve, {"document_root": settings.MEDIA_ROOT},),
    ]