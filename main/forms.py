from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
import re


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
    
    # Campos do perfil
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
    
    # Campos de senha
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
        """
        Inicializa o formulário com o usuário logado
        """
        self.user = kwargs.pop('user', None)
        super(PerfilForm, self).__init__(*args, **kwargs)
        
        # Se o usuário estiver autenticado, preencher os campos com dados atuais
        if self.user and self.user.is_authenticated:
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name
    
    def clean_first_name(self):
        """
        Validação do nome
        """
        first_name = self.cleaned_data.get('first_name', '').strip()
        
        if not first_name:
            raise ValidationError('O nome é obrigatório.')
        
        if len(first_name) < 2:
            raise ValidationError('O nome deve ter pelo menos 2 caracteres.')
        
        if len(first_name) > 30:
            raise ValidationError('O nome deve ter no máximo 30 caracteres.')
        
        # Verifica se contém apenas letras e espaços
        if not re.match(r'^[A-Za-zÀ-ÿ\s]+$', first_name):
            raise ValidationError('O nome deve conter apenas letras e espaços.')
        
        return first_name
    
    def clean_last_name(self):
        """
        Validação do sobrenome
        """
        last_name = self.cleaned_data.get('last_name', '').strip()
        
        if not last_name:
            raise ValidationError('O sobrenome é obrigatório.')
        
        if len(last_name) < 2:
            raise ValidationError('O sobrenome deve ter pelo menos 2 caracteres.')
        
        if len(last_name) > 30:
            raise ValidationError('O sobrenome deve ter no máximo 30 caracteres.')
        
        # Verifica se contém apenas letras e espaços
        if not re.match(r'^[A-Za-zÀ-ÿ\s]+$', last_name):
            raise ValidationError('O sobrenome deve conter apenas letras e espaços.')
        
        return last_name
    
    def clean_senha_atual(self):
        """
        Valida se a senha atual está correta
        """
        senha_atual = self.cleaned_data.get('senha_atual')
        nova_senha = self.cleaned_data.get('nova_senha')
        confirmar_senha = self.cleaned_data.get('confirmar_senha')
        
        # Se não está alterando a senha, não precisa validar
        if not nova_senha and not confirmar_senha:
            return senha_atual
        
        # Se está alterando, a senha atual é obrigatória
        if not senha_atual:
            raise ValidationError('Digite sua senha atual para alterar a senha.')
        
        # Verificar se a senha atual está correta
        if self.user and not self.user.check_password(senha_atual):
            raise ValidationError('Senha atual incorreta.')
        
        return senha_atual
    
    def clean_nova_senha(self):
        """
        Validação da nova senha
        """
        nova_senha = self.cleaned_data.get('nova_senha')
        senha_atual = self.cleaned_data.get('senha_atual')
        
        # Se não está alterando a senha, retorna vazio
        if not nova_senha:
            return nova_senha
        
        # Verifica se a nova senha é diferente da atual
        if self.user and self.user.check_password(nova_senha):
            raise ValidationError('A nova senha não pode ser igual à senha atual.')
        
        # Validação de tamanho mínimo
        if len(nova_senha) < 8:
            raise ValidationError('A senha deve ter pelo menos 8 caracteres.')
        
        # Validação de complexidade
        if not re.search(r'[A-Z]', nova_senha):
            raise ValidationError('A senha deve conter pelo menos uma letra maiúscula.')
        
        if not re.search(r'[a-z]', nova_senha):
            raise ValidationError('A senha deve conter pelo menos uma letra minúscula.')
        
        if not re.search(r'[0-9]', nova_senha):
            raise ValidationError('A senha deve conter pelo menos um número.')
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', nova_senha):
            raise ValidationError('A senha deve conter pelo menos um caractere especial.')
        
        # Validar usando o validador padrão do Django
        try:
            validate_password(nova_senha, self.user)
        except ValidationError as e:
            raise ValidationError(e.messages)
        
        return nova_senha
    
    def clean_confirmar_senha(self):
        """
        Valida se a confirmação de senha é igual à nova senha
        """
        confirmar_senha = self.cleaned_data.get('confirmar_senha')
        nova_senha = self.cleaned_data.get('nova_senha')
        
        # Se não está alterando a senha, retorna vazio
        if not nova_senha and not confirmar_senha:
            return confirmar_senha
        
        # Se a nova senha foi preenchida, a confirmação é obrigatória
        if nova_senha and not confirmar_senha:
            raise ValidationError('Confirme a nova senha.')
        
        # Verifica se as senhas coincidem
        if nova_senha != confirmar_senha:
            raise ValidationError('As senhas não coincidem.')
        
        return confirmar_senha
    
    def clean(self):
        """
        Validação geral do formulário
        """
        cleaned_data = super().clean()
        nova_senha = cleaned_data.get('nova_senha')
        confirmar_senha = cleaned_data.get('confirmar_senha')
        senha_atual = cleaned_data.get('senha_atual')
        
        # Se a nova senha foi preenchida, a atual é obrigatória (já validado no clean_senha_atual)
        if nova_senha and not senha_atual:
            self.add_error('senha_atual', 'Digite sua senha atual para alterar a senha.')
        
        return cleaned_data
    
    def save(self):
        """
        Salva as alterações no usuário
        """
        if not self.user or not self.user.is_authenticated:
            raise ValueError('Usuário não autenticado.')
        
        # Atualizar nome e sobrenome
        self.user.first_name = self.cleaned_data.get('first_name')
        self.user.last_name = self.cleaned_data.get('last_name')
        
        # Atualizar senha se foi fornecida
        nova_senha = self.cleaned_data.get('nova_senha')
        if nova_senha:
            self.user.set_password(nova_senha)
        
        # Salvar o usuário
        self.user.save()
        
        return self.user


class PerfilUpdateForm(forms.ModelForm):
    """
    Formulário alternativo usando ModelForm para atualização do perfil
    """
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
        self.fields['email'].disabled = True  # Impede alteração do email
    
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
    """
    Formulário específico para alteração de senha
    """
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