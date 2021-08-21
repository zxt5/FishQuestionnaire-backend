from rest_framework import filters
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from questionnaire.serializers import QuestionnaireDetailSerializer, QuestionnaireListSerializer
from questionnaire.models import Questionnaire

class QuestionnaireViewSet(viewsets.ModelViewSet):
    queryset = Questionnaire.objects.all()
    serializer_class = QuestionnaireDetailSerializer

    def get_serializer_class(self):
        if self.action == 'list':
            return QuestionnaireListSerializer
        else:
            return QuestionnaireDetailSerializer
