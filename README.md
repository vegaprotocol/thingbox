# Thingbox

Stores and serves up markdown content to users by ID

Check out README.md diles in `server` and `client` for more info.


## Updating a running server

Assuming reload watching is in use either in the service definition or the app server (e.g. uvicorn), SSH to the server and change to the project root directory, then:

```bash
git pull
cd client
yarn
yarn run build
cd ../server
poetry install
```
