# Missing

* keep-alives for connection (every 2-3 seconds)

# Protocol

## Auth

### Register
`{"cmd": "reg"}`

### Authenticate
`{"cmd": "auth", "user_id": "<user_id>"}`

## Game
### Game state
`{"cmd": "state", ......}`

### Enter queue
`{"cmd": "queue"}`

### Play game

* `{"cmd": "move", "pos": [x, y]}` - place your sign on specified coordinates  


# Deployment

Server developed and debugged using Python 2.7.13 in virtualenv

* install or setup venv (or not)
* install requirements from `requirements.txt` `pip install -r requirements.txt`
* make sure that script is able to write in it's directory  
* start `python main.py`

# Using client

* client located in `./client`
* requirements for client located in `./client` also
* by default it'll try to connect to localhost if server located elsewhere - start script with server host as parameter: `python client.py <server_host>`
* client directory should be writable by script, so it can store credentials
* as client is using ncurses - linux terminal preferred
