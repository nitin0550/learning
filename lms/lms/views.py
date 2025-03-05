# views.py
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import render, redirect
from django.contrib.auth.views import LoginView
from django.contrib.auth import login
from django.shortcuts import redirect
from django.urls import reverse
from expert.views import expert_dashboard
from student.views import student_dashboard
import random
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.contrib import messages
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class CustomAuthenticationForm(AuthenticationForm):
    def confirm_login_allowed(self, user):
        pass

class CustomLoginView(LoginView):
    template_name ='registration/login.html'  # custom login template
    authentication_form = CustomAuthenticationForm  # Use the custom form
    if User.is_active == False:
        redirect('verify_activation')

    def form_valid(self, form):
        user = form.get_user()
        if user and not user.is_active:
            try:
                # Generate OTP
                otp = random.randint(100000, 999999)
                self.request.session['activation_otp'] = otp
                self.request.session['inactive_user_id'] = user.id

                # Send OTP
                send_mail(
                    'Account Activation OTP',
                    f'Hi {user.username},\n\nYour account activation OTP is: {otp}\n\nBest regards,\nLMS Team',
                    settings.EMAIL_HOST_USER,
                    [user.email],
                    fail_silently=False,
                )
                messages.info(self.request, 'Please verify your account with OTP sent to your email.')
                return redirect('verify_activation')
            
            except Exception as e:
                logger.error(f"Error sending OTP email: {str(e)}")
                messages.error(self.request, 'Failed to send OTP email. Please try again.')
                return redirect('login')
        elif user and user.is_active:
            if user.is_staff:  # Check if the user is a staff member
                login(self.request, user)  # Log the user in
                return redirect('expert_dashboard')  # Redirect to the staff dashboard
            else:
                login(self.request, user)  # Log the user in
                return redirect('student_dashboard')
        else:
            messages.error(self.request, 'Invalid username or password.')
            return self.form_invalid(form)
            
def verify_activation(request):
    if request.method == 'POST':
        otp = request.POST.get('otp')
        stored_otp = request.session.get('activation_otp')
        user_id = request.session.get('inactive_user_id')
        
        if stored_otp and int(otp) == stored_otp:
            user = User.objects.get(id=user_id)
            user.is_active = True
            user.save()
            
            # Clear session
            del request.session['activation_otp']
            del request.session['inactive_user_id']
            
            messages.success(request, 'Account activated successfully. Please login.')
            return redirect('login')
        else:
            messages.error(request, 'Invalid OTP. Please try again.')
            
    return render(request, 'registration/verify_otp.html')


def forgot_password(request):
    return render(request, 'registration/forgot_password.html')


def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            otp = random.randint(100000, 999999)  # Generate a 6-digit OTP
            # Store the OTP in the session (or a more secure method in production)
            request.session['otp'] = otp
            request.session['otp_email'] = email
            send_mail(
                'Your OTP Code',
                f'Hi {user.username},\n\nYour OTP code is {otp}.\n\nBest regards,\nYour Company',
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False,
            )
            return redirect('verify_otp')
        except User.DoesNotExist:
            messages.error(request, "User with this email does not exist.")
    return render(request, 'registration/forgot_password.html')

def verify_otp(request):
    if request.method == 'POST':
        otp_input = request.POST.get('otp')
        if int(otp_input) == request.session.get('otp'):
            return redirect('reset_password')
        else:
            messages.error(request, "Invalid OTP. Please try again.")
    return render(request, 'registration/verify_otp.html')

def reset_password(request):
    if request.method == 'POST':
        password = request.POST.get('password')
        email = request.session.get('otp_email')
        user = User.objects.get(email=email)
        user.set_password(password)
        user.save()
        messages.success(request, "Your password has been reset successfully.")
        return redirect('login')
    return render(request, 'registration/reset_password.html')



