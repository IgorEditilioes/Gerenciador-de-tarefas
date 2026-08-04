# main/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Q
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import json
import re
import os
import uuid
import logging
from datetime import datetime

from .forms import LoginForm, PerfilForm
from .utils import (
    enviar_email_notificacao, 
    notificar_email_atribuicao, 
    notificar_email_mencao, 
    notificar_email_status_concluido
)
from .models import (
    User,
    Task,
    Board,
    Status,
    Comment,
    SubTask,
    TaskHistory,
    Workflow,
    BoardMember,
    Notification,
    Attachment,
)
from .decorators import (
    admin_required,
    gerente_or_admin_required,
    usuario_or_higher_required,
    check_permission_user_workspace,
    check_permission_user_board,
    check_permission_edit_task,
    check_permission_delete_task,
    check_permission_delete_board,
    check_permission_edit_subtask,
    check_permission_delete_subtask,
    check_permission_create_task,
    check_permission_create_board,
    check_permission_complete_task,
    board_access_required,
)

# Configurar logger
logger = logging.getLogger(__name__)


# =========================
# FUNÇÕES AUXILIARES DE NOTIFICAÇÃO
# =========================

def criar_notificacao(usuario, tipo, mensagem, origem=None, task=None, comentario=None, subtask=None):
    """Função auxiliar para criar notificações"""
    if not usuario:
        return
    
    Notification.objects.create(
        usuario=usuario,
        tipo=tipo,
        mensagem=mensagem,
        origem=origem,
        task=task,
        comentario=comentario,
        subtask=subtask
    )


def notificar_atribuicao(usuario, task, responsavel_anterior=None):
    """Cria notificação para atribuição de tarefa"""
    if not usuario:
        return
    
    if responsavel_anterior and responsavel_anterior == usuario:
        return
    
    mensagem = f"Você foi atribuído à tarefa: '{task.titulo}'"
    criar_notificacao(
        usuario=usuario,
        tipo='atribuicao',
        mensagem=mensagem,
        origem=task.atualizado_por,
        task=task
    )
    
    notificar_email_atribuicao(usuario, task)


def notificar_mencao(usuario, comentario, task):
    """Cria notificação para menção em comentário"""
    if not usuario:
        return
    
    nome_origem = comentario.usuario.get_full_name() or comentario.usuario.username
    mensagem = f"{nome_origem} mencionou você em um comentário: '{comentario.texto[:50]}...'"
    criar_notificacao(
        usuario=usuario,
        tipo='mencao',
        mensagem=mensagem,
        origem=comentario.usuario,
        task=task,
        comentario=comentario
    )
    
    notificar_email_mencao(usuario, comentario, task)


def notificar_status_concluido(task, usuario):
    """
    Cria notificação no sistema quando uma tarefa é concluída
    """
    if not task.responsavel:
        return
    
    if task.responsavel == usuario:
        return
    
    nome_origem = usuario.get_full_name() or usuario.username
    mensagem = f"{nome_origem} concluiu a tarefa: '{task.titulo}'"
    criar_notificacao(
        usuario=task.responsavel,
        tipo='atribuicao',
        mensagem=mensagem,
        origem=usuario,
        task=task
    )


# =========================
# LOGIN
# =========================
def login_view(request):
    if request.method == "POST":
        form = LoginForm(request.POST)

        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]

            usuario = User.objects.filter(username=username).first()

            if not usuario:
                messages.error(request, "Usuário não encontrado")
            else:
                user = authenticate(
                    request,
                    username=usuario.username,
                    password=password
                )

                if user:
                    login(request, user)
                    return redirect("home")
                else:
                    messages.error(request, "Senha inválida")
    else:
        form = LoginForm()

    return render(request, "login.html", {"form": form})


# =========================
# LOGOUT
# =========================
@login_required
def logout_view(request):
    logout(request)
    return redirect("login")


# =========================
# HOME
# =========================
@login_required
def home(request):
    usuario = request.user
    workspace = usuario.workspace

    if usuario.tipo == 'admin':
        boards = Board.objects.all()
    elif usuario.tipo == 'gerente':
        boards = Board.objects.filter(workspace=workspace)
    else:
        boards_ids = BoardMember.objects.filter(
            usuario=usuario
        ).values_list('board_id', flat=True)
        
        boards = Board.objects.filter(
            workspace=workspace,
            id__in=boards_ids
        )

    usuarios = User.objects.filter(workspace=workspace)
    total_tarefas = Task.objects.filter(board__workspace=workspace).count()

    return render(
        request,
        "home.html",
        {
            "usuario": usuario,
            "workspace": workspace,
            "boards": boards,
            "usuarios": usuarios,
            "total_tarefas": total_tarefas
        }
    )


# =========================
# BUSCAR RESPONSÁVEIS POR BOARD (SETOR)
# =========================
@login_required
def buscar_responsaveis(request):
    termo = request.GET.get('term', '').strip()
    tarefa_id = request.GET.get('tarefa_id')
    board_id = request.GET.get('board_id')
    
    usuario_logado = request.user
    
    if not board_id and tarefa_id:
        try:
            tarefa = Task.objects.get(id=tarefa_id)
            board_id = tarefa.board.id
        except Task.DoesNotExist:
            pass
    
    if not board_id:
        return JsonResponse([], safe=False)
    
    try:
        board = Board.objects.get(id=board_id)
    except Board.DoesNotExist:
        return JsonResponse([], safe=False)
    
    membros_ids = BoardMember.objects.filter(
        board=board
    ).exclude(
        usuario=usuario_logado
    ).values_list('usuario_id', flat=True)
    
    usuarios = User.objects.filter(
        id__in=membros_ids,
        workspace=usuario_logado.workspace
    )
    
    if termo:
        usuarios = usuarios.filter(
            Q(first_name__icontains=termo) |
            Q(last_name__icontains=termo) |
            Q(username__icontains=termo) |
            Q(email__icontains=termo)
        )
    
    if tarefa_id:
        try:
            tarefa = Task.objects.get(id=tarefa_id)
            if tarefa.responsavel and tarefa.responsavel.id != usuario_logado.id:
                usuarios = usuarios | User.objects.filter(id=tarefa.responsavel.id)
        except Task.DoesNotExist:
            pass
    
    results = []
    for usuario in usuarios[:20]:
        nome_completo = usuario.get_full_name() or usuario.username
        results.append({
            'id': usuario.id,
            'text': f"{nome_completo} ({usuario.email})",
            'nome': nome_completo,
            'email': usuario.email,
            'username': usuario.username,
            'avatar': f"https://ui-avatars.com/api/?name={nome_completo}&size=32&background=667eea&color=fff"
        })
    
    return JsonResponse(results, safe=False)


@login_required
def get_responsaveis_board(request, board_id):
    try:
        usuario_logado = request.user
        board = get_object_or_404(Board, id=board_id)
        
        if not check_permission_user_board(usuario_logado, board):
            return JsonResponse({'error': 'Sem permissão'}, status=403)
        
        membros_ids = BoardMember.objects.filter(
            board=board
        ).exclude(
            usuario=usuario_logado
        ).values_list('usuario_id', flat=True)
        
        usuarios = User.objects.filter(
            id__in=membros_ids,
            workspace=usuario_logado.workspace
        ).values('id', 'first_name', 'last_name', 'email', 'username')
        
        usuarios_list = []
        for usuario in usuarios:
            nome_completo = f"{usuario.get('first_name', '')} {usuario.get('last_name', '')}".strip()
            if not nome_completo:
                nome_completo = usuario.get('username', '')
            
            usuarios_list.append({
                'id': usuario['id'],
                'nome': nome_completo,
                'email': usuario['email'],
                'username': usuario['username']
            })
        
        return JsonResponse(usuarios_list, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# =========================
# AVATAR
# =========================
@login_required
@require_http_methods(["POST"])
def atualizar_avatar(request, id):
    try:
        usuario = get_object_or_404(User, id=id)
        
        if request.user.id != usuario.id:
            return JsonResponse({
                'success': False,
                'message': 'Permissão negada.'
            }, status=403)
        
        if request.FILES.get('avatar'):
            usuario.avatar = request.FILES['avatar']
            usuario.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Avatar atualizado com sucesso!',
                'avatar_url': usuario.avatar.url
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Nenhum arquivo enviado.'
            }, status=400)
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erro ao salvar avatar: {str(e)}'
        }, status=500)
    

# =========================
# PERFIL
# =========================
@login_required
def perfil(request, id):
    usuario = get_object_or_404(User, id=id)
    
    if request.user.id != usuario.id:
        messages.error(request, 'Você não tem permissão para editar este perfil.')
        return redirect('home')
    
    if request.method == 'GET':
        form = PerfilForm(initial={
            'first_name': usuario.first_name,
            'last_name': usuario.last_name,
            'email': usuario.email,
        }, user=usuario)
        
        context = {
            'usuario': usuario,
            'form': form,
            'is_editing': False,
        }
        return render(request, 'perfil.html', context)
    
    elif request.method == 'POST':
        form = PerfilForm(request.POST, user=usuario)
        
        if form.is_valid():
            usuario.first_name = form.cleaned_data['first_name']
            usuario.last_name = form.cleaned_data['last_name']
            
            nova_senha = form.cleaned_data.get('nova_senha')
            if nova_senha:
                usuario.set_password(nova_senha)
                update_session_auth_hash(request, usuario)
                messages.success(request, 'Senha alterada com sucesso!')
            
            usuario.save()
            messages.success(request, 'Perfil atualizado com sucesso!')
            return redirect('perfil', id=usuario.id)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{form.fields[field].label}: {error}')
            
            context = {
                'usuario': usuario,
                'form': form,
                'is_editing': True,
            }
            return render(request, 'perfil.html', context)


# =========================
# CREATE BOARD
# =========================
@login_required
def create_board(request):
    if request.method != "POST":
        return redirect("home")
    
    usuario = request.user
    workspace = usuario.workspace
    
    if not check_permission_create_board(usuario, workspace):
        messages.error(request, "Você não tem permissão para criar setores.")
        return redirect("home")
    
    board = Board.objects.create(
        workspace=workspace,
        nome=request.POST.get("nome"),
        descricao=request.POST.get("descricao", ""),
        privado=request.POST.get("privado") == "on"
    )
    
    BoardMember.objects.create(
        board=board,
        usuario=usuario
    )
    
    workflow = Workflow.objects.create(
        board=board,
        nome="Padrão",
        padrao=True
    )
    
    Status.objects.create(
        workflow=workflow,
        nome="A Fazer",
        ordem=1,
        cor="#FF4444"
    )
    Status.objects.create(
        workflow=workflow,
        nome="Em Andamento",
        ordem=2,
        cor="#FFA500"
    )
    Status.objects.create(
        workflow=workflow,
        nome="Concluído",
        ordem=3,
        cor="#00C851"
    )
    
    messages.success(request, f"Setor '{board.nome}' criado com sucesso!")
    return redirect("home")


# =========================
# OPEN TASK DIRECT
# =========================
@login_required
def open_task_direct(request, task_id):
    try:
        task = Task.objects.get(id=task_id)
    except Task.DoesNotExist:
        messages.error(request, "Esta tarefa não existe mais.")
        return redirect('home')
    
    usuario = request.user
    
    if not check_permission_user_board(usuario, task.board):
        messages.error(request, "Você não tem permissão para acessar esta tarefa.")
        return redirect('home')
    
    return redirect(f"/board/{task.board.id}/?open_task={task.id}")


# =========================
# BOARD VIEW
# =========================
@login_required
@board_access_required
def board_view(request, board_id):
    board = get_object_or_404(Board, id=board_id)
    usuario = request.user
    
    if not check_permission_user_board(usuario, board):
        messages.error(request, "Você não tem permissão para acessar este setor.")
        return redirect("home")
    
    status_list = Status.objects.filter(
        workflow__board=board
    ).order_by("ordem").prefetch_related(
        "tasks__subtasks",
        "tasks__comments",
        "tasks__history"
    )
    
    membros_ids = BoardMember.objects.filter(
        board=board
    ).values_list('usuario_id', flat=True)
    
    usuarios_board = User.objects.filter(
        id__in=membros_ids,
        workspace=usuario.workspace,
        is_active=True
    ).order_by('first_name', 'last_name')
    
    if usuario not in usuarios_board:
        usuarios_board = usuarios_board | User.objects.filter(id=usuario.id)

    usuarios = User.objects.filter(
        workspace=request.user.workspace,
        is_active=True
    )

    from datetime import date, timedelta
    today = date.today()
    today_plus_3 = today + timedelta(days=3)

    open_task_id = request.GET.get('open_task')
    
    return render(
        request,
        "board.html",
        {
            "board": board,
            "status_list": status_list,
            "usuarios": usuarios,
            "usuarios_board": usuarios_board,
            "user_tipo": usuario.tipo,
            "today": today,
            "today_plus_3": today_plus_3,
            "open_task_id": open_task_id,
        }
    )


# =========================
# GET TASK BOARD
# =========================
@login_required
def get_task_board(request, task_id):
    try:
        task = Task.objects.get(id=task_id)
    except Task.DoesNotExist:
        return JsonResponse({
            'success': False, 
            'error': 'Tarefa não encontrada'
        }, status=404)
    
    usuario = request.user
    
    if not check_permission_user_board(usuario, task.board):
        return JsonResponse({
            'success': False, 
            'error': 'Sem permissão para acessar esta tarefa'
        }, status=403)
    
    return JsonResponse({
        'success': True,
        'board_id': task.board.id,
        'task_id': task.id,
        'task_title': task.titulo
    })


# =========================
# ADD TASK (CORRIGIDO)
# =========================
@login_required
def add_task(request, board_id):
    board = get_object_or_404(Board, id=board_id)
    usuario = request.user
    
    if not check_permission_create_task(usuario, board):
        messages.error(request, "Você não tem permissão para criar tarefas neste setor.")
        return redirect("board", board_id=board.id)

    if request.method != "POST":
        return redirect("board", board_id=board.id)

    workflow = Workflow.objects.filter(board=board, padrao=True).first()
    
    if not workflow:
        workflow = Workflow.objects.filter(board=board).first()
    
    if not workflow:
        workflow = Workflow.objects.create(
            board=board,
            nome="Padrão",
            padrao=True
        )
        Status.objects.create(
            workflow=workflow,
            nome="A Fazer",
            ordem=1,
            cor="#FF4444"
        )
        Status.objects.create(
            workflow=workflow,
            nome="Em Andamento",
            ordem=2,
            cor="#FFA500"
        )
        Status.objects.create(
            workflow=workflow,
            nome="Concluído",
            ordem=3,
            cor="#00C851"
        )
    
    status = Status.objects.filter(workflow=workflow).first()
    
    if not status:
        status = Status.objects.create(
            workflow=workflow,
            nome="A Fazer",
            ordem=1,
            cor="#FF4444"
        )

    responsavel_id = request.POST.get("responsavel")
    data_entrega = request.POST.get("data_entrega")
    
    if usuario.tipo == 'usuario':
        responsavel_id = usuario.id
    
    if responsavel_id and responsavel_id != '':
        responsavel = get_object_or_404(User, id=responsavel_id)
        is_member = BoardMember.objects.filter(
            board=board,
            usuario=responsavel
        ).exists()
        
        if usuario.tipo not in ['admin', 'gerente'] and not is_member:
            messages.error(request, "Você só pode atribuir tarefas para membros deste setor.")
            return redirect("board", board_id=board.id)
    
    if data_entrega == '':
        data_entrega = None

    # ✅ CORREÇÃO: Respeitar o valor do checkbox
    # Para Admin e Gerente: usar o valor do checkbox
    # Para Usuário comum: sempre True (pode editar as próprias tarefas)
    if usuario.tipo in ['admin', 'gerente']:
        # Admin/Gerente: usa o valor enviado pelo checkbox
        permite_edicao_usuario = request.POST.get("permite_edicao_usuario") == 'on'
    else:
        # Usuário comum: sempre True (pode editar as próprias tarefas)
        permite_edicao_usuario = True

    task = Task.objects.create(
        board=board,
        workflow=workflow,
        titulo=request.POST.get("titulo"),
        descricao=request.POST.get("descricao", ""),
        status=status,
        prioridade=request.POST.get("prioridade", "media"),
        responsavel_id=responsavel_id if responsavel_id else None,
        criado_por=usuario,
        atualizado_por=usuario,
        data_entrega=data_entrega,
        permite_edicao_usuario=permite_edicao_usuario
    )

    TaskHistory.objects.create(
        task=task,
        usuario=request.user,
        campo="Criação",
        valor_antigo="",
        valor_novo="Tarefa criada"
    )

    if task.responsavel and task.responsavel != usuario:
        notificar_atribuicao(task.responsavel, task)

    messages.success(request, "Tarefa criada com sucesso!")
    return redirect("board", board_id=board.id)



# =========================
# UPDATE TASK
# =========================
@login_required
def update_task(request, task_id):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Método não permitido"})

    task = get_object_or_404(Task, id=task_id)
    usuario = request.user
    
    if not check_permission_edit_task(usuario, task):
        return JsonResponse(
            {"success": False, "error": "Sem permissão para editar esta tarefa"},
            status=403
        )

    responsavel_anterior = task.responsavel
    status_anterior = task.status

    novo_status_id = request.POST.get("status")
    
    if usuario.tipo == 'usuario':
        try:
            status_obj = get_object_or_404(Status, id=novo_status_id)
            if status_obj.nome.lower() in ["concluído", "concluido"]:
                return JsonResponse(
                    {"success": False, "error": "Usuários comuns não podem concluir tarefas"},
                    status=403
                )
        except:
            pass

    novo_responsavel_id = request.POST.get("responsavel")
    if novo_responsavel_id and novo_responsavel_id != '':
        try:
            novo_responsavel = User.objects.get(id=novo_responsavel_id)
            if usuario.tipo == 'usuario':
                is_member = BoardMember.objects.filter(
                    board=task.board,
                    usuario=novo_responsavel
                ).exists()
                
                if not is_member:
                    return JsonResponse({
                        "success": False, 
                        "error": "Você só pode atribuir tarefas para membros deste setor."
                    }, status=403)
        except User.DoesNotExist:
            pass

    data_entrega = request.POST.get("data_entrega")
    if data_entrega == '':
        data_entrega = None

    titulo = request.POST.get("title")
    descricao = request.POST.get("description")
    prioridade = request.POST.get("prioridade")
    status_id = request.POST.get("status")
    responsavel_id = request.POST.get("responsavel")
    permite_edicao_usuario = request.POST.get("permite_edicao_usuario") == 'on'

    if not titulo:
        return JsonResponse({"success": False, "error": "Título é obrigatório"})

    campos = {
        "titulo": titulo,
        "descricao": descricao,
        "prioridade": prioridade,
        "status": status_id,
        "responsavel": responsavel_id,
        "data_entrega": data_entrega,
        "permite_edicao_usuario": str(permite_edicao_usuario),
    }

    for campo, novo_valor in campos.items():
        if campo == "status":
            antigo = str(task.status_id)
        elif campo == "responsavel":
            antigo = str(task.responsavel_id)
        elif campo == "data_entrega":
            antigo = str(task.data_entrega) if task.data_entrega else ""
        elif campo == "permite_edicao_usuario":
            antigo = str(task.permite_edicao_usuario)
        else:
            antigo = str(getattr(task, campo, ""))

        if str(antigo) != str(novo_valor):
            TaskHistory.objects.create(
                task=task,
                usuario=request.user,
                campo=campo,
                valor_antigo=antigo,
                valor_novo=str(novo_valor)
            )

    task.titulo = titulo
    task.descricao = descricao if descricao else ""
    task.prioridade = prioridade if prioridade else "media"
    task.status_id = status_id
    task.responsavel_id = int(responsavel_id) if responsavel_id and responsavel_id != '' else None
    task.data_entrega = data_entrega
    task.permite_edicao_usuario = permite_edicao_usuario
    task.atualizado_por = request.user
    task.save()

    novo_status = task.status
    if (status_anterior.id != novo_status.id and 
        novo_status.nome.lower() in ["concluído", "concluido"]):
        notificar_email_status_concluido(task, usuario)
        notificar_status_concluido(task, usuario)

    if task.responsavel and task.responsavel != responsavel_anterior:
        notificar_atribuicao(task.responsavel, task, responsavel_anterior)

    return JsonResponse({"success": True})


# =========================
# UPDATE TASK STATUS (DRAG AND DROP)
# =========================
@login_required
def update_task_status(request, task_id):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Método não permitido"})
    
    task = get_object_or_404(Task, id=task_id)
    usuario = request.user
    
    if not check_permission_edit_task(usuario, task):
        return JsonResponse({
            "success": False, 
            "error": "Sem permissão para editar esta tarefa"
        }, status=403)
    
    status_id = request.POST.get("status")
    if not status_id:
        return JsonResponse({
            "success": False, 
            "error": "Status não informado"
        }, status=400)
    
    try:
        novo_status = Status.objects.get(id=status_id, workflow__board=task.board)
    except Status.DoesNotExist:
        return JsonResponse({
            "success": False, 
            "error": "Status inválido"
        }, status=400)
    
    if usuario.tipo == 'usuario' and novo_status.nome.lower() in ["concluído", "concluido"]:
        return JsonResponse({
            "success": False, 
            "error": "Usuários comuns não podem concluir tarefas"
        }, status=403)
    
    TaskHistory.objects.create(
        task=task,
        usuario=request.user,
        campo="Status",
        valor_antigo=task.status.nome,
        valor_novo=novo_status.nome
    )
    
    task.status = novo_status
    task.atualizado_por = request.user
    task.save()
    
    return JsonResponse({"success": True})


# =========================
# DELETE TASK
# =========================
@login_required
def delete_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    usuario = request.user
    board_id = task.board.id
    
    if not check_permission_delete_task(usuario, task):
        messages.error(request, "Você não tem permissão para excluir esta tarefa.")
        return redirect("board", board_id=board_id)
    
    task.delete()
    messages.success(request, "Tarefa excluída com sucesso!")
    return redirect("board", board_id=board_id)


# =========================
# COMPLETE TASK
# =========================
@login_required
def complete_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    usuario = request.user
    
    if not check_permission_complete_task(usuario, task):
        messages.error(request, "Apenas Gerentes e Administradores podem concluir tarefas.")
        return redirect("board", board_id=task.board.id)
    
    status_concluido = Status.objects.filter(
        workflow__board=task.board,
        nome__iexact="Concluído"
    ).first()
    
    if not status_concluido:
        status_concluido = Status.objects.filter(
            workflow__board=task.board,
            nome__icontains="conclu"
        ).first()
    
    if not status_concluido:
        status_concluido = Status.objects.filter(
            workflow__board=task.board
        ).order_by('ordem').last()
    
    if status_concluido:
        task.status = status_concluido
        task.save()
        
        TaskHistory.objects.create(
            task=task,
            usuario=usuario,
            campo="Status",
            valor_antigo="",
            valor_novo="Concluído"
        )
        
        notificar_email_status_concluido(task, usuario)
        notificar_status_concluido(task, usuario)
        
        messages.success(request, "Tarefa concluída com sucesso!")
    else:
        messages.error(request, "Status 'Concluído' não encontrado.")
    
    return redirect("board", board_id=task.board.id)


# =========================
# DELETE BOARD
# =========================
@login_required
def delete_board(request, board_id):
    board = get_object_or_404(Board, id=board_id)
    usuario = request.user
    
    if not check_permission_delete_board(usuario, board):
        messages.error(request, "Você não tem permissão para excluir este setor.")
        return redirect("home")
    
    board.delete()
    messages.success(request, "Setor excluído com sucesso!")
    return redirect("home")


# =========================
# COMMENT (COM MENÇÕES)
# =========================
@login_required
def add_comment(request, task_id):
    if request.method != "POST":
        return JsonResponse({"success": False})

    task = get_object_or_404(Task, id=task_id)
    usuario = request.user
    
    if not check_permission_user_board(usuario, task.board):
        return JsonResponse(
            {"success": False, "error": "Sem permissão"},
            status=403
        )

    texto = request.POST.get("comment")
    if not texto:
        return JsonResponse({"success": False})

    comment = Comment.objects.create(
        task=task,
        usuario=request.user,
        texto=texto
    )

    padrao = r'@(\w+)'
    mencoes = re.findall(padrao, texto)
    
    membros_board = BoardMember.objects.filter(board=task.board).values_list('usuario__username', flat=True)
    
    for username in mencoes:
        if username in membros_board:
            try:
                usuario_mencionado = User.objects.get(username=username)
                if usuario_mencionado != usuario:
                    notificar_mencao(usuario_mencionado, comment, task)
            except User.DoesNotExist:
                pass

    return JsonResponse({
        "success": True,
        "username": request.user.username,
        "texto": comment.texto,
        "comment_id": comment.id
    })


# =========================
# ANEXOS
# =========================
@login_required
def upload_anexo(request, task_id):
    """
    Upload de anexo para uma tarefa
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Método não permitido"})
    
    task = get_object_or_404(Task, id=task_id)
    usuario = request.user
    
    if not check_permission_user_board(usuario, task.board):
        return JsonResponse({
            "success": False, 
            "error": "Sem permissão para anexar arquivos a esta tarefa"
        }, status=403)
    
    arquivo = request.FILES.get('arquivo')
    if not arquivo:
        return JsonResponse({
            "success": False, 
            "error": "Nenhum arquivo enviado"
        }, status=400)
    
    if arquivo.size > 10 * 1024 * 1024:
        return JsonResponse({
            "success": False, 
            "error": "Arquivo muito grande. Máximo permitido: 10MB"
        }, status=400)
    
    extensoes_permitidas = [
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', 
        '.ppt', '.pptx', '.txt', '.csv',
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg',
        '.zip', '.rar', '.7z'
    ]
    
    nome_arquivo = arquivo.name.lower()
    extensao = ''
    for ext in extensoes_permitidas:
        if nome_arquivo.endswith(ext):
            extensao = ext
            break
    
    if not extensao:
        return JsonResponse({
            "success": False, 
            "error": f"Tipo de arquivo não permitido."
        }, status=400)
    
    try:
        nome_unico = f"{uuid.uuid4().hex}_{datetime.now().strftime('%Y%m%d%H%M%S')}{extensao}"
        
        pasta_anexos = os.path.join(settings.MEDIA_ROOT, 'anexos', str(task.board.id), str(task.id))
        os.makedirs(pasta_anexos, exist_ok=True)
        
        caminho_relativo = f"anexos/{task.board.id}/{task.id}/{nome_unico}"
        caminho_completo = os.path.join(settings.MEDIA_ROOT, caminho_relativo)
        
        with open(caminho_completo, 'wb+') as destination:
            for chunk in arquivo.chunks():
                destination.write(chunk)
        
        anexo = Attachment.objects.create(
            task=task,
            arquivo=caminho_relativo,
            nome=arquivo.name,
            tamanho=arquivo.size,
            tipo=arquivo.content_type,
            uploaded_by=usuario
        )
        
        if task.responsavel and task.responsavel != usuario:
            mensagem = f"{usuario.get_full_name() or usuario.username} anexou um arquivo à tarefa: '{task.titulo}'"
            criar_notificacao(
                usuario=task.responsavel,
                tipo='comentario',
                mensagem=mensagem,
                origem=usuario,
                task=task
            )
        
        return JsonResponse({
            "success": True,
            "anexo": {
                "id": anexo.id,
                "nome": anexo.nome,
                "tamanho": anexo.get_tamanho_formatado(),
                "tipo": anexo.tipo,
                "icone": anexo.get_icone(),
                "cor_icone": anexo.get_cor_icone(),
                "url": anexo.arquivo.url,
                "uploaded_by": anexo.uploaded_by.get_full_name() or anexo.uploaded_by.username,
                "criado_em": anexo.criado_em.strftime('%d/%m/%Y %H:%M')
            }
        })
        
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": f"Erro ao salvar arquivo: {str(e)}"
        }, status=500)


@login_required
def delete_anexo(request, anexo_id):
    """Exclui um anexo"""
    anexo = get_object_or_404(Attachment, id=anexo_id)
    usuario = request.user
    
    if usuario.tipo not in ['admin', 'gerente'] and anexo.uploaded_by != usuario:
        return JsonResponse({
            "success": False, 
            "error": "Você não tem permissão para excluir este anexo"
        }, status=403)
    
    try:
        if anexo.arquivo and os.path.exists(anexo.arquivo.path):
            os.remove(anexo.arquivo.path)
    except Exception as e:
        pass
    
    task_id = anexo.task.id
    anexo.delete()
    
    return JsonResponse({"success": True})


@login_required
def get_anexos(request, task_id):
    """Retorna todos os anexos de uma tarefa"""
    task = get_object_or_404(Task, id=task_id)
    usuario = request.user
    
    if not check_permission_user_board(usuario, task.board):
        return JsonResponse({
            "success": False, 
            "error": "Sem permissão"
        }, status=403)
    
    anexos = task.anexos.all()
    
    data = []
    for anexo in anexos:
        data.append({
            "id": anexo.id,
            "nome": anexo.nome,
            "tamanho": anexo.get_tamanho_formatado(),
            "tipo": anexo.tipo,
            "icone": anexo.get_icone(),
            "cor_icone": anexo.get_cor_icone(),
            "url": anexo.arquivo.url,
            "uploaded_by": anexo.uploaded_by.get_full_name() or anexo.uploaded_by.username,
            "criado_em": anexo.criado_em.strftime('%d/%m/%Y %H:%M'),
            "pode_excluir": usuario.tipo in ['admin', 'gerente'] or anexo.uploaded_by == usuario
        })
    
    return JsonResponse({
        "success": True,
        "anexos": data
    })


# =========================
# SUBTASK (CRIAR)
# =========================
@login_required
def add_subtask(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    usuario = request.user
    
    if not check_permission_user_board(usuario, task.board):
        return JsonResponse(
            {"success": False, "error": "Sem permissão"},
            status=403
        )

    if request.method == "POST":
        responsavel_id = request.POST.get("responsavel")
        data_entrega = request.POST.get("data_entrega")
        
        if data_entrega == '' or data_entrega is None:
            data_entrega = None
        
        if usuario.tipo == 'usuario':
            responsavel_id = usuario.id
        
        if responsavel_id and responsavel_id != '':
            responsavel = get_object_or_404(User, id=responsavel_id)
            if usuario.tipo not in ['admin', 'gerente']:
                is_member = BoardMember.objects.filter(
                    board=task.board,
                    usuario=responsavel
                ).exists()
                
                if not is_member:
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'success': False, 
                            'error': 'Você só pode atribuir subtarefas para membros deste setor.'
                        }, status=403)
                    messages.error(request, "Você só pode atribuir subtarefas para membros deste setor.")
                    return redirect("board", board_id=task.board.id)
        
        subtask = SubTask.objects.create(
            task=task,
            titulo=request.POST.get("titulo"),
            prioridade=request.POST.get("prioridade", "media"),
            responsavel_id=responsavel_id if responsavel_id else None,
            criado_por=usuario,
            data_entrega=data_entrega
        )
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'subtask': {
                    'id': subtask.id,
                    'titulo': subtask.titulo,
                    'prioridade': subtask.prioridade,
                    'prioridade_display': subtask.get_prioridade_display(),
                    'concluida': subtask.concluida,
                    'responsavel': subtask.responsavel.username if subtask.responsavel else None,
                    'responsavel_id': subtask.responsavel.id if subtask.responsavel else None,
                    'data_entrega': subtask.data_entrega.strftime('%Y-%m-%d') if subtask.data_entrega else None,
                }
            })

    return redirect("board", board_id=task.board.id)


# =========================
# SUBTASK (ATUALIZAR)
# =========================
@login_required
def update_subtask(request, subtask_id):
    subtask = get_object_or_404(SubTask, id=subtask_id)
    usuario = request.user
    
    if not check_permission_edit_subtask(usuario, subtask):
        messages.error(request, "Você não tem permissão para editar esta subtarefa.")
        return redirect("board", board_id=subtask.task.board.id)

    if request.method == "POST":
        subtask.titulo = request.POST.get("titulo")
        subtask.prioridade = request.POST.get("prioridade")
        
        concluida = request.POST.get("concluida")
        if concluida == "True":
            subtask.concluida = True
        elif concluida == "False":
            subtask.concluida = False
        
        responsavel_id = request.POST.get("responsavel")
        subtask.responsavel_id = int(responsavel_id) if responsavel_id and responsavel_id != '' else None
        
        data_entrega = request.POST.get("data_entrega")
        if data_entrega == '' or data_entrega is None:
            data_entrega = None
        subtask.data_entrega = data_entrega

        subtask.save()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'subtask': {
                    'id': subtask.id,
                    'titulo': subtask.titulo,
                    'prioridade': subtask.prioridade,
                    'prioridade_display': subtask.get_prioridade_display(),
                    'concluida': subtask.concluida,
                    'responsavel': subtask.responsavel.username if subtask.responsavel else None,
                    'responsavel_id': subtask.responsavel.id if subtask.responsavel else None,
                    'data_entrega': subtask.data_entrega.strftime('%Y-%m-%d') if subtask.data_entrega else None,
                }
            })

    return redirect("board", board_id=subtask.task.board.id)


# =========================
# SUBTASK (TOGGLE - MARCAR/DESMARCAR)
# =========================
@login_required
def toggle_subtask(request, subtask_id):
    subtask = get_object_or_404(SubTask, id=subtask_id)
    usuario = request.user
    
    if usuario.tipo == 'usuario':
        if not (usuario == subtask.responsavel or usuario == subtask.criado_por):
            messages.error(request, "Você não tem permissão para alterar esta subtarefa.")
            return redirect("board", board_id=subtask.task.board.id)
    
    subtask.concluida = not subtask.concluida
    subtask.save()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'concluida': subtask.concluida,
            'subtask': {
                'id': subtask.id,
                'titulo': subtask.titulo,
                'prioridade': subtask.prioridade,
                'prioridade_display': subtask.get_prioridade_display(),
                'concluida': subtask.concluida,
                'responsavel': subtask.responsavel.username if subtask.responsavel else None,
                'responsavel_id': subtask.responsavel.id if subtask.responsavel else None,
                'data_entrega': subtask.data_entrega.strftime('%Y-%m-%d') if subtask.data_entrega else None,
            }
        })
    
    return redirect("board", board_id=subtask.task.board.id)


# =========================
# SUBTASK (EXCLUIR)
# =========================
@login_required
def delete_subtask(request, subtask_id):
    subtask = get_object_or_404(SubTask, id=subtask_id)
    usuario = request.user
    
    if not check_permission_delete_subtask(usuario, subtask):
        messages.error(request, "Você não tem permissão para excluir esta subtarefa.")
        return redirect("board", board_id=subtask.task.board.id)
    
    board_id = subtask.task.board.id
    subtask.delete()
    messages.success(request, "Subtarefa excluída com sucesso!")
    return redirect("board", board_id=board_id)


# =========================
# GET SUBTASKS (AJAX)
# =========================
@login_required
def get_subtasks(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    usuario = request.user
    
    if not check_permission_user_board(usuario, task.board):
        return JsonResponse({'success': False, 'error': 'Sem permissão'}, status=403)
    
    subtasks = task.subtasks.all()
    
    data = []
    for sub in subtasks:
        data.append({
            'id': sub.id,
            'titulo': sub.titulo,
            'prioridade': sub.prioridade,
            'prioridade_display': sub.get_prioridade_display(),
            'concluida': sub.concluida,
            'responsavel': sub.responsavel.username if sub.responsavel else None,
            'responsavel_id': sub.responsavel.id if sub.responsavel else None,
            'data_entrega': sub.data_entrega.strftime('%Y-%m-%d') if sub.data_entrega else None,
        })
    
    return JsonResponse({'success': True, 'subtasks': data})


# =========================
# NOTIFICAÇÕES
# =========================
@login_required
def get_notificacoes(request):
    usuario = request.user
    
    notificacoes_nao_lidas = usuario.notificacoes.filter(lida=False)
    total_nao_lidas = notificacoes_nao_lidas.count()
    
    ultimas_notificacoes = usuario.notificacoes.all()[:10]
    
    notificacoes_data = []
    for notif in ultimas_notificacoes:
        icone = {
            'comentario': 'fa-comment',
            'mencao': 'fa-at',
            'atribuicao': 'fa-user-plus',
            'subtarefa': 'fa-check-double',
            'vencimento': 'fa-clock'
        }.get(notif.tipo, 'fa-bell')
        
        cor = {
            'comentario': '#3b82f6',
            'mencao': '#8b5cf6',
            'atribuicao': '#22c55e',
            'subtarefa': '#f59e0b',
            'vencimento': '#ef4444'
        }.get(notif.tipo, '#64748b')
        
        notificacoes_data.append({
            'id': notif.id,
            'mensagem': notif.mensagem,
            'tipo': notif.tipo,
            'icone': icone,
            'cor': cor,
            'lida': notif.lida,
            'criado_em': notif.criado_em.strftime('%d/%m/%Y %H:%M'),
            'task_id': notif.task.id if notif.task else None,
            'comentario_id': notif.comentario.id if notif.comentario else None,
        })
    
    return JsonResponse({
        'notificacoes': notificacoes_data,
        'total_nao_lidas': total_nao_lidas
    })


@login_required
def marcar_notificacao_lida(request, notificacao_id):
    notificacao = get_object_or_404(Notification, id=notificacao_id, usuario=request.user)
    notificacao.lida = True
    notificacao.save()
    return JsonResponse({'success': True})


@login_required
def marcar_todas_notificacoes_lidas(request):
    request.user.notificacoes.filter(lida=False).update(lida=True)
    return JsonResponse({'success': True})