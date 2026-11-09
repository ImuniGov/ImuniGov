import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from . import clock


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Login(Input):
    email: str = Field(max_length=254)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def email_valid(cls, value):
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Informe um e-mail válido.")
        return value.lower()


class Register(Login):
    name: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=12, max_length=128)
    consent: Literal[True]
    healthConsent: Literal[True]
    adultDeclaration: Literal[True]
    termsVersion: str = Field(min_length=1, max_length=80)
    privacyHash: str = Field(pattern=r"^[a-f0-9]{64}$")


class Dependent(Input):
    name: str = Field(min_length=2, max_length=80)
    birthDate: date
    representationConfirmed: Literal[True]

    @field_validator("birthDate")
    @classmethod
    def birth_valid(cls, value):
        if value > clock.today() or value.year < 1900:
            raise ValueError("Data de nascimento inválida.")
        return value


class Decision(Input):
    decision: Literal["aprovado", "rejeitado"]
    note: str = Field(default="", max_length=300)
    guidance: str = Field(default="", max_length=500)
    reviewer: str | None = Field(default=None, max_length=80)  # Legacy field is never trusted for identity.
    independenceConfirmed: Literal[True]


class Candidate(Input):
    vaccine: str = Field(min_length=2, max_length=80)
    dose: int = Field(ge=1, le=10)
    doseDate: date

    @field_validator("doseDate")
    @classmethod
    def date_valid(cls, value):
        if value > clock.today() or value.year < 1900:
            raise ValueError("Data da dose inválida.")
        return value


class RecordDecision(Input):
    decision: Literal["validado", "recusado"]
    note: str = Field(min_length=3, max_length=500)
    guidance: str = Field(default="", max_length=500)
    independenceConfirmed: Literal[True]


class Impediment(Input):
    reason: str = Field(min_length=3, max_length=500)


class Guidance(Input):
    text: str = Field(min_length=3, max_length=1000)
    released: bool = True


class Contact(Input):
    kind: Literal["telefone", "visita", "mensagem", "sem_contato"]
    note: str = Field(min_length=3, max_length=500)
    contactDate: date

    @field_validator("contactDate")
    @classmethod
    def valid_date(cls, value):
        if value > clock.today():
            raise ValueError("Contato não pode estar no futuro.")
        return value


class ReadNotification(Input):
    read: Literal[True]


class DosePlan(Input):
    vaccine: str = Field(min_length=2, max_length=80)
    dose: int = Field(ge=1, le=10)
    dueDate: date
    note: str = Field(min_length=3, max_length=500)


class CancelPlan(Input):
    note: str = Field(min_length=3, max_length=500)


class Rule(Input):
    id: str = Field(min_length=1, max_length=80)
    vaccine: str = Field(min_length=2, max_length=80)
    dose: int = Field(ge=1, le=10)
    due_months: int = Field(ge=0, le=1800)
    max_months: int = Field(ge=1, le=1801)
    min_months: int = Field(ge=0, default=0)
    min_age_days: int = Field(ge=0, default=0)
    min_interval_days: int = Field(ge=0, default=0)
    min_interval_months: int = Field(ge=0, default=0)
    min_from_first_months: int = Field(ge=0, default=0)

    @model_validator(mode="after")
    def ages(self):
        if self.max_months <= self.due_months or self.min_months > self.due_months:
            raise ValueError("Faixa etária da regra inválida.")
        return self


class RuleSet(Input):
    version: str = Field(min_length=3, max_length=100)
    source: str = Field(pattern=r"^https://", max_length=1000)
    valid_from: date
    valid_until: date
    rules: list[Rule] = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def valid_rules(self):
        if self.valid_until < self.valid_from or len({r.id for r in self.rules}) != len(self.rules):
            raise ValueError("Vigência ou identificadores inválidos.")
        if len({(r.vaccine, r.dose) for r in self.rules}) != len(self.rules):
            raise ValueError("Vacina/dose duplicada no conjunto de regras.")
        return self
