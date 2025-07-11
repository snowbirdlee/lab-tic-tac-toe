from dataclasses import dataclass, field
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
                self.end_message = f"Game over! \n{self.player_turn.upper()} wins! Final board:\n{self.display_board(hide_numbers=True)}"
                self.state = "game_over"
                return True
        return False
    
    def check_draw(self):
        if all(pos in ["x", "o"] for pos in self.positions): #chatgpt
            self.end_message = f"Game over! \nIt's a draw! Final board:\n{self.display_board(hide_numbers=True)}"
            self.state = "game_over"
            return True
        return False
    
    def switch_turn(self):
        if self.player_turn == "x":
            self.player_turn = "o"
        else:
            self.player_turn = "x"

    async def make_move(self, current_player):
        waiting_printed = False

        while True:
            refreshed_game = await TicTacToeBoard.load_from_redis()
            if refreshed_game.state == "game_over":
                self.state = refreshed_game.state
                self.player_turn = refreshed_game.player_turn
                self.positions = refreshed_game.positions
                self.end_message = refreshed_game.end_message
                return

            if refreshed_game.is_my_turn(current_player):
                self.state = refreshed_game.state
                self.player_turn = refreshed_game.player_turn
                self.positions = refreshed_game.positions
                break
            else:
                if not waiting_printed:
                    print("\nWaiting for player...\n")
                    waiting_printed = True

        print(self.display_board())

        while True:
            try:
                index = await asyncio.to_thread(input, "What's your move? (0-8) ")
                index = int(index)
                if index < 0 or index >= 9:
                    print("Please enter a valid number (0-8)")
                    continue
                if self.positions[index] in ["x", "o"]:
                    print("That spot is already taken.")
                    continue
                self.positions[index] = self.player_turn
                break
            except ValueError:
                print("Please enter a valid number (0-8).")

        print(self.display_board())

        if self.check_winner() or self.check_draw():
            await self.save_to_redis()
        else:
            self.switch_turn()
            await self.save_to_redis()

            
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
        refreshed_game = await TicTacToeBoard.load_from_redis()
        self.state = refreshed_game.state
        self.player_turn = refreshed_game.player_turn
        self.positions = refreshed_game.positions
        self.end_message = refreshed_game.end_message

        if self.state == "game_over":
            return

        if not self.is_my_turn(current_player):
            if not hasattr(self, "_already_waiting"):
                print("Waiting for your turn...")
                self._already_waiting = True
            return

        if hasattr(self, "_already_waiting"):
            del self._already_waiting

        await self.make_move(current_player)
        await redis_client.publish(pubsub_channel, i_am_playing)

    async def listen_for_updates(self):
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(pubsub_channel)
        print(f"Listening to channel: {pubsub_channel}")

        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                latest_game = await TicTacToeBoard.load_from_redis()
                if latest_game.state == "game_over":
                    break
                print(f"\nUpdate from other player: {message['data']}\n")
        except asyncio.CancelledError:
            print("Stopped listening")
        finally:
            await pubsub.unsubscribe(pubsub_channel)
