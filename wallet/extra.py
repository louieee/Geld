from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils import six
from Geld.celery import app
from random_word import RandomWords


class TokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return (
                six.text_type(user.pk) + six.text_type(timestamp) +
                six.text_type(user.is_active)
        )


account_activation_token = TokenGenerator()

@app.task
def get_phrase():
    r = RandomWords()
    count = 0
    phrase = ''
    while count < 7:
        try:
            phrase = phrase + r.get_random_word(hasDictionaryDef="true", includePartOfSpeech="noun,verb",
                                                minLength=5, maxLength=5) + "-"
            count = count + 1
        except Exception:
            pass
    return phrase[:int(phrase.__len__()) - 1].lower()
