# Bidpazari

CENG445 Term Project, developed by @akca and @bozbalci.

## Installation

Bidpazari relies on Django in order to persist its models. In
order to run the tests, you need to first install Python 3.8 or
greater, and then create a virtualenv.

    $ python -mvenv ~/.virtualenvs/bidpazari

Activate the virtualenv, and install the dependencies (requires Poetry):

    $ source ~/.virtualenvs/bidpazari/bin/activate
    (bidpazari) $ poetry install
    $ cd static; npm install

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

Initially, the WebSocket server will not be running. In order to run it,
visit

    http://localhost:8000/ws/server/

in order to start the WebSocket thread within the Django server.

## TODO

- [ ] Automate the WebSocket server initialization
- [ ] Refactor the strategy backend (bidding history shenanigans)
- [ ] Redesign the auctions page to be prettier
- [ ] Add an "Account" page for password changes, verification, profile settings, etc.
- [ ] Create deployment scripts
- [ ] Remove tests or write new tests
    
Happy hacking!

-Fatih, Berk
