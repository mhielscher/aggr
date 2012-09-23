from django.db import models
import datetime
import time
from dateutil import parser
from django.utils import timezone
from picklefield.fields import PickledObjectField
import feedparser
import urllib2
import re
import logging

logger = logging.getLogger(__name__)

web_timestamp_format = "%a, %d %b %Y %H:%M:%S %Z"

class Feed(models.Model):
    """Models RSS/Atom feeds; parses and caches their contents."""
    name = models.CharField(max_length=100)
    url = models.URLField(max_length=400)
    cache = PickledObjectField()
    last_updated = models.DateTimeField(auto_now_add=True)
    cache_expires = models.DateTimeField(auto_now_add=True)
    minimum_refresh_time = datetime.timedelta(seconds=120)
    
    def __unicode__(self):
        return self.name
    
    def update_cache(self, force=False):
        """Fetches and parses the feed if it has updated.
        
        Uses a conditional GET to retrieve an updated feed, then parses it,
        updates the cache, and returns the parsed feed.
        
        If force == True, do a full GET and update the cache regardless.
        """
        logger.debug("Updating cache of %s:%d." % (self.name, self.id))
        conditional_request = urllib2.Request(self.url)
        if not force:
            if self.cache and timezone.now() < self.last_updated + self.minimum_refresh_time:
                logger.debug("Not updating, minimum refresh time not passed.")
                return self.cache
            conditional_request.add_header(
                'If-Modified-Since',
                self.last_updated.strftime(web_timestamp_format)
            )
        try:
            response = urllib2.urlopen(conditional_request)
        except urllib2.HTTPError as e:
            if e.code == 304:
                # Feed hasn't updated since we last hit it; return old cache.
                return self.cache
            else:
                # Some other error. Probably should do something about it,
                # report it or something, but for now, do nothing.
                logger.debug("Got %d from %s when trying to update cache." % (e.code, self.url))
                return self.cache
        
        # Feed has been successfully downloaded.
        if response.getcode() == 200:
            logger.debug("Cache will be updated.")
            last_modified = response.headers.get('Last-Modified')
            #if last_modified:
            #    self.last_updated = parser.parse(last_modified)
            #else:
            #    self.last_updated = timezone.now()
            
            # last_updated needs to be the actual update time so that minimum_refresh_time works
            self.last_updated = timezone.now()
            logger.debug("New Last-Modified=%s" % (last_modified))
            logger.debug("Setting last_updated=%s" % (self.last_updated))
            
            if response.headers.get('Expires'):
                self.cache_expires = parser.parse(response.headers.get('Expires'))
            else:
                # No explicit Expires header;
                # check for age limits in Cache-Control.
                # This needs more thought and a closer look.
                cache_control = response.headers.get('Cache-Control')
                if cache_control and cache_control.find("max-age="):
                    start_index = cache_control.find("max-age=")
                    end_index = cache_control.find(",", start_index)
                    if end_index == -1:
                        end_index = len(cache_control)
                    max_age = int(cache_control[start_index+8:end_index])
                    self.cache_expires = self.last_updated + datetime.timedelta(seconds=max_age)
                else:
                    self.cache_expires = timezone.now() + self.minimum_refresh_time
            logger.debug("Setting cache_expires=%s" % (self.cache_expires))
            self.cache = feedparser.parse(response.read())
            self.save()
        else:
            # Some kind of redirect? Write a debug message.
            logger.debug("Cache not updating, code %d, url %s" % (response.getcode(), self.url))
        return self.cache

class FilteredFeed(models.Model):
    feed = models.ForeignKey(Feed)
    re_filter = models.CharField(max_length=400, null=True)
    
    def __unicode__(self):
        return u"%s: %s" % (self.feed, self.re_filter)
    
    def compiled_filter(self):
        return re.compile(self.re_filter)


class Aggregate(models.Model):
    """Aggregates feeds into a unified, filtered aggregate feed."""
    name = models.CharField(max_length=100)
    feeds = models.ManyToManyField(FilteredFeed)
    items = PickledObjectField(default=[])
    
    def __unicode__(self):
        return self.name
    
    # Deprecated, returns duplicates.
    def get_unfiltered_items(self):
        """Returns all items in the component feeds, sorted by published timestamp."""
        feeds = [f.feed.update_cache() for f in self.feeds.all()]
        # Add the feed name to each entry for annotation.
        for feed in feeds:
            for entry in feed.entries:
                entry['feed'] = feed.feed
        self.items = [e for f in feeds for e in f.entries]
        self.items.sort(key=lambda e: e.get('published_parsed') or e.get('updated_parsed'))
        return self.items
    
    def apply_filters(self):
        """Compiles filters; returns matching entries."""
        items = []
        for feed in self.feeds.all():
            if feed.re_filter == "":
                items.extend((e for e in feed.feed.update_cache().entries if e not in items))
            else:
                compiled_re = feed.compiled_filter()
                for entry in feed.feed.update_cache().entries:
                    if compiled_re.search(entry.title) or compiled_re.search(entry.summary):
                        if entry not in items:
                            logger.debug("Adding %s" % entry.title)
                            items.append(entry)
        # Sort by descending published date.
        self.items = sorted(items, key=lambda e: e.get('published_parsed') or e.get('updated_parsed'))
        return self.items

