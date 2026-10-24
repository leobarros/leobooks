"""Formulários WSGI (Flask-WTF) com validação estrita.

Todos os formulários carregam o token CSRF automaticamente via ``hidden_tag``
ou ``{{ form.csrf_token }}``. A validação de senha segue a regra do projeto:
mínimo 4 e máximo 10 caracteres.
"""

from __future__ import annotations

import re

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import (
    BooleanField,
    IntegerField,
    PasswordField,
    RadioField,
    SelectField,
    StringField,
    TextAreaField,
)
from wtforms.validators import DataRequired, EqualTo, Length, NumberRange, Optional, ValidationError

from config import Config
from models import BOOK_MEDIA, BOOK_STATUSES, NOTE_TYPES

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$")
ISBN_RE = re.compile(r"^[0-9Xx-]{10,17}$")
URL_RE = re.compile(r"^https?://[^\s]+$")


def password_rule(form, field):  # noqa: ANN001
    value = field.data or ""
    minimum = Config.PASSWORD_MIN_LENGTH
    maximum = Config.PASSWORD_MAX_LENGTH
    if not (minimum <= len(value) <= maximum):
        raise ValidationError(
            f"A senha deve ter entre {minimum} e {maximum} caracteres."
        )


def email_rule(form, field):  # noqa: ANN001
    value = (field.data or "").strip()
    if not EMAIL_RE.match(value):
        raise ValidationError("Informe um e-mail válido.")


def optional_url(form, field):  # noqa: ANN001
    value = (field.data or "").strip()
    if value and not URL_RE.match(value):
        raise ValidationError("A URL deve começar com http:// ou https://.")


class LoginForm(FlaskForm):
    email = StringField(
        "E-mail", validators=[DataRequired("Informe seu e-mail."), Length(max=255)]
    )
    password = PasswordField(
        "Senha",
        validators=[
            DataRequired("Informe sua senha."),
            Length(max=Config.PASSWORD_MAX_LENGTH),
        ],
    )
    remember = BooleanField("Continuar conectado", default=True)


class RegisterForm(FlaskForm):
    name = StringField(
        "Como podemos chamar você?",
        validators=[DataRequired("Diga seu nome."), Length(min=2, max=120)],
    )
    email = StringField(
        "E-mail",
        validators=[DataRequired("Informe seu e-mail."), email_rule, Length(max=255)],
    )
    password = PasswordField(
        "Senha",
        validators=[DataRequired("Crie uma senha."), password_rule],
    )
    confirm = PasswordField(
        "Repita a senha",
        validators=[
            DataRequired("Repita a senha."),
            EqualTo("password", message="As senhas não conferem."),
        ],
    )


class BookForm(FlaskForm):
    title = StringField(
        "Título", validators=[DataRequired("Informe o título."), Length(max=255)]
    )
    authors = StringField(
        "Autor(es)", validators=[DataRequired("Informe o autor."), Length(max=255)]
    )
    publisher = StringField("Editora", validators=[Optional(), Length(max=150)])
    isbn = StringField("ISBN", validators=[Optional(), Length(max=20)])
    media_type = RadioField(
        "Formato de leitura",
        choices=[(key, meta["label"]) for key, meta in BOOK_MEDIA.items()],
        default="PHYSICAL",
        validators=[DataRequired("Escolha o formato do livro.")],
    )
    total_pages = IntegerField(
        "Páginas totais",
        validators=[
            Optional(),
            NumberRange(min=0, max=50000, message="Use um número entre 0 e 50.000."),
        ],
    )
    current_page = IntegerField(
        "Página atual",
        validators=[Optional(), NumberRange(min=0, max=50000)],
        default=0,
    )
    current_percent = IntegerField(
        "Progresso (%)",
        validators=[
            Optional(),
            NumberRange(min=0, max=100, message="Use um percentual entre 0 e 100."),
        ],
        default=0,
    )
    status = SelectField(
        "Status",
        choices=[(key, meta["label"]) for key, meta in BOOK_STATUSES.items()],
        validators=[DataRequired()],
        default="READING",
    )
    cover_url = StringField("URL da capa", validators=[Optional(), optional_url, Length(max=500)])
    cover = FileField(
        "Enviar capa",
        validators=[Optional(), FileAllowed(["jpg", "jpeg", "png", "webp"], "Use JPG, PNG ou WebP.")],
    )
    remove_cover = BooleanField("Remover a capa atual", default=False)

    def validate_isbn(self, field):  # noqa: ANN001
        value = (field.data or "").strip().replace(" ", "")
        if value and not ISBN_RE.match(value):
            raise ValidationError("ISBN inválido: use 10 ou 13 dígitos (hífens são aceitos).")
        field.data = value or None

    def validate_total_pages(self, field):  # noqa: ANN001
        value = field.data or 0
        if self.media_type.data == "PHYSICAL" and value < 1:
            raise ValidationError("Informe o total de páginas do livro físico.")

    def validate_current_page(self, field):  # noqa: ANN001
        if field.data is None:
            field.data = 0
        if self.total_pages.data and field.data > self.total_pages.data:
            raise ValidationError("A página atual não pode passar do total de páginas.")


class NoteForm(FlaskForm):
    book_id = SelectField(
        "Livro", validators=[DataRequired("Escolha o livro.")], choices=[]
    )
    type = RadioField(
        "Tipo de nota",
        choices=[(key, meta["label"]) for key, meta in NOTE_TYPES.items()],
        default="QUOTE",
        validators=[DataRequired("Escolha o tipo da nota.")],
    )
    content = TextAreaField(
        "Conteúdo",
        validators=[
            DataRequired("Escreva a nota."),
            Length(max=10000, message="A nota pode ter até 10.000 caracteres."),
        ],
    )
    chapter = StringField("Capítulo", validators=[Optional(), Length(max=100)])
    page_number = IntegerField(
        "Página", validators=[Optional(), NumberRange(min=0, max=100000)]
    )
    tags = StringField("Tags", validators=[Optional(), Length(max=240)])
    photo = FileField(
        "Foto da página",
        validators=[Optional(), FileAllowed(["jpg", "jpeg", "png", "webp"], "Use JPG, PNG ou WebP.")],
    )


class NewUserForm(FlaskForm):
    name = StringField(
        "Nome", validators=[DataRequired("Informe o nome."), Length(min=2, max=120)]
    )
    email = StringField(
        "E-mail", validators=[DataRequired("Informe o e-mail."), email_rule, Length(max=255)]
    )
    password = PasswordField(
        "Senha inicial", validators=[DataRequired("Crie uma senha."), password_rule]
    )
    confirm = PasswordField(
        "Repita a senha",
        validators=[
            DataRequired("Repita a senha."),
            EqualTo("password", message="As senhas não conferem."),
        ],
    )
    is_admin = BooleanField("Conceder acesso de administrador", default=False)


class ProfileForm(FlaskForm):
    name = StringField(
        "Nome", validators=[DataRequired("Informe seu nome."), Length(min=2, max=120)]
    )
    email = StringField(
        "E-mail", validators=[DataRequired("Informe seu e-mail."), email_rule, Length(max=255)]
    )


class PasswordForm(FlaskForm):
    current_password = PasswordField(
        "Senha atual", validators=[DataRequired("Informe a senha atual.")]
    )
    new_password = PasswordField(
        "Nova senha", validators=[DataRequired("Informe a nova senha."), password_rule]
    )
    confirm = PasswordField(
        "Repita a nova senha",
        validators=[
            DataRequired("Repita a nova senha."),
            EqualTo("new_password", message="As senhas não conferem."),
        ],
    )


class DeleteAccountForm(FlaskForm):
    password = PasswordField(
        "Confirme sua senha", validators=[DataRequired("Informe sua senha.")]
    )
    confirmation = StringField(
        "Digite EXCLUIR",
        validators=[DataRequired("Digite EXCLUIR para confirmar."), Length(max=20)],
    )

    def validate_confirmation(self, field):  # noqa: ANN001
        if (field.data or "").strip().upper() != "EXCLUIR":
            raise ValidationError("Digite exatamente a palavra EXCLUIR.")


class RestoreForm(FlaskForm):
    backup = FileField(
        "Arquivo de backup",
        validators=[
            DataRequired("Selecione um arquivo de backup."),
            FileAllowed(
                ["zip", "db", "sqlite", "sqlite3"],
                "Envie o ZIP completo do LeoBooks (ou um .db antigo).",
            ),
        ],
    )


class ThemeForm(FlaskForm):
    theme = SelectField(
        "Tema",
        choices=[("light", "Claro"), ("dark", "Escuro")],
        validators=[DataRequired()],
    )
