from aggr_app.models import Feed, Aggregate
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, render_to_response, get_object_or_404
from django.template import RequestContext
import feedparser

def index(request):
    """Lists all Feeds and Aggregates by name."""
    feed_list = Feed.objects.all().order_by('-last_updated')
    aggr_list = Aggregate.objects.all().order_by('-name')
    return render(request, 'aggr_app/index.html', {'feed_list': feed_list, 'aggr_list': aggr_list})

def feed_detail(request, feed_id):
    """Displays all entries in a given feed."""
    feed = get_object_or_404(Feed, pk=feed_id)
    feed.update_cache()
    return render_to_response('aggr_app/feed_detail.html', {'feed': feed})

def new_feed(request):
    """Displays a form to create a new feed."""
    return render_to_response('aggr_app/feed_new.html', context_instance=RequestContext(request))

def create_new_feed(request):
    """Creates a new feed from POST data from the feed_new form."""
    try:
        feed = Feed(name=request.POST['name'], url=request.POST['url'])
    except KeyError:
        return render_to_response('aggr_app/feed_new.html', {'error_message': 'Something is missing.'}, context_instance=RequestContext(request))
    else:
        feed.save()
        return HttpResponseRedirect(reverse('aggr_app.views.feed_detail', args=(feed.id,)))

def delete_feed(request, feed_id):
    """Confirm (GET) and delete (POST) an Feed.
    
    With a GET, display a confirmation page.
    With POST, do the actual deletion.
    """
    if request.method == 'GET':
        feed = Feed.objects.get(pk=feed_id)
        return render_to_response('aggr_app/feed_delete.html', {'feed': feed}, context_instance=RequestContext(request))
    elif request.method == 'POST':
        try:
            if feed_id != request.POST['feed_id']:
                return render_to_response('aggr_app/feed_delete.html', {'feed': Feed.objects.get(pk=feed_id), 'error_message': 'Feed IDs do not match.'}, context_instance=RequestContext(request))
            if request.POST['confirm'] == 'Cancel':
                return HttpResponseRedirect(reverse('aggr_app.views.feed_detail', args=(feed_id,)))
            feed = Feed.objects.get(pk=feed_id)
        except KeyError:
            return render_to_response('aggr_app/feed_delete.html', {'feed': Feed.objects.get(pk=feed_id), 'error_message': 'Something is missing.'}, context_instance=RequestContext(request))
        else:
            feed.delete()
            return HttpResponseRedirect(reverse('aggr_app.views.index'))

def aggr_detail(request, aggr_id):
    """Shows all entries (filtered) in a given Aggregate."""
    aggr = get_object_or_404(Aggregate, pk=aggr_id)
    aggr.get_unfiltered_items()
    aggr.apply_filters()
    return render_to_response('aggr_app/aggr_detail.html', {'aggr': aggr})

def new_aggr(request):
    """Displays a form for creating a new Aggregate."""
    feed_list = Feed.objects.all().order_by("name")
    return render_to_response('aggr_app/aggr_new.html', {'feed_list': feed_list}, context_instance=RequestContext(request))

def create_new_aggr(request):
    """Creates a new Aggregate from POST data from new_aggr."""
    try:
        print "trying"
        feed_ids = request.POST.getlist('feeds')
        feeds = Feed.objects.filter(id__in=feed_ids)
        aggr = Aggregate(name=request.POST['name'], filters=request.POST['filters'])
        print feed_ids
    except KeyError:
        print "error"
        return render_to_response('aggr_app/aggr_new.html', {'error_message': 'Something is missing.'}, context_instance=RequestContext(request))
    else:
        aggr.save()
        aggr.feeds = feeds
        aggr.save()
        print "success"
        return HttpResponseRedirect(reverse('aggr_app.views.aggr_detail', args=(aggr.id,)))

def delete_aggr(request, aggr_id):
    """Confirm (GET) and delete (POST) an Aggregate.
    
    With a GET, display a confirmation page.
    With POST, do the actual deletion.
    """
    if request.method == 'GET':
        aggr = Aggregate.objects.get(pk=aggr_id)
        return render_to_response('aggr_app/aggr_delete.html', {'aggr': aggr}, context_instance=RequestContext(request))
    elif request.method == 'POST':
        try:
            if aggr_id != request.POST['aggr_id']:
                return render_to_response('aggr_app/aggr_delete.html', {'aggr': Aggregate.objects.get(pk=aggr_id), 'error_message': 'Feed IDs do not match.'}, context_instance=RequestContext(request))
            if request.POST['confirm'] == 'Cancel':
                return HttpResponseRedirect(reverse('aggr_app.views.aggr_detail', args=(aggr_id,)))
            aggr = Aggregate.objects.get(pk=aggr_id)
        except KeyError:
            return render_to_response('aggr_app/aggr_delete.html', {'aggr': Aggregate.objects.get(pk=aggr_id), 'error_message': 'Something is missing.'}, context_instance=RequestContext(request))
        else:
            aggr.delete()
            return HttpResponseRedirect(reverse('aggr_app.views.index'))

