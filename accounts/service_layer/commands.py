from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class RegisterUser:
    email: str
    password: str


@dataclass(frozen=True)
class Login:
    email: str
    password: str


@dataclass(frozen=True)
class GetBalance:
    user_id: int


@dataclass(frozen=True)
class ListTransactions:
    user_id: int
    from_date: str | None = None
    to_date: str | None = None


@dataclass(frozen=True)
class Transfer:
    from_user_id: int
    to_account_number: str
    amount: Decimal
