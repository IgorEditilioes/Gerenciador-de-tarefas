from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse

from .forms import LoginForm
from .models import (
    User,
    Task,
    Board,
    Status,
    Comment,
    SubTask,
    TaskHistory
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

    boards = Board.objects.filter(workspace=workspace)

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
            "total_tarefas": total_tarefas
        }
    )


# =========================
# BOARD
# =========================
@login_required
def board_view(request, board_id):

    board = get_object_or_404(Board, id=board_id)

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
            "usuarios": usuarios
        }
    )


# =========================
# UPDATE TASK
# =========================
@login_required
def update_task(request, task_id):

    if request.method != "POST":
        return JsonResponse({"success": False})

    task = get_object_or_404(Task, id=task_id)

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

    task.responsavel_id = (
        campos["responsavel"] if campos["responsavel"] else None
    )

    task.atualizado_por = request.user
    task.save()

    return JsonResponse({"success": True})


# =========================
# ADD TASK
# =========================
@login_required
def add_task(request, board_id):

    board = get_object_or_404(Board, id=board_id)

    if request.method != "POST":
        return redirect("board", board_id=board.id)

    if board.workspace != request.user.workspace:
        return JsonResponse(
            {"success": False, "error": "Sem permissão"},
            status=403
        )

    status = get_object_or_404(
        Status,
        id=request.POST.get("status")
    )

    task = Task.objects.create(
        board=board,
        workflow=status.workflow,
        titulo=request.POST.get("titulo"),
        descricao=request.POST.get("descricao", ""),
        status=status,
        prioridade="media",
        criado_por=request.user,
        atualizado_por=request.user
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
# COMMENT
# =========================
@login_required
def add_comment(request, task_id):

    if request.method != "POST":
        return JsonResponse({"success": False})

    task = get_object_or_404(Task, id=task_id)

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

    if request.method == "POST":

        SubTask.objects.create(
            task=task,
            titulo=request.POST.get("titulo"),
            prioridade=request.POST.get("prioridade"),
            responsavel_id=request.POST.get("responsavel") or None,
            criado_por=request.user
        )

    return redirect("board", board_id=task.board.id)


@login_required
def update_subtask(request, subtask_id):

    subtask = get_object_or_404(SubTask, id=subtask_id)

    if request.method == "POST":

        subtask.titulo = request.POST.get("titulo")
        subtask.prioridade = request.POST.get("prioridade")
        subtask.responsavel_id = request.POST.get("responsavel") or None

        subtask.save()

    return redirect("board", board_id=subtask.task.board.id)


# =========================
# DELETE TASK
# =========================
@login_required
def delete_task(request, task_id):

    task = get_object_or_404(Task, id=task_id)
    board_id = task.board.id
    task.delete()

    return redirect("board", board_id=board_id)


@login_required
def delete_subtask(request, subtask_id):

    subtask = get_object_or_404(SubTask, id=subtask_id)
    board_id = subtask.task.board.id
    subtask.delete()

    return redirect("board", board_id=board_id)


# =========================
# TOGGLE SUBTASK
# =========================
@login_required
def toggle_subtask(request, subtask_id):

    subtask = get_object_or_404(SubTask, id=subtask_id)
    subtask.concluida = not subtask.concluida
    subtask.save()

    return redirect("board", board_id=subtask.task.board.id)