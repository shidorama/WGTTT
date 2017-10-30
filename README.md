# Missing

* keep-alives for connection (every 2-3 seconds)
* graceful reconnect (?)

# TODO

* disconnect on action timeout


# Protocol

## Auth

### Register
`{"cmd": "reg"}`

### Authenticate
`{"cmd": "auth", "user_id": "<user_id>"}`

## Game
### Get state
`{"cmd": "state"}`

### Enter queue
`{"cmd": "queue"}`

### Play game

* `{"cmd": "move", "pos": [x, y]}` - place your sign on specified coordinates  
* `{"cmd": "game"}` - get game stats
