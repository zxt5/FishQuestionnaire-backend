from datetime import datetime

from django.utils import timezone

from rest_framework import filters, status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from questionnaire.serializers import QuestionnaireDetailSerializer, QuestionnaireListSerializer, OptionSerializer, \
    QuestionSerializer, AnswerSheetSerializer
from questionnaire.models import Questionnaire, Question, Option, AnswerSheet


class CreateListModelMixin(object):
    # 批量上传的插件
    def get_serializer(self, *args, **kwargs):
        """ if an array is passed, set serializer to many """
        if isinstance(kwargs.get('data', {}), list):
            kwargs['many'] = True
        return super(CreateListModelMixin, self).get_serializer(*args, **kwargs)


class QuestionnaireViewSet(viewsets.ModelViewSet):
    queryset = Questionnaire.objects.all()
    serializer_class = QuestionnaireDetailSerializer

    def get_serializer_class(self):
        if self.action == 'list':
            return QuestionnaireListSerializer
        else:
            return QuestionnaireDetailSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    # 开启/关闭 假设给的数据没问题
    @action(detail=True, methods=['put'],
            url_path='status', url_name='status')
    def set_status(self, request, pk=None):
        instance = Questionnaire.objects.get(pk=pk)
        instance.status = request.data.get('status')

        if instance.status == 'shared':
            if instance.first_shared_date is None:
                instance.first_shared_date = timezone.now()
            instance.last_shared_date = timezone.now()

        instance.save()
        serializer = QuestionnaireDetailSerializer(instance, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['post'],
            url_path='copy', url_name='copy')
    def copy(self, request):
        """”
            复制问卷信息，逐层地处理问卷、问题和选项
            问卷信息：置空分享状态（关闭）、初次分享和最近分享时间，创建时间改变
            问题信息：修改对应的问卷id，需要获取新的问卷ID做替换
            选项信息：同上
        """
        old_qn_pk = request.data.get('id')

        questionnaire_obj = Questionnaire.objects.get(pk=old_qn_pk)
        questionnaire_obj.pk = None
        questionnaire_obj.create_date = timezone.now()
        questionnaire_obj.first_shared_date = None
        questionnaire_obj.last_shared_date = None
        questionnaire_obj.modify_date = timezone.now()
        questionnaire_obj.status = 'closed'
        questionnaire_obj.save()

        question_list = list(Question.objects.filter(questionnaire_id=old_qn_pk))
        new_qn_pk = questionnaire_obj.pk

        for question in question_list:
            old_q_pk = question.pk

            question.pk = None
            question.modify_date = timezone.now()
            question.questionnaire_id = new_qn_pk
            question.save()

            new_q_pk = question.pk
            option_list = list(Option.objects.filter(question_id=old_q_pk))

            for option in option_list:
                option.pk = None
                option.question_id = new_q_pk
                option.save()

        serializer = QuestionnaireDetailSerializer(questionnaire_obj, context={'request': request})
        return Response(serializer.data)


class QuestionViewSet(CreateListModelMixin, viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    '''
        一个待解决的问题：这个新问题的ordering怎么办？
        1. 加到最后。获取当前问卷所有问题的最大的序号。
        2. 加到下一栏，问题之后的依次加1
        另一个问题：
    '''
    @action(detail=False, methods=['post'],
            url_path='copy', url_name='copy')
    def copy(self, request):
        old_q_pk = request.data.get('id')

        question = Question.objects.get(id=old_q_pk)
        question.pk = None
        question.modify_date = timezone.now()
        question.save()

        new_q_pk = question.pk
        option_list = list(Option.objects.filter(question_id=old_q_pk))

        for option in option_list:
            option.pk = None
            option.question_id = new_q_pk
            option.save()

        serializer = QuestionSerializer(question, context={'request': request})
        return Response(serializer.data)


class OptionViewSet(CreateListModelMixin, viewsets.ModelViewSet):
    queryset = Option.objects.all()
    serializer_class = OptionSerializer


class AnswerSheetViewSet(CreateListModelMixin, viewsets.ModelViewSet):
    queryset = AnswerSheet.objects.all()
    serializer_class = AnswerSheetSerializer

    def perform_create(self, serializer):
        max_ordering = 0
        entity = AnswerSheet.objects.order_by('-ordering').first()
        if entity is not None:
            max_ordering = entity.ordering + 1
        serializer.save(ordering=max_ordering)
