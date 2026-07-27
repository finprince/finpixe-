from django.urls import path
from .views import KikiChatView

urlpatterns = [
    path('chat/', KikiChatView.as_view(), name='kiki-chat'),
    path('investigate/', KikiChatView.as_view(), name='kiki-investigate'),
]
