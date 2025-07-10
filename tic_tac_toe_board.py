from dataclasses import dataclass, field
from redis import Redis
import json

redis_client = Redis(host="ai.thewcl.com", port=6379, password="atmega328", db=2)
redisKey = "tic_tac_toe:game_state:2"

@dataclass
class TicTacToeBoard():
    state: str = field(default = "is_playing")
    player_turn: str = field(default = "x")
    positions: list = field(default_factory = lambda: [str(n) for n in range(9)])
    end_message: str = field(default = "")
        # lambda function. creates 9 " "
    
    def is_my_turn(self, current_player):
        return current_player == self.player_turn and self.state == "is_playing" #T or F
        
    def check_winner(self):
        winning_possibilities = [
        [0, 1, 2],  [3, 4, 5], [6, 7, 8],  # rows
        [0, 3, 6],  [1, 4, 7],  [2, 5, 8],  # columns
        [0, 4, 8],  [2, 4, 6] # diagonals
        ]      
        for [a, b, c] in winning_possibilities:
            if self.positions[a] == self.positions[b] == self.positions[c] and self.positions[a] in ["x", "o"]:
                self.end_message = f"Game over! \n{self.player_turn.upper()} wins! Final board:\n{self.display_board(hide_numbers = True)}"
                self.state = "game_over"
                return True
        return False
    
    def check_draw(self):
        if all(pos in ["x", "o"] for pos in self.positions): #chatgpt
            self.end_message = f"Game over! \nIt's a draw! Final board:\n{self.display_board(hide_numbers = True)}"
            self.state = "game_over"
            return True
        return False
    
    def switch_turn(self):
        if self.player_turn == "x":
            self.player_turn = "o"
        else:
            self.player_turn = "x"

    def make_move(self, current_player):
        waiting_printed = False
        
        while True:
            refreshed_game = TicTacToeBoard.load_from_redis()
            if refreshed_game.state == "game_over": #chatgpt. refreshes the game and transfers to player's side
                self.state = refreshed_game.state
                self.player_turn = refreshed_game.player_turn
                self.positions = refreshed_game.positions
                self.end_message = refreshed_game.end_message
                print(self.end_message)
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
                index = int(input("What's your move? (0-8) "))                  
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
            self.save_to_redis()
            print(self.end_message)
        else:
            self.switch_turn()
            
    def serialize(self):
        return json.dumps({
            "state": self.state,
            "player_turn": self.player_turn,
            "positions": self.positions,
            "end_message": self.end_message
        }) # puts the attributes to json data
    
    def save_to_redis(self): #chatgpt
        json_string = self.serialize() #calls serialized string
        parsed_dictionary = json.loads(json_string) #turns it into a json dictionary
        redis_client.json().set(redisKey, ".", parsed_dictionary) #save to redisjson
        
    @classmethod
    def load_from_redis(cls):
        data = redis_client.json().get(redisKey) #gets game state from redis
        if data is None:
            raise ValueError("No game state found in Redis") #checks if it exists in redis and warns if it doesn't
        return cls(**data) #class is returned
    
    def reset_self(self): #resets the game state
        self.state = "is_playing"
        self.player_turn = "x"
        self.positions = [str(n) for n in range(9)]
        self.save_to_redis()
         
    def display_board(self, hide_numbers = False): #chatgpt. for asthetic reasons, I put it in an actual board.
        def clean(pos): #chatgpt. wouldn't return this until the end of the game, where it's true.
            return pos if pos in ["x", "o"] else (" " if hide_numbers else pos)
        
        rows = []
        for n in range(0, 9, 3):
            row = f" {clean(self.positions[n])} | {clean(self.positions[n+1])} | {clean(self.positions[n+2])}"
            rows.append(row)
            if n < 6:
                rows.append("---+---+---")
        return "\n".join(rows) + "\n"