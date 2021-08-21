from questionnaire.models import Questionnaire, Question, Option, AnswerSheet
from rest_framework import serializers
from user_info.serializers import UserDescSerializer

class OptionSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Option
        fields = '__all__'


class QuestionSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    option_list = OptionSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = '__all__'


class QuestionnaireBaseSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    answer_num = serializers.SerializerMethodField()
    author = UserDescSerializer(read_only=True)
    url = serializers.HyperlinkedIdentityField(view_name='questionnaire-detail')

    def get_answer_num(self, questionnaire):
        res = questionnaire.answer_list.filter(questionnaire=questionnaire).order_by('-ordering').first()
        if res is None:
            return 0
        else:
            res = res.ordering
            if res is None:
                return 0
            return res


class QuestionnaireDetailSerializer(QuestionnaireBaseSerializer):
    question_list = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Questionnaire
        fields = '__all__'


class QuestionnaireListSerializer(QuestionnaireBaseSerializer):
    class Meta:
        model = Questionnaire
        fields = [
            'id',
            'title',
            'answer_num',
            'url'
        ]
        read_only_fields = ['id', 'title']


class AnswerSheetSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    respondent = UserDescSerializer(read_only=True)

    class Meta:
        model = AnswerSheet
        fields = '__all__'
