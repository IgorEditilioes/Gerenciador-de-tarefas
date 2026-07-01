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
        related_name="boards"
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
        related_name="membros_boards"
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
        related_name="workflows_filhos"
    )


    padrao = models.BooleanField(
        default=False
    )


    def __str__(self):

        return self.nome





# Status
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




# Tarefa principal
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
        on_delete=models.PROTECT,
        related_name="tarefas"
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
        blank=True,
        related_name="tarefas_criadas"
    )

    atualizado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tarefas_atualizadas"
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
        ordering = ["ordem"]

    def __str__(self):
        return self.titulo





# Comentários
class Comment(models.Model):

    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="comments"
    )


    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="comentarios"
    )


    texto = models.TextField()


    criado_em = models.DateTimeField(
        auto_now_add=True
    )


    atualizado_em = models.DateTimeField(
        auto_now=True
    )


    def __str__(self):

        return f"Comentário - {self.task}"






# Subtarefas com estrutura semelhante a Task
class SubTask(models.Model):


    PRIORIDADES = (

        ("baixa", "Baixa"),
        ("media", "Média"),
        ("alta", "Alta"),
        ("urgente", "Urgente"),

    )



    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="subtasks"
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



    concluida = models.BooleanField(
        default=False
    )



    responsavel = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subtarefas_responsaveis"
    )



    criado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="subtarefas_criadas"
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



    def __str__(self):

        return self.titulo





class TaskHistory(models.Model):

    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="history"
    )

    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
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

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.task.titulo} - {self.campo}"