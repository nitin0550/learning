# student/templatetags/student_quiz_filters.py (renamed from quiz_filters.py)
from django import template

register = template.Library()

@register.filter(name='student_get_option')  # renamed filter
def student_get_option(question, number):
    """Get question option by number"""
    option_map = {
        '1': question.option_1,
        '2': question.option_2,
        '3': question.option_3,
        '4': question.option_4
    }
    return option_map.get(str(number), '')