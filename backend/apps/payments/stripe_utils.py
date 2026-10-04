import os


def get_stripe_test_secret_key():
    secret_key = os.getenv('STRIPE_SECRET_KEY', '').strip()
    if secret_key.startswith('sk_test_') and not secret_key.startswith('sk_test_your_key'):
        return secret_key
    return ''
