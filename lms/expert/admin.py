from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import ExpertProfile, Course, Enrollment, Lesson, Assignment, Quiz, Question, QuizAssignment, WithdrawalRequest, Wallet, Expert_Notification
from .models import QuizAnswer
from django.utils.html import format_html

class ExpertProfileInline(admin.StackedInline):
    model = ExpertProfile
    can_delete = False
    verbose_name_plural = 'Profile'


class CustomUserAdmin(UserAdmin):
    inlines = (ExpertProfileInline,)

class CourseAdmin(admin.ModelAdmin):
    list_display = ('id', 'course_title', 'instructor', 'price', 'is_active', 'created_at')
    list_filter = ('is_active', 'instructor')
    search_fields = ('id', 'course_title', 'instructor__username')
    ordering = ('-created_at',)

class LessonAdmin(admin.ModelAdmin):
    list_display = ('id', 'lesson_title', 'course', 'created_at', 'is_active')
    list_filter = ('is_active', 'course')
    search_fields = ('lesson_title', 'course__course_title')
    ordering = ('course', '-created_at')

class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'course', 'due_date', 'is_active')
    list_filter = ('is_active', 'course', 'due_date')
    search_fields = ('title', 'course__course_title')
    ordering = ('-due_date',)

class QuizAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'course', 'created_by', 'is_active')
    list_filter = ('is_active', 'course')
    search_fields = ('title', 'course__course_title')
    ordering = ('-created_at',)

class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'question_text', 'quiz', 'question_type', 'is_active')
    list_filter = ('question_type', 'is_active', 'quiz')
    search_fields = ('question_text', 'quiz__title')

class QuizAssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'quiz', 'student', 'completed', 'score', 'assigned_date')
    list_filter = ('completed', 'quiz')
    search_fields = ('quiz__title', 'student__username')
    ordering = ('-assigned_date',)

class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'course', 'enrolled_at', 'expiration_date', 'is_active')
    list_filter = ('is_active', 'course')
    search_fields = ('student__username', 'course__course_title')
    ordering = ('-enrolled_at',)

class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'expert', 'amount', 'status', 'created_at', 'processed_at')
    list_filter = ('status',)
    search_fields = ('expert__username',)
    ordering = ('-created_at',)
    def colored_status(self, obj):
        colors = {
            'PENDING': '#FFA500',    # Orange
            'APPROVED': '#28a745',   # Green
            'REJECTED': '#dc3545'    # Red
        }
        return format_html(
            '<span style="color: {};">{}</span>',
            colors.get(obj.status, 'black'),
            obj.get_status_display()
        )
    colored_status.short_description = 'Status'

class WalletAdmin(admin.ModelAdmin):
    list_display = ('id', 'expert', 'balance', 'last_updated')
    search_fields = ('expert__username',)
    ordering = ('-last_updated',)

admin.site.unregister(User)
# Register the new User admin with the UserProfile inline
admin.site.register(User, CustomUserAdmin)
admin.site.register(Course, CourseAdmin)
admin.site.register(WithdrawalRequest, WithdrawalRequestAdmin)
admin.site.register(Wallet, WalletAdmin)
admin.site.register(Enrollment, EnrollmentAdmin)
admin.site.register(Lesson, LessonAdmin)
admin.site.register(Assignment, AssignmentAdmin)
admin.site.register(QuizAssignment, QuizAssignmentAdmin)
admin.site.register(Quiz, QuizAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Expert_Notification)
admin.site.register(QuizAnswer)