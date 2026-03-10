import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from backend.price_tracker import _run_bulk_price_update
import backend.jobs as jobs

async def main():
    game_list = [
        {"id": 9999, "title": "Super Mario 64", "platform_name": "nintendo 64"}
    ]
    
    # Mocking database and background jobs stuff
    jobs.update = MagicMock()
    jobs.finish = MagicMock()
    
    with patch("backend.price_tracker.get_db") as mock_db, \
         patch("backend.price_tracker.set_app_meta") as mock_set_meta:
        
        # Make the mocked DB return a fake context manager
        mock_conn = MagicMock()
        mock_db.return_value.__enter__.return_value = mock_conn
        
        print("Running bulk price update...")
        try:
            await _run_bulk_price_update("dummy", game_list)
            print("Success! No crash.")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print("Crash:", e)

if __name__ == "__main__":
    asyncio.run(main())
