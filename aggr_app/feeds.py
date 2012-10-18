from django.contrib.syndication.views import Feed as RSSFeed
from aggr_app.models import Aggregate
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404

class AggregateFeed(RSSFeed):
    def get_object(self, request, aggr_id):
        aggr = get_object_or_404(Aggregate, pk=aggr_id)
        aggr.apply_filters()
        aggr.save()
        return aggr
    
    def title(self, aggr):
        return aggr.name
    
    def link(self, aggr):
        return reverse('aggr_app.views.aggr_detail', args=(aggr.id,))
    
    def description(self, aggr):
        return aggr.name
    
    def author_name(self, aggr):
        #return aggr.owner
        return "Anon"
    
    #def author_email(self, aggr):
    #def author_link(self, aggr):
    
    def items(self, aggr):
        return aggr.items
    
    def item_title(self, entry):
        return entry.title
    
    def item_description(self, entry):
        return entry.summary
    
    def item_link(self, entry):
        return entry.link
    
    def item_pubdate(self, entry):
        return entry.published

