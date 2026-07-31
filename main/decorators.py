from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from functools import wraps


# ==========================================
# DECORATORS DE PERMISSÃO
# ==========================================

def admin_required(function=None, redirect_url='home'):
    """Decorator para usuários administradores"""
    def check_user(user):
        return user.is_authenticated and user.tipo == 'admin'
    
    if function:
        return user_passes_test(check_user, login_url='home')(function)
    return user_passes_test(check_user, login_url='home')


def board_access_required(function=None, redirect_url='home'):
    """Decorator para verificar se o usuário tem acesso ao board"""
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
            
            if not check_permission_user_board(request.user, board):
                raise PermissionDenied("Você não tem permissão para acessar este setor")
            
            return view_func(request, *args, **kwargs)
        return wrapper
    
    if function:
        return decorator(function)
    return decorator


def gerente_or_admin_required(function=None, redirect_url='home'):
    """Decorator para usuários gerentes ou administradores"""
    def check_user(user):
        return user.is_authenticated and user.tipo in ['gerente', 'admin']
    
    if function:
        return user_passes_test(check_user, login_url='home')(function)
    return user_passes_test(check_user, login_url='home')


def usuario_or_higher_required(function=None, redirect_url='home'):
    """Decorator para qualquer usuário logado (todos os tipos)"""
    def check_user(user):
        return user.is_authenticated
    
    if function:
        return user_passes_test(check_user, login_url='home')(function)
    return user_passes_test(check_user, login_url='home')


# ==========================================
# FUNÇÕES DE VERIFICAÇÃO DE PERMISSÃO
# ==========================================

def check_permission_user_workspace(user, workspace):
    """Verifica se o usuário pertence ao workspace"""
    return user.workspace == workspace


def check_permission_user_board(user, board):
    """Verifica se o usuário tem permissão para acessar o board"""
    if user.tipo == 'admin':
        return True
    
    if user.tipo == 'gerente':
        return user.workspace == board.workspace
    
    if user.tipo == 'usuario':
        from .models import BoardMember
        return BoardMember.objects.filter(board=board, usuario=user).exists()
    
    return False


def check_permission_edit_task(user, task):
    """
    Verifica se o usuário pode editar a tarefa
    
    Regras:
    - Admin: sempre pode
    - Gerente: pode editar qualquer tarefa do workspace
    - Usuário: só pode editar SE:
        1. For o criador da tarefa (criado_por == user) 
           OU o responsável (responsavel == user)
        2. E o campo permite_edicao_usuario == True
    """
    if user.tipo == 'admin':
        return True
    
    if user.tipo == 'gerente':
        return user.workspace == task.board.workspace
    
    if user.tipo == 'usuario':
        # 🔥 CORREÇÃO: Usuário só pode editar se o gerente permitiu
        if not task.permite_edicao_usuario:
            return False
        
        # E se for o criador ou responsável
        return user == task.criado_por or user == task.responsavel
    
    return False


def check_permission_delete_task(user, task):
    """Verifica se o usuário pode excluir a tarefa"""
    if user.tipo == 'admin':
        return True
    
    if user.tipo == 'gerente':
        return user.workspace == task.board.workspace
    
    # Usuário comum NÃO pode excluir tarefas
    return False


def check_permission_complete_task(user, task):
    """Verifica se o usuário pode marcar a tarefa como concluída"""
    if user.tipo == 'admin':
        return True
    
    if user.tipo == 'gerente':
        return user.workspace == task.board.workspace
    
    # Usuário comum NÃO pode completar tarefas
    return False


def check_permission_delete_board(user, board):
    """Verifica se o usuário pode excluir o board"""
    if user.tipo == 'admin':
        return True
    
    if user.tipo == 'gerente':
        return user.workspace == board.workspace
    
    # Usuário comum NÃO pode excluir boards
    return False


def check_permission_edit_subtask(user, subtask):
    """Verifica se o usuário pode editar a subtarefa"""
    if user.tipo == 'admin':
        return True
    
    if user.tipo == 'gerente':
        return user.workspace == subtask.task.board.workspace
    
    if user.tipo == 'usuario':
        # Usuário pode editar se for o responsável ou criador
        return user == subtask.responsavel or user == subtask.criado_por
    
    return False


def check_permission_delete_subtask(user, subtask):
    """Verifica se o usuário pode excluir a subtarefa"""
    if user.tipo == 'admin':
        return True
    
    if user.tipo == 'gerente':
        return user.workspace == subtask.task.board.workspace
    
    # Usuário comum NÃO pode excluir subtarefas
    return False


def check_permission_create_task(user, board):
    """Verifica se o usuário pode criar tarefas no board"""
    if user.tipo == 'admin':
        return True
    
    if user.tipo == 'gerente':
        return user.workspace == board.workspace
    
    if user.tipo == 'usuario':
        return user.workspace == board.workspace
    
    return False


def check_permission_create_board(user, workspace):
    """Verifica se o usuário pode criar boards"""
    if user.tipo == 'admin':
        return True
    
    if user.tipo == 'gerente':
        return user.workspace == workspace
    
    # Usuário comum NÃO pode criar boards
    return False