from aggr_app.models import Feed, Aggregate

def navbarlinks(request):
    public_aggrs = Aggregate.objects.filter(is_public=True)
    subscribed_feeds = Feed.objects.filter(subscribers__id=request.user.id)
    my_aggrs = Aggregate.objects.filter(owner=request.user.id)
    return {'public_aggrs': public_aggrs,
        'subscribed_feeds': subscribed_feeds,
        'my_aggrs': my_aggrs}
