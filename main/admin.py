from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model

from .models import (
    Workspace,
    Board,
    BoardMember,
    Workflow,
    Status,
    Task,
    SubTask
)


User = get_user_model()



# ==========================
# USER PERSONALIZADO
# ==========================

@admin.register(User)
class CustomUserAdmin(UserAdmin):

    list_display = (
        "username",
        "email",
        "tipo",
        "workspace",
        "is_active",
        "is_staff",
    )


    list_filter = (
        "tipo",
        "workspace",
        "is_staff",
        "is_active",
    )


    fieldsets = UserAdmin.fieldsets + (

        (
            "Configurações do sistema",
            {
                "fields": (
                    "tipo",
                    "workspace",
                )
            }
        ),

    )



# ==========================
# EMPRESA
# ==========================

@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):

    list_display = (
        "nome",
        "criado_em",
    )



# ==========================
# SETORES
# ==========================

@admin.register(Board)
class BoardAdmin(admin.ModelAdmin):

    list_display = (
        "nome",
        "workspace",
        "privado",
    )


    list_filter = (
        "workspace",
        "privado",
    )



# ==========================
# MEMBROS DO SETOR
# ==========================

@admin.register(BoardMember)
class BoardMemberAdmin(admin.ModelAdmin):

    list_display = (
        "usuario",
        "board",
        "perfil",
    )


    list_filter = (
        "perfil",
        "board",
    )



# ==========================
# WORKFLOW
# ==========================

@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):

    list_display = (
        "nome",
        "board",
        "padrao",
        "workflow_pai",
    )


    list_filter = (
        "board",
        "padrao",
    )



# ==========================
# STATUS
# ==========================

@admin.register(Status)
class StatusAdmin(admin.ModelAdmin):

    list_display = (
        "nome",
        "workflow",
        "ordem",
        "cor",
    )


    list_filter = (
        "workflow",
    )




# ==========================
# TASKS
# ==========================

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):

    list_display = (
        "titulo",
        "board",
        "status",
        "responsavel",
        "criado_por",
        "criado_em",
    )


    list_filter = (

        "board",
        "workflow",
        "status",
        "responsavel",
    )


    search_fields = (

        "titulo",
        "descricao",
    )


    ordering = (
        "-criado_em",
    )


@admin.register(SubTask)
class SubtaskAdmin(admin.ModelAdmin):

    list_display = (
        "titulo",
        "task",
        "concluida",
        "criado_por",
        "criado_em",
        "atualizado_em",
    )

    list_filter = (
        "concluida",
        "criado_em",
    )

    search_fields = (
        "titulo",
        "descricao",
        "task__titulo",
        "criado_por__username",
    )

    list_editable = (
        "concluida",
    )

    readonly_fields = (
        "criado_em",
        "atualizado_em",
    )

    ordering = (
        "-criado_em",
    )