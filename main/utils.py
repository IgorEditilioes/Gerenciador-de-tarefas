# main/utils.py

from datetime import datetime

from django.core.mail import send_mail
from django.conf import settings


def enviar_email_notificacao(destinatario, assunto, mensagem):
    """
    Envia um e-mail simples sem template HTML
    """
    if not destinatario or not destinatario.email:
        return
    
    try:
        send_mail(
            subject=assunto,
            message=mensagem,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[destinatario.email],
            fail_silently=False,
        )
        print(f"✅ E-mail enviado para {destinatario.email}")
    except Exception as e:
        print(f"❌ Erro ao enviar e-mail: {e}")


def notificar_email_atribuicao(usuario, task):
    """
    Envia e-mail quando o usuário é atribuído a uma tarefa
    """
    if not usuario:
        return
    
    assunto = f"📋 Você foi atribuído a uma tarefa: {task.titulo}"
    mensagem = f"""
Olá {usuario.get_full_name() or usuario.username}!

Você foi atribuído à tarefa:

📌 Tarefa: {task.titulo}
📝 Descrição: {task.descricao or 'Sem descrição'}
📊 Prioridade: {task.get_prioridade_display()}
📅 Data de entrega: {task.data_entrega.strftime('%d/%m/%Y') if task.data_entrega else 'Não definida'}
🏷️ Setor: {task.board.nome}

Para visualizar a tarefa, acesse:
{settings.SITE_URL}/board/{task.board.id}/?open_task={task.id}

Atenciosamente,
Equipe TaskFlow
"""
    
    enviar_email_notificacao(usuario, assunto, mensagem)


def notificar_email_mencao(usuario, comentario, task):
    """
    Envia e-mail quando o usuário é mencionado em um comentário
    """
    if not usuario:
        return
    
    nome_origem = comentario.usuario.get_full_name() or comentario.usuario.username
    assunto = f"💬 {nome_origem} mencionou você em um comentário"
    mensagem = f"""
Olá {usuario.get_full_name() or usuario.username}!

{nome_origem} mencionou você em um comentário na tarefa:

📌 Tarefa: {task.titulo}
💬 Comentário: {comentario.texto}

Para visualizar o comentário, acesse:
{settings.SITE_URL}/board/{task.board.id}/?open_task={task.id}

Atenciosamente,
Equipe TaskFlow
"""
    
    enviar_email_notificacao(usuario, assunto, mensagem)


# utils.py ou views.py

def notificar_email_status_concluido(task, usuario):
    """
    Envia e-mail quando uma tarefa é concluída
    """
    if not task.responsavel:
        return
    
    # Não enviar e-mail se a mesma pessoa que concluiu é o responsável
    if task.responsavel == usuario:
        return
    
    nome_origem = usuario.get_full_name() or usuario.username
    assunto = f"✅ Tarefa concluída: {task.titulo}"
    mensagem = f"""
Olá {task.responsavel.get_full_name() or task.responsavel.username}!

A tarefa foi marcada como concluída:

📌 Tarefa: {task.titulo}
📝 Descrição: {task.descricao or 'Sem descrição'}
👤 Concluída por: {nome_origem}
📅 Data de conclusão: {datetime.now().strftime('%d/%m/%Y %H:%M')}
🏷️ Setor: {task.board.nome}

Para visualizar a tarefa, acesse:
{settings.SITE_URL}/board/{task.board.id}/?open_task={task.id}

Atenciosamente,
Equipe TaskFlow
"""
    
    enviar_email_notificacao(task.responsavel, assunto, mensagem)