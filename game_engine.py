from tic_tac_toe_board import TicTacToeBoard
import argparse
import asyncio

async def main():
    parser = argparse.ArgumentParser(description="Play Tic Tac Toe using Redis")
    parser.add_argument("--player", type=str, choices=["x", "o"], help="Your player symbol (x or o)", required=True)
    parser.add_argument("--reset", action="store_true", help="Reset the game state")

    args = parser.parse_args()

    if args.reset:
        game = TicTacToeBoard()
        await game.reset_self()
        print("Game has been reset.")
        return

    print("Let's play Tic-Tac-Toe!")

    try:
        game = await TicTacToeBoard.load_from_redis()
    except ValueError:
        print("No game state found. Creating a new board in Redis.")
        game = TicTacToeBoard()
        await game.save_to_redis()

    listener_task = asyncio.create_task(game.listen_for_updates())

    while True:
        refreshed_game = await TicTacToeBoard.load_from_redis()
        game.state = refreshed_game.state
        game.end_message = refreshed_game.end_message
        game.positions = refreshed_game.positions
        game.player_turn = refreshed_game.player_turn

        if game.state == "game_over":
            if game.end_message:
                print(game.display_board(hide_numbers=True))
                print(game.end_message)
            break

        await game.handle_board_state("A move was made!", args.player)
        await asyncio.sleep(1)


    refreshed = await TicTacToeBoard.load_from_redis()

    if game.end_message != refreshed.end_message:
        print(refreshed.display_board(hide_numbers=True))
        print(refreshed.end_message)

    listener_task.cancel()

if __name__ == "__main__":
    asyncio.run(main())
