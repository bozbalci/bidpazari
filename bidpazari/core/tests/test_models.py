import sys
import unittest
from contextlib import contextmanager
from io import StringIO

from bidpazari.core.exceptions import InvalidPassword
from bidpazari.core.models import User, UserVerificationStatus, user_repository


@contextmanager
def captured_output():
    new_out, new_err = StringIO(), StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err


class UserTestCase(unittest.TestCase):
    def setUp(self) -> None:
        user_repository.delete()

    def test_initialization_sends_mail(self):
        with captured_output() as (out, err):
            user = User(full_name='Bob Marley',
                        email='faruk@gmail.com',
                        password='sucukagaci')

        output = out.getvalue().strip()
        self.assertIn('Hello Bob Marley', output)
        self.assertIn(str(user.verification_number), output)

    def test_verification(self):
        user = User(full_name='Bob Marley',
                    email='faruk@gmail.com',
                    password='sucukagaci')

        self.assertEqual(user.verification_status, UserVerificationStatus.UNVERIFIED)
        User.verify(user.email, user.verification_number)
        self.assertEqual(user.verification_status, UserVerificationStatus.VERIFIED)

    def test_change_password(self):
        user = User(full_name='Bob Marley',
                    email='faruk@gmail.com',
                    password='sucukagaci')

        with captured_output() as (out, err):
            user.change_password(new_password='foo', old_password=None)
        output = out.getvalue().strip()
        self.assertIn(user.password, output)

        with captured_output() as (out, err):
            user.change_password(new_password='mynewsupersecurepassword',
                                 old_password=user.password)
        output = out.getvalue().strip()
        self.assertIn('Someone has recently changed the password', output)

        with self.assertRaises(InvalidPassword):
            user.change_password(new_password='hacked',
                                 old_password='jacked')


if __name__ == '__main__':
    unittest.main()
