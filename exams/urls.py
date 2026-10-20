from django.urls import path
from . import views

urlpatterns = [
    path('attempts/', views.my_attempts),
    path('attempts/<int:attempt_id>/', views.my_attempt_detail),
    path('auth/register/', views.register),
    path('auth/login/', views.login),
    path('auth/me/', views.me),
    path('exams/', views.exams),
    path('exams/<int:exam_id>/', views.exam_detail),
    path('exams/<int:exam_id>/publish/', views.publish_exam),
    path('exams/<int:exam_id>/import/', views.import_questions),
    path('exams/<int:exam_id>/questions/<int:question_id>/media/', views.upload_question_media),
    path('exams/<int:exam_id>/submit/', views.submit_exam),
    path('exams/<int:exam_id>/attempts/', views.exam_attempts),
]
