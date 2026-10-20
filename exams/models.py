from django.conf import settings
from django.db import models

class Exam(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='exams')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=60, default='TOEIC')
    duration_minutes = models.PositiveIntegerField(default=30)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

class Question(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='questions')
    position = models.PositiveIntegerField(default=0)
    part = models.CharField(max_length=30, default='Part 5')
    question_type = models.CharField(max_length=10, default='single')
    prompt = models.TextField()
    passage = models.TextField(blank=True)
    explanation = models.TextField(blank=True)
    points = models.PositiveIntegerField(default=1)
    difficulty = models.CharField(max_length=20, default='easy')
    image = models.ImageField(upload_to='questions/images/', blank=True, null=True)
    audio = models.FileField(upload_to='questions/audio/', blank=True, null=True)

    class Meta:
        ordering = ['position', 'id']

class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    text = models.TextField()
    is_correct = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['position', 'id']

class Attempt(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.SET_NULL, null=True, blank=True, related_name='attempts')
    exam_title = models.CharField(max_length=200, blank=True)
    exam_description = models.TextField(blank=True)
    exam_category = models.CharField(max_length=60, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    guest_name = models.CharField(max_length=80, blank=True)
    answers = models.JSONField(default=dict)
    score = models.PositiveIntegerField(default=0)
    max_score = models.PositiveIntegerField(default=0)
    result_snapshot = models.JSONField(default=dict, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at']
