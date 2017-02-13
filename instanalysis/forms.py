import logging
from django import forms

# Configure logger
logger = logging.getLogger(__name__)

class PivotEditForm(forms.Form):
    lat = forms.CharField()
    lng = forms.CharField()