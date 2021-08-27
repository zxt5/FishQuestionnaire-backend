from questionnaire.models import Option, Question


class Template:

    def create_option(self, question, option_title_list):
        for ordering in range(len(option_title_list)):
            option = Option.objects.create(
                title=option_title_list[ordering],
                ordering=ordering + 1,
                question_id=question.id
            )
            option.save()

    def create_question(self, title, ordering, type, instance):
        question = Question.objects.create(
            title=title,
            questionnaire_id=instance.id,
            type=type,
            ordering=ordering
        )
        question_instance = question.save()
        if type == 'completion':
            option = Option.objects.create(
                title='填空题小空',
                ordering='1',
                question_id=question_instance.id,
            )
            option.save()
        elif type == 'position':
            option = Option.objects.create(
                title='定位题小空',
                ordering='1',
                question_id=question_instance.id,
            )
            option.save()
        return question

    def vote(self, instance):
        question = self.create_question("投票单选择题", "single-choice", instance)
        option_title_list = ["第一个选项", "第二个选项"]
        self.create_option(question, option_title_list)

    def signup(self, instance):
        self.create_question("姓名", 1, "completion", instance)
        self.create_question("手机号", 2, "completion", instance)
        question = self.create_question("报名单选题", "single-choice", instance)
        option_title_list = ["第一个选项", "第二个选项"]
        self.create_option(question, option_title_list)

    def exam(self, instance):
        self.create_question("姓名", 1, "completion", instance)
        self.create_question("学号", 2, "completion", instance)

    def epidemic_check_in(self, instance):
        self.create_question("姓名", 1, "completion", instance)
        self.create_question("学号", 2, "completion", instance)
        temp_question = self.create_question("体温范围", 3, "single-choice", instance)
        self.create_option(temp_question, ['正常(37.2°及以下)',
                                           '37.3-38',
                                           '38.1-38.5',
                                           '38.6-39',
                                           '39.1-40'
                                           ]
                           )
        is_high_risk_question = self.create_question("有无去过高风险地区", 4, "single-choice", instance)
        self.create_option(is_high_risk_question, ['无', '有'])
        is_health = self.create_question("有无新冠症状", 5, "single-choice", instance)
        self.create_option(is_health, ['无', '有'])
        self.create_question("定位题", 6, "position", instance)
