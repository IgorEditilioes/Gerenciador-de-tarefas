from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .forms import LoginForm
from .models import User, Task, Board, Status



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

    board = get_object_or_404(Board, id=board_id)

    status_list = Status.objects.filter(
        workflow__board=board
    ).order_by("ordem")

    tasks = Task.objects.filter(
        board=board
    )


    contexto = {

        "board": board,
        "status_list": status_list,
        "tasks": tasks,

    }

    return render(
        request,
        "core/board.html",
        contexto
    )