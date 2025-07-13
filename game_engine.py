import argparse
import asyncio
import httpx
from redis.asyncio import Redis
import os
from dotenv import load_dotenv
import json

load_dotenv()

redis_client = Redis(host="ai.thewcl.com", port=6379, password=os.getenv("redis_client_password"), db=2, decode_responses=True)
pubsub_channel = "ttt:game_state_changed:2"

#STEP 3 METHODS
async def handle_board_state(i_am_playing, game_data, client): #chatgpt help    
    if game_data["player_turn"] != i_am_playing or game_data["state"] != "is_playing":
        return
    print(game_data["display"])
    try:
        index = int(input("Your move (0-8): "))
    except ValueError:
        print("Invalid input. Please enter a whole number between 0-8.")
        return
    response = await client.post("http://localhost:8000/move", json={ #step 6
        "player": i_am_playing,
        "index": index
    })  
    if response.status_code != 200:
        try:
            error = response.json()
            print(error.get("message", "Move failed.")) #step 6. just in case it failed to get the message
        except Exception:
            print("Move failed.")
        return 
    try:
        result = response.json()
    except Exception as e:
        print("Failed to parse move response JSON:", e)
        return     
    if result["success"]:
        if "board" in result and "display" in result["board"]:
            print(result["board"]["display"])    
        # Show the message: "Move successful" or "Game over"
        print(result["message"])
        # 🔊 Publish to pubsub so the other player sees the change
        await redis_client.publish(pubsub_channel, json.dumps({
            "type": "GAME_UPDATE",
            "from": i_am_playing,  # or player
            "message": f"\nUpdate from Redis: {i_am_playing.upper()} moved!"
        }))

async def listen_for_updates(player, client): #mostly chatgpt
    pubsub = redis_client.pubsub()
    await pubsub.unsubscribe(pubsub_channel)  # clear any past sub
    await pubsub.subscribe(pubsub_channel)
    print(f"Subscribed to {pubsub_channel}")
    try:
        async for message in pubsub.listen():
            if not isinstance(message["data"], str) or not message["data"].startswith("{"): #checks if it's json. chatgpt.
                continue  # skip old/raw or bad data
            try:
                data = json.loads(message["data"])
            except Exception:
                continue
            if data.get("type") != "GAME_UPDATE": #step 6
                continue
            if data.get("from") == player:  #step 6. skip your own update. chatgpt
                continue   
            if "message" in data:
                print(data["message"])
            response = await client.get("http://localhost:8000/state") #step 6
            if response.status_code != 200:
                print("Failed to update board from other player.")
                continue
            try:
                game_data = response.json()
            except Exception:
                continue
            if game_data["state"] == "game_over":
                print(game_data["display"])
                print(game_data["end_message"])
                break
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe(pubsub_channel)


async def main():
    parser = argparse.ArgumentParser(description="Play Tic Tac Toe using Redis")
    parser.add_argument("--player", type=str, choices=["x", "o"], help="Your player symbol (x or o)", required=True)
    parser.add_argument("--reset", action="store_true", help="Reset the game state")
    args = parser.parse_args()
    i_am_playing = args.player

    if args.reset:
        async with httpx.AsyncClient() as client:
            await client.post("http://localhost:8000/request") #step 6
        print("Game has been reset.")
        return

    print("Let's play Tic-Tac-Toe!")

    async with httpx.AsyncClient() as client:
        listener_task = asyncio.create_task(listen_for_updates(i_am_playing, client))
        waiting_printed = False

        while True:
            response = await client.get("http://localhost:8000/state") #step 6
            if response.status_code != 200:
                print("The server did not return a valid response.")
                return
            try:
                game_data = response.json()
            except Exception as e:
                print("Failed to parse JSON:", e)
                return                     
            if game_data["state"] == "game_over":
                break
            await handle_board_state(i_am_playing, game_data, client)
            # reset if it was printed earlier
            if game_data["player_turn"] != i_am_playing:
                if not waiting_printed:
                    print("Waiting for your turn...")
                    waiting_printed = True
                    continue
            else:
                waiting_printed = False
            await asyncio.sleep(1)

    # Cancel listener
    listener_task.cancel()
    try:
        await listener_task
    except asyncio.CancelledError:
        pass

if __name__ == "__main__":
    asyncio.run(main())
