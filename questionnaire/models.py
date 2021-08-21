from django.db import models
from django.contrib.auth.models import User
# Create your models here.


class Questionnaire(models.Model):
    author = models.ForeignKey(
        User,
        null=False,
        on_delete=models.CASCADE,
        related_name='questionnaire_list',
        verbose_name='问卷创建者'
    )
