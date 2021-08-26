request = {'question_x_list':[59],'question_y_list':[60]}
cross_table = {}
pk=8
question_x_list = request['question_x_list']
question_y_list = request['question_y_list']
questionnaire = Questionnaire.objects.get(id=pk)
cross_table = {}
question_x = Question.objects.get(pk=question_x_list[0])
question_y = Question.objects.get(pk=question_y_list[0])

option_x_list = question_x.option_list.all()
option_y_list = question_y.option_list.all()

for option_x in option_x_list:
    x = option_x.title
    cross_table[x] = []

    for option_y in option_y_list:
        y = option_y.title
        answer_sheet_list = AnswerSheet.objects.filter(questionnaire=questionnaire)
        answer_sheet_x = answer_sheet_list.filter(answer_detail_list__option__id=option_x.id)
        answer_sheet_y = answer_sheet_list.filter(answer_detail_list__option__id=option_y.id)
        num = (answer_sheet_x & answer_sheet_y).count()
        # num = AnswerSheet.objects.filter(questionnaire=questionnaire) \
        #     .filter(Q(answer_detail_list__option__id=option_x.id) &
        #             Q(answer_detail_list__option__id=option_y.id)).count()
        print({y: num})
        cross_table[x].append({y: num})
