from django.db import models
from django.contrib.auth.models import AbstractUser


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



class Workspace(models.Model):

    nome = models.CharField(
        max_length=100
    )


    criado_em = models.DateTimeField(
        auto_now_add=True
    )


    def __str__(self):

        return self.nome



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



class Task(models.Model):

    PRIORIDADES = (
        ("baixa", "Baixa"),
        ("media", "Média"),
        ("alta", "Alta"),
        ("urgente", "Urgente"),
    )

    permite_edicao_usuario = models.BooleanField(
        default=True,
        verbose_name="Permitir edição por usuários",
        help_text="Permite que usuários comuns editem esta tarefa"
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
    


class Notification(models.Model):
    TIPOS = (
        ('comentario', 'Comentário'),
        ('mencao', 'Menção'),
        ('atribuicao', 'Atribuição'),
        ('subtarefa', 'Subtarefa Concluída'),
        ('vencimento', 'Vencimento Próximo'),
    )
    
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notificacoes'
    )
    
    tipo = models.CharField(
        max_length=20,
        choices=TIPOS
    )
    
    mensagem = models.TextField()
    
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notificacoes'
    )
    
    comentario = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notificacoes'
    )
    
    subtask = models.ForeignKey(
        SubTask,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notificacoes'
    )
    
    origem = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notificacoes_criadas'
    )
    
    lida = models.BooleanField(default=False)
    
    criado_em = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-criado_em']
    
    def __str__(self):
        return f"{self.usuario} - {self.tipo} - {self.criado_em}"


# =========================
# ANEXOS
# =========================
class Attachment(models.Model):
    """
    Modelo para anexos de tarefas
    """
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='anexos'
    )
    
    arquivo = models.FileField(
        upload_to='anexos/%Y/%m/%d/',
        max_length=255
    )
    
    nome = models.CharField(
        max_length=255,
        blank=True
    )
    
    tamanho = models.PositiveIntegerField(
        default=0
    )
    
    tipo = models.CharField(
        max_length=100,
        blank=True
    )
    
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='anexos_enviados'
    )
    
    criado_em = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-criado_em']
    
    def __str__(self):
        return self.nome or self.arquivo.name
    
    def get_tamanho_formatado(self):
        """Retorna o tamanho formatado (KB, MB, GB)"""
        if self.tamanho < 1024:
            return f"{self.tamanho} B"
        elif self.tamanho < 1024 * 1024:
            return f"{self.tamanho / 1024:.1f} KB"
        elif self.tamanho < 1024 * 1024 * 1024:
            return f"{self.tamanho / (1024 * 1024):.1f} MB"
        else:
            return f"{self.tamanho / (1024 * 1024 * 1024):.1f} GB"
    
    def get_icone(self):
        """Retorna o ícone baseado no tipo do arquivo"""
        if not self.tipo:
            return 'fa-file'
        
        tipo = self.tipo.lower()
        if 'image' in tipo:
            return 'fa-file-image'
        elif 'pdf' in tipo:
            return 'fa-file-pdf'
        elif 'word' in tipo or 'document' in tipo:
            return 'fa-file-word'
        elif 'excel' in tipo or 'sheet' in tipo:
            return 'fa-file-excel'
        elif 'powerpoint' in tipo or 'presentation' in tipo:
            return 'fa-file-powerpoint'
        elif 'zip' in tipo or 'rar' in tipo or 'compressed' in tipo:
            return 'fa-file-archive'
        elif 'text' in tipo:
            return 'fa-file-alt'
        else:
            return 'fa-file'
    
    def get_cor_icone(self):
        """Retorna a cor do ícone baseado no tipo"""
        tipo = self.tipo.lower() if self.tipo else ''
        if 'image' in tipo:
            return '#8b5cf6'
        elif 'pdf' in tipo:
            return '#ef4444'
        elif 'word' in tipo or 'document' in tipo:
            return '#3b82f6'
        elif 'excel' in tipo or 'sheet' in tipo:
            return '#22c55e'
        elif 'powerpoint' in tipo or 'presentation' in tipo:
            return '#f59e0b'
        else:
            return '#6b7280'