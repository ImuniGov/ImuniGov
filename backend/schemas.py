import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class Login(Input):
    email: str = Field(max_length=254)
    password: str = Field(min_length=1, max_length=128)

    @field_validator('email')
    @classmethod
    def email_valid(cls, value):
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
            raise ValueError('Informe um e-mail válido.')
        return value.lower()


class Register(Login):
    name: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=12, max_length=128)
    consent: Literal[True]


class Dependent(Input):
    name: str = Field(min_length=2, max_length=80)
    birthDate: date

    @field_validator('birthDate')
    @classmethod
    def birth_valid(cls, value):
        if value > date.today() or value.year < 1900:
            raise ValueError('Data de nascimento inválida.')
        return value


class Decision(Input):
    decision: Literal['aprovado', 'rejeitado']
    note: str = Field(default='', max_length=300)
    reviewer: str | None = Field(default=None, max_length=80)  # Legacy field is never trusted for identity.


class Candidate(Input):
    vaccine: str = Field(min_length=2, max_length=80)
    dose: int = Field(ge=1, le=10)
    doseDate: date

    @field_validator('doseDate')
    @classmethod
    def date_valid(cls, value):
        if value > date.today() or value.year < 1900:
            raise ValueError('Data da dose inválida.')
        return value


class RecordDecision(Input):
    decision: Literal['validado', 'recusado']
    note: str = Field(min_length=3, max_length=500)


class Guidance(Input):
    text: str = Field(min_length=3, max_length=1000)
    released: bool = True


class Contact(Input):
    kind: Literal['telefone', 'visita', 'mensagem', 'sem_contato']
    note: str = Field(min_length=3, max_length=500)
    contactDate: date

    @field_validator('contactDate')
    @classmethod
    def valid_date(cls, value):
        if value > date.today():
            raise ValueError('Contato não pode estar no futuro.')
        return value


class ReadNotification(Input):
    read: Literal[True]
