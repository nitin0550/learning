# teacher/views.py
import json
import mimetypes
import os
import random
import subprocess
from click import File
from django.shortcuts import render, redirect, get_object_or_404
from django.core.mail import send_mail
from lms import settings
from .utils import convert_to_hls
from .forms import ExpertRegistrationForm, ExpertProfileForm, CourseForm, LessonForm, LessonEditForm, QuizForm, AssignmentForm, QuestionForm
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login
from .models import ExpertProfile, Course, Lesson, Quiz, Assignment, Enrollment, Question, QuizAssignment, Wallet, WithdrawalRequest, user_directory_path_videos, user_directory_path_thumbnails, Expert_Notification, QuizAnswer
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth.models import User
from chat.models import Message
from django.db.models import Count
from django.utils.timezone import now
from django.forms import modelformset_factory
from django.utils import timezone
import logging
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from datetime import timedelta
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from datetime import datetime
from decimal import Decimal
from django.db.models import Count, Sum, Avg, Max, Min, Case, When
from django.db.models.functions import TruncMonth, TruncDay
from .notifications import create_notification_expert, create_notification_student
from django.db.models.functions import Greatest
import google.auth
from google.cloud import storage
from django.urls import reverse

def staff_required(user):
    return user.is_staff or user.is_superuser
logger = logging.getLogger(__name__)
#=========== view for expert dashboard =======================================
@login_required
@user_passes_test(staff_required)
def expert_dashboard(request):
    expert = request.user
    total_courses = Course.objects.filter(expert=expert, is_active=True).count()
    due_assignment = Assignment.objects.filter(course__expert=expert, due_date__gte=now(), is_active=True).count()
    enrolled_student = Enrollment.objects.filter(course__expert=expert).values('student').distinct().count()
    quizzes = Quiz.objects.filter(created_by=expert, is_active=True).count()
    context = {'total_courses': total_courses, 'due_assignment': due_assignment, 'enrolled_student': enrolled_student, 'quizzes': quizzes}
    return render(request, 'expert/expert_dashboard.html', context)

#============ view for expert registration form =================================
def expert_register(request):
    if request.user.is_authenticated:
        return render(request, 'expert/expert_dashboard.html')
    else:
        if request.method == 'POST':
            form = ExpertRegistrationForm(request.POST)
            if form.is_valid():
                user = form.save(commit=False)
                user.set_password(form.cleaned_data['password'])
                user.is_expert = True
                user.is_staff = True
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
            form = ExpertRegistrationForm()
        return render(request, 'expert/expert_register.html', {'form': form})

#================== view for verify expert registration ==========================

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

#============ view for expert profile setting form =============================
@login_required
@user_passes_test(staff_required)
def expert_profile_setting(request):
    try:
        expert_profile, created = ExpertProfile.objects.get_or_create(user=request.user)
        if request.method == 'POST':
            form = ExpertProfileForm(request.POST, request.FILES, instance=expert_profile, user=request.user)
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
                            raise ValueError('Username cannot be empty')
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
                            messages.success(request, 'Profile updated successfully!')
                            return redirect('expert_profile')  # Redirect to the profile page
                except ValueError as e:
                    messages.error(request, str(e))
                except Exception as e:
                    messages.error(request, f'Error updating profile: {str(e)}')
        else:
            form = ExpertProfileForm(instance=expert_profile, user=request.user)
        return render(request, 'expert/expert_profile_setting.html', {'form': form})
    except Exception as e:
        messages.error(request, f'Error updating profile: {str(e)}')
        return redirect('expert_dashboard')

#============ view for expert profile ============================================
@login_required
@user_passes_test(staff_required)
def expert_profile(request):
    try:
        profile, created = ExpertProfile.objects.get_or_create(user=request.user)
        expert = request.user
        courses = Course.objects.filter(expert=expert, is_active=True).order_by('-created_at')

        if request.method == 'POST':
            try:
                with transaction.atomic():
                    if 'profile_picture' in request.FILES:
                        # Delete old picture if exists
                        if profile.profile_picture:
                            profile.profile_picture.delete()
                        profile.profile_picture = request.FILES['profile_picture']
                        profile.save()
                        messages.success(request, 'Profile picture updated successfully!')
                    return redirect('expert_profile')
            except Exception as e:
                messages.error(request, f'Error updating profile picture: {str(e)}')
        context = {
            'profile': profile,
            'courses': courses,
            'total_courses': courses.count(),
            'total_students': Enrollment.objects.filter(course__in=courses).count()
        }
        return render(request, 'expert/expert_profile.html', context)
    except Exception as e:
        messages.error(request, f'Error loading profile: {str(e)}')
        return redirect('expert_dashboard')


#============ view for creating new course =============================

@login_required
@user_passes_test(staff_required)
def expert_upload_course(request):
    try:
        if request.method == 'POST':
            course_form = CourseForm(request.POST)
            lesson_form = LessonForm(request.POST, request.FILES)

            if course_form.is_valid() and lesson_form.is_valid():
                try:
                    with transaction.atomic():
                        # Save course
                        course = course_form.save(commit=False)
                        course.expert = request.user
                        course.instructor = request.user
                        course.is_active = True
                        course.save()

                        # Create lesson
                        lesson = lesson_form.save(commit=False)
                        lesson.course = course
                        lesson.save()

                        # Get video path
                        video_path = request.FILES['video'].temporary_file_path()

                        # Create the directory for HLS files
                        hls_output_dir = os.path.join(
                            settings.MEDIA_ROOT, 
                            'expert', 
                            str(request.user.id),
                            'courses', 
                            str(course.id), 
                            'hls', 
                            str(lesson.id)
                        )

                        # Convert video with all required arguments
                        try:
                            relative_hls_path = convert_to_hls(
                                video_path=video_path,
                                output_dir=hls_output_dir,
                                user_id=str(request.user.id),
                                course_id=str(course.id),
                                lesson_id=str(lesson.id)
                            )

                            # Update lesson with HLS URL
                            lesson.hls_url = relative_hls_path

                            # Save lesson
                            #lesson.save()
                            messages.success(request, 'Course uploaded successfully!')
                            return redirect('expert_lessons', course_id=course.id)
                        except Exception as e:
                            if 'lesson' in locals():
                                lesson.video.delete(save=False)
                                lesson.thumbnail.delete(save=False)
                                lesson.delete()
                            if 'course' in locals():
                                course.delete()
                            messages.error(request, f'Error uploading course: {str(e)}')
                            
                except ValueError as e:
                    if 'lesson' in locals():
                        lesson.video.delete(save=False)
                        lesson.thumbnail.delete(save=False)
                    messages.error(request, f'Error uploading course: {str(e)}')
        else:
            course_form = CourseForm()
            lesson_form = LessonForm()
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
    
    return render(request, 'expert/expert_upload_course.html', {
        'course_form': CourseForm,
        'lesson_form': LessonForm
    })



#========================== view for delete course =============================
@login_required
@user_passes_test(staff_required)
def delete_course(request, course_id):
    course = get_object_or_404(Course, id=course_id, instructor=request.user)  # Ensure the course belongs to the logged-in user
    if request.method == 'POST':
        course.is_active = False
        course.save()
        messages.success(request, 'Course deleted successfully!')
        return redirect('expert_my_courses')  # Redirect back to the "My Courses" page
    return render(request, 'expert/delete_course_confirm.html', {'course': course})


#========================== view for rename course =============================
@login_required
@user_passes_test(staff_required)
def rename_course(request, course_id):
    course = get_object_or_404(Course, id=course_id, expert=request.user)  # Ensure course belongs to the expert
    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, 'Course updated successfully!')
            return redirect('expert_my_courses')
    else:
        form = CourseForm(instance=course)
    
    return render(request, 'expert/rename_course.html', {'form': form, 'course': course})




#========================== view for view all course that are created by expert =============================
@login_required
@user_passes_test(staff_required)
def expert_my_courses(request):
    # Get the logged-in expert
    expert = request.user
    courses = Course.objects.filter(expert=expert, is_active=True).order_by('-created_at')

    context = {'courses': courses}
    return render(request, 'expert/expert_my_courses.html', context)

#========================== view for expert student management =============================
@login_required
@user_passes_test(staff_required)
def expert_student_management(request):
    expert = request.user
    search_query = request.GET.get('search', '') 
    enrollments = Enrollment.objects.filter(course__expert=expert, is_active=True)
    # Retrieve all enrollments for courses uploaded by the expert

    if search_query:
        enrollments = enrollments.filter(student__username__icontains=search_query)

    enrollments = enrollments.select_related('student', 'course').order_by('course__course_title', 'student__username')

    context = {
        'enrollments': enrollments,
        'search_query': search_query,
    }
    return render(request, 'expert/expert_student_management.html', context)
#================== views for remove user from enrolled course ======================
def remove_enrollment(request, enrollment_id):
    # Get the enrollment object, ensuring it belongs to the logged-in expert's course
    enrollment = get_object_or_404(Enrollment, id=enrollment_id, course__expert=request.user, is_active=True)
    
    if request.method == "POST":
        # Delete the enrollment if the request is a POST
        enrollment.is_active = False
        enrollment.save()
        messages.success(request, f"Enrollment of {enrollment.student.username} in {enrollment.course.course_title} has been removed.")
        return redirect('expert_student_management')
    

#================== views for expert notifications ==================================
@login_required
@user_passes_test(staff_required)
def expert_notifications(request):
    notifications = Expert_Notification.objects.filter(
        recipient=request.user
    ).order_by('-created_at')[:20]

    # Mark all as read
    Expert_Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).update(is_read=True)
        
    context = {
        'notifications': notifications,
        'unread_count': Expert_Notification.objects.filter(
            recipient=request.user,
            is_read=False
            ).count()
    }

    return render(request, 'expert/expert_notification.html', context)

#@login_required
#@require_POST
#def mark_notifications_read(request):
#    notification_id = request.POST.get('notification_id')
#    
#    if notification_id:
#        # Mark single notification as read
#        Notification.objects.filter(
#            id=notification_id,
#            recipient=request.user
#        ).update(is_read=True)
#    else:
#        # Mark all notifications as read
#        Notification.objects.filter(
#            recipient=request.user
#        ).update(is_read=True)
#    
#    return JsonResponse({
#        'status': 'success',
#        'unread_count': Notification.objects.filter(
#            recipient=request.user,
#            is_read=False
#        ).count()
#    })

#================== views for create assignment =====================================
@login_required
@user_passes_test(staff_required)
def expert_assignment(request, assignment_id=None):
    try:
        # If an assignment_id is provided, we are editing an existing assignment
        if assignment_id:
            assignment = get_object_or_404(Assignment, id=assignment_id)
            message = "Edit Assignment"
        else:
            # Otherwise, we are creating a new assignment
            assignment = None
            message = "Create Assignment"

        if request.method == 'POST':
            if assignment:  # Editing existing assignment
                form = AssignmentForm(request.POST, instance=assignment)
            else:  # Creating a new assignment
                form = AssignmentForm(request.POST)
            form = AssignmentForm(request.POST, instance=assignment, user=request.user)
            if form.is_valid():
                assignment = form.save(commit=False)
                assignment.created_by = request.user
                assignment.is_active = True
                form.save()
                create_notification_expert(
                    request.user,
                    "New Assignment Created",
                    f"You have created a new assignment: {assignment.title}",
                    "assignment"
                )
                # Get enrolled students and create notifications
                enrolled_students = Enrollment.objects.filter(
                    course=assignment.course,
                    is_active=True
                ).values_list('student', flat=True)
                for student_id in enrolled_students:
                    create_notification_student(
                        User.objects.get(id=student_id),
                        "New Assignment Available",
                        f"A new assignment '{assignment.title}' has been posted",
                        "assignment"
                    )
                messages.success(
                        request, 
                        'Assignment updated successfully' if assignment_id else 'Assignment created successfully'
                    )
                return redirect('expert_assignment')  # Redirect to a success page or assignment list
        else:
            #if assignment:  # Pre-populate form with existing assignment data
            #    form = AssignmentForm(user=request.user)
            #else:
            #    form = AssignmentForm()
            form = AssignmentForm(instance=assignment, user=request.user)

        expert_assignments =  Assignment.objects.filter(created_by=request.user, due_date__gte=now(), is_active=True).order_by('due_date')

        context = {
            'form': form,
            'assignments': expert_assignments,  # Pass the list of assignments
            'message': message, # Pass the correct message for create/edit
        }

        return render(request, 'expert/expert_assignment.html', context)
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
        return redirect('expert_assignment')

#=================== view for delete the assignment ====================================
def delete_assignment(request, assignment_id):
    # Fetch the assignment or return 404 if it doesn't exist
    assignment = get_object_or_404(Assignment, id=assignment_id, created_by=request.user)

    # If the request is POST, delete the assignment
    if request.method == 'POST':
        assignment.is_active = False
        assignment.save()
        messages.success(request, 'Assignment deleted successfully')
        return redirect('expert_assignment')  # Redirect back to the assignment list page



#================= view for expert create quiz ======================================


@login_required
@user_passes_test(staff_required)
def expert_create_quiz(request):
    if request.method == 'POST':
        try:
            title = request.POST.get('title')
            description = request.POST.get('description')
            duration = request.POST.get('duration')
            course_id = request.POST.get('course')
            passing_score = request.POST.get('passing_score')

            # Validate course
            try:
                course = Course.objects.get(id=course_id, instructor=request.user)
            except Course.DoesNotExist:
                messages.error(request, 'Please select a valid course')
                return render(request, 'expert/expert_create_quiz.html', {
                    'title': title,
                    'description': description,
                    'duration': duration,
                    'passing_score': passing_score,
                    'courses': Course.objects.filter(instructor=request.user),
                    'questions': request.POST
                })
            
            # Validate duration
            try:
                duration_minutes = int(duration)
                if duration_minutes <= 0:
                    raise ValueError
                duration_timedelta = timedelta(minutes=duration_minutes)
            except (TypeError, ValueError):
                messages.error(request, 'Please enter a valid duration in minutes')
                return render(request, 'expert/expert_create_quiz.html', {
                    'title': title,
                    'description': description,
                    'duration': duration,
                    'passing_score': passing_score,
                    'questions': request.POST
                })
            
            # Validate required fields
            if not title:
                messages.error(request, 'Quiz title is required')
                return render(request, 'expert/expert_create_quiz.html', {
                    'title': title,
                    'description': description,
                    'duration': duration,
                    'passing_score': passing_score,
                    'questions': request.POST
                })
            
            # Check for duplicate quiz title (case insensitive)
            if Quiz.objects.filter(
                title__iexact=title, 
                created_by=request.user
            ).exists():
                messages.error(request, 'You already have a quiz with this title. Please choose a different title.')
                return render(request, 'expert/expert_create_quiz.html', {
                    'title': title,
                    'description': description,
                    'duration': duration,
                    'passing_score': passing_score,
                    'questions': request.POST
                })

            # Start database transaction
            with transaction.atomic():
                # Create quiz
                quiz = Quiz.objects.create(
                    title=title,
                    description=description,
                    duration=duration_timedelta,
                    created_by=request.user,    
                    course=course,
                    passing_score=passing_score,
                    created_at=timezone.now()
                )

                questions_created = 0
                
                # Process each question
                for i in range(1, 101):
                    question_text = request.POST.get(f'question_text_{i}')
                    question_type = request.POST.get(f'question_type_{i}')
                    
                    if not question_text or not question_type:
                        continue
                        
                    # Create question based on type
                    if question_type == 'MCQ':
                        options = []
                        for j in range(1, 5):
                            option = request.POST.get(f'option_{i}_{j}')
                            if option:
                                options.append(option)
                                
                        if len(options) < 2:
                            raise ValueError(f'Question {i}: At least 2 options required')
                            
                        correct_answer = request.POST.get(f'correct_option_{i}')
                        if not correct_answer:
                            raise ValueError(f'Question {i}: Correct answer required')
                            
                        Question.objects.create(
                            quiz=quiz,
                            question_text=question_text,
                            question_type=question_type,
                            option_1=options[0],
                            option_2=options[1],
                            option_3=options[2] if len(options) > 2 else None,
                            option_4=options[3] if len(options) > 3 else None,
                            correct_answer=correct_answer
                        )
                        questions_created += 1
                        
                    elif question_type == 'TF':
                        correct_answer = request.POST.get(f'correct_option_{i}')
                        if not correct_answer:
                            raise ValueError(f'Question {i}: Select True or False')
                            
                        Question.objects.create(
                            quiz=quiz,
                            question_text=question_text,
                            question_type=question_type,
                            option_1='True',
                            option_2='False', 
                            correct_answer=correct_answer
                        )
                        questions_created += 1
                        
                    else: # Short Answer
                        correct_answer = request.POST.get(f'correct_answer_{i}')
                        if not correct_answer:
                            raise ValueError(f'Question {i}: Correct answer required')
                            
                        Question.objects.create(
                            quiz=quiz,
                            question_text=question_text,
                            question_type=question_type,
                            correct_answer=correct_answer
                        )
                        questions_created += 1
                        
                if questions_created == 0:
                    raise ValueError('At least one question is required')

                messages.success(request, f'Quiz created successfully with {questions_created} questions')
                return redirect('expert_create_quiz')

        except ValueError as e:
            messages.error(request, str(e))
            return render(request, 'expert/expert_create_quiz.html', {
                'title': title,
                'description': description,
                'duration': duration,
                'passing_score': passing_score,
                'questions': request.POST
            })
            
        except Exception as e:
            logger.error(f"Error creating quiz: {str(e)}")
            messages.error(request, 'An error occurred while saving the quiz')
            return render(request, 'expert/expert_create_quiz.html', {
                'title': title,
                'description': description,
                'duration': duration,
                'passing_score': passing_score,
                'questions': request.POST
            })

    return render(request, 'expert/expert_create_quiz.html', {
        'courses': Course.objects.filter(instructor=request.user)
    })

#==============view for expert quiz list ==========================================
@login_required
@user_passes_test(staff_required)
def expert_quiz_list(request):
    quizzes = Quiz.objects.filter(created_by=request.user, is_active=True)
    return render(request, 'expert/expert_quiz_list.html', {'quizzes': quizzes})

#================= view for expert quiz detail ======================================

@login_required
@user_passes_test(staff_required)
def expert_quiz_detail(request, quiz_id):
    try:
        # Get quiz with validation for ownership
        quiz = get_object_or_404(
            Quiz, 
            id=quiz_id, 
            created_by=request.user,
            is_active=True
        )
        
        # Get quiz questions with proper ordering
        questions = quiz.questions.filter(
            is_active=True
        ).order_by('created_at')
        
        # Get assignment stats
        assignments = QuizAssignment.objects.filter(quiz=quiz)
        total_attempts = assignments.count()
        completed_attempts = assignments.filter(completed=True).count()
        avg_score = assignments.filter(completed=True).aggregate(
            Avg('score')
        )['score__avg'] or 0
        
        context = {
            'quiz': quiz,
            'questions': questions,
            'total_attempts': total_attempts,
            'completed_attempts': completed_attempts,
            'avg_score': round(avg_score, 2),
            'course': quiz.course
        }
        
        return render(request, 'expert/expert_quiz_detail.html', context)
        
    except Quiz.DoesNotExist:
        messages.error(request, 'Quiz not found.')
        return redirect('expert_quiz_list')
    except Exception as e:
        messages.error(request, f'Error loading quiz details: {str(e)}')
        return redirect('expert_quiz_list')

#================= view for expert edit quiz ======================================
@login_required
@user_passes_test(staff_required)
def expert_edit_quiz(request, quiz_id):
    try:
        # Get quiz with ownership validation
        quiz = get_object_or_404(Quiz, 
            id=quiz_id, 
            created_by=request.user,
            is_active=True
        )
        
        if request.method == 'POST':
            with transaction.atomic():
                # Get form data
                title = request.POST.get('title')
                description = request.POST.get('description')
                duration = request.POST.get('duration')

                # Validate required fields
                if not title:
                    raise ValueError('Quiz title is required')

                # Validate duration
                try:
                    duration_minutes = int(duration)
                    if duration_minutes <= 0:
                        raise ValueError('Duration must be positive')
                    duration_timedelta = timedelta(minutes=duration_minutes)
                except (TypeError, ValueError) as e:
                    messages.error(request, str(e))
                    return render(request, 'expert/expert_edit_quiz.html', {
                        'quiz': quiz,
                        'questions': quiz.questions.all().order_by('id')
                    })

                # Update quiz
                quiz.title = title
                quiz.description = description
                quiz.duration = duration_timedelta
                quiz.save()

                # Handle questions
                for i in range(1, 101):  # Max 100 questions
                    question_id = request.POST.get(f'question_id_{i}')
                    if not question_id:
                        continue

                    question = get_object_or_404(Question, id=question_id, quiz=quiz)
                    question.question_text = request.POST.get(f'question_text_{i}')
                    question.question_type = request.POST.get(f'question_type_{i}')

                    if question.question_type == 'MCQ':
                        question.option_1 = request.POST.get(f'option_{i}_1')
                        question.option_2 = request.POST.get(f'option_{i}_2')
                        question.option_3 = request.POST.get(f'option_{i}_3')
                        question.option_4 = request.POST.get(f'option_{i}_4')
                        question.correct_answer = request.POST.get(f'correct_option_{i}')
                    elif question.question_type == 'TF':
                        question.correct_answer = request.POST.get(f'correct_option_{i}')

                    question.save()

                messages.success(request, 'Quiz updated successfully!')
                return redirect('expert_quiz_detail', quiz_id=quiz.id)

        # GET request
        context = {
            'quiz': quiz,
            'questions': quiz.questions.all().order_by('id')
        }
        return render(request, 'expert/expert_edit_quiz.html', context)

    except ValueError as e:
        messages.error(request, str(e))
    except Exception as e:
        messages.error(request, f'Error updating quiz: {str(e)}')
    
    return redirect('expert_quiz_list')

#================= view for expert delete quiz ======================================
@login_required
@user_passes_test(staff_required)
def expert_delete_quiz(request, quiz_id):
    if request.method == 'POST':
        try:
            quiz = get_object_or_404(
                Quiz, 
                id=quiz_id, 
                created_by=request.user,
                is_active=True
            )
            quiz.is_active = False  # Soft delete
            quiz.save()
            messages.success(request, 'Quiz deleted successfully!')
            return JsonResponse({
                'status': 'success',
                'message': 'Quiz deleted successfully'
            })
        except Quiz.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Quiz not found'}, status=404)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error deleting quiz: {str(e)}'
            }, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

#================= view for send quiz to students ======================================
@login_required
@user_passes_test(staff_required)
def send_quiz_to_students(request, quiz_id):
    if request.method == 'POST':
        try:
            # Get quiz and validate ownership
            quiz = get_object_or_404(Quiz, id=quiz_id, created_by=request.user)
            course = quiz.course

            if not course:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Quiz is not associated with any course'
                })
            
            # Get enrolled students
            enrolled_students = course.enrollments.filter(is_active=True)

            if not enrolled_students.exists():
                return JsonResponse({
                    'status': 'error',
                    'message': 'No students enrolled in this course'
                })

            # Create quiz assignments for enrolled students
            assignments_created = 0
            for enrollment in enrolled_students:
                assignment, created = QuizAssignment.objects.get_or_create(
                    quiz=quiz,
                    student=enrollment.student,
                    defaults={
                        'assigned_date': timezone.now(),
                        'due_date': timezone.now() + quiz.duration,
                        'completed': False
                    }
                )
                
                if created:
                    assignments_created += 1
                    create_notification_student(
                    enrollment.student,
                    "New Quiz Assigned",
                    f"You have a new quiz '{quiz.title}' assigned by {request.user.username}",
                    "quiz"
                )

            if assignments_created == 0:
                return JsonResponse({
                    'status': 'warning',
                    'message': 'All students already have this quiz assigned'
                })
            # Send notifications (implement your notification system)
            
            return JsonResponse({
                'status': 'success',
                'message': f'Quiz sent to {enrolled_students.count()} students'
            })
        except Course.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Course not found'
            }, status=404)

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error assigning quiz: {str(e)}'
            }, status=500)
            
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    }, status=400)


#================== view for expert view result ======================================
@login_required
@user_passes_test(staff_required)
def expert_view_result_list(request):
    quizzes = Quiz.objects.filter(created_by=request.user, is_active=True).select_related('course').order_by('-created_at')
    context = {
        'quizzes': quizzes,
        'total_quizzes': quizzes.count()
        }
    return render(request, 'expert/expert_view_result_list.html', context)



#================= view for expert view quiz results ======================================

@login_required
@user_passes_test(staff_required)
def expert_view_quiz_results(request, quiz_id):
    try:
        # Get quiz with validation
        quiz = get_object_or_404(
            Quiz, 
            id=quiz_id, 
            created_by=request.user,
            is_active=True
        )
        
        # Get completed quiz assignments
        assignments = QuizAssignment.objects.filter(
            quiz=quiz,
            completed=True
        ).select_related(
            'student'
        ).order_by('student__username')
        
        # Calculate statistics
        total_assigned = QuizAssignment.objects.filter(quiz=quiz).count()
        total_completed = assignments.count()
        completion_rate = (total_completed / total_assigned * 100) if total_assigned > 0 else 0
        
        if assignments.exists():
            avg_score = sum(a.score for a in assignments) / assignments.count()
            highest_score = max(a.score for a in assignments)
            lowest_score = min(a.score for a in assignments)
        else:
            avg_score = highest_score = lowest_score = 0

        context = {
            'quiz': quiz,
            'course': quiz.course,
            'assignments': assignments,
            'stats': {
                'total_assigned': total_assigned,
                'total_completed': total_completed,
                'completion_rate': round(completion_rate, 2),
                'avg_score': round(avg_score, 2),
                'highest_score': highest_score,
                'lowest_score': lowest_score
            }
        }
        
        return render(request, 'expert/expert_view_quiz_results.html', context)
        
    except Quiz.DoesNotExist:
        messages.error(request, 'Quiz not found or access denied.')
        return redirect('expert_quiz_list')
    except Exception as e:
        messages.error(request, f'Error viewing quiz results: {str(e)}')
        return redirect('expert_quiz_list')

#================ views for expert view student result =====================================

def student_quiz_details(request, quiz_id, student_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    student = get_object_or_404(User, id=student_id)
    assignment = get_object_or_404(QuizAssignment, quiz=quiz, student=student)
    
    # Get detailed answers for this student
    student_answers = QuizAnswer.objects.filter(
        assignment=assignment
    ).select_related('question')
    
    context = {
        'quiz': quiz,
        'student': student,
        'assignment': assignment,
        'student_answers': student_answers,
    }
    return render(request, 'expert/student_quiz_details.html', context)


#================= views for expert learning resources ======================================
@login_required
@user_passes_test(staff_required)
def expert_learning_resources(request):
    return render(request, 'expert/expert_learning_resources.html')


#================= view for show all video lessions in the course ======================
@login_required
@user_passes_test(staff_required)
def expert_lessons(request, course_id):
    try:
        # Get course and verify it's active and owned by user
        course = get_object_or_404(
            Course, 
            id=course_id, 
            instructor=request.user,
            is_active=True  # Only allow active courses
        )
        
        # Get active lessons
        lessons = Lesson.objects.filter(
            course=course,
            is_active=True
        ).order_by('created_at')
        
        context = {
            'course': course,
            'lessons': lessons
        }
        
        return render(request, 'expert/expert_lessons.html', context)
        
    except Course.DoesNotExist:
        messages.error(request, 'Course not found or is no longer active.')
        return redirect('expert_my_courses')
    except Exception as e:
        messages.error(request, f'Error loading lessons: {str(e)}')
        return redirect('expert_my_courses')


#========================== view for delete lesson video =============================

@login_required
@user_passes_test(staff_required)
def delete_video(request, lesson_id):
    # Fetch the lesson by ID
    lesson = get_object_or_404(Lesson, id=lesson_id)

    # Ensure that the user is the course creator or is an admin
    if request.user == lesson.course.expert or request.user.is_superuser:
        # Delete the video file
        lesson.is_active = False
        lesson.save()

        messages.success(request, 'Video deleted successfully!')
        return redirect('expert_lessons', course_id=lesson.course.id)
    else:
        messages.error(request, 'You do not have permission to delete this video.')
        return redirect('expert_lessons', course_id=lesson.course.id)
    


#========================== view for edit lesson video =============================

@login_required
@user_passes_test(staff_required)
def edit_video(request, lesson_id):
    try:
        # Get lesson with validation
        lesson = get_object_or_404(
            Lesson, 
            id=lesson_id,
            is_active=True
        )
        
        # Verify ownership
        if not (request.user == lesson.course.instructor or request.user.is_superuser):
            messages.error(request, 'You do not have permission to edit this video.')
            return redirect('expert_lessons', course_id=lesson.course.id)
        
        if request.method == 'POST':
            form = LessonEditForm(request.POST, request.FILES, instance=lesson)
            if form.is_valid():
                try:
                    with transaction.atomic():
                        # Handle thumbnail
                        old_thumbnail = lesson.thumbnail
                        
                        if 'thumbnail-clear' in request.POST:
                            if old_thumbnail:
                                old_thumbnail.delete()
                            lesson.thumbnail = None
                        elif 'thumbnail' in request.FILES:
                            new_thumbnail = request.FILES['thumbnail']
                            if old_thumbnail and old_thumbnail != new_thumbnail:
                                old_thumbnail.delete()
                            lesson.thumbnail = new_thumbnail
                        
                        # Save form
                        form.save()
                        messages.success(request, 'Video details updated successfully!')
                        return redirect('expert_lessons', course_id=lesson.course.id)
                        
                except Exception as e:
                    messages.error(request, f'Error updating video: {str(e)}')
            else:
                messages.error(request, 'Please correct the errors below.')
        else:
            form = LessonEditForm(instance=lesson)
            
        return render(request, 'expert/edit_video.html', {
            'form': form, 
            'lesson': lesson
        })
        
    except Exception as e:
        messages.error(request, f'Error loading video: {str(e)}')
        return redirect('expert_lessons', course_id=lesson.course.id)


#========================== view for play lesson videos =============================


from google.cloud import storage
from datetime import timedelta

def generate_signed_url(bucket_name, blob_name, content_type=None, expiration=3600):
    client = storage.Client(credentials=settings.GS_CREDENTIALS, project=settings.GS_PROJECT_NAME)
    bucket = client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)

    if content_type:
        blob.content_type = content_type

    signed_url = blob.generate_signed_url(
        expiration=timedelta(seconds=expiration),
        method="GET",
        version="v4",
        response_type=content_type if content_type else None
    )
    return signed_url

@login_required
@user_passes_test(staff_required)
def get_hls_manifest(request, lesson_id):
    """Proxy for m3u8 manifests that generates signed URLs for all segments"""
    try:
        lesson = get_object_or_404(Lesson, id=lesson_id, is_active=True)
        
        # Check permission
        if not request.user == lesson.course.expert and not request.user.is_superuser:
            raise Http404("You don't have permission to view this video")
            
        # Base path for the lesson's HLS content
        base_path = f"expert/{lesson.course.expert.id}/courses/{lesson.course.id}/hls/{lesson.id}/"
        
        # Get the m3u8 content from GCS
        client = storage.Client(credentials=settings.GS_CREDENTIALS, project=settings.GS_PROJECT_NAME)
        bucket = client.get_bucket(settings.GS_BUCKET_NAME)
        blob = bucket.blob(f"{base_path}index.m3u8")
        
        if not blob.exists():
            raise Http404("Manifest not found")
            
        # Download and process the manifest
        m3u8_content = blob.download_as_text()
        lines = m3u8_content.splitlines()
        modified_lines = []
        
        for line in lines:
            if line.endswith('.ts') or (line.endswith('.m3u8') and line != 'index.m3u8'):
                # Generate signed URL for segment or playlist
                segment_path = f"{base_path}{line}"
                content_type = "video/MP2T" if line.endswith('.ts') else "application/vnd.apple.mpegurl"
                signed_url = generate_signed_url(
                    settings.GS_BUCKET_NAME,
                    segment_path,
                    content_type=content_type,
                    expiration=7200  # 2 hours
                )
                modified_lines.append(signed_url)
            else:
                # Keep non-media lines unchanged
                modified_lines.append(line)
                
        # Return the modified manifest
        response = HttpResponse('\n'.join(modified_lines), content_type='application/vnd.apple.mpegurl')
        response['Cache-Control'] = 'max-age=0, no-cache, no-store, must-revalidate'
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Origin, Content-Type, Accept, Range'
        response['Access-Control-Expose-Headers'] = 'Content-Length, Content-Range'
        return response
        
    except Exception as e:
        logger.error(f"Error serving HLS manifest: {str(e)}")
        raise Http404("Error serving video manifest")



# views.py - expert_play_video
@login_required
@user_passes_test(staff_required)
def expert_play_video(request, lesson_id):
    try:
        lesson = get_object_or_404(Lesson, id=lesson_id, is_active=True)

        # Check if user has permission to view this lesson
        if not request.user == lesson.course.expert and not request.user.is_superuser:
            raise Http404("You don't have permission to view this video")
        
        #hls_path = f"/media/expert/{lesson.course.expert.id}/courses/{lesson.course.id}/hls/{lesson.id}/index.m3u8"
        # If using Google Cloud Storage URLs directly
        #blob_path = f"expert/{lesson.course.expert.id}/courses/{lesson.course.id}/hls/{lesson.id}/index.m3u8"
        #hls_path = generate_signed_url(
        #    settings.GS_BUCKET_NAME,
        #    blob_path,
        #    content_type="application/vnd.apple.mpegurl",
        #    expiration=3600  # 1 hour
        #)
        #hls_path = f"https://storage.googleapis.com/{settings.GS_BUCKET_NAME}/expert/{lesson.course.expert.id}/courses/{lesson.course.id}/hls/{lesson.id}/index.m3u8"
        # Fetch all lessons in the same course, excluding the current one


        hls_path = reverse('get_hls_manifest', args=[lesson_id])
        recommended_videos = Lesson.objects.filter(course=lesson.course, is_active=True).exclude(id=lesson_id)
        context = {
            'lesson': lesson,
            'hls_path': hls_path,
            'video_url': lesson.video.url if lesson.video else None,
            'thumbnail_url': lesson.thumbnail.url if lesson.thumbnail else None,
            'course': lesson.course,
            'recommended_videos': recommended_videos,
            'gcs_bucket': settings.GS_BUCKET_NAME  # Pass bucket name to template
        }

        response = render(request, 'expert/expert_play_video.html', context)
        # Add required headers for video streaming
        response['Accept-Ranges'] = 'bytes'
        response['Cache-Control'] = 'no-cache'
        return response

    except Exception as e:
        logger.error(f"Error in expert_play_video: {str(e)}")
        return render(request, 'expert/expert_play_video.html', {
            'error': str(e)
        })
    
def serve_hls_segment(request, path):
    """Serve HLS video segments and playlists"""
    try:
        # Construct full path - remove 'hls' from join since it's in the URL
        full_path = os.path.join(settings.MEDIA_ROOT, path)
        
        if not os.path.exists(full_path):
            logger.error(f"Video segment not found: {full_path}")
            raise Http404("Video segment not found")

        # Set content type based on file extension
        if path.endswith('.m3u8'):
            content_type = 'application/vnd.apple.mpegurl'
        elif path.endswith('.ts'):
            content_type = 'video/MP2T'
        else:
            content_type = mimetypes.guess_type(full_path)[0]

        # Use FileResponse for efficient file serving
        response = FileResponse(
            open(full_path, 'rb'),
            content_type=content_type
        )
        # Add required headers for video streaming
        response['Accept-Ranges'] = 'bytes'
        response['Cache-Control'] = 'no-cache'
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Origin, Content-Type, Accept'

        return response

    except Exception as e:
        logger.error(f"Error serving video segment: {str(e)}")
        raise Http404("Error serving video segment")

# Add this if you need to serve HLS segments (optional)
#def serve_hls_segment(request, path):
#    """Serve HLS segments with proper headers"""
#    full_path = os.path.join(settings.MEDIA_ROOT, 'hls', path)
#    
#    if not os.path.exists(full_path):
#        raise Http404("Video segment not found")
#        
#    with open(full_path, 'rb') as f:
#        response = HttpResponse(f.read(), content_type='application/vnd.apple.mpegurl' 
#                              if path.endswith('.m3u8') else 'video/MP2T')
#        response['Access-Control-Allow-Origin'] = '*'
#        return response

#========================== view for add new video lesson in the existing course =============================
# views.py
@login_required
@user_passes_test(staff_required)
def expert_upload_video(request, course_id):
    try:
        course = get_object_or_404(Course, id=course_id, instructor=request.user, is_active=True)
        
        if request.method == 'POST':
            form = LessonForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    with transaction.atomic():
                        # Validate and process video file
                        if 'video' not in request.FILES:
                            raise ValidationError('Video file is required')
                        
                        video_file = request.FILES['video']
                        if not video_file.content_type.startswith('video/'):
                            raise ValidationError('Invalid file type. Please upload a video file.')
                        
                        # Create lesson
                        lesson = form.save(commit=False)
                        lesson.course = course
                        lesson.save()

                        # Create HLS directory
                        hls_output_dir = os.path.join(
                            settings.MEDIA_ROOT,
                            'expert',
                            str(request.user.id),
                            'courses',
                            str(course.id),
                            'hls',
                            str(lesson.id)
                        )
                        os.makedirs(hls_output_dir, exist_ok=True)

                        try:
                            # Convert video to HLS
                            relative_hls_path = convert_to_hls(
                                video_path=lesson.video.path,
                                output_dir=hls_output_dir,
                                user=str(request.user.id),
                                course_title=str(course.id),
                                lesson_id=str(lesson.id)
                            )
                            
                            # Update lesson with HLS URL
                            lesson.hls_url = relative_hls_path
                            #lesson.save()
                            
                            messages.success(request, 'Video uploaded successfully!')
                            return redirect('expert_lessons', course_id=course.id)
                        
                        except Exception as e:
                            # Cleanup on conversion failure
                            lesson.video.delete(save=False)
                            if lesson.thumbnail:
                                lesson.thumbnail.delete(save=False)
                            lesson.delete()
                            raise Exception(f'Video conversion failed: {str(e)}')

                except ValidationError as e:
                    messages.error(request, str(e))
                except Exception as e:
                    logger.error(f"Error in video upload: {e}")
                    messages.error(request, 'An error occurred while uploading the video.')
                    if 'lesson' in locals():
                        lesson.video.delete(save=False)
                        lesson.delete()
            else:
                messages.error(request, 'Please correct the errors below.')
        else:
            form = LessonForm()

        return render(request, 'expert/expert_upload_video.html', {
            'form': form,
            'course': course
        })

    except Exception as e:
        logger.error(f"Error in expert_upload_video: {e}")
        messages.error(request, 'An error occurred. Please try again.')
        return redirect('expert_my_courses')
#===================== views for expert chat page ==========================================

@login_required
@user_passes_test(staff_required)
def expert_chat(request):
    try:
        # Get all students who have chatted with expert
        students = User.objects.filter(
            Q(sent_messages__receiver=request.user) | 
            Q(received_messages__sender=request.user)
        ).annotate(
            unread_count=Count(
                'sent_messages',
                filter=Q(
                    sent_messages__receiver=request.user, 
                    sent_messages__is_read=False,
                    sent_messages__deleted_for_expert=False
                ),
                distinct=True  # Count unique messages only
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
        ).exclude(
            is_staff=True
        ).order_by('-last_message', '-id').distinct()

        context = {
            'students': students,
            'total_unread': sum(student.unread_count for student in students)
        }

        return render(request, 'chat/expert_chat.html', context)
    
    except Exception as e:
        messages.error(request, f'Error loading chat: {str(e)}')
        return redirect('expert_dashboard')


def delete_all_chat(request, student_id):
    try:
        student = get_object_or_404(User, id=student_id)
        
        # Soft delete messages
        Message.objects.filter(
            Q(sender=request.user, receiver=student) | 
            Q(sender=student, receiver=request.user)
        ).update(deleted_for_expert=True)
        
        messages.success(request, "Chat messages deleted successfully.")
        return redirect('expert_chat')
        
    except Exception as e:
        messages.error(request, f'Error deleting chat: {str(e)}')
        return redirect('expert_chat')

#===================== views for selles report ==========================================
# views.py


@login_required
@user_passes_test(staff_required)
def selles_dashboard(request):
    try:
        # Get or create wallet
        wallet, created = Wallet.objects.get_or_create(
            expert=request.user,
            defaults={'balance': 0}
        )
        
        # Get withdrawals history
        withdrawals = WithdrawalRequest.objects.filter(
            expert=request.user
        ).order_by('-created_at')
        # Get expert's courses
        courses = Course.objects.filter(instructor=request.user).select_related('instructor')
        
        # Monthly enrollments
        monthly_enrollments = Enrollment.objects.filter(
            course__in=courses,
            enrolled_at__gte=timezone.now() - timedelta(days=365)  # Last 12 months
        ).annotate(
            month=TruncMonth('enrolled_at')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')

        # Daily enrollments for last 30 days
        daily_enrollments = Enrollment.objects.filter(
            course__in=courses,
            enrolled_at__gte=timezone.now() - timedelta(days=30)
        ).annotate(
            day=TruncDay('enrolled_at')
        ).values('day').annotate(
            count=Count('id')
        ).order_by('day')

        # Format data for charts
        enrollment_data = {
            'monthly': [
                {
                    'date': item['month'].isoformat(),
                    'count': item['count']
                } 
                for item in monthly_enrollments
            ],
            'daily': [
                {
                    'date': item['day'].isoformat(),
                    'count': item['count']
                } 
                for item in daily_enrollments
            ]
        }
        
        # Course statistics
        course_stats = []
        total_earnings = 0
        
        for course in courses:
            enrollments = Enrollment.objects.filter(course=course)
            earnings = enrollments.count() * course.price
            total_earnings += earnings
            
            course_stats.append({
                'title': course.course_title,
                'is_active': course.is_active, 
                'enrollments': enrollments.count(),
                'earnings': earnings,
                'price': course.price
            })
        
        context = {
            'total_earnings': total_earnings,
            'total_students': Enrollment.objects.filter(course__in=courses).count(),
            'total_courses': courses.count(),
            'course_stats': course_stats,
            'monthly_data': list(monthly_enrollments),
            'wallet': wallet,
            'withdrawals': withdrawals,
            'enrollment_data': json.dumps(enrollment_data)
        }
        
        return render(request, 'expert/selles_dashboard.html', context)
        
    except Exception as e:
        messages.error(request, f'Error loading dashboard: {str(e)}')
        return redirect('expert_dashboard')
    
#===================== views for withrawal request ==========================================

@login_required
@user_passes_test(staff_required)
def request_withdrawal(request):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                amount = Decimal(request.POST.get('amount', 0))
                bank_account = request.POST.get('bank_account')
                ifsc_code = request.POST.get('ifsc_code')

                # Validate input fields
                if not all([amount, bank_account, ifsc_code]):
                    raise ValueError("All fields are required")

                wallet = Wallet.objects.select_for_update().get(expert=request.user)
                
                if amount <= 0:
                    raise ValueError("Amount must be positive")
                
                if amount > wallet.balance:
                    messages.error(request, 'Insufficient balance')
                    return redirect('selles_dashboard')

                # Create withdrawal request
                withdrawal = WithdrawalRequest.objects.create(
                    expert=request.user,
                    amount=amount,
                    bank_account=bank_account,
                    ifsc_code=ifsc_code,
                    status='PENDING'
                )

                # Deduct amount from wallet
                wallet.balance -= amount
                wallet.save()

                messages.success(request, 'Withdrawal request submitted successfully')
                
        except Wallet.DoesNotExist:
            messages.error(request, 'Wallet not found')
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Error processing withdrawal: {str(e)}')
            
    return redirect('selles_dashboard')



#===================== views for make announcement ==========================================

def send_announcement(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if request.method == 'POST':
        announcement_text = request.POST.get('announcementText')
        if announcement_text:
            # Get active enrollments
            enrollments = Enrollment.objects.filter(course=course, is_active=True)
            
            # Send email to all active enrollments
            #recipients = [enrollment.student.email for enrollment in enrollments]
            #send_mail(
            #    subject=f'Announcement for {course.course_title}',
            #    message=announcement_text,
            #    from_email='your_email@example.com',
            #    recipient_list=recipients,
            #    fail_silently=False,
            #)

            # Send chat message to all enrolled students
            for enrollment in enrollments:
                Message.objects.create(
                    sender=request.user,
                    receiver=enrollment.student,
                    content=f"[ANNOUNCEMENT] {announcement_text}"
                )

            messages.success(request, 'Announcement sent successfully via email and chat.')
        else:
            messages.error(request, 'Please write an announcement before sending.')

    return redirect('expert_lessons', course_id=course.id)