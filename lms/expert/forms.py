# teacher/forms.py
from django import forms
from django.contrib.auth.models import User
from .models import ExpertProfile, Course, Lesson, Quiz, Assignment, Question
from django.core.exceptions import ValidationError

class ExpertRegistrationForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)
    password_confirm = forms.CharField(widget=forms.PasswordInput, label='Confirm Password',  required=True)
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password']
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError("This username is already taken. Please choose another.")
        return username
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("This email is already registered. Please choose another.")
        return email
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError("Passwords do not match")
        
    

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
            ExpertProfile.objects.create(user=user)
        return user
    
class ExpertProfileForm(forms.ModelForm):
    username = forms.CharField(max_length=30, required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)

    class Meta:
        model = ExpertProfile
        fields = ['profile_picture','mobile_number','address','subject','is_expert']
        
    def __init__(self, *args, **kwargs):
        # Pass the user instance separately
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            # Initialize fields from the User model
            self.fields['username'].initial = user.username
            #self.fields['username'].disabled = True  # Freeze the username field
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email

    def save(self, commit=True):
        # Save ExpertProfile fields
        expert_profile = super().save(commit=False)

        # Update User fields
        user = expert_profile.user
        #user.username = self.cleaned_data['username']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']

        if commit:
            user.save()  # Save User model
            expert_profile.save()  # Save ExpertProfile model

        return expert_profile

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['course_title', 'about_course', 'price', 'enrollment_duration']
    enrollment_duration = forms.IntegerField(
        min_value=1,
        help_text="Set the duration in days for student access",
        label="Enrollment Duration (days)"
    )


def validate_image(image):
    if image.size > 2 * 1024 * 1024:  # Limit size to 2MB
        raise ValidationError("Image file too large ( > 2MB )")

class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ['lesson_title', 'description', 'video', 'thumbnail']  # Add video field to form

        def clean_thumbnail(self):
            thumbnail = self.cleaned_data.get('thumbnail')
            # Call the custom validation function
            if thumbnail:
                validate_image(thumbnail)
            return thumbnail
        
class LessonEditForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ['lesson_title', 'description', 'thumbnail']  # Fields to be edited
        widgets = {
            'thumbnail': forms.ClearableFileInput(),
        }

class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ['title', 'description', 'due_date', 'course']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Enter assignment title'}),
            'description': forms.Textarea(attrs={'placeholder': 'Enter assignment description'}),
            'due_date': forms.TextInput(attrs={  # Keep this as a regular text input
                'type': 'text', 
                'placeholder': 'Enter due date (YYYY-MM-DD)'
            }),
            'course': forms.Select(attrs={'placeholder': 'Select a course'}),
        }
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Pass the user when initializing the form
        super().__init__(*args, **kwargs)
        if user:
            # Filter the course dropdown to show only courses created by the logged-in expert
            self.fields['course'].queryset = Course.objects.filter(expert=user)



class QuizForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = ['title', 'description', 'duration']

class QuestionForm(forms.ModelForm):
    correct_answer = forms.CharField(required=False)  # Add it as a custom form field

    class Meta:
        model = Question
        fields = ['question_text', 'question_type']

    def clean(self):
        cleaned_data = super().clean()
        question_type = cleaned_data.get('question_type')
        correct_answer = cleaned_data.get('correct_answer')

        if question_type == 'TF' and correct_answer not in ['True', 'False']:
            raise forms.ValidationError("Correct answer for True/False must be 'True' or 'False'.")

        return cleaned_data


