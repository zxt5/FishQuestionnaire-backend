import django_filters
import xlwt
from django_filters import BaseInFilter, CharFilter
from django_filters.rest_framework import DjangoFilterBackend, FilterSet
from rest_pandas import PandasView, PandasExcelRenderer, PandasViewSet, PandasCSVRenderer

from django.db.models import F
from django.utils import timezone

from rest_framework import filters, status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from questionnaire.serializers import QuestionnaireDetailSerializer, QuestionnaireListSerializer, OptionSerializer, \
    QuestionSerializer, AnswerSheetSerializer, QuestionReportSerializer, QuestionnaireReportSerializer
from questionnaire.models import Questionnaire, Question, Option, AnswerSheet


class CreateListModelMixin(object):
    # 批量上传的插件
    def get_serializer(self, *args, **kwargs):
        """ if an array is passed, set serializer to many """
        if isinstance(kwargs.get('data', {}), list):
            kwargs['many'] = True
        return super(CreateListModelMixin, self).get_serializer(*args, **kwargs)


class CharInFilter(BaseInFilter, CharFilter):
    pass


class QuestionnaireFilter(FilterSet):
    status = CharInFilter(field_name='status', lookup_expr='in')
    title = django_filters.CharFilter(field_name='title', lookup_expr='icontains')

    class Meta:
        model = Questionnaire
        fields = ['title', 'status']


class QuestionnaireViewSet(viewsets.ModelViewSet):
    queryset = Questionnaire.objects.all()
    serializer_class = QuestionnaireDetailSerializer

    filter_backends = [DjangoFilterBackend]
    filterset_class = QuestionnaireFilter
    # filter_backends = [filters.SearchFilter]
    # search_fields = ['title']

    # def get_queryset(self):
    #     user = self.request.user
    #     if user.is_authenticated:
    #         return Questionnaire.objects.filter(author=user)
    #     else:
    #         return Questionnaire.objects.none()


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
        '-create_date', 'create_date', 创建时间
         '-last_shared_date', 'last_shared_date', 最后分享时间
        '-answer_num' 回收的问卷数
    '''
    @action(detail=False, methods=['put'],
            url_path='sort', url_name='sort')
    def sort(self, request):
        user = request.user
        if user.is_authenticated:
            keyword = request.data.get('keyword')
            questionnaire_list = Questionnaire.objects.exclude(status='deleted') \
                .filter(author=user).order_by(keyword)
            serializers = QuestionnaireListSerializer(questionnaire_list, context={'request': request}, many=True)
            return Response(serializers.data, status.HTTP_200_OK)
        else:
            return Response({"message": "仅登录用户可进行排序"}, status=status.HTTP_401_UNAUTHORIZED)

    @action(detail=False, methods=['put'],
            url_path='search', url_name='search')
    def search(self, request):
        user = request.user
        if user.is_authenticated:
            keyword = request.data.get('keyword')
            questionnaire_list = Questionnaire.objects.exclude(status='deleted') \
                .filter(author=user).filter(title__icontains=keyword)
            serializers = QuestionnaireListSerializer(questionnaire_list, context={'request': request}, many=True)
            return Response(serializers.data, status.HTTP_200_OK)
        else:
            return Response({"message": "仅登录用户可进行搜索"}, status=status.HTTP_401_UNAUTHORIZED)


    # 删除指定id问卷的所有答卷
    @action(detail=False, methods=['delete'],
            url_path='delete-all-answer', url_name='delete-all-answer')
    def delete_all_answer(self, request):

        pk = request.data.get('id')
        questionnaire = Questionnaire.objects.get(id=pk)

        # 删除该问卷名下的所有答卷
        answer_list = AnswerSheet.objects.filter(questionnaire=questionnaire)
        answer_list.delete()
        questionnaire.answer_num = 0

        serializers = QuestionnaireDetailSerializer(questionnaire, context={'request': request})
        return Response(serializers.data, status.HTTP_200_OK)

    # 获取指定id问卷的分析内容
    @action(detail=True, methods=['get'],
            url_path='report', url_name='report',
            serializer_class=QuestionnaireReportSerializer)
    def report(self, request, pk=None):
        questionnaire = Questionnaire.objects.get(id=pk)
        count = AnswerSheet.objects.filter(questionnaire=questionnaire).count()
        if count == 0:
            no_answer_message = '此问卷暂时还没有答卷，请先回收答卷'
            return Response({'message': no_answer_message},
                            status.HTTP_400_BAD_REQUEST)
        else:
            serializer = QuestionnaireReportSerializer(questionnaire,
                                                       context={'request': request})

            return Response(serializer.data,
                            status.HTTP_200_OK)

    # 导出excel
    @action(detail=True, methods=['get'],
            url_path='export-xls',url_name='export-xls')
    def export_xls(self, request, pk=None):
        response = Response(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename=Expenses' + \
            str(timezone.now()) + '.xls'
        workbook = xlwt.Workbook(encoding='utf-8')
        worksheet = workbook.add_sheet('origin_data')
        row_num = 0
        font_style = xlwt.XFStyle()
        font_style.font.bold = True

        columns = ['回收问卷序号', 'IP', '题目描述', '题目序号', '选项描述', '选项序号']
        for col_num in range(len(columns)):
            worksheet.write(row_num, col_num, columns[col_num], font_style)

        rows = AnswerSheet.objects.filter(questionnaire_id=pk)


    # # 导出Excel
    # def get_renderers(self):
    #     if self.action == 'exportxls':
    #         renderer_classes = [PandasExcelRenderer]
    #         return [renderer() for renderer in renderer_classes]
    #     else:
    #         return super().get_renderers()
    #
    #
    # @action(detail=True)
    # def exportxls(self, request, pk):
    #     queryset = Questionnaire.objects.filter(id=pk)
    #     return Response(
    #         QuestionnaireExportSerializer(
    #             queryset, many=True,
    #             context={'request': request}).data, status.HTTP_200_OK)
    #     # return Response(QuestionnaireExportSerializer(queryset, many=True).data, status.HTTP_200_OK)


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
        # 此时instance还是老的，还未更新
        old_ordering = serializer.instance.ordering
        # 此时的instance中的数据已经被更新了
        instance = serializer.save()
        new_ordering = instance.ordering
        if old_ordering != new_ordering:
            if old_ordering < new_ordering:
                question_list = Question.objects.filter(questionnaire_id=instance.questionnaire_id). \
                    filter(ordering__lte=new_ordering).filter(ordering__gt=old_ordering). \
                    exclude(id=instance.id)
                question_list.update(ordering=F('ordering') - 1)

            else:
                question_list = Question.objects.filter(questionnaire_id=instance.questionnaire_id). \
                    filter(ordering__lt=old_ordering).filter(ordering__gte=new_ordering). \
                    exclude(id=instance.id)
                question_list.update(ordering=F('ordering') + 1)

    def perform_create(self, serializer):
        ordering = serializer.validated_data.get('ordering', None)
        if ordering is not None:
            instance = serializer.save()
            questionnaire_id = instance.questionnaire_id
            ordering = instance.ordering
            question_list = Question.objects.filter(questionnaire_id=questionnaire_id). \
                filter(ordering__gte=ordering).exclude(id=instance.id)
            question_list.update(ordering=F('ordering') + 1)
        else:
            questionnaire = serializer.validated_data.get('questionnaire', None)
            max_ordering = Question.objects.filter(questionnaire=questionnaire).\
                order_by('-ordering').first().ordering
            if max_ordering is None:
                max_ordering = 0
            max_ordering = max_ordering + 1
            serializer.save(ordering=max_ordering)


    @action(detail=False, methods=['post'],
            url_path='copy', url_name='copy')
    def copy(self, request):
        old_q_pk = request.data.get('id')

        question = Question.objects.get(id=old_q_pk)
        question.pk = None

        question_list = Question.objects.filter(questionnaire_id=question.questionnaire_id). \
            filter(ordering__gt=question.ordering)
        question_list.update(ordering=F('ordering') + 1)
        question.ordering = question.ordering + 1
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
        entity = AnswerSheet.objects.filter(questionnaire_id=questionnaire_id). \
            order_by('-ordering').first()
        if entity is not None:
            max_ordering = entity.ordering + 1
        questionnaire = Questionnaire.objects.get(id=questionnaire_id)
        questionnaire.answer_num = max_ordering
        questionnaire.save()
        serializer.save(ordering=max_ordering)
