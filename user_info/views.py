from django.shortcuts import render

# Create your views here.
from django.contrib.auth.models import User

from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly

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