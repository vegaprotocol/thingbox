# Thingbox server

Allows _somewhat_ secure storage of sensitive data to be retrieved by authenticated users.


## Getting started

Clone the repo and install [Poetry](https://python-poetry.org/), if you don't already have it, then:

```bash
poetry install
```

To configure the server copy `dev.env` to `myenv.env` and edit the configuration as required.

You will need to provide four additional environment variables. One of these (`THINGBOX_ENV`) must be provided on the command line/from your login environment, as it is used to ifnd and open the `$THINGBOX_ENV.env` file, the other three can be stored in the `.env` file or loaded some other way (command line, GCP secrets, etc.). These are:

- `THINGBOX_ENV`: name of environment, the server will load settings from `$THINGBOX_ENV.env`
- `PRIVATE_KEY_B58`: base58 encoded private key for the server
- `TWITTER_API_KEY`: the Twitter API key from the Twitter Developer portal
- `TWITTER_API_SECRET`: the Twitter API secret from the Twitter Developer portal

Now you can run the server. In this example these four variables are included on the command line:

```bash
THINGBOX_ENV=dev PRIVATE_KEY_B58=xxxxx TWITTER_API_KEY=xxxxx TWITTER_API_SECRET=xxxxx poetry run uvicorn thingbox.api:app --reload
```


## Authentication methods/user types

Currently supports sign in with Twitter.


## Item data

Item data can be any markdown, though the default UI may not style everything well.

The server is started with a secret private key, which should only ever reside in RAM. Items must be ecnrypted to the server's public key before being uploaded. This means that at rest the items (probably) cannot be read unless you are inspecting the running application.


## CLI tool

Also included is a CLI tool. To get started:

```bash
python -m thingbox.cli help
```

## Database and migrations

Thingbox currently uses SQLite to store data, therefore the DB can be backed up by backing up the DB file.

Migrations are manual. If the database file doesn't exist it'll be created along with the correct schema, but if the schema changes you'll need to do manual SQL to update things. It is a *very* simple schema.
