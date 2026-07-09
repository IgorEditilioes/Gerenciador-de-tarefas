from django.urls import path
from .views import (
    home,
    perfil,
    login_view,
    logout_view,
    board_view,
    update_task,
    delete_task,
    add_task,
    add_comment,
    add_subtask,
    update_subtask,
    toggle_subtask,
    delete_subtask,
    get_subtasks,
    create_board,
    get_responsaveis_board,
    buscar_responsaveis
)

urlpatterns = [
    # ======================
    # AUTENTICAÇÃO
    # ======================
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),

    # ======================
    # HOME
    # ======================
    path("", home, name="home"),

    # ======================
    # BOARD
    # ======================
    path("board/<int:board_id>/", board_view, name="board"),
    path("board/create/", create_board, name="create_board"),  # 👈 ADICIONADO

    # ======================
    # TASKS
    # ======================
    path("board/<int:board_id>/add-task/", add_task, name="add_task"),
    path("task/update/<int:task_id>/", update_task, name="update_task"),
    path("task/<int:task_id>/delete/", delete_task, name="delete_task"),

    # ======================
    # SUBTASKS
    # ======================
    path("task/<int:task_id>/subtasks/", get_subtasks, name="get_subtasks"),
    path("task/<int:task_id>/add-subtask/", add_subtask, name="add_subtask"),
    path("subtask/<int:subtask_id>/update/", update_subtask, name="update_subtask"),
    path("subtask/<int:subtask_id>/toggle/", toggle_subtask, name="toggle_subtask"),
    path("subtask/<int:subtask_id>/delete/", delete_subtask, name="delete_subtask"),

    # ======================
    # COMENTÁRIOS
    # ======================
    path("task/<int:task_id>/comment/", add_comment, name="add_comment"),


    # ======================
    # Perfil
    # ======================
    path('perfil/<int:id>', perfil, name="perfil"),

    path('buscar-responsaveis/', buscar_responsaveis, name='buscar_responsaveis'),
    path('get-responsaveis-setor/', get_responsaveis_board, name='get_responsaveis_setor'),
]