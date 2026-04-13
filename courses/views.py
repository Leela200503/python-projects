from django.shortcuts import render, redirect, get_object_or_404
from .models import Course, Lesson, Enrollment, LessonProgress
from django.contrib.auth.decorators import login_required
from users.models import CustomUser
from django.template.loader import render_to_string
from django.http import HttpResponse
from xhtml2pdf import pisa
import io



def landing_view(request):
    return render(request, 'landing.html')

@login_required
def course_list(request):
    courses = Course.objects.all()
    return render(request, 'courses/course_list.html', {'courses': courses})

@login_required
def create_course(request):
    if request.user.role not in ['admin', 'instructor']:
        return redirect('course_list')

    if request.method == 'POST':
        title = request.POST['title']
        description = request.POST['description']
        image = request.FILES.get('image')
        Course.objects.create(title=title, description=description, instructor=request.user, image=image)
        return redirect('course_create')

    courses = Course.objects.filter(instructor=request.user)
    return render(request, 'courses/course_create.html', {'courses': courses})


@login_required
def add_lesson(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if request.user != course.instructor and not request.user.is_superuser:
        return redirect('dashboard')
    if request.method == 'POST':
        title = request.POST['title']
        content = request.POST['content']
        video_url = request.POST['video_url']
        order = request.POST.get('order', 0)
        Lesson.objects.create(course=course, title=title, content=content, video_url=video_url, order=order)
    lessons = course.lessons.all() # ordering is handled by Meta in models.py
    return render(request, 'courses/add_lesson.html', {'course': course, 'lessons': lessons})

# Redundant view removed later in the file

@login_required
def edit_course(request, course_id):
    course = get_object_or_404(Course, id=course_id, instructor=request.user)
    if request.method == 'POST':
        course.title = request.POST['title']
        course.description = request.POST['description']
        if request.FILES.get('image'):
            course.image = request.FILES['image']
        course.save()
        return redirect('course_create')
    return render(request, 'courses/edit_course.html', {'course': course})


@login_required
def delete_course(request, course_id):
    course = get_object_or_404(Course, id=course_id, instructor=request.user)
    if request.method == 'POST':
        course.delete()
        return redirect('course_create')
    return render(request, 'courses/delete_course.html', {'course': course})



@login_required
def edit_lesson(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)

    # Only course instructor or superuser can edit
    if not (request.user == lesson.course.instructor or request.user.is_superuser):
        return redirect('dashboard')

    if request.method == 'POST':
        lesson.title = request.POST['title']
        lesson.content = request.POST['content']
        lesson.video_url = request.POST['video_url']
        lesson.order = request.POST.get('order', 0)
        lesson.save()
        return redirect('add_lesson', course_id=lesson.course.id)

    return render(request, 'courses/edit_lesson.html', {'lesson': lesson})


@login_required
def delete_lesson(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)

    # Only course instructor or superuser can delete
    if not (request.user == lesson.course.instructor or request.user.is_superuser):
        return redirect('dashboard')

    if request.method == 'POST':
        course_id = lesson.course.id
        lesson.delete()
        return redirect('add_lesson', course_id=course_id)

    return render(request, 'courses/delete_lesson.html', {'lesson': lesson})



@login_required
def view_lessons(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    lessons = course.lessons.all()

    # Preload progress for this user
    completed_lessons = LessonProgress.objects.filter(
        student=request.user,
        lesson__in=lessons,
        completed=True
    ).values_list('lesson_id', flat=True)

    # Add a custom attribute to each lesson object
    for lesson in lessons:
        lesson.is_completed = lesson.id in completed_lessons

    # Progress calculation
    total_lessons = lessons.count()
    completed_count = len(completed_lessons)
    progress_percentage = (completed_count / total_lessons * 100) if total_lessons > 0 else 0

    return render(request, 'courses/view_lessons.html', {
        'course': course,
        'lessons': lessons,
        'progress_percentage': progress_percentage,
        'is_fully_completed': progress_percentage == 100 and total_lessons > 0
    })


@login_required
def download_certificate(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    # Check if student completed all lessons
    total_lessons = course.lessons.count()
    completed_count = LessonProgress.objects.filter(
        student=request.user, 
        lesson__course=course, 
        completed=True
    ).count()

    if total_lessons == 0 or completed_count < total_lessons:
        return HttpResponse("You haven't completed this course yet.", status=403)

    context = {
        'user': request.user,
        'course': course,
    }
    
    html = render_to_string('courses/certificate.html', context)
    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode("UTF-8")), result)
    
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="certificate_{course.title}.pdf"'
        return response
    
    return HttpResponse('Error generating PDF', status=500)


@login_required
def mark_lesson_complete(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)

    if request.user.role == 'student':
        LessonProgress.objects.update_or_create(
            student=request.user,
            lesson=lesson,
            defaults={'completed': True}
        )

    return redirect('view_lessons', course_id=lesson.course.id)
