from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
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
    buscar_responsaveis,
    update_task_status,
    get_notificacoes,
    marcar_notificacao_lida,
    marcar_todas_notificacoes_lidas,
    open_task_direct,
    get_task_board,
    upload_anexo,
    delete_anexo,
    get_anexos
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
    path("board/create/", create_board, name="create_board"),

    # ======================
    # TASKS
    # ======================
    path("board/<int:board_id>/add-task/", add_task, name="add_task"),
    path("task/update/<int:task_id>/", update_task, name="update_task"),
    path("task/<int:task_id>/delete/", delete_task, name="delete_task"),
    path("task/<int:task_id>/update-status/", update_task_status, name="update_task_status"),

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
    # PERFIL
    # ======================
    path('perfil/<int:id>/', perfil, name="perfil"),

    # ======================
    # RESPONSÁVEIS (API)
    # ======================
    path('buscar-responsaveis/', buscar_responsaveis, name='buscar_responsaveis'),
    path('get-responsaveis-board/<int:board_id>/', get_responsaveis_board, name='get_responsaveis_board'),

    # ======================
    # NOTIFICAÇÕES
    # ======================
    path('notificacoes/', get_notificacoes, name='get_notificacoes'),
    path('notificacao/<int:notificacao_id>/marcar-lida/', marcar_notificacao_lida, name='marcar_notificacao_lida'),
    path('notificacoes/marcar-todas-lidas/', marcar_todas_notificacoes_lidas, name='marcar_todas_notificacoes_lidas'),

    path('task/<int:task_id>/open/', open_task_direct, name='open_task_direct'),
    path('task/<int:task_id>/get-board/', get_task_board, name='get_task_board'),

    path('task/<int:task_id>/upload-anexo/', upload_anexo, name='upload_anexo'),
    path('anexo/<int:anexo_id>/delete/', delete_anexo, name='delete_anexo'),
    path('task/<int:task_id>/anexos/', get_anexos, name='get_anexos'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)