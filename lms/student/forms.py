# student/forms.py
from django import forms
from django.contrib.auth.models import User
from .models import StudentProfile
from django.core.exceptions import ValidationError

class StudentRegistrationForm(forms.ModelForm):
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
            StudentProfile.objects.create(user=user)
        return user

class StudentProfileForm(forms.ModelForm):
    username = forms.CharField(max_length=30, required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)

    class Meta:
        model = StudentProfile
        fields = ['profile_picture','mobile_number']

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
        # Save StudentProfile fields
        student_profile = super().save(commit=False)

        # Update User fields
        user = student_profile.user
        #user.username = self.cleaned_data['username']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']

        if commit:
            user.save()  # Save User model
            student_profile.save()  # Save StudentProfile model

        return student_profile

class CourseSearchForm(forms.Form):
    query = forms.CharField(label='Search Courses', max_length=100)
    def __init__(self, *args, **kwargs):
        super(CourseSearchForm, self).__init__(*args, **kwargs)
        self.fields['query'].widget.attrs.update({'class': 'search', 'placeholder': 'Search...'})