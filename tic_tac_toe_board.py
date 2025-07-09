from dataclasses import dataclass, field

@dataclass
class TicTacToeBoard():
    state: str = field(default = "is_playing")
    player_turn: str = field(default = "x")
    positions: list = field(default_factory = lambda: [" " for _ in range(9)])
        # lambda function. creates 9 " "
    
    def is_my_turn(self):
        i_am = input("Are you 'X' or 'O'? ").lower().strip()
        return i_am == self.player_turn # if they match
        
    def check_winner(self):
        if (
            self.positions[0] == self.positions[1] == self.positions[2] != " "
        or self.positions[3] == self.positions[4] == self.positions[5] != " "
        or self.positions[6] == self.positions[7] == self.positions[8] != " "
        or self.positions[0] == self.positions[3] == self.positions[6] != " "
        or self.positions[1] == self.positions[4] == self.positions[7] != " "
        or self.positions[2] == self.positions[5] == self.positions[8] != " "
        or self.positions[0] == self.positions[4] == self.positions[8] != " "
        or self.positions[2] == self.positions[4] == self.positions[6] != " "
        ):
            if self.player_turn == "x":
                print("\nX wins!")
            else:
                print("\nO wins!")
            self.state = "game_over"
            return True
        return False
    
    def check_draw(self):
        if " " not in self.positions:
            print("\nIt's a draw!")
            self.state = "game_over"
            return True
        return False
    
    def switch_turn(self):
        if self.player_turn == "x":
            self.player_turn = "o"
        else:
            self.player_turn = "x"

    def make_move(self):
        while True:
            if self.is_my_turn():
                break
            else:
                print("Waiting for player...")
        
        while True:
            try:
                index = int(input("What's your move? (0-8) "))                  
                if index < 0 or index >= 9:
                    print("Please enter a valid number (0-8)")
                    continue                
                if self.positions[index] != " ":
                    print("That spot is already taken.")
                    continue                
                self.positions[index] = self.player_turn
                break             
            except ValueError:
                print("Please enter a valid number (0-8).")

        print(f"\n{self.positions}\n")
        if not self.check_winner():
            self.check_draw()
            self.switch_turn()