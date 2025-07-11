from dataclasses import dataclass, field, asdict
from redis.asyncio import Redis
import json
import asyncio

redis_client = Redis(host="ai.thewcl.com", port=6379, password="atmega328", db=2, decode_responses=True)
redisKey = "tic_tac_toe:game_state:2"
pubsub_channel = "ttt:game_state_changed:2"

@dataclass
class TicTacToeBoard:
    state: str = field(default = "is_playing")
    player_turn: str = field(default = "x")
    positions: list = field(default_factory=lambda: [str(n) for n in range(9)])
    end_message: str = field(default = "")
    
    
    
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
                return True
        return False
    
    def check_draw(self):
        if all(pos in ["x", "o"] for pos in self.positions): #chatgpt
            self.end_message = "Game over! \nIt's a draw!"
            self.state = "game_over"
            return True
        return False
    
    def switch_turn(self):
        if self.player_turn == "x":
            self.player_turn = "o"
        else:
            self.player_turn = "x"

    async def make_move(self, current_player, index):
        # Reload latest game state
        refreshed_game = await TicTacToeBoard.load_from_redis()
        self.state = refreshed_game.state
        self.player_turn = refreshed_game.player_turn
        self.positions = refreshed_game.positions
        self.end_message = refreshed_game.end_message

        if self.state == "game_over":
            return {
                "success": False,
                "message": "Game is already over."
            }

        if not self.is_my_turn(current_player):
            return {
                "success": False,
                "message": "It's not your turn."
            }

        # Validate move
        if not (0 <= index <= 8):
            return {
                "success": False,
                "message": "Please enter a valid number (0-8)."
            }

        if self.positions[index] in ["x", "o"]:
            return {
                "success": False,
                "message": "That spot is already taken."
            }

        # Make the move
        self.positions[index] = self.player_turn

        if self.check_winner() or self.check_draw():
            await self.save_to_redis()
            return {
                "success": True,
                "message": self.end_message,
                "board": self.display_board(hide_numbers=True)
            }

        # Otherwise, switch turns and continue
        self.switch_turn()
        await self.save_to_redis()

        return {
            "success": True,
            "message": "Move successful.",
            "board": self.display_board(hide_numbers=False)
        }
    
            
#STEP 2 METHODS
    def serialize(self):
        return json.dumps({
            "state": self.state,
            "player_turn": self.player_turn,
            "positions": self.positions,
            "end_message": self.end_message
        }) # puts the attributes to json data
    
    async def save_to_redis(self): #chatgpt
        json_string = self.serialize() #calls serialized string
        parsed_dictionary = json.loads(json_string) #turns it into a json dictionary
        await redis_client.json().set(redisKey, ".", parsed_dictionary) #save to redisjson
        
    @classmethod
    async def load_from_redis(cls):
        data = await redis_client.json().get(redisKey) #gets game state from redis
        if data is None:
            raise ValueError("No game state found in Redis") #checks if it exists in redis and warns if it doesn't
        return cls(**data) #class is returned
    
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
    
#STEP 3 METHODS
    async def handle_board_state(self, i_am_playing, current_player):
        messages = []
        
        refreshed_game = await TicTacToeBoard.load_from_redis()
        self.state = refreshed_game.state
        self.player_turn = refreshed_game.player_turn
        self.positions = refreshed_game.positions
        self.end_message = refreshed_game.end_message

        if self.state == "game_over":
            return

        if not self.is_my_turn(current_player):
            if not hasattr(self, "_already_waiting"):
                self._already_waiting = True
            messages.append({
                "status": "not_your_turn",
                "message": "Waiting for your turn..."
            })

        if hasattr(self, "_already_waiting"):
            del self._already_waiting

        await self.make_move(current_player)
        await redis_client.publish(pubsub_channel, i_am_playing)
        
        return {"messages": messages}

    async def listen_for_updates(self):
        self.latest_pubsub_message = None
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(pubsub_channel)
        self.subscribed = True

        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                
                latest_game = await TicTacToeBoard.load_from_redis()
                if latest_game.state == "game_over":
                    break
                self.latest_pubsub_messages = {
                    "status": "opponent_update",
                    "message": f"Update from other player: {message['data']}",
                    "raw_data": message["data"],
                }
                
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe(pubsub_channel)
        
        return
                 
#STEP 4 METHODS
    def to_dict(self, include_display=True, hide_numbers=False): #new method, similar variables
        board_dict = asdict(self)
        if include_display:
            board_dict["display"] = self.display_board(hide_numbers=hide_numbers)
        return board_dict

