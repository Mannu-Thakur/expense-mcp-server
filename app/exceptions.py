class ExpenseNotFoundError(Exception):
    """Raised when an expense cannot be found by ID."""

    def __init__(self, expense_id: int) -> None:
        self.expense_id = expense_id
        super().__init__(f"Expense with ID {expense_id} not found.")


class ExpenseValidationError(Exception):
    """Raised when expense input data is invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
