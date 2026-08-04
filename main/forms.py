from django import forms
from .models import User  
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone
import re
from .models import Task, Board, BoardMember, Comment 
from .decorators import check_permission_edit_task, check_permission_create_task


# ==========================================
# SEUS FORMULÁRIOS EXISTENTES (mantidos intactos)
# ==========================================

class LoginForm(forms.Form):
    username = forms.CharField(
        label="Username",
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "Digite seu Username"
            }
        )
    )

    password = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Digite sua senha"
            }
        )
    )


class PerfilForm(forms.Form):
    """
    Formulário para edição de perfil do usuário
    Permite alterar nome completo e senha
    """
    
    first_name = forms.CharField(
        label='Nome',
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite seu nome',
            'id': 'nome'
        })
    )
    
    last_name = forms.CharField(
        label='Sobrenome',
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite seu sobrenome',
            'id': 'sobrenome'
        })
    )
    
    senha_atual = forms.CharField(
        label='Senha atual',
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite sua senha atual',
            'id': 'senhaAtual',
            'autocomplete': 'current-password'
        })
    )
    
    nova_senha = forms.CharField(
        label='Nova senha',
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite a nova senha',
            'id': 'novaSenha',
            'autocomplete': 'new-password'
        })
    )
    
    confirmar_senha = forms.CharField(
        label='Confirmar nova senha',
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirme a nova senha',
            'id': 'confirmarSenha',
            'autocomplete': 'new-password'
        })
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(PerfilForm, self).__init__(*args, **kwargs)
        
        if self.user and self.user.is_authenticated:
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name
    
    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name', '').strip()
        if not first_name:
            raise ValidationError('O nome é obrigatório.')
        if len(first_name) < 2:
            raise ValidationError('O nome deve ter pelo menos 2 caracteres.')
        if len(first_name) > 30:
            raise ValidationError('O nome deve ter no máximo 30 caracteres.')
        if not re.match(r'^[A-Za-zÀ-ÿ\s]+$', first_name):
            raise ValidationError('O nome deve conter apenas letras e espaços.')
        return first_name
    
    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name', '').strip()
        if not last_name:
            raise ValidationError('O sobrenome é obrigatório.')
        if len(last_name) < 2:
            raise ValidationError('O sobrenome deve ter pelo menos 2 caracteres.')
        if len(last_name) > 30:
            raise ValidationError('O sobrenome deve ter no máximo 30 caracteres.')
        if not re.match(r'^[A-Za-zÀ-ÿ\s]+$', last_name):
            raise ValidationError('O sobrenome deve conter apenas letras e espaços.')
        return last_name
    
    def clean_senha_atual(self):
        senha_atual = self.cleaned_data.get('senha_atual')
        nova_senha = self.cleaned_data.get('nova_senha')
        
        if not nova_senha:
            return senha_atual
        
        if not senha_atual:
            raise ValidationError('Digite sua senha atual para alterar a senha.')
        
        if self.user and not self.user.check_password(senha_atual):
            raise ValidationError('Senha atual incorreta.')
        
        return senha_atual
    
    def clean_nova_senha(self):
        nova_senha = self.cleaned_data.get('nova_senha')
        
        if not nova_senha:
            return nova_senha
        
        if self.user and self.user.check_password(nova_senha):
            raise ValidationError('A nova senha não pode ser igual à senha atual.')
        
        if len(nova_senha) < 8:
            raise ValidationError('A senha deve ter pelo menos 8 caracteres.')
        
        if not re.search(r'[A-Z]', nova_senha):
            raise ValidationError('A senha deve conter pelo menos uma letra maiúscula.')
        
        if not re.search(r'[a-z]', nova_senha):
            raise ValidationError('A senha deve conter pelo menos uma letra minúscula.')
        
        if not re.search(r'[0-9]', nova_senha):
            raise ValidationError('A senha deve conter pelo menos um número.')
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', nova_senha):
            raise ValidationError('A senha deve conter pelo menos um caractere especial.')
        
        try:
            validate_password(nova_senha, self.user)
        except ValidationError as e:
            raise ValidationError(e.messages)
        
        return nova_senha
    
    def clean_confirmar_senha(self):
        confirmar_senha = self.cleaned_data.get('confirmar_senha')
        nova_senha = self.cleaned_data.get('nova_senha')
        
        if not nova_senha and not confirmar_senha:
            return confirmar_senha
        
        if nova_senha and not confirmar_senha:
            raise ValidationError('Confirme a nova senha.')
        
        if nova_senha != confirmar_senha:
            raise ValidationError('As senhas não coincidem.')
        
        return confirmar_senha
    
    def clean(self):
        cleaned_data = super().clean()
        nova_senha = cleaned_data.get('nova_senha')
        senha_atual = cleaned_data.get('senha_atual')
        
        if nova_senha and not senha_atual:
            self.add_error('senha_atual', 'Digite sua senha atual para alterar a senha.')
        
        return cleaned_data
    
    def save(self):
        if not self.user or not self.user.is_authenticated:
            raise ValueError('Usuário não autenticado.')
        
        self.user.first_name = self.cleaned_data.get('first_name')
        self.user.last_name = self.cleaned_data.get('last_name')
        
        nova_senha = self.cleaned_data.get('nova_senha')
        if nova_senha:
            self.user.set_password(nova_senha)
        
        self.user.save()
        return self.user


class PerfilUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Digite seu nome'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Digite seu sobrenome'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Digite seu e-mail'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super(PerfilUpdateForm, self).__init__(*args, **kwargs)
        self.fields['email'].required = True
        self.fields['email'].disabled = True
    
    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name', '').strip()
        if len(first_name) < 2:
            raise ValidationError('O nome deve ter pelo menos 2 caracteres.')
        return first_name
    
    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name', '').strip()
        if len(last_name) < 2:
            raise ValidationError('O sobrenome deve ter pelo menos 2 caracteres.')
        return last_name


class CustomPasswordChangeForm(forms.Form):
    senha_atual = forms.CharField(
        label='Senha atual',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite sua senha atual'
        })
    )
    
    nova_senha = forms.CharField(
        label='Nova senha',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite a nova senha'
        })
    )
    
    confirmar_senha = forms.CharField(
        label='Confirmar nova senha',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirme a nova senha'
        })
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(CustomPasswordChangeForm, self).__init__(*args, **kwargs)
    
    def clean_senha_atual(self):
        senha_atual = self.cleaned_data.get('senha_atual')
        if self.user and not self.user.check_password(senha_atual):
            raise ValidationError('Senha atual incorreta.')
        return senha_atual
    
    def clean_nova_senha(self):
        nova_senha = self.cleaned_data.get('nova_senha')
        
        if len(nova_senha) < 8:
            raise ValidationError('A senha deve ter pelo menos 8 caracteres.')
        
        if not re.search(r'[A-Z]', nova_senha):
            raise ValidationError('A senha deve conter pelo menos uma letra maiúscula.')
        
        if not re.search(r'[a-z]', nova_senha):
            raise ValidationError('A senha deve conter pelo menos uma letra minúscula.')
        
        if not re.search(r'[0-9]', nova_senha):
            raise ValidationError('A senha deve conter pelo menos um número.')
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', nova_senha):
            raise ValidationError('A senha deve conter pelo menos um caractere especial.')
        
        try:
            validate_password(nova_senha, self.user)
        except ValidationError as e:
            raise ValidationError(e.messages)
        
        return nova_senha
    
    def clean_confirmar_senha(self):
        confirmar_senha = self.cleaned_data.get('confirmar_senha')
        nova_senha = self.cleaned_data.get('nova_senha')
        
        if nova_senha != confirmar_senha:
            raise ValidationError('As senhas não coincidem.')
        
        return confirmar_senha
    
    def save(self):
        nova_senha = self.cleaned_data.get('nova_senha')
        self.user.set_password(nova_senha)
        self.user.save()
        return self.user


# ==========================================
# NOVOS FORMULÁRIOS DE TAREFAS
# ==========================================

class TaskForm(forms.ModelForm):
    """
    Formulário base para criação e edição de tarefas
    """
    
    class Meta:
        model = Task
        fields = [
            'titulo',
            'descricao',
            'board',
            'responsavel',
            'prioridade',
            'data_entrega',
            'permite_edicao_usuario'
        ]
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Digite o título da tarefa',
                'maxlength': 200
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Descreva a tarefa em detalhes...'
            }),
            'board': forms.Select(attrs={
                'class': 'form-select'
            }),
            'responsavel': forms.Select(attrs={
                'class': 'form-select'
            }),
            'prioridade': forms.Select(attrs={
                'class': 'form-select'
            }),
            'data_entrega': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'permite_edicao_usuario': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        labels = {
            'titulo': 'Título da Tarefa',
            'descricao': 'Descrição',
            'board': 'Setor',
            'responsavel': 'Responsável',
            'prioridade': 'Prioridade',
            'data_entrega': 'Prazo',
            'permite_edicao_usuario': 'Permitir edição por usuários',
        }
        help_texts = {
            'titulo': 'Máximo de 200 caracteres.',
            'permite_edicao_usuario': 'Marque esta opção para permitir que usuários comuns editem os campos principais desta tarefa.',
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.board_id = kwargs.pop('board_id', None)
        self.is_edit = kwargs.pop('is_edit', False)
        
        super(TaskForm, self).__init__(*args, **kwargs)
        
        self._configure_board_field()
        self._configure_responsavel_field()
        self._configure_permicao_edicao()
        self._configure_data_entrega()
        
        if self.instance and self.instance.pk and self.user:
            self._check_edit_permissions()
    
    def _configure_board_field(self):
        if self.board_id:
            self.fields['board'].initial = self.board_id
            self.fields['board'].queryset = Board.objects.filter(id=self.board_id)
            self.fields['board'].widget = forms.HiddenInput()
            self.fields['board'].required = True
        elif self.instance and self.instance.pk and hasattr(self.instance, 'board'):
            self.fields['board'].queryset = Board.objects.filter(id=self.instance.board.id)
            self.fields['board'].widget = forms.HiddenInput()
            self.fields['board'].required = True
        elif self.user:
            boards = Board.objects.filter(workspace=self.user.workspace)
            self.fields['board'].queryset = boards
            self.fields['board'].empty_label = "Selecione um setor"
    
    def _configure_responsavel_field(self):
        if self.user:
            usuarios = User.objects.filter(
                workspace=self.user.workspace
            ).order_by('first_name')
            
            self.fields['responsavel'].queryset = usuarios
            self.fields['responsavel'].empty_label = "Selecione um responsável"
            
            choices = [('', 'Selecione um responsável')]
            for usuario in usuarios:
                tipo_label = {
                    'admin': '👑 Admin',
                    'gerente': '👔 Gerente',
                    'usuario': '👤 Usuário'
                }.get(usuario.tipo, usuario.tipo)
                choices.append((usuario.id, f"{usuario.get_full_name()} ({tipo_label})"))
            
            self.fields['responsavel'].choices = choices
    
    def _configure_permicao_edicao(self):
        if self.user:
            if self.user.tipo not in ['admin', 'gerente']:
                # Usuário comum: campo escondido e False
                self.fields['permite_edicao_usuario'].widget = forms.HiddenInput()
                self.fields['permite_edicao_usuario'].required = False
                self.fields['permite_edicao_usuario'].disabled = True
                self.fields['permite_edicao_usuario'].initial = False
            else:
                # Admin ou Gerente: mostra o checkbox
                self.fields['permite_edicao_usuario'].widget = forms.CheckboxInput(attrs={
                    'class': 'form-check-input'
                })
                # ✅ Para nova tarefa, usar o default do modelo (True)
                if not self.instance or not self.instance.pk:
                    self.fields['permite_edicao_usuario'].initial = True
                else:
                    # Para edição, manter o valor atual
                    self.fields['permite_edicao_usuario'].initial = self.instance.permite_edicao_usuario
    
    def _configure_data_entrega(self):
        if not self.instance or not self.instance.pk:
            self.fields['prioridade'].initial = 'media'
            self.fields['data_entrega'].initial = timezone.now().date() + timezone.timedelta(days=7)
    
    def _check_edit_permissions(self):
        if not self.user:
            return
        
        pode_editar = check_permission_edit_task(self.user, self.instance)
        if not pode_editar:
            for field_name, field in self.fields.items():
                if field_name == 'permite_edicao_usuario':
                    continue
                field.disabled = True
                field.widget.attrs['readonly'] = True
                field.widget.attrs['disabled'] = True
                
                if isinstance(field.widget, forms.Select):
                    field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' disabled'
    
    def clean_titulo(self):
        titulo = self.cleaned_data.get('titulo', '').strip()
        if not titulo:
            raise ValidationError('O título da tarefa é obrigatório.')
        if len(titulo) < 3:
            raise ValidationError('O título deve ter pelo menos 3 caracteres.')
        if len(titulo) > 200:
            raise ValidationError('O título deve ter no máximo 200 caracteres.')
        return titulo
    
    def clean_descricao(self):
        descricao = self.cleaned_data.get('descricao', '').strip()
        if descricao and len(descricao) > 2000:
            raise ValidationError('A descrição deve ter no máximo 2000 caracteres.')
        return descricao
    
    def clean_data_entrega(self):
        data_entrega = self.cleaned_data.get('data_entrega')
        if not data_entrega:
            return None
        from datetime import date
        if data_entrega < date.today():
            raise ValidationError('O prazo não pode ser uma data passada.')
        return data_entrega
    
    def clean_board(self):
        board = self.cleaned_data.get('board')
        if not board:
            raise ValidationError('Selecione um setor.')
        if self.user and not check_permission_create_task(self.user, board):
            raise ValidationError('Você não tem permissão para criar tarefas neste setor.')
        return board
    
    def clean_responsavel(self):
        responsavel = self.cleaned_data.get('responsavel')
        if not responsavel:
            return responsavel
        if self.user and responsavel.workspace != self.user.workspace:
            raise ValidationError('O responsável deve pertencer ao mesmo workspace.')
        return responsavel
    
    def clean_permite_edicao_usuario(self):
        permite = self.cleaned_data.get('permite_edicao_usuario', False)
        if self.user and self.user.tipo == 'usuario':
            return False
        return permite
    
    def save(self, commit=True):
        instance = super(TaskForm, self).save(commit=False)
        
        if not instance.pk and self.user:
            instance.criado_por = self.user
        
        # ✅ REMOVIDO: Não forçar False para usuários comuns
        # O valor vem do formulário corretamente
        
        if commit:
            instance.save()
            if instance.responsavel:
                BoardMember.objects.get_or_create(
                    board=instance.board,
                    usuario=instance.responsavel
                )
        
        return instance


class TaskCreateForm(TaskForm):
    """
    Formulário específico para criação de tarefas
    """
    def __init__(self, *args, **kwargs):
        super(TaskCreateForm, self).__init__(*args, **kwargs)
        if self.user and self.user.tipo not in ['admin', 'gerente']:
            # Usuário comum: campo escondido e False
            self.fields['permite_edicao_usuario'].initial = False
            self.fields['permite_edicao_usuario'].disabled = True
            self.fields['permite_edicao_usuario'].widget = forms.HiddenInput()
        else:
            # ✅ Admin/Gerente: iniciar com True (default do modelo)
            self.fields['permite_edicao_usuario'].initial = True


class TaskUpdateForm(TaskForm):
    """
    Formulário específico para edição de tarefas
    """
    def __init__(self, *args, **kwargs):
        super(TaskUpdateForm, self).__init__(*args, **kwargs)
        self.fields['board'].disabled = True
        self.fields['board'].widget = forms.HiddenInput()
    
    def clean(self):
        cleaned_data = super().clean()
        if self.user and self.instance and self.instance.pk:
            if not check_permission_edit_task(self.user, self.instance):
                for field_name, field in self.fields.items():
                    if field_name == 'permite_edicao_usuario':
                        continue
                    field.disabled = True
                    field.widget.attrs['readonly'] = True
                    field.widget.attrs['disabled'] = True
        return cleaned_data


class TaskFilterForm(forms.Form):
    """
    Formulário para filtros na lista de tarefas
    """
    status = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Todos os status'),
            ('pendente', 'Pendente'),
            ('em_andamento', 'Em Andamento'),
            ('concluida', 'Concluída'),
            ('cancelada', 'Cancelada'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    prioridade = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Todas as prioridades'),
            ('baixa', 'Baixa'),
            ('media', 'Média'),
            ('alta', 'Alta'),
            ('urgente', 'Urgente'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    responsavel = forms.ModelChoiceField(
        required=False,
        queryset=User.objects.none(),
        empty_label="Todos os responsáveis",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    busca = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar tarefas por título ou descrição...'
        })
    )
    
    prazo_inicio = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    prazo_fim = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(TaskFilterForm, self).__init__(*args, **kwargs)
        if user:
            usuarios = User.objects.filter(workspace=user.workspace).order_by('first_name')
            self.fields['responsavel'].queryset = usuarios
    
    def clean(self):
        cleaned_data = super().clean()
        prazo_inicio = cleaned_data.get('prazo_inicio')
        prazo_fim = cleaned_data.get('prazo_fim')
        if prazo_inicio and prazo_fim and prazo_fim < prazo_inicio:
            self.add_error('prazo_fim', 'A data final deve ser posterior à data inicial.')
        return cleaned_data


class TaskBulkActionForm(forms.Form):
    """
    Formulário para ações em massa nas tarefas
    """
    acao = forms.ChoiceField(
        required=True,
        choices=[
            ('', 'Selecione uma ação'),
            ('mudar_status', 'Mudar status'),
            ('mudar_prioridade', 'Mudar prioridade'),
            ('atribuir_responsavel', 'Atribuir responsável'),
            ('excluir', 'Excluir selecionados'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    novo_status = forms.ChoiceField(
        required=False,
        choices=[
            ('pendente', 'Pendente'),
            ('em_andamento', 'Em Andamento'),
            ('concluida', 'Concluída'),
            ('cancelada', 'Cancelada'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    nova_prioridade = forms.ChoiceField(
        required=False,
        choices=[
            ('baixa', 'Baixa'),
            ('media', 'Média'),
            ('alta', 'Alta'),
            ('urgente', 'Urgente'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    novo_responsavel = forms.ModelChoiceField(
        required=False,
        queryset=User.objects.none(),
        empty_label="Selecione um responsável",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    tarefas_ids = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(TaskBulkActionForm, self).__init__(*args, **kwargs)
        if user:
            usuarios = User.objects.filter(workspace=user.workspace).order_by('first_name')
            self.fields['novo_responsavel'].queryset = usuarios
    
    def clean(self):
        cleaned_data = super().clean()
        acao = cleaned_data.get('acao')
        
        if not acao:
            return cleaned_data
        
        tarefas_ids = cleaned_data.get('tarefas_ids', '').strip()
        if not tarefas_ids:
            raise ValidationError('Selecione pelo menos uma tarefa.')
        
        if acao == 'mudar_status':
            novo_status = cleaned_data.get('novo_status')
            if not novo_status:
                self.add_error('novo_status', 'Selecione um status.')
        elif acao == 'mudar_prioridade':
            nova_prioridade = cleaned_data.get('nova_prioridade')
            if not nova_prioridade:
                self.add_error('nova_prioridade', 'Selecione uma prioridade.')
        elif acao == 'atribuir_responsavel':
            novo_responsavel = cleaned_data.get('novo_responsavel')
            if not novo_responsavel:
                self.add_error('novo_responsavel', 'Selecione um responsável.')
        
        return cleaned_data


class ComentarioForm(forms.ModelForm):
    """
    Formulário para comentários
    """
    class Meta:
        model = Comment
        fields = ['texto']
        widgets = {
            'texto': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Digite seu comentário...'
            })
        }
        labels = {'texto': ''}
    
    def clean_texto(self):
        texto = self.cleaned_data.get('texto', '').strip()
        if not texto:
            raise ValidationError('O comentário não pode estar vazio.')
        if len(texto) > 500:
            raise ValidationError('O comentário deve ter no máximo 500 caracteres.')
        return texto