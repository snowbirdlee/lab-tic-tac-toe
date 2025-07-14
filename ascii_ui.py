# websocket_server.py
import asyncio
import websockets
import json
import os

WEBSOCKET_URL = "ws://ai.thewcl.com:8702"

async def listen_for_updates():
    async with websockets.connect(WEBSOCKET_URL) as websocket:
        print("Connected to WebSocket server!")
        async for message in websocket:
            try:
                game_data = json.loads(message)
                game_state = game_data.get("positions")  # still named "positions", but it's actually the full game state
                if not game_state:
                    print("No game state in message") #chatgpt
                    continue
                
                positions = game_state.get("positions") #chatgpt
                state = game_state.get("state")
                
                if positions is not None and len(positions) == 9:
                    os.system('cls' if os.name == 'nt' else 'clear')
                    print(display_board(positions))
                else:
                    print("Warning. Missing or malformed 'positions' field")
                    
                if state == "game_over":
                    print("Game over. Closing viewer.")
                    break
            except json.JSONDecodeError:
                print("Warning: Received non-JSON message:", message)

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
