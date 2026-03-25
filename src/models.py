from sqlalchemy import Numeric, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from pydantic import BaseModel, ConfigDict, Field

from decimal import Decimal
from typing import Optional
from datetime import datetime


class Base(DeclarativeBase):
    pass


class Loan(Base):
    __tablename__ = 'loans'

    id: Mapped[int] = mapped_column(primary_key=True)
    monthly_payment: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    annual_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    years: Mapped[int] = mapped_column(nullable=False)

    max_loan_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    total_payment: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    total_interest: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f'<Loan(id={self.id}, payment={self.monthly_payment}, rate={self.annual_rate}%, years={self.years})>'


class LoanInput(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(gt=0, description='Loan ID')
    monthly_payment: Decimal = Field(gt=0, description='Monthly payment must be positive')
    annual_rate: Decimal = Field(ge=0, le=150, description='Annual rate 0-150%')
    years: int = Field(gt=0, le=100, description='Loan term 1-100 years')


class LoanCalculated(LoanInput):
    max_loan_amount: Decimal = Field(ge=0, description='Calculated max loan amount')
    total_payment: Decimal = Field(gt=0, description='Calculated total payment')
    total_interest: Decimal = Field(ge=0, description='Calculated total interest')
    calculated_at: datetime = Field(description='Timestamp of calculation')
