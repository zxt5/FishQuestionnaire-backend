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


class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer


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
