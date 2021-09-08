# Thingbox server

Allows _somewhat_ secure storage of sensitive data to be retrieved by authenticated users.


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
