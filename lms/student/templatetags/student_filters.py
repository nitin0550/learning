# student/templatetags/student_filters.py
from django import template

register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    return dictionary.get(key) if dictionary else None

@register.filter(name='minutes')
def minutes(duration):
    """Convert duration to minutes"""
    if duration:
        return int(duration.total_seconds() // 60)
    return 0