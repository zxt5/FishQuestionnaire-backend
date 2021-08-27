from rest_framework import serializers

from questionnaire.models import Questionnaire, Question, Option, AnswerSheet, AnswerDetail
from questionnaire.template_create import Template
from user_info.serializers import UserDescSerializer


class OptionBaseSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Option
        fields = ['id', 'title', 'ordering']


class OptionSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Option
        fields = '__all__'


class OptionNestSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=False, required=False)

    answer_num = serializers.SerializerMethodField(read_only=True)

    def get_answer_num(self, option):
        return option.get_answer_num()

    class Meta:
        model = Option
        exclude = ['question']


class QuestionBaseSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Question
        fields = [
            'id',
            'title',
            'type',
            'ordering'
        ]


class QuestionSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    option_list = OptionNestSerializer(many=True, required=False)
    ordering = serializers.IntegerField(required=False)
    answer_num = serializers.SerializerMethodField(read_only=True)

    def get_answer_num(self, question):
        return question.get_answer_num()

    class Meta:
        model = Question
        fields = '__all__'

    def create(self, validated_data):
        option_list_data = validated_data.get('option_list')
        if option_list_data is not None:
            validated_data.pop('option_list')

        question = Question.objects.create(**validated_data)

        if option_list_data is not None:
            for option in option_list_data:
                option['id'] = None
                Option.objects.create(question=question, **option)
        return question

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
                    opt = Option.objects.create(question_id=instance.id, **option_data)
                    reserve_options_list.append(opt.id)
            # 删除那些不在此次PUT json中的数据
            all_option = Option.objects.filter(question_id=instance.id)
            for option in all_option:
                if option.id not in reserve_options_list:
                    option.delete()
        # 更新非嵌套的内容
        super().update(instance, validated_data)

        return instance


class QuestionNestSerializer(QuestionSerializer):
    id = serializers.IntegerField(read_only=False, required=False)


class QuestionnaireBaseSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    author = UserDescSerializer(read_only=True)
    url = serializers.HyperlinkedIdentityField(view_name='questionnaire-detail')
    answer_num = serializers.SerializerMethodField()
    question_num = serializers.SerializerMethodField()

    def get_answer_num(self, questionnaire):
        return questionnaire.get_answer_num()

    def get_question_num(self, questionnaire):
        return questionnaire.get_question_num()


class QuestionnaireDetailSerializer(QuestionnaireBaseSerializer):
    question_list = serializers.SerializerMethodField(required=False)
    '''
        解析问卷。一次性传入，然后看题目的id是否存在。类似于题目选项的写法，难点是封装成一个递归函数
    '''

    def get_question_list(self, instance):
        question_list = instance.question_list.all().order_by('ordering')
        return QuestionNestSerializer(question_list, many=True).data

    def create(self, validated_data):
        questionnaire = Questionnaire.objects.create(**validated_data)
        questionnaire_type = questionnaire.type()
        template = Template()
        if questionnaire_type == 'vote':
            template.vote(questionnaire)
        elif questionnaire_type == 'signup':
            template.signup(questionnaire)
        elif questionnaire_type == 'exam':
            template.exam(questionnaire)
        elif questionnaire_type == 'epidemic-check-in':
            template.epidemic_check_in(questionnaire)

        return questionnaire

    def update(self, instance, validated_data):
        question_list_data = validated_data.get('question_list')
        question_class = QuestionSerializer()
        if question_list_data is not None:
            validated_data.pop('question_list')
            reverse_question_list = []
            for question_data in question_list_data:
                question_id = question_data.get('id')
                # 如果题目ID存在，说明该题目是要被更新的
                if question_id is not None:
                    question = Question.objects.get(id=question_id)
                    reverse_question_list.append(question_data.pop('id'))
                    # 因为question下面还有一层option需要处理，所以不能用原生的super().update方法
                    question_class.update(question, question_data)
                # 如果题目ID不存在，说明要新建一个题目
                else:
                    print(question_data)
                    question = question_class.create(question_data)
                    reverse_question_list.append(question.id)
            # 删除那些不在此次PUT的但保留在数据库中的question实体
            all_question = Question.objects.filter(questionnaire_id=instance.id)
            for question in all_question:
                if question.id not in reverse_question_list:
                    question.delete()
        # 更新非嵌套的内容
        super().update(instance, validated_data)
        return instance

    class Meta:
        model = Questionnaire
        fields = '__all__'


class QuestionnaireListSerializer(QuestionnaireBaseSerializer):
    class Meta:
        model = Questionnaire
        fields = '__all__'
        read_only_fields = ['id', 'title']


class AnswerDetailNestSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=False, required=False)

    class Meta:
        model = AnswerDetail
        exclude = ['sheet']


class AnswerSheetSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    respondent = UserDescSerializer(read_only=True)
    answer_list = AnswerDetailNestSerializer(many=True,
                                             required=False)

    class Meta:
        model = AnswerSheet
        fields = '__all__'

    def create(self, validated_data):
        answer_list_data = validated_data.get('answer_list')
        if answer_list_data is not None:
            validated_data.pop('answer_list')

        answer_sheet = AnswerSheet.objects.create(**validated_data)

        if answer_list_data is not None:
            for answer_list_detail in answer_list_data:
                answer_list_detail['id'] = None
                AnswerDetail.objects.create(sheet=answer_sheet,
                                            **answer_list_detail)
        return answer_sheet


class AnswerDetailReportSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    respondent = serializers.SerializerMethodField()
    ip = serializers.SerializerMethodField(read_only=True)
    modified_time = serializers.SerializerMethodField(read_only=True)
    ordering = serializers.SerializerMethodField(read_only=True)

    # ordering为0的原因是，方便前端修改增加序号等。
    def get_ordering(self, instance):
        return 0

    def get_ip(self, instance):
        return instance.sheet.ip

    def get_modified_time(self, instance):
        return instance.sheet.modified_time

    def get_respondent(self, instance):
        respondent = instance.sheet.respondent
        return UserDescSerializer(respondent).data

    class Meta:
        model = AnswerDetail
        fields = '__all__'


class OptionReportSerializer(serializers.ModelSerializer):
    number = serializers.SerializerMethodField()
    answer_list = serializers.SerializerMethodField()
    percent = serializers.SerializerMethodField()
    percent_string = serializers.SerializerMethodField()

    def get_number(self, instance):
        return instance.answer_detail_list.count()

    def get_percent(self, instance):
        option_num = instance.answer_detail_list.count()
        total = instance.question.get_answer_num()
        if total != 0:
            return int(option_num / total * 100 * 100) / 100
        else:
            return 0
        # total = AnswerSheet.objects.filter(question_id=instance.question_id). \
        #     values('ordering').distinct().count()
        # if total != 0:
        #     return int(instance.answer_list.count() / total * 100 * 100) / 100
        # else:
        #     return 0

    def get_percent_string(self, instance):
        option_num = instance.answer_detail_list.count()
        total = instance.question.get_answer_num()
        if total != 0:
            return format(option_num / total * 100, '.2f') + "%"
        else:
            return '0'

    def get_answer_list(self, instance):
        answer_list = instance.answer_detail_list.all()
        return AnswerDetailReportSerializer(answer_list, many=True).data

    class Meta:
        model = Option
        fields = '__all__'


class QuestionReportSerializer(QuestionBaseSerializer):
    option_list = serializers.SerializerMethodField()
    number = serializers.SerializerMethodField()

    def get_number(self, instance):
        return instance.get_answer_num()

    def get_option_list(self, instance):
        option_list = instance.option_list.all().order_by('ordering')
        return OptionReportSerializer(option_list, many=True).data

    class Meta:
        model = Question
        fields = '__all__'


class QuestionnaireReportSerializer(QuestionnaireBaseSerializer):
    question_list = serializers.SerializerMethodField()

    def get_question_list(self, instance):
        question_list = instance.question_list.all().order_by('ordering')
        return QuestionReportSerializer(question_list, many=True).data

    class Meta:
        model = Questionnaire
        fields = '__all__'


class OptionSignUPSerializer(serializers.ModelSerializer):
    number = serializers.SerializerMethodField()

    def get_number(self, instance):
        if instance.is_limit_answer:
            return instance.limit_answer_number - instance.get_answer_num()
        return 0

    class Meta:
        model = Option
        fields = '__all__'


class QuestionSignUPSerializer(serializers.ModelSerializer):
    option_list = serializers.SerializerMethodField()

    def get_option_list(self, instance):
        option_list = instance.option_list.all().order_by('ordering')
        return OptionSignUPSerializer(option_list, many=True).data

    class Meta:
        model = Question
        fields = '__all__'


class QuestionnaireSignUPSerializer(QuestionnaireBaseSerializer):
    number = serializers.SerializerMethodField()
    question_list = serializers.SerializerMethodField(required=False)

    def get_number(self, instance):
        if instance.is_limit_answer:
            return instance.limit_answer_number - instance.get_answer_num()
        return 0

    def get_question_list(self, instance):
        question_list = instance.question_list.all().order_by('ordering')
        return QuestionSignUPSerializer(question_list, many=True).data

    class Meta:
        model = Questionnaire
        fields = '__all__'
