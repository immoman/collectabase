import asyncio
import sqlite3
from backend.price_tracker import _run_bulk_price_update
from backend.database import get_db

async def main():
    print("Preparing dummy game list...")
    with get_db() as db:
        # Create a game to test
        db.execute("INSERT OR REPLACE INTO games (id, title, platform_id, is_wishlist) VALUES (9999, 'Test Game', NULL, 0)")
        db.commit()
    
    game_list = [
        {"id": 9999, "title": "Super Mario 64", "platform_name": "nintendo 64"}
    ]
    
    print("Running bulk price update...")
    try:
        await _run_bulk_price_update("dummy_job", game_list)
        print("Success! No crash.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("Crashed with error:", e)

    with get_db() as db:
        db.execute("DELETE FROM games WHERE id = 9999")
        db.execute("DELETE FROM price_history where game_id = 9999")
        db.commit()

if __name__ == "__main__":
    asyncio.run(main())
