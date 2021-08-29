from django.contrib.auth.models import User
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from user_info.validator import SetCustomErrorMessagesMixin


class UserDescSerializer(serializers.ModelSerializer):
    # url = serializers.HyperlinkedIdentityField(view_name='user-detail', lookup_field='username')

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            # 'url',
        ]


class UserRegisterSerializer(SetCustomErrorMessagesMixin, serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='user-detail', lookup_field='username')

    class Meta:
        model = User
        fields = [
            'url',
            'id',
            'username',
            'password'
        ]
        extra_kwargs = {
            'password': {'write_only': True}
        }
        custom_error_messages_for_validators = {
            'username': {
                UniqueValidator: _('该用户名已被注册'),
                UnicodeUsernameValidator: _('用户名最长可包含150个字符，且仅可包含数字、字母或者@.+-_特殊字符')
            }
        }

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

    def update(self, instance, validated_data):
        if 'password' in validated_data:
            password = validated_data.pop('password')
            instance.set_password(password)
        return super().update(instance, validated_data)