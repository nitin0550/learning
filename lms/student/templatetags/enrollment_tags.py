from django import template
from expert.models import Enrollment

register = template.Library()

@register.filter
def is_enrolled(course, student):
    return Enrollment.objects.filter(course=course, student=student).exists()