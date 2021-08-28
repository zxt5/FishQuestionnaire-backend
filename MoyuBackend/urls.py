from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from questionnaire.views import QuestionnaireViewSet, QuestionViewSet, OptionViewSet, AnswerSheetViewSet, \
    QuestionOptionLogicRelationViewSet
from user_info.views import UserViewSet

router = DefaultRouter()
router.register(r'user', UserViewSet)
router.register(r'questionnaire', QuestionnaireViewSet)
router.register(r'question', QuestionViewSet)
router.register(r'option', OptionViewSet)
router.register(r'answer', AnswerSheetViewSet)
router.register(r'question_option_logic_relation', QuestionOptionLogicRelationViewSet)


urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/', include(router.urls)),  # 类视图的注册路由
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),  # rest_framewor
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),


]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
