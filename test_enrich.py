import asyncio
from backend.price_tracker import enrich_catalog_from_library
from backend.database import get_db

async def main():
    # Insert a dummy game that doesn't exist in catalog
    with get_db() as db:
        db.execute("INSERT OR REPLACE INTO games (id, title, platform_id, is_wishlist) VALUES (9999, 'Super Mario 64', NULL, 0)")
        db.execute("DELETE FROM price_catalog WHERE title = 'Super Mario 64'")
        db.commit()
    
    print("Running enrich_catalog_from_library(limit=1)...")
    try:
        res = await enrich_catalog_from_library(limit=1, _admin=None)
        print("Result:", res)
    except Exception as e:
        import traceback
        traceback.print_exc()

    with get_db() as db:
        catalog = db.execute("SELECT * FROM price_catalog WHERE title = 'Super Mario 64'").fetchall()
        print("Inserted in catalog:", [dict(r) for r in catalog])
        db.execute("DELETE FROM games WHERE id = 9999")
        db.execute("DELETE FROM price_catalog WHERE title = 'Super Mario 64'")
        db.commit()

if __name__ == "__main__":
    asyncio.run(main())
