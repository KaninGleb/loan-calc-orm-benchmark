from sqlalchemy import Numeric, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from pydantic import BaseModel, ConfigDict, Field

from decimal import Decimal
from typing import Optional
from datetime import datetime


# ЗЕРКАЛО БАЗЫ ДАННЫХ (ORM)
# Классы описывают физическую структуру таблиц в PostgreSQL.
# Используются SQLAlchemy для генерации SQL-запросов под капотом.

class Base(DeclarativeBase):
    pass


class LoanApplication(Base):
    """
    Физическая таблица с кредитными заявками.
    Хранит как входные данные от клиента, так и результаты расчетов.
    """
    __tablename__ = 'loan_applications'

    id: Mapped[int] = mapped_column(primary_key=True)
    monthly_payment: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    annual_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    loan_term_years: Mapped[int] = mapped_column(nullable=False)

    calculated_loan_limit: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    total_repayment_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    total_interest_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f'<LoanApplication(id={self.id}, payment={self.monthly_payment}, rate={self.annual_rate}%, years={self.loan_term_years})>'


# Pydantic DTO (Data Transfer Objects).
# Модели для строгого контроля данных в памяти Питона.
# Гарантируют, что расчет не начнется с неверными типами (ApplicationInput),
# и что в базу не запишется неполный результат (ApplicationCalculated).

class ApplicationInput(BaseModel):
    """
    Сырые данные заявки на кредит от клиента.
    Валидируем их до начала вычислений.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(gt=0, description='Loan ID')
    monthly_payment: Decimal = Field(gt=0, description='Monthly payment must be positive')
    annual_rate: Decimal = Field(ge=0, le=150, description='Annual rate 0-150%')
    loan_term_years: int = Field(gt=0, le=100, description='Loan term 1-100 years')


class ApplicationCalculated(ApplicationInput):
    """
    Финальная проверка объекта после расчетов.
    Гарантируем, что расчёты не вернули неполный объект, перед записью в БД.
    """
    calculated_loan_limit: Decimal = Field(ge=0, description='Calculated max loan amount')
    total_repayment_amount: Decimal = Field(gt=0, description='Calculated total payment')
    total_interest_amount: Decimal = Field(ge=0, description='Calculated total interest')
    calculated_at: datetime = Field(description='Timestamp of calculation')
