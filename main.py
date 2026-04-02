from sqlalchemy import select
from datetime import datetime, timezone

from src.database import SessionLocal
from src import (
    LoanApplication,
    ApplicationInput,
    CalculationParameters,
    calculate_annuity_loan_limit,
    ApplicationCalculated
)


def update_pending_loan_applications():
    """
    Основная процедура расчёта кредитных заявок.
    
    Пайплайн обработки заявок:
    1. Извлекаем необработанные заявки из БД.
    2. Перебираем заявки.
    3. Проверяем входные данные.
    4. Производим расчёты.
    5. Проверяем полноту объекта после расчета.
    6. Записываем в БД через вложенные транзакции.
    
    Ошибки в отдельных заявках не останавливают процесс.
    """
    with SessionLocal() as session:
        try:
            stmt = select(LoanApplication).where(LoanApplication.calculated_loan_limit.is_(None))
            pending_applications = session.execute(stmt).scalars().all()

            print('=' * 60)
            print(f'Found {len(pending_applications)} uncalculated loan applications in database.\n')

            if not pending_applications:
                print('Nothing to process. Exiting.')
                print('=' * 60)
                return

            updated_count = 0

            for application in pending_applications:
                application_id = application.id
                application_repr = repr(application)

                with session.begin_nested() as nested_transaction:
                    try:
                        valid_input = ApplicationInput.model_validate(application)

                        params = CalculationParameters(
                            monthly_payment=valid_input.monthly_payment,
                            annual_rate=valid_input.annual_rate,
                            loan_term_years=valid_input.loan_term_years
                        )

                        result = calculate_annuity_loan_limit(params)

                        validated_data = ApplicationCalculated(
                            id=valid_input.id,
                            monthly_payment=valid_input.monthly_payment,
                            annual_rate=valid_input.annual_rate,
                            loan_term_years=valid_input.loan_term_years,
                            calculated_loan_limit=result.calculated_loan_limit,
                            total_repayment_amount=result.total_repayment_amount,
                            total_interest_amount=result.total_interest_amount,
                            calculated_at=datetime.now(timezone.utc)
                        )

                        application.calculated_loan_limit = validated_data.calculated_loan_limit
                        application.total_repayment_amount = validated_data.total_repayment_amount

                        # =====================================================
                        # ТЕСТОВАЯ ОШИБКА
                        # =====================================================
                        # if application.id == 3:
                        #     raise Exception('Test calculation error')

                        application.total_interest_amount = validated_data.total_interest_amount
                        application.calculated_at = validated_data.calculated_at

                        updated_count += 1

                    except Exception as e:
                        nested_transaction.rollback()
                        print(f'[ERROR]: Failed to process Loan #{application_id}.')
                        print(f'- Input Data: {application_repr}')
                        print(f'- Reason: {e}\n')

            session.commit()
            print(f'Successfully updated {updated_count}/{len(pending_applications)} loan applications.')

        except Exception as e:
            session.rollback()
            print(f'[CRITICAL] Database error: {type(e).__name__} - {e}')
            raise

        print('=' * 60)


if __name__ == '__main__':
    update_pending_loan_applications()
