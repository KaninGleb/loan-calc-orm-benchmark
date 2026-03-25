from dotenv import load_dotenv
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from datetime import datetime, timezone
import os

from src import Loan, LoanInput, LoanCalculated, calculate_loan, LoanParameters

load_dotenv()

DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'fintech')

if not DB_PASSWORD:
    raise ValueError('DB_PASSWORD not found! Create .env file')

DATABASE_URL = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def main():
    with SessionLocal() as session:
        try:
            stmt = select(Loan).where(Loan.max_loan_amount.is_(None))
            loans = session.execute(stmt).scalars().all()

            print('=' * 60)
            print(f'Found {len(loans)} uncalculated loans in database\n')

            if not loans:
                print('Nothing to process. Exiting.')
                print('=' * 60)
                return

            updated_count = 0

            for loan in loans:
                try:
                    valid_input = LoanInput.model_validate(loan)

                    params = LoanParameters(
                        payment=valid_input.monthly_payment,
                        annual_rate=valid_input.annual_rate,
                        years=valid_input.years
                    )

                    result = calculate_loan(params)

                    validated_data = LoanCalculated(
                        id=valid_input.id,
                        monthly_payment=valid_input.monthly_payment,
                        annual_rate=valid_input.annual_rate,
                        years=valid_input.years,
                        max_loan_amount=result.max_loan_amount,
                        total_payment=result.total_payment,
                        total_interest=result.total_interest,
                        calculated_at=datetime.now(timezone.utc)
                    )

                    loan.max_loan_amount = validated_data.max_loan_amount
                    loan.total_payment = validated_data.total_payment
                    loan.total_interest = validated_data.total_interest
                    loan.calculated_at = validated_data.calculated_at

                    updated_count += 1

                except Exception as e:
                    print(f'[ERROR] Loan #{loan.id} calculation or validation failed: {e}')

            session.commit()

            print(f'\nSuccessfully updated {updated_count}/{len(loans)} loans.')

        except Exception as e:
            print(f'[CRITICAL] Database error: {type(e).__name__} - {e}')
            session.rollback()
            raise

        print('=' * 60)


if __name__ == '__main__':
    main()
