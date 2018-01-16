"""automation URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from django.contrib import admin

from reports.views import get_report, get_test_live_report, test_progress, \
    download_test_report, cancel_test


urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^', include('reports.urls')),
    url(r'^report/$', view = get_report, name = "report"),
    url(r'^live_report/$', view = get_test_live_report, name = "live_report"),
    url(r'^cancel_test/$', view = cancel_test, name = "cancel_test"),
    url(r'^test/$', view = test_progress, name = "test_progress"),
    url(r'^download/(?P<fileid>\w+)/$', view = download_test_report, name = "download"),
]
