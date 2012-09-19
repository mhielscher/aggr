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

logger = logging.getLogger('aggr_debug')

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
            if timezone.now() < self.last_updated + self.minimum_refresh_time:
                logger.debug("Not updating, minimum refresh time not passed.")
                return self.cache
            conditional_request.add_header('If-Modified-Since', self.last_updated.strftime(web_timestamp_format))
        try:
            response = urllib2.urlopen(conditional_request)
        except urllib2.HTTPError as e:
            if e.code == 304:
                # Feed hasn't updated since we last hit it; return old cache.
                return self.cache
            else:
                # Some other error. Probably should do something about it,
                # report it or something, but for now, do nothing.
                return self.cache
        
        if response.getcode() == 200:
            # Feed has been successfully downloaded.
            logger.debug("Cache will be updated.")
            last_modified = response.headers.get('Last-Modified')
            if last_modified:
                self.last_updated = parser.parse(last_modified)
            else:
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
            # 304 or an error, do nothing
            logger.debug("Cache not updating, code %d" % (response.getcode()))
        return self.cache


class Aggregate(models.Model):
    """Aggregates feeds into a unified, (soon to be) filtered aggregate feed."""
    name = models.CharField(max_length=100)
    feeds = models.ManyToManyField(Feed)
    filters = models.TextField(default="", null=True)
    items = PickledObjectField(default=[])
    
    def __unicode__(self):
        return self.name
    
    def get_unfiltered_items(self):
        """Returns all items in the component feeds, sorted by published timestamp."""
        feeds = [f.update_cache() for f in self.feeds.all()]
        # Add the feed name to each entry for annotation.
        for f in feeds:
            for e in f.entries:
                e['feed'] = f.feed
        self.items = [e for f in feeds for e in f.entries]
        self.items.sort(key=lambda e: e.get('published_parsed') or e.get('updated_parsed'))
        return self.items
    
    def apply_filters(self):
        """Compiles filters, returns matching entries."""
        compiled_filters = [re.compile(f) for f in self.filters.split("\n")]
        filtered_items = []
        for entry in self.items:
            for regex in compiled_filters:
                if regex.search(entry.title) or regex.search(entry.summary):
                    filtered_items.append(entry)
                    break
        self.items = filtered_items
        return filtered_items

