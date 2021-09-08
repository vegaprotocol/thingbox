# Thingbox server

Allows _somewhat_ secure storage of sensitive data to be retrieved by authenticated users.


## Authentication methods/user types

Currently supports sign in with Twitter


## Item data

Item data can be any markdown, though the default UI may not style everything well.

The server is started with a secret private key, which should only ever reside in RAM. Items must be ecnrypted to the server's public key before being uploaded. This means that at rest the items (probably) cannot be read unless you are inspecting the running application.


## CLI tool

Also included is a CLI tool. To get started:

```bash
python -m thingbox.cli help
```
