# from questionnaire.models import Questionnaire
#
# request = {'data':{'question_x_list':[59],'question_y_list':[60]}}
# cross_table = {}
# pk=8
# '''
# a = {"table_list" :
#         [
#             {
#                 "question_x":23,
#                 "question_y":24,
#                 "option_x_list":
#                                 [
#                                     {"id":241},
#                                     {"id":242}
#                                 ]
#             }
#         ]
#     }
#
# '''
# question_x_list = request['data']['question_x_list']
# question_y_list = request['data']['question_y_list']
# questionnaire = Questionnaire.objects.get(id=pk)
# answer_sheet_list = AnswerSheet.objects.filter(questionnaire=questionnaire)
# cross_table['table_list'] = []
# for pk_x in question_x_list:
#     for pk_y in question_y_list:
#         question_x = Question.objects.get(pk=pk_x)
#         question_y = Question.objects.get(pk=pk_y)
#         question_x_data = QuestionBaseSerializer(question_x).data
#         question_y_data = QuestionBaseSerializer(question_y).data
#         table = {}
#         cross_table['table_list'].append(table)
#         table['question_x'] = question_x_data
#         table['question_y'] = question_y_data
#         table['option_x_list'] = []
#         option_y_list_obj = question_y.option_list.all()
#         option_x_list = table['option_x_list'] = OptionBaseSerializer(question_x.option_list.all(),
#                                                                       many=True).data
#
#         for option_x in option_x_list:
#             option_x['option_y_list'] = OptionBaseSerializer(option_y_list_obj,
#                                                              many=True).data
#             for option_y in option_x['option_y_list']:
#                 option_y_id = option_y['id']
#                 option_x_id = option_x['id']
#                 answer_sheet_x = answer_sheet_list.filter(answer_detail_list__option__id=option_x_id)
#                 answer_sheet_y = answer_sheet_list.filter(answer_detail_list__option__id=option_y_id)
#                 option_y['num'] = (answer_sheet_x & answer_sheet_y).count()
# response = JsonResponse(cross_table)
# response.status_code = 200
# return response
