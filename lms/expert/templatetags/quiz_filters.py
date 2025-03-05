from django import template
from datetime import timedelta

register = template.Library()

@register.filter
def minutes(td):
    """Convert timedelta to minutes"""
    if isinstance(td, timedelta):
        return int(td.total_seconds() / 60)
    return td