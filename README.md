# Bidpazari

CENG445 Term Project, developed by @akca and @bozbalci.

## Installation

Bidpazari requires Python 3.8 or greater. You may use [pyenv](https://github.com/pyenv/pyenv) in order to
manage multiple versions of Python without changing the global Python version. After configuration is done,
run the following command to set the global Python version:

    $ pyenv global 3.8.0
    $ python --version  # should be 3.8.0

Install Poetry in order to manage dependencies:

    $ curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python

Create a virtualenv and install dependencies:

    $ python -mvenv ~/.virtualenvs/bidpazari
    $ source ~/.virtualenvs/bidpazari/bin/activate
    (bidpazari) $ poetry install
    (bidpazari) $ cd static; npm install

## Development

If you are developing JavaScript, you are probably interested in running
webpack-dev-server. Run it like below:

    DJANGO_SETTINGS_MODULE=bidpazari.settings.dev ./manage.py webpackdevserver

If you are not interested in developing JavaScript, you still need to generate
a Webpack build for some of the website to work. For this, you should run

    DJANGO_SETTINGS_MODULE=bidpazari.settings.dev ./manage.py buildfrontend

If you would like to generate a production build, use `bidpazari.settings.prod`.

After running webpack-dev-server or creating a static build, run the Django server:

    DJANGO_SETTINGS_MODULE=bidpazari.settings.dev ./manage.py runserver

If it complains about unapplied migrations, run

    ./manage.py makemigrations && ./manage.py migrate

in order to create a DB and apply migrations.

Initially, the WebSocket server will not be running. In order to run it,
visit

    http://localhost:8000/ws/server/

in order to start the WebSocket thread within the Django server.

Happy hacking!

-Fatih, Berk
