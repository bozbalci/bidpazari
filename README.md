# Bidpazari

CENG445 Term Project, developed by @akca and @bozbalci.

## Installation

Bidpazari relies on Django in order to persist its models. In
order to run the tests, you need to first install Python 3.6 or
greater, and then create a virtualenv.

    $ python -mvenv ~/.virtualenvs/bidpazari

Activate the virtualenv, and install the requirements:

    $ source ~/.virtualenvs/bidpazari/bin/activate
    (bidpazari) $ pip install -r requirements.txt


## Testing

You can run the tests with

    (bidpazari) $ ./manage.py test

Note that the tests will print a lot of stuff to the standard output,
namely

- user's transaction history
- user's received emails (relies on Django's `EMAIL_BACKEND`)
- auction reports
- auction histories

The format of these outputs are pretty self-explanatory.

Happy hacking!

## TODO

- [ ] Create a `sell(...)` method that wraps transaction creation
- [ ] Fix thread blocking issue in decrement strategy
- [ ] Fix price decrementing having an extra call upon stopping
- [ ] Fix the unit tests

-Fatih, Berk
