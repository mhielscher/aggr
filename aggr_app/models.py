from django.db import models
import datetime
import time
from dateutil import parser
from django.utils import timezone
from picklefield.fields import PickledObjectField
import feedparser
import urllib2
import re

web_timestamp_format = "%a, %d %b %Y %H:%M:%S %Z"

class FeedCacheField(PickledObjectField):
    def __unicode__(self):
        return unicode(self.to_python())

class Feed(models.Model):
    name = models.CharField(max_length=100)
    url = models.URLField(max_length=400)
    cache = FeedCacheField()
    last_updated = models.DateTimeField(auto_now_add=True)
    cache_expires = models.DateTimeField(auto_now_add=True)
    minimum_refresh_time = datetime.timedelta(seconds=120)
    
    def __unicode__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        #self.get_cache_or_refresh()
        super(Feed, self).save(*args, **kwargs)
    
    def update_cache(self, force=False):
        print "Updating cache of %s:%d." % (self.name, self.id)
        conditional_request = urllib2.Request(self.url)
        if not force:
            if timezone.now() < self.last_updated + self.minimum_refresh_time:
                print "Not updating, minimum refresh time not passed."
                return self.cache
            conditional_request.add_header('If-Modified-Since', self.last_updated.strftime(web_timestamp_format))
        try:
            response = urllib2.urlopen(conditional_request)
        except urllib2.HTTPError as e:
            if e.code == 304:
                return self.cache
            else:
                return self.cache
        
        if response.getcode() == 200:
            print "Cache will be updated."
            last_modified = response.headers.get('Last-Modified')
            if last_modified:
                self.last_updated = parser.parse(last_modified)
            else:
                self.last_updated = timezone.now()
            print "New Last-Modified=%s" % (last_modified)
            print "Setting last_updated=%s" % (self.last_updated)
            expires = response.headers.get('Expires')
            if not expires:
                cache_control = response.headers.get('Cache-Control')
                if cache_control and cache_control.find("max-age="):
                    start_index = cache_control.find("max-age=")
                    end_index = cache_control.find(",", start_index)
                    if end_index == -1:
                        end_index = len(cache_control)
                    max_age = int(cache_control[start_index+8:end_index])
                    expires = parser.parse(response.headers['Date']) + datetime.timedelta(seconds=max_age)
            else:
                expires = parser.parse(expires)
            if expires:
                self.cache_expires = expires
            else:
                self.cache_expires = timezone.now() + self.minimum_refresh_time
            print "Setting cache_expires=%s" % (self.cache_expires)
            feed = feedparser.parse(response.read())
            self.cache = feed
            self.save()
        else:
            # 304 or an error, do nothing
            print "Cache not updating, code %d" % (response.getcode())
        return self.cache
    
    """
    def get_cache_or_refresh(self):
        # if minimum refresh time has not passed, return cache
        # else do a HEAD request
        #   if update time is older than last_updated, return cache
        #   else update_cache()
        #if not self.last_updated:
        #    print "Setting last_updated=%s (now)" % (timezone.now())
        #    self.last_updated = timezone.now()
        #if not self.cache_expires:
        #    print "Setting cache_expires=%s (now)" % (timezone.now())
        #    self.cache_expires = timezone.now()
        if (not self.cache) or (self.last_updated < timezone.now() - self.minimum_refresh_time):
            conditional_request = urllib2.Request(self.url, headers={'If-Modified-Since': self.last_updated.strftime(web_timestamp_format)})
            response = urllib2.urlopen(conditional_request)
            if response.getcode() == 200:
                last_modified = parser.parse(response.headers.setdefault('Last-Modified', str(timezone.now())))
                print "Updating %s:%d? last_updated=%s, Last-Modified=%s" % (self.name, self.id, self.last_updated, last_modified)
                if last_modified > self.last_updated:
                    self.update_cache()
        return self.cache
    """


class Aggregate(models.Model):
    name = models.CharField(max_length=100)
    feeds = models.ManyToManyField(Feed)
    filters = models.TextField(default="", null=True)
    items = FeedCacheField(default=[])
    
    def __unicode__(self):
        return self.name
    
    def get_unfiltered_items(self):
        feeds = [f.update_cache() for f in self.feeds.all()]
        for f in feeds:
            for e in f.entries:
                e['feed'] = f.feed
        self.items = [e for f in feeds for e in f.entries]
        self.items.sort(key=lambda e: e.get('published_parsed') or e.get('updated_parsed'))
        return self.items
    
    def apply_filters(self):
        compiled_filters = [re.compile(f) for f in self.filters.split("\n")]
        filtered_items = []
        for entry in self.items:
            for regex in compiled_filters:
                if regex.search(entry.title) or regex.search(entry.summary):
                    filtered_items.append(entry)
                    break
        return filtered_items
    
    def save(self, *args, **kwargs):
        if not self.pk:
            print "Pre-saving"
            super(Aggregate, self).save(*args, **kwargs)
        print self.feeds
        print "Getting items"
        self.get_unfiltered_items()
        print "Saving"
        super(Aggregate, self).save(*args, **kwargs)

