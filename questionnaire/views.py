from datetime import datetime

from django.db.models import F
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

    filter_backends = [filters.SearchFilter]
    search_fields = ['title']

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


    '''
        '-created_time', 'created_time', '-last_shared_date', 'last_shared_date',
        回收量？!
        '-answer_num'
    '''
    @action(detail=False, methods=['get'],
            url_path='sort', url_name='sort')
    def sort(self, request):
        keyword = request.data.get('keyword')
        questionnaire_list = Questionnaire.objects.exclude(status='deleted')\
            .order_by(keyword)
        serializers = QuestionnaireListSerializer(questionnaire_list,context={'request': request}, many=True)
        return Response(serializers, status.HTTP_200_OK)


class QuestionViewSet(CreateListModelMixin, viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    '''
        删除之前更新list，使其ordering-1。 删除问题的同时，选项也该被删除。
        如果更新时，其实例的ordering改变了，那么就找出被交换的另一方，进行属性更新
        创建之前，所有在这之后的实例的ordering+1
        如果复制问题，新的问题出现在原问题的下面，其余问题的ordering+1
    '''
    def perform_destroy(self, instance):
        question_list = Question.objects.filter(questionnaire_id=instance.questionnaire_id). \
            filter(ordering__gte=instance.ordering)
        question_list.update(ordering=F('ordering') - 1)

        instance.delete()

    def perform_update(self, serializer):
        old_ordering = serializer.instance.ordering
        instance = serializer.save()
        new_ordering = instance.ordering
        if old_ordering != new_ordering:
            exchanged_question = Question.objects.filter(questionnaire_id=instance.questionnaire_id). \
                exclude(id=instance.id).get(ordering=new_ordering)
            exchanged_question.ordering = old_ordering
            exchanged_question.save()

    def perform_create(self, serializer):
        instance = serializer.save()
        questionnaire_id = instance.questionnaire_id
        ordering = instance.ordering
        question_list = Question.objects.filter(questionnaire_id=questionnaire_id). \
            filter(ordering__gte=ordering).exclude(id=instance.id)
        question_list.update(ordering=F('ordering') + 1)

    @action(detail=False, methods=['post'],
            url_path='copy', url_name='copy')
    def copy(self, request):
        old_q_pk = request.data.get('id')

        question = Question.objects.get(id=old_q_pk)
        question.pk = None

        question_list = Question.objects.filter(questionnaire_id=question.questionnaire_id). \
            filter(ordering__gt=question.ordering)
        question_list.update(ordering=F('ordering') + 1)
        question.ordering = question.ordering+1
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

    def perform_destroy(self, instance):
        option_list = Option.objects.filter(question_id=instance.question_id). \
            filter(ordering__gte=instance.ordering)
        option_list.update(ordering=F('ordering') - 1)
        instance.delete()

    def perform_update(self, serializer):
        old_ordering = serializer.instance.ordering
        instance = serializer.save()
        new_ordering = instance.ordering
        if old_ordering != new_ordering:
            exchanged_option = Option.objects.filter(question_id=instance.question_id). \
                exclude(id=instance.id).get(ordering=new_ordering)
            exchanged_option.ordering = old_ordering
            exchanged_option.save()

    def perform_create(self, serializer):
        instance = serializer.save()
        question_id = instance.question_id
        ordering = instance.ordering
        option_list = Question.objects.filter(question_id=question_id). \
            filter(ordering__gte=ordering).exclude(id=instance.id)
        option_list.update(ordering=F('ordering') + 1)


class AnswerSheetViewSet(CreateListModelMixin, viewsets.ModelViewSet):
    queryset = AnswerSheet.objects.all()
    serializer_class = AnswerSheetSerializer

    def perform_create(self, serializer):
        max_ordering = 1
        questionnaire_id = serializer.data[0].get('questionnaire')
        entity = AnswerSheet.objects.filter(questionnaire_id=questionnaire_id).\
            order_by('-ordering').first()
        if entity is not None:
            max_ordering = entity.ordering + 1
        questionnaire = Questionnaire.objects.get(id=questionnaire_id)
        questionnaire.answer_num = max_ordering
        questionnaire.save()
        serializer.save(ordering=max_ordering)
