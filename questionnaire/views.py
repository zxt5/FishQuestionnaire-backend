import random
from datetime import datetime

import django_filters
import pytz
import xlwt
from django.db import transaction
from django.db.models import F, Count
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django_filters import BaseInFilter, CharFilter
from django_filters.rest_framework import DjangoFilterBackend, FilterSet
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from questionnaire.models import Questionnaire, Question, Option, AnswerSheet, QuestionOptionLogicRelation
from questionnaire.serializers import QuestionnaireDetailSerializer, QuestionnaireListSerializer, OptionSerializer, \
    QuestionSerializer, AnswerSheetSerializer, QuestionnaireReportSerializer, QuestionnaireSignUPSerializer, \
    QuestionBaseSerializer, OptionBaseSerializer, QuestionNestSerializer, QuestionOptionLogicRelationSerializer


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
    queryset = Questionnaire.objects.annotate(answer_num=Count('answer_sheet_list'))
    serializer_class = QuestionnaireDetailSerializer
    # permission_classes = [IsSelfOrReadOnly]

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

    @action(detail=True, methods=['get'],
            url_path='fill_or_preview', url_name='fill_or_preview')
    def fill_or_preview(self, request):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        # 如果没有，那就默认为False，就不管了
        if instance.order_type == 'disorder':
            user = request.user
            if not user.is_authenticated:
                return Response({"message": "需要用户登陆后才可查看具体内容"},
                                status.HTTP_401_UNAUTHORIZED)
            else:
                question_list = list(instance.question_list.all())
                random.seed(request.user.id)
                random.shuffle(question_list)
                qs = QuestionNestSerializer(question_list, many=True).data
                serializer_data = serializer.data
                serializer_data['question_list'] = qs
            return Response(serializer_data)
        return Response(serializer.data)

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
        questionnaire_obj.title = questionnaire_obj.title + '_副本'
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
            questionnaire_list = self.queryset.exclude(status='deleted') \
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
    @action(detail=False, methods=['put'],
            url_path='delete-all-answer', url_name='delete-all-answer')
    def delete_all_answer(self, request):

        pk = request.data.get('id')
        questionnaire = Questionnaire.objects.get(id=pk)

        # 删除该问卷名下的所有答卷
        answer_list = AnswerSheet.objects.filter(questionnaire=questionnaire)
        answer_list.delete()
        # questionnaire.answer_num = 0

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
            url_path='export-xls', url_name='export-xls')
    def export_xls(self, request, pk=None):
        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename=' + 'Questionnaire_' + str(pk) + '.xls'
        workbook = xlwt.Workbook(encoding='utf-8')
        worksheet = workbook.add_sheet('origin_data')
        font_style = xlwt.XFStyle()

        # 确定额外的信息
        columns = ['respondent__username', 'modified_time']
        trans_dic = {'respondent__username': '用户名', 'modified_time': '提交答题时间'}
        # 获取答卷表单，确定顺序不变
        answer_list = AnswerSheet.objects.filter(questionnaire_id=pk).order_by('modified_time')
        ans_list = answer_list.values_list('respondent__username', 'modified_time')

        # 首先填写额外的信息

        for col_num in range(len(columns)):
            row_num = 0
            worksheet.write(row_num, col_num, trans_dic[columns[col_num]], font_style)
            row_num += 1
            for ans in ans_list:
                data = ans[col_num]
                if isinstance(data, datetime):
                    data = data.astimezone(pytz.timezone('Asia/Shanghai')).strftime(
                        '%Y-%m-%d %H:%M:%S')
                worksheet.write(row_num, col_num, data, font_style)
                row_num = row_num + 1

        col_num = len(columns)

        question_list = Question.objects.filter(questionnaire_id=pk).order_by('ordering')
        question_type_dic = {'multiple-choice': '多选题', 'single-choice': '单选题', 'completion': '填空题',
                             'scoring': '评分题'}

        option_pos_dic = {}
        for question in question_list:
            option_list = Option.objects.filter(question=question).order_by('ordering')
            for option in option_list:
                column_str = ''.join([str(question.ordering), '.',
                                      question.title, ':', option.title, '[',
                                      question_type_dic.get(question.type, '未知题目类型'), ']'])
                worksheet.write(0, col_num, column_str, font_style)
                option_pos_dic[option.pk] = col_num
                # option_pos_dic.update({option.pk, col_num})
                col_num = col_num + 1
        # 一行行填写答案
        row_num = 1
        for answer in answer_list:
            answer_detail_list = answer.answer_detail_list.all()
            for answer_detail in answer_detail_list:
                if answer_detail.content:
                    worksheet.write(row_num, option_pos_dic.get(answer_detail.option.id),
                                    answer_detail.content, font_style)
                else:
                    worksheet.write(row_num, option_pos_dic.get(answer_detail.option.id),
                                    1, font_style)
            row_num += 1

        workbook.save(response)
        return response

    # 交叉分析接口
    @action(detail=True, methods=['put'],
            url_path='cross-analysis', url_name='cross-analysis')
    def cross_analysis(self, request, pk=None):
        question_x_list = request.data['question_x_list']
        question_y_list = request.data['question_y_list']
        questionnaire = Questionnaire.objects.get(id=pk)
        answer_sheet_list = AnswerSheet.objects.filter(questionnaire=questionnaire)
        cross_table = {'table_list': []}
        for pk_x in question_x_list:
            for pk_y in question_y_list:
                question_x = Question.objects.get(pk=pk_x)
                question_y = Question.objects.get(pk=pk_y)
                question_x_data = QuestionBaseSerializer(question_x).data
                question_y_data = QuestionBaseSerializer(question_y).data
                table = {}
                cross_table['table_list'].append(table)
                table['question_x'] = question_x_data
                table['question_y'] = question_y_data
                table['option_x_list'] = []
                option_y_list_obj = question_y.option_list.all()
                option_x_list = table['option_x_list'] = OptionBaseSerializer(question_x.option_list.all(),
                                                                              many=True).data

                answer_sheet_question_y = answer_sheet_list.filter(answer_detail_list__question_id=question_y.id)

                for option_x in option_x_list:
                    option_x['option_y_list'] = OptionBaseSerializer(option_y_list_obj,
                                                                     many=True).data
                    option_x_id = option_x['id']
                    answer_sheet_x = answer_sheet_list.filter(answer_detail_list__option__id=option_x_id)
                    option_x['num'] = (answer_sheet_x & answer_sheet_question_y).count()
                    for option_y in option_x['option_y_list']:
                        option_y_id = option_y['id']
                        answer_sheet_y = answer_sheet_list.filter(answer_detail_list__option__id=option_y_id)
                        option_y['num'] = (answer_sheet_x & answer_sheet_y).count()
                        if option_x['num'] != 0:
                            option_y['percent'] = int(option_y['num'] / option_x['num'] * 100 * 100) / 100
                        else:
                            option_y['percent'] = 0

                        option_y['percent_string'] = format(option_y['percent'], '.2f') + "%"

        response = JsonResponse(cross_table)
        response.status_code = 200
        return response

    @action(detail=True, methods=['get'],
            url_path='sign-up', url_name='sign-up',
            serializer_class=QuestionnaireSignUPSerializer)
    def sign_up_detail(self, request, pk=None):
        questionnaire = Questionnaire.objects.get(pk=pk)
        serializer = QuestionnaireSignUPSerializer(questionnaire,
                                                   context={'request': request})

        return Response(serializer.data,
                        status.HTTP_200_OK)

    # @action(detail=True, methods=['get'],
    #         url_path='sign-up', url_name='sign-up',
    #         serializer_class=QuestionnaireSignUPSerializer)
    #


class QuestionViewSet(CreateListModelMixin, viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    # permission_classes = [IsSelfOrReadOnly]

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
            first_question = Question.objects.filter(questionnaire=questionnaire). \
                order_by('-ordering').first()
            if first_question is None:
                max_ordering = 0
            else:
                max_ordering = first_question.ordering
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

    # permission_classes = [IsSelfOrReadOnly]

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

    @transaction.atomic(durable=True)
    def create(self, request, *args, **kwargs):
        # 锁住限额的问题，直到事务结束，下一个事务进来无法获取会卡在这里，达成了阻塞并发的目的
        questionnaire = Questionnaire.objects.select_for_update().get(pk=request.data['questionnaire'])

        # 判断问题是否限额
        if questionnaire.is_limit_answer:
            total_questionnaire_answer_num = questionnaire.get_answer_num()
            delta = questionnaire.limit_answer_number - total_questionnaire_answer_num
            if delta <= 0:
                return Response({"message": "限额已满！无法提交！"},
                                status=status.HTTP_400_BAD_REQUEST)

        # 判断选项是否限额
        answer_list = request.data['answer_list']
        for answer in answer_list:
            # 锁住限额的问题，直到事务结束，下一个事务进来无法获取会卡在这里，达成了阻塞并发的目的
            option = Option.objects.select_for_update().get(pk=answer['option'])
            if option.is_limit_answer:
                delta = option.limit_answer_number - option.get_answer_num()
                if delta <= 0:
                    return Response({"message": "限额已满！无法提交！"},
                                    status=status.HTTP_400_BAD_REQUEST)
        # 数据更新
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if self.request.user.is_authenticated:
            serializer.save(respondent=self.request.user)
        else:
            serializer.save()

        questionnaire_data = QuestionnaireDetailSerializer(questionnaire, context={'request': request}).data
        headers = self.get_success_headers(serializer.data)

        # 如果为考试题，看是否进行评测
        if questionnaire.type == 'exam':
            question_list = questionnaire_data['question_list']
            questionnaire_data['is_show_answer_detail'] = False
            # 如果里面存在评测题，显示答案详情让用户回答
            for question in question_list:
                if question['is_scoring']:
                    questionnaire_data['is_show_answer_detail'] = True
                    break
            # 显示问题详情。
            if questionnaire_data['is_show_answer_detail']:
                # 判断是否乱序
                if questionnaire_data['order_type'] == 'disorder':
                    user = request.user
                    if not user.is_authenticated:
                        return Response({"message": "需要用户登陆后才可查看具体内容"},
                                        status.HTTP_401_UNAUTHORIZED)
                    else:
                        random.seed(request.user.id)
                        random.shuffle(question_list)
                # 判断每一个题目的得分，每个选项是否回答过
                if questionnaire_data['is_show_answer_detail']:
                    answer_list = request.data['answer_list']
                    questionnaire_data['total_score'] = 0
                    questionnaire_data['user_get_score'] = 0
                    questionnaire_data['total_score_question_cnt'] = 0
                    questionnaire_data['user_get_score_question_cnt'] = 0
                    for question in question_list:
                        # 如果是参与评分
                        if question['is_scoring']:  # 判断用户是否答了这道题
                            option_list = question['option_list']
                            # 默认回答正确,获得所有分数
                            question['is_user_answer_right'] = True
                            question['user_get_score'] = question['question_score']
                            questionnaire_data['total_score'] += question['question_score']
                            questionnaire_data['user_get_score'] += question['question_score']
                            questionnaire_data['total_score_question_cnt'] += 1
                            questionnaire_data['user_get_score_question_cnt'] += 1
                            for option in option_list:
                                # 默认没有回答过
                                option['is_user_answer'] = False
                                index = 0
                                for answer in answer_list:
                                    if str(answer['option']) == str(option['id']):
                                        # 如果回答过
                                        option['is_user_answer'] = True
                                        if question['type'] == 'single-choice':
                                            question['answer_ordering'] = option['ordering']
                                        content = answer.get('content', None)
                                        option['user_answer_content'] = content
                                        del answer_list[index]
                                        # 跳出循环即可
                                        break
                                    index += 1
                                if question['is_user_answer_right']:
                                    # 如果是选择题，需要看每个选项。如果选项被选了，但不是正确答案或者选项没被选，但是是正确选项，回答错误。
                                    if question['type'] == 'single-choice' or question['type'] == 'multiple-choice':
                                        if ((option['is_answer_choice'] and (not option['is_user_answer'])) or
                                                ((not option['is_answer_choice']) and option['is_user_answer'])):
                                            question['is_user_answer_right'] = False
                                            question['user_get_score'] = 0
                                            questionnaire_data['user_get_score'] -= question['question_score']
                                            questionnaire_data['user_get_score_question_cnt'] -= 1
                                    # 如果是填空题，很简单，首先看用户是否回答过，如果有有，那再看只用看用户的回答是否和答案相同
                                    elif question['type'] == 'completion':
                                        if (not option['is_user_answer']) or \
                                                option['answer'] != option['user_answer_content']:
                                            question['is_user_answer_right'] = False
                                            question['user_get_score'] = 0
                                            questionnaire_data['user_get_score'] -= question['question_score']
                                            questionnaire_data['user_get_score_question_cnt'] -= 1

                            question['option_list'] = option_list
                total = questionnaire_data['total_score_question_cnt']
                get_score_cnt = questionnaire_data['user_get_score_question_cnt']
                questionnaire_data['correct_rate'] = format(get_score_cnt / total * 100, '.2f') + "%"
                questionnaire_data['question_list'] = question_list

        return Response(questionnaire_data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=False, methods=['put'],
            url_path='check_answer', url_name='check_answer',
            serializer_class=QuestionnaireSignUPSerializer)
    def check_answer(self, request):
        user = request.user
        has_answer = False
        pk = request.data['id']
        questionnaire = Questionnaire.objects.get(id=pk)
        if not user.is_authenticated:
            return Response({"message": "用户首先应该登录"}, status=status.HTTP_401_UNAUTHORIZED)
        respondent_id_list = list(questionnaire.answer_sheet_list.values("respondent").distinct())
        for respondent in respondent_id_list:
            if user.id == respondent["respondent"]:
                has_answer = True
                break
        if has_answer:
            return Response({"has_answer": True}, status=status.HTTP_200_OK)
        else:
            return Response({"has_answer": False}, status=status.HTTP_200_OK)


class QuestionOptionLogicRelationViewSet(CreateListModelMixin, viewsets.ModelViewSet):
    queryset = QuestionOptionLogicRelation.objects.all()
    serializer_class = QuestionOptionLogicRelationSerializer

    @transaction.atomic
    @action(detail=False, methods=['put'],
            url_path='edit', url_name='edit')
    def edit(self, request):
        question_id = request.data['question_id']
        relation_list = request.data['relation_list']
        QuestionOptionLogicRelation.objects.filter(
            option__question_id=question_id
        ).delete()
        if relation_list:
            for relation in relation_list:
                obj = QuestionOptionLogicRelation.objects.create(option_id=relation['option'],
                                                                 question_id=relation['question'])
                obj.save()
        questionnaire = Questionnaire.objects.get(question_list__id=question_id)
        questionnaire_data = QuestionnaireDetailSerializer(questionnaire, context={'request': request}).data
        return Response(questionnaire_data, status.HTTP_200_OK)

    @action(detail=False, methods=['put'],
            url_path='delete_list', url_name='delete_list')
    def delete_list(self, request):
        delete_list = request.data['delete_list']
        for obj_data in delete_list:
            obj = QuestionOptionLogicRelation.objects.get(question=obj_data['question'], option=obj_data['option'])
            obj.delete()
        return Response(status.HTTP_200_OK)

    @action(detail=False, methods=['put'],
            url_path='delete_all', url_name='delete_all')
    def delete_all(self, request):
        id = request.data['id']
        type = request.data['type']
        if type == 'questionnaire':
            QuestionOptionLogicRelation.objects.filter(
                option__questionnaire_id=id
            ).delete()
        if type == 'question':
            QuestionOptionLogicRelation.objects.filter(
                option__question_id=id
            ).delete()

        return Response(status.HTTP_200_OK)
