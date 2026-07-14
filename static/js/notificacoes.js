function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function carregarNotificacoes() {
    const container = document.getElementById('conteudo-notificacoes');
    if (!container) return;
    
    fetch('/notificacoes/', {
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        const contador = document.getElementById('contador-notificacoes');
        
        if (data.total_nao_lidas > 0) {
            contador.textContent = data.total_nao_lidas;
            contador.style.display = 'inline';
            // Adicionar classe para animação do sino
            document.querySelector('#sino-notificacoes .fa-bell')?.classList.add('has-notification');
        } else {
            contador.style.display = 'none';
            document.querySelector('#sino-notificacoes .fa-bell')?.classList.remove('has-notification');
        }
        
        if (data.notificacoes.length === 0) {
            container.innerHTML = `
                <li class="dropdown-item text-center text-muted py-4">
                    <i class="fas fa-bell-slash" style="font-size: 32px; display: block; margin-bottom: 8px;"></i>
                    Nenhuma notificação
                </li>
            `;
        } else {
            let html = '';
            data.notificacoes.forEach(notif => {
                const bgColor = notif.lida ? '' : 'background-color: #f0f4ff;';
                const borderColor = notif.lida ? '' : 'border-left: 3px solid #667eea;';
                
                // Link para a tarefa se tiver task_id
                const link = notif.task_id ? `onclick="abrirNotificacao(${notif.id}, '${notif.tipo}', ${notif.task_id})"` : '';
                
                html += `
                    <li class="dropdown-item" style="${bgColor} ${borderColor} padding: 12px 16px; cursor: pointer;" 
                        ${link}>
                        <div class="d-flex align-items-start">
                            <div class="flex-shrink-0" style="margin-right: 12px;">
                                <div style="width: 36px; height: 36px; border-radius: 50%; background: ${notif.cor}20; display: flex; align-items: center; justify-content: center; color: ${notif.cor};">
                                    <i class="fas ${notif.icone}"></i>
                                </div>
                            </div>
                            <div class="flex-grow-1">
                                <div style="font-size: 13px; color: #1a1a2e; line-height: 1.4;">${notif.mensagem}</div>
                                <small class="text-muted" style="font-size: 11px;">
                                    <i class="far fa-clock"></i> ${notif.criado_em}
                                    ${!notif.lida ? '<span class="badge bg-primary ms-2" style="font-size: 9px;">Nova</span>' : ''}
                                </small>
                            </div>
                        </div>
                    </li>
                `;
            });
            container.innerHTML = html;
        }
    })
    .catch(error => {
        console.error('Erro ao carregar notificações:', error);
        container.innerHTML = `
            <li class="dropdown-item text-center text-danger py-3">
                <i class="fas fa-exclamation-circle"></i> Erro ao carregar notificações
            </li>
        `;
    });
}

function abrirNotificacao(notificacaoId, tipo, taskId) {
    // Marcar como lida
    fetch(`/notificacao/${notificacaoId}/marcar-lida/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'X-Requested-With': 'XMLHttpRequest'
        }
    });
    
    if (taskId) {
        const dropdown = bootstrap.Dropdown.getInstance(document.getElementById('sino-notificacoes'));
        if (dropdown) dropdown.hide();
        
        // Verificar se está no board ou na home
        if (typeof openTaskModal === 'function') {
            // Está no board
            openTaskModal(taskId);
        } else {
            // Está na home - redirecionar para o board
            window.location.href = `/board/${taskId}/`;
        }
    }
}

function marcarTodasLidas() {
    if (!confirm('Marcar todas as notificações como lidas?')) return;
    
    fetch('/notificacoes/marcar-todas-lidas/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.getElementById('contador-notificacoes').style.display = 'none';
            document.querySelector('#sino-notificacoes .fa-bell')?.classList.remove('has-notification');
            carregarNotificacoes();
        }
    });
}

// Inicializar quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    // Carregar notificações
    const sino = document.getElementById('sino-notificacoes');
    if (sino) {
        sino.addEventListener('click', function() {
            carregarNotificacoes();
        });
    }
    
    // Carregar contador inicial
    setTimeout(carregarNotificacoes, 500);
});

// Atualizar notificações a cada 60 segundos
setInterval(() => {
    carregarNotificacoes();
}, 60000);