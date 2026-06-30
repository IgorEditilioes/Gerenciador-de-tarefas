from django.db import models
from django.contrib.auth.models import AbstractUser


# Usuário customizado
class User(AbstractUser):

    TIPOS = (

        ("admin", "Administrador"),

        ("gerente", "Gerente"),

        ("usuario", "Usuário"),

    )


    tipo = models.CharField(
        max_length=20,
        choices=TIPOS,
        default="usuario"
    )


    workspace = models.ForeignKey(
        "Workspace",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="usuarios"
    )


    def __str__(self):
        return self.username


# Empresa / Ambiente
class Workspace(models.Model):

    nome = models.CharField(
        max_length=100
    )


    criado_em = models.DateTimeField(
        auto_now_add=True
    )


    def __str__(self):
        return self.nome


# Setor / Board
class Board(models.Model):

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="setores"
    )


    nome = models.CharField(
        max_length=100
    )


    descricao = models.TextField(
        blank=True
    )


    privado = models.BooleanField(
        default=False
    )


    criado_em = models.DateTimeField(
        auto_now_add=True
    )


    def __str__(self):
        return self.nome


# Usuários dentro do setor
class BoardMember(models.Model):

    PERFIS = (

        ("gerente", "Gerente"),

        ("usuario", "Usuário"),

    )


    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="participacoes"
    )


    board = models.ForeignKey(
        Board,
        on_delete=models.CASCADE,
        related_name="membros"
    )


    perfil = models.CharField(
        max_length=20,
        choices=PERFIS,
        default="usuario"
    )


    def __str__(self):

        return f"{self.usuario} - {self.board}"


# Workflow
class Workflow(models.Model):

    board = models.ForeignKey(
        Board,
        on_delete=models.CASCADE,
        related_name="workflows"
    )


    nome = models.CharField(
        max_length=100
    )


    workflow_pai = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="derivados"
    )


    padrao = models.BooleanField(
        default=False
    )


    def __str__(self):

        return self.nome


# Status principal
class Status(models.Model):

    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name="status"
    )


    nome = models.CharField(
        max_length=100
    )


    ordem = models.PositiveIntegerField(
        default=0
    )


    cor = models.CharField(
        max_length=20,
        default="#000000"
    )




    class Meta:

        ordering = [
            "ordem"
        ]



    def __str__(self):

        return self.nome


# Tarefa / Card
class Task(models.Model):

    PRIORIDADES = (

        ("baixa", "Baixa"),

        ("media", "Média"),

        ("alta", "Alta"),

        ("urgente", "Urgente"),

    )

    board = models.ForeignKey(
        Board,
        on_delete=models.CASCADE,
        related_name="tarefas"
    )

    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.PROTECT
    )

    titulo = models.CharField(
        max_length=200
    )

    descricao = models.TextField(
        blank=True
    )

    prioridade = models.CharField(
        max_length=20,
        choices=PRIORIDADES,
        default="media"
    )

    status = models.ForeignKey(
        Status,
        on_delete=models.PROTECT,
        default='Pendente',
        related_name="tasks"
    )


    responsavel = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tarefas_responsaveis"
    )

    criado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="tarefas_criadas"
    )


    ordem = models.PositiveIntegerField(
        default=0
    )


    data_entrega = models.DateField(
        null=True,
        blank=True
    )


    criado_em = models.DateTimeField(
        auto_now_add=True
    )


    atualizado_em = models.DateTimeField(
        auto_now=True
    )


    class Meta:

        ordering = [
            "ordem"
        ]



    def __str__(self):

        return self.titulo


class Comment(models.Model):

    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="comments"
    )

    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    texto = models.TextField()

    criado_em = models.DateTimeField(
        auto_now_add=True
    )

    atualizado_em = models.DateTimeField(
        auto_now=True
    )


    def __str__(self):
        return f"Comentário em {self.task.titulo}"


# Subtarefas
class SubTask(models.Model):

    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="subtasks"
    )


    titulo = models.CharField(
        max_length=200
    )


    concluida = models.BooleanField(
        default=False
    )


    descricao = models.TextField(
        blank=True
    )


    criado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="subtarefas_criadas"
    )


    criado_em = models.DateTimeField(
        auto_now_add=True
    )


    atualizado_em = models.DateTimeField(
        auto_now=True
    )


    def __str__(self):

        return self.titulo


# Histórico da tarefa
class TaskHistory(models.Model):

    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="history"
    )

    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )

    campo = models.CharField(
        max_length=100
    )

    valor_antigo = models.TextField(
        null=True,
        blank=True
    )

    valor_novo = models.TextField(
        null=True,
        blank=True
    )

    criado_em = models.DateTimeField(
        auto_now_add=True
    )


    def __str__(self):
        return f"{self.task.titulo} - {self.campo}"
    

