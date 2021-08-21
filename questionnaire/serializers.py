from questionnaire.models import Questionnaire, Question, Option, AnswerSheet
from rest_framework import serializers


class OptionSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Option
        fields = '__all__'


class QuestionSerializer(serializers.ModelSerializer):
    option_list = OptionSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = '__all__'


class QuestionnaireBaseSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)
    answer_num = serializers.SerializerMethodField()




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
