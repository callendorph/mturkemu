# File: mturkemu/urls.py
# Author: Carl Allendorph
#
# Description:
#   Main URL definitions for the application.
#

from django.conf import settings
from django.conf.urls import url, include
from django.contrib import admin
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    # Default Login/Logout URLs for Django
    url('^accounts/login/', auth_views.login, name="login"),
    url('^accounts/logout/', auth_views.logout, name="logout"),

]

# In production we need to serve these static images from
# the webserver directly - NOT THROUGH DJANGO
if settings.DEBUG:
    urlpatterns += static(
        settings.STATIC_URL, document_root=settings.STATIC_ROOT
    )
