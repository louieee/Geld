from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils import six


class TokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return (
                six.text_type(user.pk) + six.text_type(timestamp) +
                six.text_type(user.is_active)
        )


account_activation_token = TokenGenerator()

questions = [
    'What was the name of the primary school you attended ?',
    "What is your mother's maiden name ?",
    "When is your spouse's birthday ?",
    "In which city where you born ?",
    "What is the surname of your best friend ?",
    "What is the name of your father's company ?",
    "Where did you first meet your spouse ?",
    "What is the name of your best TV program ?",
    "In which city did you meet your spouse ?",
    "What is the name of the high school you attended ?"
]
