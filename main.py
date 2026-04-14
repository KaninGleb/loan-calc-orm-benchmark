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


def update_pending_loan_applications(batch_size: int = 50):
    """
    Основная процедура расчёта кредитных заявок.
    
    Пайплайн обработки заявок:
    1. Извлекаем необработанные заявки из БД.
    2. Перебираем заявки пачками (batch_size).
    3. Проверяем входные данные.
    4. Производим расчёты.
    5. Проверяем полноту объекта после расчета.
    6. Записываем в БД батчами.

    Ошибки в отдельных заявках не останавливают процесс.
    Память не расходуется пропорционально количеству записей.
    """
    with SessionLocal() as session:
        try:
            stmt = (
                select(LoanApplication)
                .where(LoanApplication.calculated_loan_limit.is_(None))
                .order_by(LoanApplication.id)
                .execution_options(yield_per=batch_size)
            )

            pending_applications = session.execute(stmt).scalars()

            print('=' * 60)
            print(f'Starting batch processing (batch_size={batch_size}).\n')

            updated_count = 0
            processed_count = 0

            for application in pending_applications:
                processed_count += 1
                application_id = application.id
                application_repr = repr(application)

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
                    session.expunge(application)
                    print(f'[ERROR]: Failed to process Loan #{application_id}.')
                    print(f'- Input Data: {application_repr}')
                    print(f'- Reason: {e}\n')

                if processed_count % batch_size == 0:
                    session.flush()
                    print(f'Batch flushed | total={processed_count} | updated={updated_count}')

            session.commit()
            if processed_count == 0:
                print('Nothing to process.')
            else:
                print(f'\nSuccessfully updated {updated_count} loan applications.')

        except Exception as e:
            session.rollback()
            print(f'[CRITICAL] Database error: {type(e).__name__} - {e}')
            raise

        print('=' * 60)


if __name__ == '__main__':
    update_pending_loan_applications()
