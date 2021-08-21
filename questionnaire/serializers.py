from questionnaire.models import Questionnaire, Question, Option, AnswerSheet
from rest_framework import serializers
from user_info.serializers import UserDescSerializer

class OptionSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Option
        fields = '__all__'


class QuestionSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)
    option_list = OptionSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = '__all__'


class QuestionnaireBaseSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)
    answer_num = serializers.SerializerMethodField()
    author = UserDescSerializer(read_only=True)


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
            'title'
        ]
        read_only_fields = ['id', 'title']


class AnswerSheetSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    respondent = UserDescSerializer(read_only=True)

    class Meta:
        model = AnswerSheet
        fields = '__all__'
