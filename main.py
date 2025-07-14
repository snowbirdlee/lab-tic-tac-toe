from fastapi import FastAPI, Body #Request
from tic_tac_toe_board import TicTacToeBoard
from fastapi.responses import JSONResponse
app = FastAPI()

@app.get("/state")
async def get_state():
    try:
        #import ipdb; ipdb.set_trace()
        board = await TicTacToeBoard.load_from_redis()
        hide_numbers = board.state == "game_over"
        if board.positions == [str(n) for n in range(9)]:  # Detect "empty board"
            await board.save_to_redis()
        return board.to_dict(hide_numbers=hide_numbers)
    except Exception as e:
        print("ERROR in /state:", e)
        raise

@app.post("/move")
async def post_move(
    player: str = Body(...), #accept JSON body
    index: int = Body(...)):
    board = await TicTacToeBoard.load_from_redis()
    result = await board.make_move(player, index) #called make_move
    status = 200 if result["success"] else 400
    return JSONResponse(content=result, status_code=status)

@app.post("/reset") #i had a typo; it's supposed to be reset not request
async def reset_board():
    board = await TicTacToeBoard.load_from_redis()
    await board.reset_self()
    return {
        "message": "Game has been reset.", #now it prints a message :)
        "board": board.to_dict() 
    }
