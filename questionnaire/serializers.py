from rest_framework.serializers import raise_errors_on_nested_writes
from rest_framework.utils import model_meta

from questionnaire.models import Questionnaire, Question, Option, AnswerSheet
from rest_framework import serializers
from user_info.serializers import UserDescSerializer


class OptionSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Option
        fields = '__all__'


class OptionNestSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=False)

    class Meta:
        model = Option
        exclude = ['question']


class QuestionSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    option_list = OptionNestSerializer(many=True, required=False)

    def create(self, validated_data):
        option_list_data = validated_data.get('option_list')
        if option_list_data is not None:
            validated_data.pop('option_list')

        question = Question.objects.create(**validated_data)

        if option_list_data is not None:
            for option in option_list_data:
                Option.objects.create(question=question, **option)
        return question

    class Meta:
        model = Question
        fields = '__all__'

    def update(self, instance, validated_data):
        option_list_data = validated_data.get('option_list')
        if option_list_data is not None:
            validated_data.pop('option_list')
            for option_data in option_list_data:
                op_id = option_data.get('id')
                if op_id is not None:
                    option_instance = Option.objects.get(id=op_id)
                    option_data.pop('id')
                    print(option_data)
                    super().update(option_instance, option_data)
                else:
                    Option.objects.create(option_data)

        super().update(instance, validated_data)
        return instance


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
        fields = '__all__'
        read_only_fields = ['id', 'title']


class AnswerSheetSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    respondent = UserDescSerializer(read_only=True)

    class Meta:
        model = AnswerSheet
        fields = '__all__'
