# Thingbox

Stores and serves up markdown content to users by ID

Check out README.md diles in `server` and `client` for more info.


## updating everything on a running server (assuming reload watching is on)

SSH to the server and change to the project root directory, then:

```bash
git pull
cd client
npm build
cd ../server
poetry install
```
