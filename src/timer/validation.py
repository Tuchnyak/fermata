class ValidationError(ValueError):
    """Invalid user input; `key` is the localization key of the message to show."""

    def __init__(self, key: str):
        super().__init__(key)
        self.key = key
