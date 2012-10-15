from aggr_app.models import Feed, FilteredFeed, Aggregate
from aggr_app.feeds import AggregateFeed
from aggr_app.forms import NewFeedForm, NewAggrForm
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, render_to_response, get_object_or_404
from django.template import RequestContext
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
import feedparser
import logging

logger = logging.getLogger(__name__)

def new_user(request):
    """Registers a new user."""
    if request.method == "GET":
        form = UserCreationForm()
        return render(
            request,
            'registration/register.html',
            {'form': form},
        )
    elif request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(form.cleaned_data['username'], password=form.cleaned_data['password1'])
            user.save()
            login(request, user)
            return HttpResponseRedirect(reverse('aggr_app.views.home'))
        else:
            return render(
                request,
                'registration/register.html',
                {'form': form}
            )

def home(request):
    """Lists all Feeds and Aggregates by name."""
    if request.user.is_authenticated():
        feed_list = request.user.feed_set.all().order_by('-last_updated')
        aggr_list = request.user.aggregate_set.all().order_by('-name')
    else:
        feed_list = None
        aggr_list = Aggregate.objects.filter(is_public=True)
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

@login_required
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
                feed = Feed.objects.get(url=url)
            else:
                feed = Feed(name=name, url=url)
                # do an initial save so we can manipulate ManyToMany
                feed.save()
            feed.subscribers.add(request.user)
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
            

@login_required
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
            return HttpResponseRedirect(reverse('aggr_app.views.home'))

def aggr_detail(request, aggr_id):
    """Shows all entries (filtered) in a given Aggregate."""
    aggr = get_object_or_404(Aggregate, pk=aggr_id)
    if not aggr.is_public and not request.user.is_authenticated():
        return HttpResponseRedirect(reverse('django.contrib.auth.views.login'))
    if aggr.owner != request.user:
        return HttpResponseRedirect(reverse('aggr_app.views.home')) # temporary
    
    # Authenticated to get this aggr
    aggr.apply_filters()
    aggr.save()
    rss_url = reverse('aggr-rss', args=(aggr.id,))
    return render(
        request,
        'aggr_app/aggr_detail.html',
        {'aggr': aggr, 'rss_url': rss_url}
    )

@login_required
def new_aggr(request, aggr_id=None):
    """Create a new Aggregate.
    
    GET: display the new aggr form.
    POST: attempt to create the new aggr.
    """
    logger.debug("aggr_id=%s" % aggr_id)
    feed_choices = [(feed.id, feed.name) for feed in request.user.feed_set.all()]
    if request.method == 'GET':
        if aggr_id:
            aggr = Aggregate.objects.get(pk=aggr_id)
            form = NewAggrForm(initial={'name': aggr.name}, feed_choices=feed_choices, filters=aggr.feed_tuple())
        else:
            aggr = None
            form = NewAggrForm(feed_choices=feed_choices)
        
        # Neat trick to turn ['feed0', 'filter0', 'feed1', 'filter1', ...]
        # into [('feed0', 'filter0'), ('feed1', 'filter1'), ...]
        filter_fields_iter = list(form)[3:].__iter__()
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
        form = NewAggrForm(request.POST, filter_count=filter_count, feed_choices=feed_choices)
        if form.is_valid():
            logger.debug("Form is valid.")
            if aggr_id:
                logger.debug("Modifying existing Aggr id=%s" % aggr_id)
                aggr = Aggregate.objects.get(pk=aggr_id)
                aggr.name = form.cleaned_data['name']
                aggr.is_public = form.cleaned_data['is_public']
            else:
                logger.debug("Creating new Aggr")
                aggr = Aggregate(name=form.cleaned_data['name'], is_public=form.cleaned_data['is_public'], owner=request.user)
            
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
            
@login_required
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
            return HttpResponseRedirect(reverse('aggr_app.views.home'))

