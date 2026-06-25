from django.urls import path
from .views import home, login_view, logout_view, board_view

urlpatterns = [
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("board/<int:board_id>/", board_view, name="board"),
    path("", home, name="home"),
]