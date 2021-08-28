from django.contrib import admin

from questionnaire.models import Questionnaire, Question, AnswerSheet, Option, AnswerDetail, QuestionOptionLogicRelation


# Register your models here.


class QuestionnaireAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'content')
    search_fields = ('title',)


class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'content')
    search_fields = ('title',)


class OptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'content')
    search_fields = ('title',)


class AnswerSheetAdmin(admin.ModelAdmin):
    list_display = ('id', 'modified_time')


class AnswerDetailAdmin(admin.ModelAdmin):
    list_display = ('id', 'option_id')


class QuestionOptionLogicRelationAdmin(admin.ModelAdmin):
    list_display = ('question', 'option')


admin.site.register(Questionnaire, QuestionnaireAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Option, OptionAdmin)
admin.site.register(AnswerSheet, AnswerSheetAdmin)
admin.site.register(AnswerDetail, AnswerDetailAdmin)
admin.site.register(QuestionOptionLogicRelation, QuestionOptionLogicRelationAdmin)
