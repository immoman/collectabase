import asyncio
from backend.services.lookup_service import lookup_igdb_title, cache_remote_cover

async def main():
    print("Testing IGDB lookup for 'Super Mario 64'")
    res = await lookup_igdb_title("Super Mario 64")
    print("IGDB Result:", res)
    
    if res.get("results") and res["results"][0].get("cover_url"):
        url = res["results"][0]["cover_url"]
        print("Caching URL:", url)
        cached = await cache_remote_cover(url)
        print("Cached URL:", cached)

if __name__ == "__main__":
    asyncio.run(main())
