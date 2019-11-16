from bidpazari.core.models import User


def verify_user(email, verification_number):
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        raise Exception("No user with this email exists.")

    if user.verification_number == verification_number:
        user.verify()
    else:
        user.email_user()
