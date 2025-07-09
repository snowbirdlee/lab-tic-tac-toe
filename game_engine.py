from tic_tac_toe_board import TicTacToeBoard

def main():
    print("Let's play Tic-Tac-Toe!")
    game = TicTacToeBoard()
    
    while game.state == "is_playing": # runs until 'state' changes
         # x always starts
        game.make_move()


if __name__ == "__main__":
    main()
