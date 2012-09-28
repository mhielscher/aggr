from aggr_app.models import Feed, FilteredFeed, Aggregate
from aggr_app.feeds import AggregateFeed
from aggr_app.forms import NewFeedForm, NewAggrForm
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, render_to_response, get_object_or_404
from django.template import RequestContext
import feedparser
import logging

logger = logging.getLogger(__name__)

def index(request):
    """Lists all Feeds and Aggregates by name."""
    feed_list = Feed.objects.all().order_by('-last_updated')
    aggr_list = Aggregate.objects.all().order_by('-name')
    return render(
        request,
        'aggr_app/index.html', 
        {'feed_list': feed_list, 'aggr_list': aggr_list}
    )

def feed_detail(request, feed_id):
    """Displays all entries in a given feed."""
    feed = get_object_or_404(Feed, pk=feed_id)
    feed.update_cache()
    return render(
        request,
        'aggr_app/feed_detail.html',
        {'feed': feed}
    )

def new_feed(request):
    """Create a new feed.
    
    GET: display the new feed form.
    POST: attempt to create the new feed.
    """
    if request.method == 'GET':
        form = NewFeedForm()
        return render(
            request,
            'aggr_app/feed_new.html',
            {'form': form}
        )
    
    elif request.method == 'POST':
        form = NewFeedForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            url = form.cleaned_data['url']
            
            if Feed.objects.filter(url=url).exists():
                return render(
                    request,
                    'aggr_app/feed_new.html',
                    {
                        'error_message': 'That feed already exists.',
                        'form': form
                    }
                )
        
            # Finally create the new Feed.
            feed = Feed(name=name, url=url)
            feed.save()
            return HttpResponseRedirect(
                reverse('aggr_app.views.feed_detail',
                args=(feed.id,))
            )
        else:
            return render(
                request,
                'aggr_app/feed_new.html',
                {
                    'form': form
                }
            )
            

def delete_feed(request, feed_id):
    """Confirm (GET) and delete (POST) an Feed.
    
    GET: display a confirmation page.
    POST: do the actual deletion.
    """
    if request.method == 'GET':
        feed = Feed.objects.get(pk=feed_id)
        return render(
            request,
            'aggr_app/feed_delete.html',
            {'feed': feed}
        )
    
    elif request.method == 'POST':
        try:
            if feed_id != request.POST['feed_id']:
                logger.info("Attempted delete failed: feed IDs did not match. [%s vs. %s]" % (feed_id, request.POST['feed_id']))
                return render(
                    request,
                    'aggr_app/feed_delete.html',
                    {
                        'feed': Feed.objects.get(pk=feed_id),
                        'error_message': 'Feed IDs do not match. Something went wrong!'
                    },
                    context_instance=RequestContext(request)
                )
            
            if request.POST['confirm'] == 'Cancel':
                return HttpResponseRedirect(
                    reverse('aggr_app.views.feed_detail',
                    args=(feed_id,))
                )
        except KeyError:
            return render(
                request,
                'aggr_app/feed_delete.html',
                {
                    'feed': Feed.objects.get(pk=feed_id),
                    'error_message': 'Something is missing.'
                }
            )
        else:
            feed = Feed.objects.get(pk=feed_id)
            feed.delete()
            return HttpResponseRedirect(reverse('aggr_app.views.index'))

def aggr_detail(request, aggr_id):
    """Shows all entries (filtered) in a given Aggregate."""
    aggr = get_object_or_404(Aggregate, pk=aggr_id)
    aggr.apply_filters()
    aggr.save()
    rss_url = reverse('aggr-rss', args=(aggr.id,))
    return render(
        request,
        'aggr_app/aggr_detail.html',
        {'aggr': aggr, 'rss_url': rss_url}
    )

def new_aggr(request, aggr_id=None):
    """Create a new Aggregate.
    
    GET: display the new aggr form.
    POST: attempt to create the new aggr.
    """
    logger.debug("aggr_id=%s" % aggr_id)
    if request.method == 'GET':
        if aggr_id:
            aggr = Aggregate.objects.get(pk=aggr_id)
            form = NewAggrForm(initial={'name': aggr.name}, filters=aggr.feed_tuple())
        else:
            aggr = None
            form = NewAggrForm()
        
        # Neat trick to turn ['feed0', 'filter0', 'feed1', 'filter1', ...]
        # into [('feed0', 'filter0'), ('feed1', 'filter1'), ...]
        filter_fields_iter = list(form)[2:].__iter__()
        filter_fields = zip(filter_fields_iter, filter_fields_iter)
        
        return render(
            request,
            'aggr_app/aggr_new.html',
            {
                'aggr': aggr,
                'form': form,
                'filter_fields': filter_fields
            }
        )
    
    elif request.method == 'POST':
        logger.debug("trying")
        filter_count = int(request.POST.get('filter_count'))
        form = NewAggrForm(request.POST, filter_count=filter_count)
        if form.is_valid():
            logger.debug("Form is valid.")
            if aggr_id:
                logger.debug("Modifying existing Aggr id=%s" % aggr_id)
                aggr = Aggregate.objects.get(pk=aggr_id)
                aggr.name = form.cleaned_data['name']
            else:
                logger.debug("Creating new Aggr")
                aggr = Aggregate(name=form.cleaned_data['name'])
            
            feed_filters = []
            logger.debug("filter_count=%d" % (filter_count,))
            for (feed, feed_filter) in (('feed%d'%i, 'filter%d'%i) for i in range(filter_count)):
                feed_obj = Feed.objects.get(pk=form.cleaned_data[feed])
                logger.debug(feed_obj)
                filtered_feed = FilteredFeed(feed=feed_obj, re_filter=form.cleaned_data[feed_filter])
                filtered_feed.save()
                feed_filters.append(filtered_feed)
        else:
            logger.debug("Form NOT valid.")
            logger.debug(form)
            aggr = None
            filter_fields_iter = list(form)[2:].__iter__()
            filter_fields = zip(filter_fields_iter, filter_fields_iter)
            return render(
                request,
                'aggr_app/aggr_new.html',
                {
                    'aggr': aggr,
                    'form': form,
                    'filter_fields': filter_fields
                }
            )
        # Pre-save the model before we can use the ManyToManyField.
        if not aggr_id:
            aggr.save()
        logger.debug(feed_filters)
        aggr.feeds = feed_filters
        aggr.save()
        logger.debug("success")
        return HttpResponseRedirect(
            reverse('aggr_app.views.aggr_detail',
            args=(aggr.id,))
        )
            
def delete_aggr(request, aggr_id):
    """Confirm (GET) and delete (POST) an Aggregate.
    
    With a GET, display a confirmation page.
    With POST, do the actual deletion.
    """
    if request.method == 'GET':
        aggr = Aggregate.objects.get(pk=aggr_id)
        return render(
            request,
            'aggr_app/aggr_delete.html',
            {'aggr': aggr}
        )
    
    elif request.method == 'POST':
        try:
            if aggr_id != request.POST['aggr_id']:
                return render(
                    request,
                    'aggr_app/aggr_delete.html',
                    {
                        'aggr': Aggregate.objects.get(pk=aggr_id),
                        'error_message': 'Feed IDs do not match.'
                    },
                    context_instance=RequestContext(request)
                )
            if request.POST['confirm'] == 'Cancel':
                return HttpResponseRedirect(
                    reverse('aggr_app.views.aggr_detail',
                    args=(aggr_id,))
                )
            aggr = Aggregate.objects.get(pk=aggr_id)
        except KeyError:
            return render(
                request,
                'aggr_app/aggr_delete.html',
                {
                    'aggr': Aggregate.objects.get(pk=aggr_id),
                    'error_message': 'Something is missing.'
                },
                context_instance=RequestContext(request)
            )
        else:
            for feed in aggr.feeds.all():
                feed.delete()
            aggr.delete()
            return HttpResponseRedirect(reverse('aggr_app.views.index'))

