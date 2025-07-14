# websocket_server.py
import asyncio
import websockets
import json
import os

WEBSOCKET_URL = "ws://localhost:8702" #step 7. chatgpt

async def listen_for_updates():
    async with websockets.connect(WEBSOCKET_URL) as websocket:
        print("Connected to WebSocket server!")
        try:
            async for message in websocket:
                try:
                    game_data = json.loads(message)
                    
                    positions = game_data.get("positions") #chatgpt
                    state = game_data.get("state")
                    player_turn = game_data.get("player_turn")
                    
                    if positions is not None and len(positions) == 9:
                        os.system('cls' if os.name == 'nt' else 'clear')
                        print(display_board(positions))
                        if state == "is_playing" and player_turn in ["x", "o"]:
                            print(f"\nIt is player {player_turn.upper()}'s turn.")
                        elif state == "game_over":
                            print("\nGame over.")
                            break  
                    else:
                        print("Warning. Missing or malformed 'positions' field")
                        
                except json.JSONDecodeError:
                    print("Warning: Received non-JSON message:", message)
        except websockets.exceptions.ConnectionClosedError:
            print("Connection closed by server. Exiting viewer.")

def display_board(positions, hide_numbers=False): #chatgpt. for asthetic reasons, I put it in an actual board.
    def clean(pos): #chatgpt. wouldn't return this until the end of the game, where it's true.
        return pos if pos in ["x", "o"] else (" " if hide_numbers else pos)
        
    rows = []
    for n in range(0, 9, 3):
        row = f" {clean(positions[n])} | {clean(positions[n+1])} | {clean(positions[n+2])}"
        rows.append(row)
        if n < 6:
            rows.append("---+---+---")
    return "\n".join(rows) + "\n"

if __name__ == "__main__":
    asyncio.run(listen_for_updates())
