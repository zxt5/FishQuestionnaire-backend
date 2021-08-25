from django.contrib.auth.models import User
from django.db import models
# Create your models here.
from django.utils import timezone


class Questionnaire(models.Model):
    title = models.CharField(max_length=255,verbose_name='问卷标题')
    content = models.TextField(verbose_name='问卷备注')
    author = models.ForeignKey(
        to=User,
        on_delete=models.CASCADE,
        verbose_name='问卷作者',
        related_name='questionnaire_list'
    )
    create_date = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    first_shared_date = models.DateTimeField(blank=True, null=True, verbose_name='初次发布时间')
    last_shared_date = models.DateTimeField(blank=True, null=True, verbose_name='最新发布时间')
    modify_date = models.DateTimeField(auto_now=True, verbose_name='最后修改时间')
    STATUS_IN_CHOICES = [
        ('deleted', '处于回收站中'),
        ('shared', '已发布'),
        ('closed', '未发布')
    ]
    status = models.CharField(
        max_length=50,
        choices=STATUS_IN_CHOICES,
        default='closed',
        verbose_name='问卷状态',
    )

    TYPE_IN_CHOICES = [
        ('normal', '普通问卷'),
        ('vote', '投票问卷'),
        ('exam', '考试问卷'),
        ('signup', '报名问卷'),
    ]
    type = models.CharField(
        max_length=50,
        choices=TYPE_IN_CHOICES,
        default='normal',
        verbose_name='问卷类型',
    )

    # answer_num = models.IntegerField(default=0, blank=True, verbose_name='回收问卷数')

    is_locked = models.BooleanField(default=False, verbose_name="访问是否需要密码")
    password = models.CharField(max_length=255, blank=True, default='', verbose_name="访问密码")

    # 只允许回答一次的前提是，is_required_login为True
    is_required_login = models.BooleanField(default=False, verbose_name="填写是否需要登录")
    is_only_answer_once = models.BooleanField(default=False, verbose_name='是否只允许回答一次')

    ORDER_TYPE_IN_CHOICES = [
        ('order', '按照题号排序显示'),
        ('disorder', '乱序显示')
    ]
    order_type = models.CharField(
        max_length=50,
        choices=ORDER_TYPE_IN_CHOICES,
        default='order',
        verbose_name='问卷题目显示方式',
    )

    # 用户填写后是否显示填写结果
    is_show_result = models.BooleanField(default=False, verbose_name="是否为填写者显示填写的统计结果")

    class Meta:
        ordering = ['-create_date']

    def __str__(self):
        return '_'.join([str(self.pk), self.title])


class Question(models.Model):
    questionnaire = models.ForeignKey(
        to='Questionnaire',
        on_delete=models.CASCADE,
        verbose_name='问卷ID',
        related_name='question_list'
    )
    title = models.CharField(max_length=255, verbose_name='题目标题')
    content = models.TextField(verbose_name='题目备注', blank=True)
    TYPE_IN_CHOICES = [
        ('single-choice', '单选题'),
        ('multiple-choice', '多选题'),
        ('completion', '填空题'),
        ('scoring', '评分题'),
    ]
    type = models.CharField(
        max_length=50,
        choices=TYPE_IN_CHOICES,
        verbose_name='问题类型',
    )
    ORDER_TYPE_IN_CHOICES = [
        ('order', '按照选项排序号正序显示'),
        ('disorder', '乱序显示')
    ]
    order_type = models.CharField(
        max_length=50,
        choices=ORDER_TYPE_IN_CHOICES,
        default='order',
        verbose_name='题目选项的显示方式',
    )
    modify_date = models.DateTimeField(auto_now=True, verbose_name='最后修改时间')

    ordering = models.PositiveIntegerField(verbose_name='题目序号')
    is_must_answer = models.BooleanField(default=False, verbose_name='是否必答')
    is_limit_answer = models.BooleanField(default=False, verbose_name='是否限制该题答题人数')
    limit_answer_number = models.IntegerField(default=0, verbose_name='该题限制的答题人数')

    # 当且仅当is_scoring存在时，题目分数才有意义，且后者可为null，即不计分
    is_scoring = models.BooleanField(default=False, verbose_name='是否评分')
    question_score = models.IntegerField(default=0, blank=True, null=True, verbose_name='题目分数')
    answer = models.TextField(blank=True, verbose_name='参考答案')

    def __str__(self):
        return '_'.join([str(self.pk), self.title])


class Option(models.Model):
    question = models.ForeignKey(
        to='Question',
        on_delete=models.CASCADE,
        verbose_name='题目ID',
        related_name='option_list'
    )
    title = models.CharField(max_length=255, verbose_name='选项标题')
    content = models.TextField(verbose_name='选项备注', blank=True)
    ordering = models.PositiveIntegerField(verbose_name='选项序号')


    # 投票功能
    is_limit_answer = models.BooleanField(default=False, verbose_name='是否限制该选项选择人数')
    limit_answer_number = models.IntegerField(default=0, verbose_name='该选项限制的选择人数')

    # 考试题
    is_answer_choice = models.BooleanField(default=False, verbose_name="该选项是否为答案")

    # 填空题
    score = models.DecimalField(null=True, blank=True, max_digits=4, decimal_places=1,
                                verbose_name="该选项/填空分数")
    answer = models.CharField(max_length=255,
                              blank=True,
                              verbose_name='参考答案')

    # 字段限制
    is_attr_limit = models.BooleanField(default=False, verbose_name="是否进行字段限制")
    attr_limit_type = models.CharField(max_length=255,blank=True, verbose_name="字段限制类型")
    validator_regex = models.CharField(max_length=255,
                                       blank=True,
                                       verbose_name='以正则表达形式式存储的字段检查正则式')
    is_must_answer = models.BooleanField(default=False, verbose_name='是否必答')

    def __str__(self):
        return '_'.join([str(self.pk), self.title])


class AnswerSheet(models.Model):
    questionnaire = models.ForeignKey(
        to='Questionnaire',
        on_delete=models.CASCADE,
        verbose_name='问卷',
        related_name='answer_sheet_list'
    )
    respondent = models.ForeignKey(
        to=User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name='答卷人',
        related_name='answer_sheet_list'
    )
    started_time = models.DateTimeField(default=timezone.now, verbose_name='回答开始时间')
    modified_time = models.DateTimeField(default=timezone.now, verbose_name='回答结束时间')
    ip = models.CharField(max_length=255, blank=True, verbose_name='用户IP地址')


class AnswerDetail(models.Model):
    sheet = models.ForeignKey(
        to='AnswerSheet',
        on_delete=models.CASCADE,
        verbose_name='答卷',
        related_name='answer_detail_list'
    )
    question = models.ForeignKey(
        to='Question',
        on_delete=models.CASCADE,
        verbose_name='题目',
        related_name='answer_detail_list'
    )
    option = models.ForeignKey(
        to='Option',
        on_delete=models.CASCADE,
        verbose_name='选项',
        related_name='answer_detail_list'
    )
    content = models.TextField(blank=True, null=True, verbose_name='选项填空内容')
