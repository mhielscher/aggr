from django.conf.urls import patterns, include, url
from django.views.generic import DeleteView
from aggr_app.models import Aggregate
from aggr_app.feeds import AggregateFeed

urlpatterns = patterns('aggr_app.views',
    url(r'^$', 'home'),
    url(r'^feed/(?P<feed_id>\d+)$', 'feed_detail'),
    url(r'^feed/new$', 'new_feed'),
    url(r'^feed/(?P<feed_id>\d+)/delete$', 'delete_feed'),
    url(r'^aggr/(?P<aggr_id>\d+)$', 'aggr_detail'),
    url(r'^aggr/new$', 'new_aggr'),
    url(r'^aggr/(?P<aggr_id>\d+)/modify$', 'new_aggr'),
    url(r'^aggr/(?P<aggr_id>\d+)/delete$', 'delete_aggr'),
    url(r'^rss/(?P<aggr_id>\d+)$', AggregateFeed(), name='aggr-rss'),
)

urlpatterns += patterns('',
    url(r'^login$', 'django.contrib.auth.views.login'),
    url(r'^logout$', 'django.contrib.auth.views.logout'),
)
