# ==============================================================================
# ПЕСОЧНИЦА: Работа с JSONB и валидация через Pydantic
# Учебный файл. Не лезет в продакшен.
# ==============================================================================

from pydantic import BaseModel, ConfigDict, ValidationError
from typing import Optional

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import select

from src.database import SessionLocal


class Base(DeclarativeBase):
    pass


class ClientProfile(Base):
    __tablename__ = 'client_profiles'

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_data: Mapped[dict] = mapped_column(JSONB)


class ProfileData(BaseModel):
    model_config = ConfigDict(strict=True)

    name: str
    age: int
    city: str

    device: Optional[str] = None
    has_car: Optional[bool] = None


def fetch_and_validate_profiles():
    with SessionLocal() as session:
        result = session.execute(select(ClientProfile))
        rows = result.scalars().all()

        for row in rows:
            raw_data = row.profile_data

            print(f'Raw JSON from DB: {raw_data}')

            try:
                profile = ProfileData.model_validate(raw_data)

                print('Validation: SUCCESS')
                print(f'Name: {profile.name}')
                print(f'Age: {profile.age}')
                print(f'City: {profile.city}')

                if profile.device:
                    print(f'Device: {profile.device}')

                if profile.has_car is not None:
                    print(f'Has car: {profile.has_car}')

            except ValidationError as e:
                print('Validation: FAILED')
                for error in e.errors():
                    print(f"- Field '{error['loc'][0]}': {error['msg']}")

            print(f"\n{'=' * 60}\n")


if __name__ == '__main__':
    fetch_and_validate_profiles()
