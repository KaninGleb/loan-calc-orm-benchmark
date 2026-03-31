from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

# КОНСТАНТЫ ДЛЯ РАСЧЁТОВ

PERCENT_DIVISOR = Decimal('100')
MONTHS_IN_YEAR = 12
DECIMAL_PLACES = Decimal('0.01')


# КЛАССЫ ДЛЯ ПЕРЕДАЧИ ДАННЫХ В РАСЧЁТ
# Иммутабельные классы для расчётов.
# Защищают расчетные данные от случайной перезаписи в памяти.

@dataclass(frozen=True)
class CalculationParameters:
    """
    Параметры для расчёта кредита.
    Используется как входные данные для функции calculate_annuity_loan_limit.
    """
    monthly_payment: Decimal
    annual_rate: Decimal
    loan_term_years: int


@dataclass(frozen=True)
class CalculationResult:
    """
    Результат расчёта кредита.
    Содержит все вычисленные значения: лимит, проценты и выгода.
    """
    calculated_loan_limit: Decimal
    total_repayment_amount: Decimal
    total_interest_amount: Decimal


def calculate_annuity_loan_limit(params: CalculationParameters) -> CalculationResult:
    """
    Рассчитывает лимит кредита по аннуитетной формуле.
    """
    if params.monthly_payment <= 0:
        raise ValueError('Monthly payment must be a positive number.')
    if params.annual_rate < 0:
        raise ValueError('Annual interest rate cannot be negative.')
    if params.loan_term_years <= 0:
        raise ValueError('Loan term must be at least 1 year.')
    if params.loan_term_years > 100:
        raise ValueError('Loan term cannot exceed 100 years.')

    # Формула аннуитета:
    # PV = PMT * (1 - (1 + r)^-n) / r
    # PV - сумма кредита, PMT - платёж, r - ставка (месячная), n - количество месяцев

    total_months = params.loan_term_years * MONTHS_IN_YEAR

    if params.annual_rate == 0:
        # Беспроцентный кредит. Просто умножаем платёж на количество месяцев.
        calculated_loan_limit = params.monthly_payment * total_months
    else:
        # Аннуитетная формула с процентами
        monthly_rate = params.annual_rate / PERCENT_DIVISOR / MONTHS_IN_YEAR
        calculated_loan_limit = params.monthly_payment * (1 - (1 + monthly_rate) ** -total_months) / monthly_rate

    calculated_loan_limit = calculated_loan_limit.quantize(DECIMAL_PLACES, rounding=ROUND_HALF_UP)

    total_repayment_amount = params.monthly_payment * total_months
    total_repayment_amount = total_repayment_amount.quantize(DECIMAL_PLACES, rounding=ROUND_HALF_UP)

    total_interest_amount = total_repayment_amount - calculated_loan_limit
    total_interest_amount = total_interest_amount.quantize(DECIMAL_PLACES, rounding=ROUND_HALF_UP)

    return CalculationResult(
        calculated_loan_limit=calculated_loan_limit,
        total_repayment_amount=total_repayment_amount,
        total_interest_amount=total_interest_amount
    )
