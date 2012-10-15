from django import forms
from aggr_app.models import Feed

class NewFeedForm(forms.Form):
    name = forms.CharField(max_length=100, required=True)
    url = forms.URLField(max_length=400, required=True)

class NewAggrForm(forms.Form):
    """Variable form."""
    name = forms.CharField(max_length=100)
    is_public = forms.BooleanField(initial=False, label="Make public")
    filter_count = forms.CharField(widget=forms.HiddenInput())
    
    def __init__(self, *args, **kwargs):
        """Initialize the form with a variable number of filter fields.
        
        At least one of the following arguments required:
        filter_count: The number of filter fields to include.
        filters: A tuple of 2-tuples matching feed id to filter string.
        
        If filter_count is less than the number of filters, filter_count is ignored.
        Otherwise, extra fields are filled in with defaults.
        """
        feed_choices = tuple(kwargs.pop('feed_choices', tuple()))
        filters = kwargs.pop('filters', tuple())
        filter_count = int(kwargs.pop('filter_count', 1))
        super(NewAggrForm, self).__init__(*args, **kwargs)
        if filter_count < len(filters):
            filter_count = len(filters)
        self.fields['filter_count'].initial = filter_count
        for i in range(filter_count):
            self.fields['feed%d' % i] = forms.ChoiceField(choices=feed_choices)
            self.fields['filter%d' % i] = forms.CharField(max_length=400)
        for i in range(len(filters)):
            self.fields['feed%d' % i].initial = filters[i][0]
            self.fields['filter%d' % i].initial = filters[i][1]
            
    """
    def __init__(self, *args, **kwargs):
        ""\"Initialize the form with a variable number of filter fields.
        
        filters: Required. A tuple of 2-tuples matching feed id to filter string.
        ""\"
        filters = kwargs.pop('filters', ((0,''),))
        super(NewAggrForm, self).__init__(*args, **kwargs)
        self.fields['filter_count'].initial = len(filters)
        for i in range(num_filters):
            self.fields['feed%d' % i] = forms.ChoiceField(choices=feed_choices)
            self.fields['feed%d' % i].initial = filters[i][0]
            self.fields['filter%d' % i] = forms.CharField(max_length=400)
            self.fields['filter%d' % i].initial = filters[i][1]
    """
