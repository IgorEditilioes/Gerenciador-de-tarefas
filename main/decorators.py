from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from functools import wraps


# ==========================================
# DECORATORS DE PERMISSÃO
# ==========================================

def admin_required(function=None, redirect_url='home'):
    """
    Decorator para usuários administradores
    """
    def check_user(user):
        return user.is_authenticated and user.tipo == 'admin'
    
    if function:
        return user_passes_test(check_user, login_url='home')(function)
    return user_passes_test(check_user, login_url='home')


# decorators.py - Adicione logs na função board_access_required

def board_access_required(function=None, redirect_url='home'):
    """
    Decorator para verificar se o usuário tem acesso ao board
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            board_id = kwargs.get('board_id')
            if not board_id:
                raise PermissionDenied("Board ID não fornecido")
            
            from .models import Board
            try:
                board = Board.objects.get(id=board_id)
            except Board.DoesNotExist:
                raise PermissionDenied("Board não encontrado")
            
            # 🔥 LOGS PARA DEBUG
            print(f"🔍 ===== VERIFICANDO ACESSO AO BOARD =====")
            print(f"🔍 Board ID: {board_id}")
            print(f"🔍 Usuário: {request.user.username}")
            print(f"🔍 Tipo do usuário: {request.user.tipo}")
            print(f"🔍 Workspace do usuário: {request.user.workspace}")
            print(f"🔍 Workspace do board: {board.workspace}")
            
            if not check_permission_user_board(request.user, board):
                print(f"❌ Acesso NEGADO para {request.user.username}")
                raise PermissionDenied("Você não tem permissão para acessar este setor")
            
            print(f"✅ Acesso PERMITIDO para {request.user.username}")
            return view_func(request, *args, **kwargs)
        return wrapper
    
    if function:
        return decorator(function)
    return decorator



def gerente_or_admin_required(function=None, redirect_url='home'):
    """
    Decorator para usuários gerentes ou administradores
    """
    def check_user(user):
        return user.is_authenticated and user.tipo in ['gerente', 'admin']
    
    if function:
        return user_passes_test(check_user, login_url='home')(function)
    return user_passes_test(check_user, login_url='home')


def usuario_or_higher_required(function=None, redirect_url='home'):
    """
    Decorator para qualquer usuário logado (todos os tipos)
    """
    def check_user(user):
        return user.is_authenticated
    
    if function:
        return user_passes_test(check_user, login_url='home')(function)
    return user_passes_test(check_user, login_url='home')


# ==========================================
# FUNÇÕES DE VERIFICAÇÃO DE PERMISSÃO
# ==========================================

def check_permission_user_workspace(user, workspace):
    """
    Verifica se o usuário pertence ao workspace
    """
    return user.workspace == workspace


def check_permission_user_board(user, board):
    """
    Verifica se o usuário tem permissão para acessar o board
    """
    # Admin tem acesso a tudo
    if user.tipo == 'admin':
        return True
    
    # Gerente acessa boards do seu workspace
    if user.tipo == 'gerente':
        return user.workspace == board.workspace
    
    # Usuário comum: verifica se é membro do board
    if user.tipo == 'usuario':
        from .models import BoardMember
        return BoardMember.objects.filter(board=board, usuario=user).exists()
    
    return False


def check_permission_edit_task(user, task):
    """
    Verifica se o usuário pode editar a tarefa
    """
    # Admin tem acesso a tudo
    if user.tipo == 'admin':
        return True
    
    # Gerente pode editar qualquer tarefa do workspace
    if user.tipo == 'gerente':
        return user.workspace == task.board.workspace
    
    # Usuário comum: só pode editar se for o responsável ou criador
    if user.tipo == 'usuario':
        return user == task.responsavel or user == task.criado_por
    
    return False


def check_permission_delete_task(user, task):
    """
    Verifica se o usuário pode excluir a tarefa
    """
    # Admin pode excluir qualquer tarefa
    if user.tipo == 'admin':
        return True
    
    # Gerente pode excluir qualquer tarefa do workspace
    if user.tipo == 'gerente':
        return user.workspace == task.board.workspace
    
    # Usuário comum NÃO pode excluir tarefas
    return False


def check_permission_complete_task(user, task):
    """
    Verifica se o usuário pode marcar a tarefa como concluída
    Apenas Gerente e Admin podem alterar status para concluído
    """
    # Admin pode completar qualquer tarefa
    if user.tipo == 'admin':
        return True
    
    # Gerente pode completar qualquer tarefa do workspace
    if user.tipo == 'gerente':
        return user.workspace == task.board.workspace
    
    # Usuário comum NÃO pode completar tarefas
    return False


def check_permission_delete_board(user, board):
    """
    Verifica se o usuário pode excluir o board
    Apenas Admin e Gerente podem excluir boards
    """
    # Admin pode excluir qualquer board
    if user.tipo == 'admin':
        return True
    
    # Gerente pode excluir boards do seu workspace
    if user.tipo == 'gerente':
        return user.workspace == board.workspace
    
    # Usuário comum NÃO pode excluir boards
    return False


def check_permission_edit_subtask(user, subtask):
    """
    Verifica se o usuário pode editar a subtarefa
    """
    # Admin tem acesso a tudo
    if user.tipo == 'admin':
        return True
    
    # Gerente pode editar qualquer subtarefa do workspace
    if user.tipo == 'gerente':
        return user.workspace == subtask.task.board.workspace
    
    # Usuário comum: só pode editar se for o responsável ou criador
    if user.tipo == 'usuario':
        return user == subtask.responsavel or user == subtask.criado_por
    
    return False


def check_permission_delete_subtask(user, subtask):
    """
    Verifica se o usuário pode excluir a subtarefa
    """
    # Admin pode excluir qualquer subtarefa
    if user.tipo == 'admin':
        return True
    
    # Gerente pode excluir qualquer subtarefa do workspace
    if user.tipo == 'gerente':
        return user.workspace == subtask.task.board.workspace
    
    # Usuário comum NÃO pode excluir subtarefas
    return False


def check_permission_create_task(user, board):
    """
    Verifica se o usuário pode criar tarefas no board
    """
    # Admin pode criar em qualquer board
    if user.tipo == 'admin':
        return True
    
    # Gerente pode criar em boards do seu workspace
    if user.tipo == 'gerente':
        return user.workspace == board.workspace
    
    # Usuário comum pode criar tarefas apenas em boards do seu workspace
    if user.tipo == 'usuario':
        return user.workspace == board.workspace
    
    return False


def check_permission_create_board(user, workspace):
    """
    Verifica se o usuário pode criar boards
    """
    # Admin pode criar em qualquer workspace
    if user.tipo == 'admin':
        return True
    
    # Gerente pode criar no seu workspace
    if user.tipo == 'gerente':
        return user.workspace == workspace
    
    # Usuário comum NÃO pode criar boards
    return False