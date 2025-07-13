from dataclasses import dataclass, field, asdict
from redis.asyncio import Redis
import json
from dotenv import load_dotenv
import os
import asyncio


load_dotenv()

# Redis info
redis_client_password = os.getenv("redis_client_password")
redis_client = Redis(host="ai.thewcl.com", port=6379, password=redis_client_password, db=2, decode_responses=True)
redis_key = "tic_tac_toe:game_state:2"
pubsub_channel = "ttt:game_state_changed:2"

#THE BOARD
@dataclass
class TicTacToeBoard:
    state: str = field(default = "is_playing")
    player_turn: str = field(default = "x")
    positions: list = field(default_factory=lambda: [str(n) for n in range(9)]) #numbers the board
    end_message: str = field(default = "")
    redis_key: str = redis_key
    
    
    
#STEP 1 METHODS
    def is_my_turn(self, current_player: str):
        return current_player == self.player_turn and self.state == "is_playing" #T or F
        
    def check_winner(self):
        winning_possibilities = [
        [0, 1, 2],  [3, 4, 5], [6, 7, 8],  # rows
        [0, 3, 6],  [1, 4, 7],  [2, 5, 8],  # columns
        [0, 4, 8],  [2, 4, 6] # diagonals
        ]      
        for [a, b, c] in winning_possibilities:
            if self.positions[a] == self.positions[b] == self.positions[c] and self.positions[a] in ["x", "o"]:
                self.end_message = f"Game over! \n{self.player_turn.upper()} wins!"
                self.state = "game_over"
                return True #runs when winner is found
        return False
    
    def check_draw(self):
        if not self.check_winner():
            if all(pos in ["x", "o"] for pos in self.positions): #chatgpt
                self.end_message = "Game over! \nIt's a draw!"
                self.state = "game_over"
                return True #runs when a draw is found
        return False
    
    def switch_turn(self):
        if self.player_turn == "x":
            self.player_turn = "o"
        else:
            self.player_turn = "x"

    async def make_move(self, current_player, index):
        # Reload latest game state
        await self.refresh_game()

        # when game is over, we don't want any more moves
        if self.state == "game_over": 
            return {
                "success": False,
                "message": "Game is already over."
            }
        # if it's not their turn, we don't want them to go
        if not self.is_my_turn(current_player):
            return {
                "success": False,
                "message": "It's not your turn."
            }
        # Validate move; if they didn't put an integer between 0 and 8, we don't want them to go
        if not isinstance(index, int) or not (0 <= index <= 8):
            return {
                "success": False,
                "message": "Please enter a valid whole number (0-8)."
            }
        # if the spot is already taken, we don't want them to go    
        if self.positions[index] in ["x", "o"]:
            return {
                "success": False,
                "message": "That spot is already taken."
            }
        # Make the move if all the "if's" don't pass
        self.positions[index] = self.player_turn
        # if there's a winner or a draw, we're done and it'll show the board
        if self.check_winner() or self.check_draw():
            await self.save_to_redis()
            return {
                "success": True,
                "message": self.end_message,
                "board": self.to_dict(hide_numbers=True)
            }
        else:
            # Otherwise, switch turns and continue. save to redis.
            self.switch_turn()
            await self.save_to_redis()
            # it'll make a move
            return {
                "success": True,
                "message": "Move successful.",
                "board": self.to_dict(hide_numbers=False)
            }
            
#STEP 2 METHODS
    def serialize(self):
        return json.dumps(self.to_dict(include_display=False)) # puts the attributes to json data
    
    async def save_to_redis(self): #chatgpt
        json_string = self.serialize()
        #parsed_dictionary = json.loads(json_string) #turns it into a json dictionary
        await redis_client.set(self.redis_key, json_string) #save to redisjson
        
    @classmethod
    async def load_from_redis(cls):
        temp_instance = cls()
        raw_data = await redis_client.get(temp_instance.redis_key) # gets the board from redis
        if raw_data is None:
            return cls() # the class itself
        data = json.loads(raw_data)
        data.pop("display", None)
        return cls(**data) #class is returned. ** is dictionary UNPACKING
        
    async def reset_self(self): #resets the game state
        self.state = "is_playing"
        self.player_turn = "x"
        self.positions = [str(n) for n in range(9)]
        await self.save_to_redis()
         
    def display_board(self, hide_numbers=False): #chatgpt. for asthetic reasons, I put it in an actual board.
        def clean(pos): #chatgpt. wouldn't return this until the end of the game, where it's true.
            return pos if pos in ["x", "o"] else (" " if hide_numbers else pos)
        
        rows = []
        for n in range(0, 9, 3):
            row = f" {clean(self.positions[n])} | {clean(self.positions[n+1])} | {clean(self.positions[n+2])}"
            rows.append(row)
            if n < 6:
                rows.append("---+---+---")
        return "\n".join(rows) + "\n"
    
          
#STEP 4 METHODS
    def to_dict(self, include_display=True, hide_numbers=False): #new method, similar variables
        board_dict = asdict(self)
        if include_display:
            board_dict["display"] = self.display_board(hide_numbers=hide_numbers)
        return board_dict

#misc
    async def refresh_game(self):
        refreshed_game = await TicTacToeBoard.load_from_redis()
        self.state = refreshed_game.state
        self.player_turn = refreshed_game.player_turn
        self.positions = refreshed_game.positions
        self.end_message = refreshed_game.end_message
        return
    
if __name__ == "__main__":
    async def test_make_move():
        board = TicTacToeBoard(redis_key=redis_key)
        await board.reset_self()  # Always start from clean state

        move_result = await board.make_move("x", 0)
        print("Move Result:", move_result)
        print(board.display_board())

    asyncio.run(test_make_move())



    
    