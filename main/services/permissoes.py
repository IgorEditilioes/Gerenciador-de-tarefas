from models import BoardMember

def pode_ver_setor(usuario, board):

    if usuario.tipo == "admin":
        return True


    if usuario.tipo == "gerente":
        return True


    return BoardMember.objects.filter(
        usuario=usuario,
        board=board
    ).exists()


def pode_editar_tarefa(usuario, task):

    if usuario.tipo in ["admin", "gerente"]:
        return True


    return task.criado_por == usuario