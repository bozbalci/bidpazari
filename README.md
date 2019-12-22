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
    $ npm install

Start the project by using the following commands:

    # Start the webpack dev server (optional, required for the WebSocket client)
    $ npm start
    # Start the Django development server.
    $ ./manage.py runserver

## TODO

- [ ] Different alert colors for different Django messages
- [ ] Refactor the strategy backend (bidding history shenanigans)
- [ ] Create production configs for Webpack and Django
- [ ] Redesign the auctions page to be prettier
- [ ] Add an "Account" page for password changes, verification, profile settings, etc.
- [ ] Move js code under static/
- [ ] Refactor /media/ usages in templates
- [ ] Create deployment scripts
- [ ] Remove tests or write new tests
    
Happy hacking!

-Fatih, Berk
