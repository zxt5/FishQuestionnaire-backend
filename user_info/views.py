from django.shortcuts import render

# Create your views here.
from django.contrib.auth.models import User
from django.utils import timezone

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from questionnaire.models import Questionnaire
from questionnaire.serializers import QuestionnaireListSerializer, QuestionnaireDetailSerializer
from user_info.permissions import IsSelfOrReadOnly
from user_info.serializers import UserRegisterSerializer


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserRegisterSerializer

    lookup_field = 'username'
    lookup_value_regex = "[^/]+"

    def get_permissions(self):
        if self.request.method == 'POST':
            self.permission_classes = [AllowAny]
        else:
            self.permission_classes = [IsAuthenticatedOrReadOnly, IsSelfOrReadOnly]

        return super().get_permissions()

    @action(detail=True, methods=['get'],
            url_path='questionnaire', url_name='questionnaire')
    def questionnaire(self, request, username=None):
        queryset = User.objects.get(username=username).questionnaire_list.exclude(status='deleted')
        serializer_context = {
            'request': request,
        }
        serializer = QuestionnaireListSerializer(queryset, many=True, context=serializer_context)
        return Response(serializer.data)

    @action(detail=True, methods=['get'],
            url_path='recycle', url_name='recycle')
    def recycle(self, request, username=None):
        queryset = User.objects.get(username=username).questionnaire_list.filter(status='deleted')
        serializer_context = {
            'request': request,
        }
        serializer = QuestionnaireListSerializer(queryset, many=True, context=serializer_context)
        return Response(serializer.data)

    @action(detail=True, methods=['put'],
            url_path='filter', url_name='filter')
    def filter(self, request, pk=None):
            tempquestionnaire = Questionnaire.objects.get(pk=pk)
            tempquestionnaire.status = request.data.get('status')

            if tempquestionnaire.status == 'shared' and tempquestionnaire.first_shared_date is None:
                tempquestionnaire.first_shared_date = timezone.now()

            tempquestionnaire.save()
            serializer = QuestionnaireDetailSerializer(tempquestionnaire, context={'request': request})
            return Response(serializer.data)