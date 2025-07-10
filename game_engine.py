from tic_tac_toe_board import TicTacToeBoard
import argparse #chatgpt



def main():
    parser = argparse.ArgumentParser(description="Play Tic Tac Toe using Redis")
    parser.add_argument("--player", type=str, choices=["x", "o"], help="Your player symbol (x or o)", required=True)
    parser.add_argument("--reset", action="store_true", help="Reset the game state")

    args = parser.parse_args()

    if args.reset:
        game = TicTacToeBoard()
        game.reset_self()
        print("Game has been reset.")
        return
    
    print("Let's play Tic-Tac-Toe!")
    
    try: #chatgpt. if it's on redis, it gets it. if it's not, then it'll create one
        game = TicTacToeBoard.load_from_redis()
    except ValueError:
        print("No game state found. Creating a new board in Redis.")
        game = TicTacToeBoard()
        game.save_to_redis()
    
    while game.state == "is_playing": # runs until 'state' changes
         # x always starts
        game.make_move(args.player)
        game.save_to_redis()
        
    game.save_to_redis()

if __name__ == "__main__":
    main()
