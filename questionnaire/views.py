from rest_framework import filters
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from questionnaire.serializers import QuestionnaireDetailSerializer, QuestionnaireListSerializer, OptionSerializer, QuestionSerializer
from questionnaire.models import Questionnaire, Question, Option, AnswerSheet


class QuestionnaireViewSet(viewsets.ModelViewSet):
    queryset = Questionnaire.objects.all()
    serializer_class = QuestionnaireDetailSerializer

    def get_serializer_class(self):
        if self.action == 'list':
            return QuestionnaireListSerializer
        else:
            return QuestionnaireDetailSerializer


class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer


class OptionViewSet(viewsets.ModelViewSet):
    queryset = Option.objects.all()
    serializer_class = OptionSerializer
