from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .forms import LoginForm
from .models import User, Task, Board, Status, Comment, TaskHistory



def login_view(request):


    if request.method == "POST":

        form = LoginForm(request.POST)


        if form.is_valid():

            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]

            usuario = User.objects.filter(
                username=username
            ).first()


            if usuario:
                user = authenticate(
                    request,
                    username=usuario.username,
                    password=password
                )

                if user:
                    login(request, user)

                    return redirect("home")
                else:
                    messages.error(
                        request,
                        "Senha inválida"
                    )
            else:

                messages.error(
                    request,
                    "Usuário não encontrado"
                )
    else:
        form = LoginForm()
    return render(
        request,
        "login.html",
        {
            "form": form
        }
    )


@login_required
def logout_view(request):
    logout(request)

    return redirect('login')


@login_required
def home(request):

    usuario = request.user


    workspace = usuario.workspace


    boards = Board.objects.filter(
        workspace=workspace
    )


    total_tarefas = Task.objects.filter(
        board__workspace=workspace
    ).count()

    contexto = {

        "usuario": usuario,

        "workspace": workspace,

        "boards": boards,

        "total_tarefas": total_tarefas,

    }

    return render(
        request,
        "home.html",
        contexto
    )


@login_required
def board_view(request, board_id):

    board = get_object_or_404(
        Board,
        id=board_id
    )


    status_list = Status.objects.filter(
        workflow__board=board
    ).order_by(
        "ordem"
    ).prefetch_related(
        "tasks__subtasks"
    )


    contexto = {

        "board": board,
        "status_list": status_list,

    }


    return render(
        request,
        "board.html",
        contexto
    )



def update_task(request, task_id):

    task = get_object_or_404(Task, id=task_id)

    if request.method == "POST":

        titulo_antigo = task.titulo
        descricao_antiga = task.descricao
        status_antigo = task.status

        novo_titulo = request.POST.get("title")
        nova_descricao = request.POST.get("description")
        novo_status = Status.objects.get(
            id=request.POST.get("status")
        )


        if titulo_antigo != novo_titulo:

            TaskHistory.objects.create(
                task=task,
                usuario=request.user,
                campo="Título",
                valor_antigo=titulo_antigo,
                valor_novo=novo_titulo
            )


        if descricao_antiga != nova_descricao:

            TaskHistory.objects.create(
                task=task,
                usuario=request.user,
                campo="Descrição",
                valor_antigo=descricao_antiga,
                valor_novo=nova_descricao
            )


        if status_antigo != novo_status:

            TaskHistory.objects.create(
                task=task,
                usuario=request.user,
                campo="Status",
                valor_antigo=status_antigo.nome,
                valor_novo=novo_status.nome
            )


        task.titulo = novo_titulo
        task.descricao = nova_descricao
        task.status = novo_status

        task.save()


        return redirect(
            "board",
            board_id=task.board.id
        )
    

@login_required
def add_comment(request, task_id):

    task = get_object_or_404(
        Task,
        id=task_id
    )

    if request.method == "POST":

        texto = request.POST.get("comment")

        if texto:

            Comment.objects.create(
                task=task,
                usuario=request.user,
                texto=texto
            )

            TaskHistory.objects.create(
                task=task,
                usuario=request.user,
                campo="Comentário",
                valor_antigo="",
                valor_novo=texto
            )

    return redirect(
        "board",
        board_id=task.board.id
    )