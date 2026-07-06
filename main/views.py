from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import Count

from .forms import LoginForm
from .models import (
    User,
    Task,
    Board,
    Status,
    Comment,
    SubTask,
    TaskHistory,
    Workflow
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

    # Admin vê todos os boards, outros vêem apenas do seu workspace
    if usuario.tipo == 'admin':
        boards = Board.objects.all()
    else:
        boards = Board.objects.filter(workspace=workspace)

    usuarios = User.objects.filter(workspace=workspace)

    total_tarefas = Task.objects.filter(
        board__workspace=workspace
    ).count()

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
# CREATE BOARD - APENAS ADMIN E GERENTE
# =========================
@login_required
def create_board(request):
    if request.method != "POST":
        return redirect("home")
    
    usuario = request.user
    workspace = usuario.workspace
    
    # Verifica permissão para criar board
    if not check_permission_create_board(usuario, workspace):
        messages.error(request, "Você não tem permissão para criar setores.")
        return redirect("home")
    
    board = Board.objects.create(
        workspace=workspace,
        nome=request.POST.get("nome"),
        descricao=request.POST.get("descricao", ""),
        privado=request.POST.get("privado") == "on"
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
# BOARD - VISUALIZAÇÃO
# =========================
@login_required
def board_view(request, board_id):
    board = get_object_or_404(Board, id=board_id)
    usuario = request.user
    
    # Verifica permissão de acesso
    if not check_permission_user_board(usuario, board):
        messages.error(request, "Você não tem permissão para acessar este setor.")
        return redirect("home")
    
    status_list = Status.objects.filter(
        workflow__board=board
    ).order_by(
        "ordem"
    ).prefetch_related(
        "tasks__subtasks",
        "tasks__comments",
        "tasks__history"
    )

    usuarios = User.objects.filter(workspace=request.user.workspace)

    return render(
        request,
        "board.html",
        {
            "board": board,
            "status_list": status_list,
            "usuarios": usuarios,
            "user_tipo": usuario.tipo,
        }
    )


# =========================
# ADD TASK
# =========================
@login_required
def add_task(request, board_id):
    board = get_object_or_404(Board, id=board_id)
    usuario = request.user
    
    # Verifica permissão para criar tarefa
    if not check_permission_create_task(usuario, board):
        messages.error(request, "Você não tem permissão para criar tarefas neste setor.")
        return redirect("board", board_id=board.id)

    if request.method != "POST":
        return redirect("board", board_id=board.id)

    # Buscar o primeiro status do workflow padrão
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
    
    # REGRA: Usuário comum só pode criar tarefa para si mesmo
    if usuario.tipo == 'usuario':
        responsavel_id = usuario.id
    
    task = Task.objects.create(
        board=board,
        workflow=workflow,
        titulo=request.POST.get("titulo"),
        descricao=request.POST.get("descricao", ""),
        status=status,
        prioridade=request.POST.get("prioridade", "media"),
        responsavel_id=responsavel_id if responsavel_id else None,
        criado_por=usuario,
        atualizado_por=usuario
    )

    TaskHistory.objects.create(
        task=task,
        usuario=request.user,
        campo="Criação",
        valor_antigo="",
        valor_novo="Tarefa criada"
    )

    return redirect("board", board_id=board.id)


# =========================
# UPDATE TASK
# =========================
@login_required
def update_task(request, task_id):
    if request.method != "POST":
        return JsonResponse({"success": False})

    task = get_object_or_404(Task, id=task_id)
    usuario = request.user
    
    # Verifica permissão para editar
    if not check_permission_edit_task(usuario, task):
        return JsonResponse(
            {"success": False, "error": "Sem permissão para editar esta tarefa"},
            status=403
        )

    # REGRA: Usuário comum NÃO pode alterar status para "Concluído"
    novo_status = request.POST.get("status")
    if usuario.tipo == 'usuario':
        status_obj = get_object_or_404(Status, id=novo_status)
        if status_obj.nome.lower() == "concluído":
            return JsonResponse(
                {"success": False, "error": "Usuários comuns não podem concluir tarefas"},
                status=403
            )

    campos = {
        "titulo": request.POST.get("title"),
        "descricao": request.POST.get("description"),
        "prioridade": request.POST.get("prioridade"),
        "status": request.POST.get("status"),
        "responsavel": request.POST.get("responsavel")
    }

    for campo, novo_valor in campos.items():
        if campo == "status":
            antigo = str(task.status_id)
        elif campo == "responsavel":
            antigo = str(task.responsavel_id)
        else:
            antigo = str(getattr(task, campo))

        if str(antigo) != str(novo_valor):
            TaskHistory.objects.create(
                task=task,
                usuario=request.user,
                campo=campo,
                valor_antigo=antigo,
                valor_novo=str(novo_valor)
            )

    task.titulo = campos["titulo"]
    task.descricao = campos["descricao"]
    task.prioridade = campos["prioridade"]
    task.status_id = campos["status"]

    responsavel_valor = campos["responsavel"]
    task.responsavel_id = int(responsavel_valor) if responsavel_valor and responsavel_valor != '' else None

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
    
    # Verifica permissão para excluir
    if not check_permission_delete_task(usuario, task):
        messages.error(request, "Você não tem permissão para excluir esta tarefa.")
        return redirect("board", board_id=task.board.id)
    
    board_id = task.board.id
    task.delete()
    messages.success(request, "Tarefa excluída com sucesso!")
    return redirect("board", board_id=board_id)


# =========================
# COMPLETE TASK - APENAS GERENTE E ADMIN
# =========================
@login_required
def complete_task(request, task_id):
    """Endpoint específico para marcar tarefa como concluída"""
    task = get_object_or_404(Task, id=task_id)
    usuario = request.user
    
    # Verifica se o usuário pode completar a tarefa
    if not check_permission_complete_task(usuario, task):
        messages.error(request, "Apenas Gerentes e Administradores podem concluir tarefas.")
        return redirect("board", board_id=task.board.id)
    
    # Busca o status "Concluído"
    status_concluido = Status.objects.filter(
        workflow__board=task.board,
        nome__icontains="concluído"
    ).first()
    
    if not status_concluido:
        status_concluido = Status.objects.filter(
            workflow__board=task.board
        ).last()
    
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
        
        messages.success(request, "Tarefa concluída com sucesso!")
    
    return redirect("board", board_id=task.board.id)


# =========================
# DELETE BOARD - APENAS ADMIN E GERENTE
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
# COMMENT
# =========================
@login_required
def add_comment(request, task_id):
    if request.method != "POST":
        return JsonResponse({"success": False})

    task = get_object_or_404(Task, id=task_id)
    usuario = request.user
    
    # Verifica se o usuário tem acesso ao board da tarefa
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

    return JsonResponse({
        "success": True,
        "username": request.user.username,
        "texto": comment.texto
    })


# =========================
# SUBTASK
# =========================
@login_required
def add_subtask(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    usuario = request.user
    
    # Verifica se tem acesso ao board
    if not check_permission_user_board(usuario, task.board):
        return JsonResponse(
            {"success": False, "error": "Sem permissão"},
            status=403
        )

    if request.method == "POST":
        responsavel_id = request.POST.get("responsavel")
        
        # REGRA: Usuário comum só pode criar subtarefa para si mesmo
        if usuario.tipo == 'usuario':
            responsavel_id = usuario.id
        
        subtask = SubTask.objects.create(
            task=task,
            titulo=request.POST.get("titulo"),
            prioridade=request.POST.get("prioridade", "media"),
            responsavel_id=responsavel_id if responsavel_id else None,
            criado_por=usuario
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
                }
            })

    return redirect("board", board_id=task.board.id)


@login_required
def update_subtask(request, subtask_id):
    subtask = get_object_or_404(SubTask, id=subtask_id)
    usuario = request.user
    
    # Verifica permissão para editar subtask
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
                }
            })

    return redirect("board", board_id=subtask.task.board.id)


@login_required
def delete_subtask(request, subtask_id):
    subtask = get_object_or_404(SubTask, id=subtask_id)
    usuario = request.user
    
    # Verifica permissão para excluir subtask
    if not check_permission_delete_subtask(usuario, subtask):
        messages.error(request, "Você não tem permissão para excluir esta subtarefa.")
        return redirect("board", board_id=subtask.task.board.id)
    
    board_id = subtask.task.board.id
    subtask.delete()
    return redirect("board", board_id=board_id)


@login_required
def toggle_subtask(request, subtask_id):
    subtask = get_object_or_404(SubTask, id=subtask_id)
    usuario = request.user
    
    # Verifica permissão para alternar status
    if usuario.tipo == 'usuario':
        # Usuário comum só pode alternar se for responsável ou criador
        if not (usuario == subtask.responsavel or usuario == subtask.criado_por):
            messages.error(request, "Você não tem permissão para alterar esta subtarefa.")
            return redirect("board", board_id=subtask.task.board.id)
    
    subtask.concluida = not subtask.concluida
    subtask.save()
    return redirect("board", board_id=subtask.task.board.id)


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
        })
    
    return JsonResponse({'success': True, 'subtasks': data})