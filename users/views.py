from django.contrib.auth import logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import CustomUser
from .forms import RegisterForm
from courses.models import Course, Enrollment, Lesson, LessonProgress
import json


def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user:
            # Automatically set role based on superuser status
            if user.is_superuser:
                user.role = 'admin'  # or 'instructor'
                user.save()
            elif not user.role:
                user.role = 'student'
                user.save()
            login(request, user)
            return redirect('dashboard')
    return render(request, 'registration/login.html')


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'admin' if user.is_superuser else 'student'
            user.save()
            return redirect('login')
    else:
        form = RegisterForm()
    return render(request, 'registration/register.html', {'form': form})


@login_required
def dashboard(request):
    if request.user.role == 'student':
        if request.user.role == 'student':
            enrollments = Enrollment.objects.filter(student=request.user)
            progress_data = []

            for enroll in enrollments:
                lessons = Lesson.objects.filter(course=enroll.course)
                total = lessons.count()
                completed = LessonProgress.objects.filter(student=request.user, lesson__in=lessons,
                                                          completed=True).count()
                percent = int((completed / total) * 100) if total > 0 else 0
                progress_data.append({
                    'course': enroll.course,
                    'progress': percent,
                    'completed': completed,
                    'total': total
                })

            return render(request, 'dashboard_student.html', {'progress_data': progress_data})

    elif request.user.role == 'instructor':
        courses = Course.objects.filter(instructor=request.user)
        course_names = []
        enrollment_counts = []
        completion_rates = []

        for course in courses:
            course_names.append(course.title)
            enroll_count = Enrollment.objects.filter(course=course).count()
            enrollment_counts.append(enroll_count)

            total_lessons = Lesson.objects.filter(course=course).count()
            if enroll_count > 0 and total_lessons > 0:
                total_possible = enroll_count * total_lessons
                completed = LessonProgress.objects.filter(
                    lesson__course=course, completed=True
                ).count()
                rate = round((completed / total_possible) * 100, 1)
            else:
                rate = 0
            completion_rates.append(rate)

        return render(request, 'dashboard_instructor.html', {
            'courses': courses,
            'course_names_json': json.dumps(course_names),
            'enrollment_counts_json': json.dumps(enrollment_counts),
            'completion_rates_json': json.dumps(completion_rates),
            'total_courses': courses.count(),
            'total_enrollments': sum(enrollment_counts),
        })
    else:
        return render(request, 'dashboard_admin.html')

def logout_view(request):
    logout(request)
    return redirect('login')
