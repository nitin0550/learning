# student/views.py
import random
from django.shortcuts import render, redirect, get_object_or_404

from django.core.mail import send_mail
from django.conf import settings
from .forms import StudentRegistrationForm, StudentProfileForm, CourseSearchForm
#from django.contrib import messages
from chat.models import Message
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
from .models import StudentProfile, Student_Notification
from expert.models import Course, Enrollment, Lesson, Assignment, Quiz, QuizAnswer, QuizAssignment
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count
from django.db.models import Q
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q, Count, Max, Case, When
from django.db import transaction
from expert.notifications import create_notification_expert, create_notification_student, create_enrollment_notification
from django.db.models.functions import Greatest


def student_required(user):
    return user.is_staff == False or user.is_superuser == True
#=================== views for student dashboard  ======================

@user_passes_test(student_required)
def student_dashboard(request):
    if request.user.is_authenticated:
        return render(request, 'student/student_dashboard.html')
    else:
        return redirect('login')

#===================  views for home  page ======================

def home(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('expert_dashboard')
        else:
            return redirect('student_dashboard')
    else:
        return render(request, 'student/home.html')
    
#===================   views for student registration  ======================

def student_register(request):
    if request.user.is_authenticated:
        return render(request, 'student/student_dashboard.html')
    else:
        if request.method == 'POST':
            form = StudentRegistrationForm(request.POST)
            if form.is_valid():
                user = form.save(commit=False)
                user.is_staff = False
                user.is_active = False
                user.save()

                # Generate OTP
                otp = random.randint(100000, 999999)
                request.session['registration_otp'] = otp
                request.session['user_id'] = user.id
                
                # Send OTP email
                send_mail(
                    'Verify Your Email',
                    f'Hi {user.username},\n\nYour verification OTP is: {otp}\n\nBest regards,\nLMS Team',
                    settings.EMAIL_HOST_USER,
                    [user.email],
                    fail_silently=False,
                )
                messages.success(request, 'Please check your email for OTP verification.')
                #messages.success(request, 'Account created successfully. Please login to continue.')
                return redirect('verify_registration')
        else:
            form = StudentRegistrationForm()
        return render(request, 'student/student_register.html', {'form': form})

#===================   views for student registration verification  ======================

def verify_registration(request):
    if request.method == 'POST':
        otp = request.POST.get('otp')
        stored_otp = request.session.get('registration_otp')
        user_id = request.session.get('user_id')
        
        if stored_otp and int(otp) == stored_otp:
            user = User.objects.get(id=user_id)
            user.is_active = True
            user.save()
            
            # Clear session data
            del request.session['registration_otp']
            del request.session['user_id']
            
            messages.success(request, 'Email verified successfully. You can now login.')
            return redirect('login')
        else:
            messages.error(request, 'Invalid OTP. Please try again.')
    
    return render(request, 'registration/verify_otp.html')


#==================  views for student profile ======================

@login_required
@user_passes_test(student_required)
def student_profile(request):
    profile, created = StudentProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        if 'profile_picture' in request.FILES:
            profile.profile_picture = request.FILES['profile_picture']
            profile.save()
            return redirect('student_profile')
    return render(request, 'student/student_profile.html', {'profile': profile})


#============ view for student profile setting form =============================
@login_required
@user_passes_test(student_required)
def student_profile_setting(request):
    try:
        student_profile, created = StudentProfile.objects.get_or_create(user=request.user)
        if request.method == 'POST':
            form = StudentProfileForm(request.POST, request.FILES, instance=student_profile, user=request.user)
            if form.is_valid():
                try:
                    with transaction.atomic():
                        user = request.user
                        user.email = form.cleaned_data['email']
                        user.first_name = form.cleaned_data['first_name']
                        user.last_name = form.cleaned_data['last_name']
                        user.username = form.cleaned_data['username']
                        if not user.username.strip():
                            form.add_error('username', 'Username cannot be empty.')
                        elif (
                            User.objects.filter(username=user.username)
                            .exclude(pk=user.pk)
                            .exists()
                        ):
                            form.add_error('username', 'This username is already in use.')
                            raise ValueError('Username already exists')
                        else:
                            user.save()
                            form.save()
                            messages.success(request, 'Profile updated successfully.')
                            return redirect('student_profile')
                except Exception as e:
                    messages.error(request, f'Error updating profile: {str(e)}')

        else:
            form = StudentProfileForm(instance=student_profile, user=request.user)
        return render(request, 'student/student_profile_setting.html', {'form': form})
    except Exception as e:
        messages.error(request, f'Error updating profile: {str(e)}')
        return redirect('student_profile')

#===============================================================================

def calculate_expiration_date(course, enrolled_at):
    # Fallback to a default of 30 days if enrollment_duration is None
    enrollment_duration = course.enrollment_duration if course.enrollment_duration is not None else 30
    # Ensure enrolled_at is not None
    enrolled_at = enrolled_at or timezone.now()
    return enrolled_at + timedelta(days=enrollment_duration)
#=======================  view for course enrollment ======================

@login_required
@user_passes_test(student_required)
def enroll_in_course(request, course_id):
    try:
        # Get course or 404
        course = get_object_or_404(Course, id=course_id, is_active=True)
        
        # Check if already enrolled
        existing_enrollment = Enrollment.objects.filter(student=request.user, course=course).first()
        if existing_enrollment:
            if existing_enrollment.is_active:
                messages.warning(request, f'You are already enrolled in {course.course_title}')
                return redirect('student_course_search')
            else:
                # Check if enrollment is expired
                if existing_enrollment.expiration_date < timezone.now():
                    existing_enrollment.delete()  # Remove expired enrollment to allow re-enrollment
            
        enrolled_at = timezone.now()
        expiration_date = calculate_expiration_date(course, enrolled_at)

        # Create enrollment
        enrollment = Enrollment.objects.create(
            student=request.user,
            course=course,
            enrolled_at=enrolled_at,
            expiration_date=expiration_date
        )
        create_enrollment_notification(course.expert, request.user)

        messages.success(request, f'Successfully enrolled in {course.course_title}')
        return redirect('student_enrolled_courses')
    except Course.DoesNotExist:
        messages.error(request, 'Course not found or is no longer active.')
        return redirect('student_course_search')
    except Exception as e:
        messages.error(request, f'Error enrolling in course: {str(e)}')
        return redirect('student_course_search')


#====================   views for student enrolled courses ======================

@login_required
@user_passes_test(student_required)
def student_enrolled_courses(request):
    try:
        now = timezone.now()
        enrollments = Enrollment.objects.filter(student=request.user, is_active=True).select_related('course')
        active_courses = []
        expired_enrollments = []
        for enrollment in enrollments:
            expiration_date = enrollment.enrolled_at + timedelta(days=enrollment.course.enrollment_duration)
            if now >= expiration_date:
                # Mark as inactive instead of deleting
                enrollment.is_active = False
                expired_enrollments.append(enrollment)
            elif enrollment.course.is_active:
                active_courses.append(enrollment.course)
        # Bulk update expired enrollments
        if expired_enrollments:
            Enrollment.objects.bulk_update(
                expired_enrollments, 
                ['is_active']
            )
        context = {
            'courses': active_courses,
            'total_courses': len(active_courses),
            'expired_count': len(expired_enrollments)
        }
        return render(request, 'student/student_enrolled_course.html', context)
    except Exception as e:
        messages.error(request, f'Error loading courses: {str(e)}')
        return redirect('student_dashboard')
    
#====================  views for student assignment of inrolled courses =====================
from django.utils.timezone import now
@login_required
@user_passes_test(student_required)
def student_course_assignments(request, course_id):
    try:
        # Verify course exists and student is enrolled
        course = get_object_or_404(
            Course, 
            id=course_id,
            enrollments__student=request.user,
            enrollments__is_active=True,
            is_active=True
        )
        
        # Get active assignments not past due date
        assignments = Assignment.objects.filter(
            course=course,
            due_date__gte=now(),
            is_active=True
        ).order_by('due_date')
        
        context = {
            'course': course,
            'assignments': assignments,
            'today': now()
        }
        
        return render(request, 'student/student_assignment.html', context)
        
    except Course.DoesNotExist:
        messages.error(request, 'Course not found or is no longer available.')
        return redirect('student_enrolled_courses')
    except Exception as e:
        messages.error(request, f'Error loading assignments: {str(e)}')
        return redirect('student_enrolled_courses')

#====================views for student all assignments =====================
@login_required
@user_passes_test(student_required)
def student_all_assignments(request):
    try:
        # Get enrolled courses
        enrolled_courses = Course.objects.filter(
            enrollments__student=request.user,
            enrollments__is_active=True,
            enrollments__enrolled_at__lte=now(),
            is_active=True
        ).distinct()
        
        # Get assignments from enrolled courses
        assignments = Assignment.objects.filter(
            course__in=enrolled_courses,
            due_date__gte=now(),
            is_active=True
        ).select_related(
            'course',
            'created_by'
        ).order_by(
            'due_date',
            'course__course_title'
        )
        
        return render(request, 'student/student_all_assignments.html', {
            'assignments': assignments
        })
        
    except Exception as e:
        messages.error(request, f'Error loading assignments: {str(e)}')
        return redirect('student_dashboard')

#==================== views for student quiz of inrolled courses =====================
@login_required
@user_passes_test(student_required)
def student_quiz_list(request):
    try:
        # Get enrolled courses
        enrolled_courses = Course.objects.filter(
            enrollments__student=request.user,
            enrollments__is_active=True,
        )
        
        # Get only assigned quizzes
        assigned_quizzes = Quiz.objects.filter(
            course__in=enrolled_courses,
            is_active=True,
            quizassignment__student=request.user  # Only get quizzes that have assignments
        ).select_related(
            'course'
        ).prefetch_related(
            'quizassignment_set'
        ).order_by(
            '-quizassignment__assigned_date',
            '-created_at'
        ).distinct()
        
        # Get assignments for current student
        assignments = QuizAssignment.objects.filter(
            student=request.user,
            quiz__in=assigned_quizzes
        ).select_related('quiz').order_by('-assigned_date')
        
        # Create assignment dictionary
        assignment_dict = {
            assignment.quiz.id: assignment 
            for assignment in assignments
        }
        
        context = {
            'quizzes': assigned_quizzes,
            'assignment_dict': assignment_dict
        }
        
        return render(request, 'student/student_quiz_list.html', context)
        
    except Exception as e:
        messages.error(request, f'Error loading quizzes: {str(e)}')
        return redirect('student_dashboard')


#==================== views for student take quiz =====================

@login_required
@user_passes_test(student_required)
def student_take_quiz(request, quiz_id):
    try:
        quiz = get_object_or_404(Quiz, id=quiz_id, is_active=True)
        assignment = QuizAssignment.objects.filter(
            quiz=quiz, 
            student=request.user,
            completed=False
        ).order_by('-assigned_date').first()  # Get latest assignment

        if not assignment:
            messages.error(request, 'Quiz not available or already completed')
            return redirect('student_quiz_list')
        
        questions = quiz.questions.filter(is_active=True)

        context = {
            'quiz': quiz,
            'assignment': assignment,
            'questions': questions,
            'duration': quiz.duration
        }

        return render(request, 'student/take_quiz.html', context)
    except Quiz.DoesNotExist:
        messages.error(request, 'Quiz not found.')
        return redirect('student_quiz_list')
    except QuizAssignment.DoesNotExist:
        messages.error(request, 'Quiz assignment not found.')
        return redirect('student_quiz_list')
    except Exception as e:
        messages.error(request, f'Error loading quiz: {str(e)}')
        return redirect('student_quiz_list')


#==================== views for student submit quiz =====================

@login_required
@user_passes_test(student_required)
def submit_quiz(request, quiz_id):
    try:
        if request.method == 'POST':
            try:
                quiz = get_object_or_404(Quiz, id=quiz_id, is_active=True)
                assignment = get_object_or_404(
                    QuizAssignment, 
                    quiz=quiz, 
                    student=request.user,
                    completed=False,
                    completed_date=None
                )

                # Calculate score
                questions = quiz.questions.all()
                total_questions = questions.count()
                correct_answers = 0

                for question in questions:
                    student_answer = request.POST.get(f'q{question.id}')

                    if question.question_type == 'TF':
                        # Normalize true/false answers (case-insensitive)
                        if student_answer and student_answer.lower() == 'true':
                            student_answer = '1'
                        elif student_answer and student_answer.lower() == 'false':
                            student_answer = '2'

                        # Strict comparison after normalization
                        if student_answer and student_answer.strip().upper() == question.correct_answer.strip().upper():
                            correct_answers += 1
                    else:
                        # Handle MCQ answers
                        if student_answer and student_answer.strip() == question.correct_answer.strip():
                            correct_answers += 1

                    # Save the answer
                    QuizAnswer.objects.create(
                        assignment=assignment,
                        question=question,
                        student_answer=student_answer,
                        is_correct=(student_answer and student_answer.strip() == question.correct_answer.strip())
                    )

                # Calculate percentage score
                score = (correct_answers / total_questions) * 100 if total_questions > 0 else 0

                # Update assignment
                assignment.completed = True
                assignment.score = score
                assignment.completed_date = timezone.now()
                assignment.save()

                messages.success(request, f'Quiz submitted successfully! Score: {score:.1f}%')
                return redirect('student_quiz_list')
            except Quiz.DoesNotExist:
                messages.error(request, 'Quiz not found.')
                return redirect('student_quiz_list')
            except QuizAssignment.DoesNotExist:
                messages.error(request, 'Quiz assignment not found.')
                return redirect('student_quiz_list')
            except Exception as e:
                messages.error(request, f'Error submitting quiz: {str(e)}')
                return redirect('student_quiz_list')
        return redirect('student_quiz_list')
    except Exception as e:
        messages.error(request, f'Error submitting quiz: {str(e)}')
        return redirect('student_quiz_list')

#====================   views for student enrolled lessons ======================

@login_required
@user_passes_test(student_required)
def student_enrolled_lessons(request, course_id):
    try:
        course = get_object_or_404(Course, id=course_id)
        
        # Check if course is active
        if not course.is_active:
            messages.error(request, 'This course is no longer available.')
            return redirect('student_enrolled_courses')
            
        # Check enrollment
        if not Enrollment.objects.filter(student=request.user, course=course, is_active=True).exists():
            messages.error(request, 'You are not enrolled in this course.')
            return redirect('student_enrolled_courses')
            
        lessons = Lesson.objects.filter(course=course, is_active=True)
        context = {
            'course': course,
            'lessons': lessons
        }
        return render(request, 'student/student_enrolled_lessons.html', context)
        
    except Exception as e:
        messages.error(request, f'Error loading course: {str(e)}')
        return redirect('student_enrolled_courses')


#========================== view for play lesson videos =============================
@login_required
@user_passes_test(student_required)
def student_play_video(request, lesson_id):
    try:
        lessons = get_object_or_404(
                Lesson,
                id=lesson_id,
                course__enrollments__student=request.user,
                is_active=True
            )
        # Verify course is active
        if not lessons.course.is_active:
            messages.error(request, 'This course is no longer active.')
            return redirect('student_enrolled_courses')
        # Verify enrollment is active
        enrollment = get_object_or_404(
            Enrollment,
            student=request.user,
            course=lessons.course,
            is_active=True
        )

        # Handle missing thumbnail
        thumbnail_url = None
        if lessons.thumbnail and lessons.thumbnail.name:
            thumbnail_url = lessons.thumbnail.url

        course = lessons.course

        # Fetch all lessons in the same course, excluding the current one
        hls_path = f"/media/expert/{lessons.course.expert.id}/courses/{lessons.course.id}/hls/{lessons.id}/index.m3u8"
        recommended_videos = Lesson.objects.filter(course=course, is_active=True).exclude(id=lesson_id).order_by('-created_at')

        context = {
            'lessons': lessons,
            'course': course,
            'hls_path': hls_path,
            'thumbnail_url': thumbnail_url,
            'video_url': lessons.video.url if lessons.video else None,
            'recommended_videos': recommended_videos,
        }

        response = render(request, 'student/student_play_video.html', context)
        response['X-Frame-Options'] = 'SAMEORIGIN'
        return response
    
    except Exception as e:
        messages.error(request, f'Error playing video: {str(e)}')
        return redirect('student_enrolled_courses')



#===================== views for student notifications ==========================

#@login_required
#@user_passes_test(student_required)
#def student_notification(request):
#    return render(request, 'student/student_notification.html')
#
@login_required
@user_passes_test(student_required)
def student_notifications(request):
    notifications = Student_Notification.objects.filter(
        recipient=request.user
    ).order_by('-created_at')[:20]
    Student_Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).update(is_read=True)
    context = {
        'notifications': notifications,
        'unread_count': Student_Notification.objects.filter(
            recipient=request.user,
            is_read=False
            ).count()
    }

    return render(request, 'student/student_notification.html', context)

#===================== views for student course search ==========================

@login_required
@user_passes_test(student_required)
def student_course_search(request):
    try:
        form = CourseSearchForm(request.GET or None)
        courses = []
        if form.is_valid():
            query = form.cleaned_data['query']
            courses = Course.objects.filter(course_title__icontains=query,is_active=True).prefetch_related('lessons')
            enrolled_courses = Enrollment.objects.filter(student=request.user, course__in=courses, is_active=True).values_list('course_id', flat=True)
            # Attach enrollment status to each course
            for course in courses:
                course.is_enrolled = course.id in enrolled_courses
        return render(request, 'student/student_course_search.html', {'form': form, 'courses': courses})
    except Exception as e:
        messages.error(request, f'Error loading courses: {str(e)}')
        return redirect('student_dashboard')


#======================= views for student chats ============================
@login_required
@user_passes_test(student_required)
def student_chat(request):
    try:
        student = request.user
        experts = (
            User.objects
            .filter(
                is_staff=True,
                instructor_courses__enrollments__student=student
                
            )
            .distinct()
            .annotate(
                unread_count=Count(
                    'sent_messages',
                    filter=Q(
                        sent_messages__receiver=student,
                        sent_messages__is_read=False,
                        sent_messages__deleted_for_student=False
                    ),
                    distinct=True 
                ),
                last_message=Greatest(
                Max(
                    Case(
                        When(
                            sent_messages__deleted_for_expert=False,
                            then='sent_messages__timestamp'
                        ),
                        default=None
                    )
                ),
                Max(
                    Case(
                        When(
                            received_messages__deleted_for_expert=False,
                            then='received_messages__timestamp'
                        ),
                        default=None
                    )
                )
            )
        )
            .order_by('-last_message')
        )
        context = {
            'experts': experts,
            'total_unread': sum(expert.unread_count for expert in experts)
        }

        return render(request, 'chat/student_chat.html', context)

    except Exception as e:
        messages.error(request, f'Error loading chat: {str(e)}')
        return redirect('student_dashboard')

#======================= views for student delete chat ============================
@login_required
@user_passes_test(student_required)
def delete_all_chat(request, expert_id):
    try:
        expert = get_object_or_404(User, id=expert_id, is_staff=True)
        
        # Soft delete messages using update
        Message.objects.filter(
            Q(sender=request.user, receiver=expert) | 
            Q(sender=expert, receiver=request.user)
        ).update(deleted_for_student=True)
        
        messages.success(request, "Chat messages deleted successfully.")
        return redirect('student_chat')
        
    except Exception as e:
        messages.error(request, f'Error deleting chat: {str(e)}')
        return redirect('student_chat')

