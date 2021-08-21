from django.contrib import admin
from django.contrib import admin

from questionnaire.models import Questionnaire, Question, AnswerSheet, Option


# Register your models here.


class QuestionnaireAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'content')


class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'content')


class OptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'content')


class AnswerSheetAdmin(admin.ModelAdmin):
    list_display = ('id',)


admin.site.register(Questionnaire, QuestionnaireAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Option, OptionAdmin)
admin.site.register(AnswerSheet, AnswerSheetAdmin)
