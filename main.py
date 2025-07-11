from fastapi import FastAPI, Body #Request
from tic_tac_toe_board_refactored import TicTacToeBoard
app = FastAPI()

@app.get("/state")
async def get_state():
    board = await TicTacToeBoard.load_from_redis()
    return board.to_dict()

@app.post("/move")
async def post_move(
    player: str = Body(...), #accept JSON body
    index: int = Body(...)):
    board = await TicTacToeBoard.load_from_redis()
    result = await board.make_move(player, index) #called make_move
    return result

@app.post("/request")
async def reset_board():
    board = await TicTacToeBoard.load_from_redis()
    await board.reset_self()
    return board.to_dict()