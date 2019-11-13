from typing import Optional


class UserRepository:
    def __init__(self):
        self.users = {}

    def delete(self):
        self.users = {}

    def save(self, user):
        self.users[user.email] = user

    def find_by_email(self, email: str) -> Optional['User']:
        return self.users.get(email, None)
