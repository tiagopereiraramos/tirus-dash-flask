"""
Formulários para gerenciamento de usuários
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, BooleanField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional, EqualTo, ValidationError
from apps.models.usuario import Usuario, PerfilUsuario


class UsuarioForm(FlaskForm):
    """Formulário para criar/editar usuário"""

    nome_completo = StringField('Nome Completo', validators=[
        DataRequired(message='Nome completo é obrigatório'),
        Length(min=2, max=255, message='Nome deve ter entre 2 e 255 caracteres')
    ])

    email = StringField('Email', validators=[
        DataRequired(message='Email é obrigatório'),
        Email(message='Email deve ter um formato válido'),
        Length(max=255, message='Email não pode ter mais de 255 caracteres')
    ])

    username = StringField('Nome de Usuário', validators=[
        DataRequired(message='Nome de usuário é obrigatório'),
        Length(min=3, max=64,
               message='Nome de usuário deve ter entre 3 e 64 caracteres')
    ])

    telefone = StringField('Telefone', validators=[
        Optional(),
        Length(max=20, message='Telefone não pode ter mais de 20 caracteres')
    ])

    perfil_usuario = SelectField('Perfil',
                                 choices=[
                                     (PerfilUsuario.OPERADOR.value, 'Operador'),
                                     (PerfilUsuario.APROVADOR.value, 'Aprovador'),
                                     (PerfilUsuario.ADMINISTRADOR.value,
                                      'Administrador')
                                 ],
                                 validators=[DataRequired(
                                     message='Perfil é obrigatório')]
                                 )

    status_ativo = BooleanField('Usuário Ativo', default=True)

    password = PasswordField('Nova Senha', validators=[
        Optional(),
        Length(min=6, message='Senha deve ter pelo menos 6 caracteres')
    ])

    confirm_password = PasswordField('Confirmar Nova Senha', validators=[
        EqualTo('password', message='Senhas devem ser iguais')
    ])

    submit = SubmitField('Salvar')

    def __init__(self, usuario_id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario_id = usuario_id

    def validate_email(self, email):
        """Valida se o email não está sendo usado por outro usuário"""
        query = Usuario.query.filter_by(email=email.data)
        if self.usuario_id:
            query = query.filter(Usuario.id != self.usuario_id)

        if query.first():
            raise ValidationError(
                'Este email já está sendo usado por outro usuário.')

    def validate_username(self, username):
        """Valida se o username não está sendo usado por outro usuário"""
        query = Usuario.query.filter_by(username=username.data)
        if self.usuario_id:
            query = query.filter(Usuario.id != self.usuario_id)

        if query.first():
            raise ValidationError('Este nome de usuário já está sendo usado.')


class FiltroUsuarioForm(FlaskForm):
    """Formulário para filtros na listagem de usuários"""

    nome = StringField('Nome', validators=[Optional()])
    email = StringField('Email', validators=[Optional()])
    username = StringField('Usuário', validators=[Optional()])

    perfil_usuario = SelectField('Perfil',
                                 choices=[
                                     ('', 'Todos os perfis'),
                                     (PerfilUsuario.OPERADOR.value, 'Operador'),
                                     (PerfilUsuario.APROVADOR.value, 'Aprovador'),
                                     (PerfilUsuario.ADMINISTRADOR.value,
                                      'Administrador')
                                 ],
                                 validators=[Optional()]
                                 )

    status_ativo = SelectField('Status',
                               choices=[
                                   ('', 'Todos'),
                                   ('True', 'Ativo'),
                                   ('False', 'Inativo')
                               ],
                               validators=[Optional()]
                               )

    submit = SubmitField('Filtrar')


class AlterarSenhaForm(FlaskForm):
    """Formulário para alterar senha (perfil do usuário)"""

    senha_atual = PasswordField('Senha Atual', validators=[
        DataRequired(message='Senha atual é obrigatória')
    ])

    nova_senha = PasswordField('Nova Senha', validators=[
        DataRequired(message='Nova senha é obrigatória'),
        Length(min=6, message='Nova senha deve ter pelo menos 6 caracteres')
    ])

    confirmar_senha = PasswordField('Confirmar Nova Senha', validators=[
        DataRequired(message='Confirmação de senha é obrigatória'),
        EqualTo('nova_senha', message='Senhas devem ser iguais')
    ])

    submit = SubmitField('Alterar Senha')


class PerfilUsuarioForm(FlaskForm):
    """Formulário para editar perfil do usuário logado"""

    nome_completo = StringField('Nome Completo', validators=[
        DataRequired(message='Nome completo é obrigatório'),
        Length(min=2, max=255, message='Nome deve ter entre 2 e 255 caracteres')
    ])

    email = StringField('Email', validators=[
        DataRequired(message='Email é obrigatório'),
        Email(message='Email deve ter um formato válido'),
        Length(max=255, message='Email não pode ter mais de 255 caracteres')
    ])

    telefone = StringField('Telefone', validators=[
        Optional(),
        Length(max=20, message='Telefone não pode ter mais de 20 caracteres')
    ])

    submit = SubmitField('Atualizar Perfil')

    def __init__(self, usuario_atual, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario_atual = usuario_atual

    def validate_email(self, email):
        """Valida se o email não está sendo usado por outro usuário"""
        if email.data != self.usuario_atual.email:
            usuario = Usuario.query.filter_by(email=email.data).first()
            if usuario:
                raise ValidationError(
                    'Este email já está sendo usado por outro usuário.')
