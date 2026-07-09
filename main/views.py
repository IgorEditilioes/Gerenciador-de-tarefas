from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Q
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import datetime

from .forms import LoginForm, PerfilForm
from .models import (
    User,
    Task,
    Board,
    Status,
    Comment,
    SubTask,
    TaskHistory,
    Workflow,
    BoardMember  # Para verificar membros do board
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

    # 🔥 FILTRO DE BOARDS POR PERFIL
    if usuario.tipo == 'admin':
        boards = Board.objects.all()
    elif usuario.tipo == 'gerente':
        boards = Board.objects.filter(workspace=workspace)
    else:
        from .models import BoardMember
        boards_ids = BoardMember.objects.filter(
            usuario=usuario
        ).values_list('board_id', flat=True)
        
        boards = Board.objects.filter(
            workspace=workspace,
            id__in=boards_ids
        )

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
# BUSCAR RESPONSÁVEIS POR BOARD (SETOR)
# =========================
@login_required
def buscar_responsaveis(request):
    """
    Busca usuários do mesmo board (setor) para serem responsáveis pela tarefa
    """
    termo = request.GET.get('term', '').strip()
    tarefa_id = request.GET.get('tarefa_id')
    board_id = request.GET.get('board_id')
    
    usuario_logado = request.user
    
    # Se não tiver board_id, tenta buscar da tarefa
    if not board_id and tarefa_id:
        try:
            tarefa = Task.objects.get(id=tarefa_id)
            board_id = tarefa.board.id
        except Task.DoesNotExist:
            pass
    
    # Se ainda não tiver board_id, retorna vazio
    if not board_id:
        return JsonResponse([], safe=False)
    
    # Buscar o board
    try:
        board = Board.objects.get(id=board_id)
    except Board.DoesNotExist:
        return JsonResponse([], safe=False)
    
    # Buscar membros do board (exceto o próprio usuário)
    membros_ids = BoardMember.objects.filter(
        board=board
    ).exclude(
        usuario=usuario_logado
    ).values_list('usuario_id', flat=True)
    
    usuarios = User.objects.filter(
        id__in=membros_ids,
        workspace=usuario_logado.workspace
    )
    
    # Se tiver um termo de busca, filtrar
    if termo:
        usuarios = usuarios.filter(
            Q(first_name__icontains=termo) |
            Q(last_name__icontains=termo) |
            Q(username__icontains=termo) |
            Q(email__icontains=termo)
        )
    
    # Se for uma tarefa específica, permitir o responsável atual
    if tarefa_id:
        try:
            tarefa = Task.objects.get(id=tarefa_id)
            if tarefa.responsavel and tarefa.responsavel.id != usuario_logado.id:
                # Adicionar o responsável atual à lista mesmo que não seja membro do board
                usuarios = usuarios | User.objects.filter(id=tarefa.responsavel.id)
        except Task.DoesNotExist:
            pass
    
    # Formatar para o Select2
    results = []
    for usuario in usuarios[:20]:  # Limitar a 20 resultados
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
    """
    Retorna todos os usuários do mesmo board (setor)
    """
    try:
        usuario_logado = request.user
        
        # Buscar o board
        board = get_object_or_404(Board, id=board_id)
        
        # Verificar se o usuário tem acesso ao board
        if not check_permission_user_board(usuario_logado, board):
            return JsonResponse({'error': 'Sem permissão'}, status=403)
        
        # Buscar membros do board (exceto o próprio usuário)
        membros_ids = BoardMember.objects.filter(
            board=board
        ).exclude(
            usuario=usuario_logado
        ).values_list('usuario_id', flat=True)
        
        usuarios = User.objects.filter(
            id__in=membros_ids,
            workspace=usuario_logado.workspace
        ).values('id', 'first_name', 'last_name', 'email', 'username')
        
        # Formatar nomes
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
    """
    View para atualizar o avatar do usuário via AJAX
    """
    try:
        usuario = get_object_or_404(User, id=id)
        
        # Verificar permissão
        if request.user.id != usuario.id:
            return JsonResponse({
                'success': False,
                'message': 'Permissão negada.'
            }, status=403)
        
        if request.FILES.get('avatar'):
            # Salvar o avatar
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
    """
    View para exibir e editar o perfil do usuário
    """
    usuario = get_object_or_404(User, id=id)
    
    # Verificar se o usuário logado é o mesmo do perfil
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
    
    # Adicionar o criador como membro do board
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
# BOARD VIEW
# =========================
@login_required
def board_view(request, board_id):
    board = get_object_or_404(Board, id=board_id)
    usuario = request.user
    
    if not check_permission_user_board(usuario, board):
        messages.error(request, "Você não tem permissão para acessar este setor.")
        return redirect("home")
    
    # Buscar status
    if usuario.tipo == 'admin':
        status_list = Status.objects.filter(
            workflow__board=board
        ).order_by("ordem").prefetch_related(
            "tasks__subtasks",
            "tasks__comments",
            "tasks__history"
        )
    elif usuario.tipo == 'gerente':
        status_list = Status.objects.filter(
            workflow__board=board
        ).order_by("ordem").prefetch_related(
            "tasks__subtasks",
            "tasks__comments",
            "tasks__history"
        )
    else:
        status_list = Status.objects.filter(
            workflow__board=board
        ).order_by("ordem").prefetch_related(
            "tasks__subtasks",
            "tasks__comments",
            "tasks__history"
        )

    # 🔥 CORREÇÃO: Buscar TODOS os membros do board (incluindo o próprio usuário)
    from .models import BoardMember
    
    # Buscar todos os membros do board
    membros_ids = BoardMember.objects.filter(
        board=board
    ).values_list('usuario_id', flat=True)
    
    # Buscar usuários membros do board (todos, sem filtro de tipo)
    usuarios_board = User.objects.filter(
        id__in=membros_ids,
        workspace=usuario.workspace,
        is_active=True
    ).order_by('first_name', 'last_name')
    
    # 🔥 IMPORTANTE: Garantir que o próprio usuário também esteja na lista
    if usuario not in usuarios_board:
        # Se o usuário logado não estiver na lista, adicionar
        usuarios_board = usuarios_board | User.objects.filter(id=usuario.id)

    # Todos os usuários do workspace (para outras funcionalidades)
    usuarios = User.objects.filter(
        workspace=request.user.workspace,
        is_active=True
    )

    # Data atual para comparação nos templates
    from datetime import date
    today = date.today()
    
    # Calcular data para daqui 3 dias
    from datetime import timedelta
    today_plus_3 = today + timedelta(days=3)

    return render(
        request,
        "board.html",
        {
            "board": board,
            "status_list": status_list,
            "usuarios": usuarios,
            "usuarios_board": usuarios_board,  # Todos os membros do board
            "user_tipo": usuario.tipo,
            "today": today,
            "today_plus_3": today_plus_3,
        }
    )


# =========================
# ADD TASK
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
    
    # REGRA: Usuário comum só pode criar tarefa para si mesmo
    if usuario.tipo == 'usuario':
        responsavel_id = usuario.id
    
    # REGRA: Verificar se o responsável é membro do board
    if responsavel_id and responsavel_id != '':
        responsavel = get_object_or_404(User, id=responsavel_id)
        # Verificar se o responsável é membro do board
        is_member = BoardMember.objects.filter(
            board=board,
            usuario=responsavel
        ).exists()
        
        # Se não for admin/gerente e o responsável não for membro do board
        if usuario.tipo not in ['admin', 'gerente'] and not is_member:
            messages.error(request, "Você só pode atribuir tarefas para membros deste setor.")
            return redirect("board", board_id=board.id)
    
    # Converter data_entrega para None se vazio
    if data_entrega == '':
        data_entrega = None

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
        data_entrega=data_entrega  # 🔥 ADICIONADO: Data de entrega
    )

    TaskHistory.objects.create(
        task=task,
        usuario=request.user,
        campo="Criação",
        valor_antigo="",
        valor_novo="Tarefa criada"
    )

    messages.success(request, "Tarefa criada com sucesso!")
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
    
    if not check_permission_edit_task(usuario, task):
        return JsonResponse(
            {"success": False, "error": "Sem permissão para editar esta tarefa"},
            status=403
        )

    # Verificar status "Concluído"
    novo_status_id = request.POST.get("status")
    if usuario.tipo == 'usuario':
        status_obj = get_object_or_404(Status, id=novo_status_id)
        if status_obj.nome.lower() in ["concluído", "concluido"]:
            return JsonResponse(
                {"success": False, "error": "Usuários comuns não podem concluir tarefas"},
                status=403
            )

    # Verificar se o novo responsável é membro do board
    novo_responsavel_id = request.POST.get("responsavel")
    if novo_responsavel_id and novo_responsavel_id != '':
        try:
            novo_responsavel = User.objects.get(id=novo_responsavel_id)
            # Se o usuário não for admin/gerente, verifica se é membro do board
            if usuario.tipo not in ['admin', 'gerente']:
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

    # 🔥 ADICIONADO: Processar data_entrega
    data_entrega = request.POST.get("data_entrega")
    if data_entrega == '':
        data_entrega = None

    campos = {
        "titulo": request.POST.get("title"),
        "descricao": request.POST.get("description"),
        "prioridade": request.POST.get("prioridade"),
        "status": request.POST.get("status"),
        "responsavel": request.POST.get("responsavel"),
        "data_entrega": data_entrega  # 🔥 ADICIONADO
    }

    for campo, novo_valor in campos.items():
        if campo == "status":
            antigo = str(task.status_id)
        elif campo == "responsavel":
            antigo = str(task.responsavel_id)
        elif campo == "data_entrega":
            antigo = str(task.data_entrega) if task.data_entrega else ""
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

    # 🔥 ADICIONADO: Atualizar data_entrega
    task.data_entrega = campos["data_entrega"]

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
    
    if not check_permission_delete_task(usuario, task):
        messages.error(request, "Você não tem permissão para excluir esta tarefa.")
        return redirect("board", board_id=task.board.id)
    
    board_id = task.board.id
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
# COMMENT
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
    
    if not check_permission_user_board(usuario, task.board):
        return JsonResponse(
            {"success": False, "error": "Sem permissão"},
            status=403
        )

    if request.method == "POST":
        responsavel_id = request.POST.get("responsavel")
        data_entrega = request.POST.get("data_entrega")
        
        # Converter data_entrega para None se vazio
        if data_entrega == '':
            data_entrega = None
        
        if usuario.tipo == 'usuario':
            responsavel_id = usuario.id
        
        # Verificar se o responsável é membro do board
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
            data_entrega=data_entrega  # 🔥 ADICIONADO: Data de entrega
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
        
        # 🔥 ADICIONADO: Atualizar data_entrega
        data_entrega = request.POST.get("data_entrega")
        if data_entrega == '':
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