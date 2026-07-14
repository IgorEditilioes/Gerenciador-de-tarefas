from models import BoardMember

def pode_ver_setor(usuario, board):
    """
    Verifica se o usuário pode visualizar o setor (board)
    """
    # Admin pode ver todos os setores
    if usuario.tipo == "admin":
        return True

    # Gerente pode ver setores do seu workspace
    if usuario.tipo == "gerente":
        return usuario.workspace == board.workspace

    # Usuário comum: verifica se é membro do board
    return BoardMember.objects.filter(
        usuario=usuario,
        board=board
    ).exists()


def pode_editar_tarefa(usuario, task):
    """
    Verifica se o usuário pode editar a tarefa
    """
    # Admin pode editar qualquer tarefa
    if usuario.tipo == "admin":
        return True
    
    # Gerente pode editar qualquer tarefa do workspace
    if usuario.tipo == "gerente":
        return usuario.workspace == task.board.workspace

    # Usuário comum: só pode editar se for o criador ou responsável
    return task.criado_por == usuario or task.responsavel == usuario


def pode_excluir_tarefa(usuario, task):
    """
    Verifica se o usuário pode excluir a tarefa
    """
    # Admin pode excluir qualquer tarefa
    if usuario.tipo == "admin":
        return True
    
    # Gerente pode excluir qualquer tarefa do workspace
    if usuario.tipo == "gerente":
        return usuario.workspace == task.board.workspace

    # Usuário comum NÃO pode excluir tarefas
    return False


def pode_completar_tarefa(usuario, task):
    """
    Verifica se o usuário pode marcar a tarefa como concluída
    """
    # Admin pode completar qualquer tarefa
    if usuario.tipo == "admin":
        return True
    
    # Gerente pode completar qualquer tarefa do workspace
    if usuario.tipo == "gerente":
        return usuario.workspace == task.board.workspace

    # Usuário comum NÃO pode completar tarefas
    return False