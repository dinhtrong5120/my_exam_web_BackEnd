from django.contrib import admin
from .models import Exam, Question, Choice, Attempt

class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'exam', 'position', 'part', 'prompt')
    inlines = [ChoiceInline]

admin.site.register(Exam)
admin.site.register(Attempt)
