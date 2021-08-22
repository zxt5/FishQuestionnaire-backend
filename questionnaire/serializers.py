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
    id = serializers.IntegerField(read_only=False, required=False)

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
            reserve_options_list = []
            for option_data in option_list_data:
                op_id = option_data.get('id')
                # 如果选项ID存在，说明该选项是被更新的，保留。
                if op_id is not None:
                    option_instance = Option.objects.get(id=op_id)
                    reserve_options_list.append(option_data.pop('id'))
                    super().update(option_instance, option_data)
                # 如果选项ID不存在，说明该选项是要创建的，保留
                else:
                    print(option_data)
                    print(instance)
                    opt = Option.objects.create(question_id=instance.id, **option_data)
                    reserve_options_list.append(opt.id)
            # 删除那些不在此次PUT json中的数据
            all_option = Option.objects.filter(question_id=instance.id)
            for option in all_option:
                if option.id not in reserve_options_list:
                    option.delete()

        super().update(instance, validated_data)

        return instance


class QuestionnaireBaseSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    author = UserDescSerializer(read_only=True)
    url = serializers.HyperlinkedIdentityField(view_name='questionnaire-detail')
    answer_num = serializers.SerializerMethodField()

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
