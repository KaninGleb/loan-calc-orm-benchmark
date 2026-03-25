from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

PERCENT_DIVISOR = Decimal('100')
MONTHS_IN_YEAR = 12
DECIMAL_PLACES = Decimal('0.01')


@dataclass(frozen=True)
class LoanParameters:
    payment: Decimal
    annual_rate: Decimal
    years: int


@dataclass(frozen=True)
class LoanResult:
    max_loan_amount: Decimal
    monthly_payment: Decimal
    total_payment: Decimal
    total_interest: Decimal


def calculate_loan(params: LoanParameters) -> LoanResult:
    if params.payment <= 0:
        raise ValueError('Monthly payment must be a positive number.')
    if params.annual_rate < 0:
        raise ValueError('Annual interest rate cannot be negative.')
    if params.years <= 0:
        raise ValueError('Loan term must be at least 1 year.')
    if params.years > 100:
        raise ValueError('Loan term cannot exceed 100 years.')

    # Annuity formula:
    # PV = PMT * (1 - (1 + r)^-n) / r
    # PV - loan amount, PMT - payment, r - interest rate (monthly), n - number of months

    total_months = params.years * MONTHS_IN_YEAR

    if params.annual_rate == 0:
        max_loan_amount = params.payment * total_months
    else:
        monthly_rate = params.annual_rate / PERCENT_DIVISOR / MONTHS_IN_YEAR
        max_loan_amount = params.payment * (1 - (1 + monthly_rate) ** -total_months) / monthly_rate

    max_loan_amount = max_loan_amount.quantize(DECIMAL_PLACES, rounding=ROUND_HALF_UP)

    total_payment = params.payment * total_months
    total_payment = total_payment.quantize(DECIMAL_PLACES, rounding=ROUND_HALF_UP)

    total_interest = total_payment - max_loan_amount
    total_interest = total_interest.quantize(DECIMAL_PLACES, rounding=ROUND_HALF_UP)

    return LoanResult(
        max_loan_amount=max_loan_amount,
        monthly_payment=params.payment,
        total_payment=total_payment,
        total_interest=total_interest
    )
