from tic_tac_toe_board_refactored import TicTacToeBoard, redis_client, pubsub_channel
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

    waiting_printed = False  # So we don’t repeat “Waiting for your turn…”

    while True:
        refreshed_game = await TicTacToeBoard.load_from_redis()
        game.state = refreshed_game.state
        game.end_message = refreshed_game.end_message
        game.positions = refreshed_game.positions
        game.player_turn = refreshed_game.player_turn

        if game.state == "game_over":
            print(game.display_board(hide_numbers=True))
            print(game.end_message)
            break

        # show any pubsub updates
        if getattr(game, "latest_pubsub_message", None):
            print(game.latest_pubsub_message["message"])
            game.latest_pubsub_message = None

        if game.is_my_turn(args.player):
            # Show board before move (with numbered positions)
            print(game.display_board(hide_numbers=False))

            try:
                index = int(input("Your move (0–8): "))
            except ValueError:
                print("Please enter a valid number.")
                continue

            result = await game.make_move(args.player, index)

            if result["success"]:
                print(result["board"])
                await redis_client.publish(pubsub_channel, args.player)

            waiting_printed = False  # reset if it was printed earlier
        else:
            if not waiting_printed:
                print("Waiting for your turn...")
                waiting_printed = True

        await asyncio.sleep(1)

    # Cancel listener
    listener_task.cancel()

if __name__ == "__main__":
    asyncio.run(main())
