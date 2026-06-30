from django.urls import path
from .views import home, login_view, logout_view, board_view, update_task, add_comment

urlpatterns = [
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("board/<int:board_id>/", board_view, name="board"),
    path("task/update/<int:task_id>/", update_task, name="update_task"),
    path("task/<int:task_id>/comment/", add_comment, name="add_comment"),
    path("", home, name="home"),
    
]