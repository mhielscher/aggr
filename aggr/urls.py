from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('aggr_app.views',
    url(r'^$', 'index'),
    url(r'^feed/(?P<feed_id>\d+)/$', 'feed_detail'),
    url(r'^feed/new/$', 'new_feed'),
    url(r'^feed/new/create/$', 'create_new_feed'),
    url(r'^feed/(?P<feed_id>\d+)/delete/confirm/$', 'confirm_delete_feed'),
    url(r'^feed/(?P<feed_id>\d+)/delete/$', 'delete_feed'),
    url(r'^aggr/(?P<aggr_id>\d+)/$', 'aggr_detail'),
    url(r'^aggr/new/', 'new_aggr'),
    url(r'^aggr/new/create/$', 'create_new_aggr'),
)

urlpatterns += patterns('',
    url(r'^admin/', include(admin.site.urls)),
)
