from questionnaire.models import Questionnaire
from rest_framework import serializers

class QuestionnaireBaseSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)


class QuestionnaireDetailSerializer(QuestionnaireBaseSerializer):

    class Meta:
        model = Questionnaire
        fields = '__all__'
        '''
        exclude = [
            'who_like'
        ]
        '''

class QuestionnaireListSerializer(QuestionnaireBaseSerializer):

    class Meta:
        model = Questionnaire
        fields = [
            'id',
            'title'
        ]
        read_only_fields = ['id', 'title']

