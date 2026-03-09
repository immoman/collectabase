import os
import sqlite3
import argparse
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt

# Initialize Rich console
console = Console()

# Database path (relative or absolute)
DB_PATH = os.path.join(os.path.dirname(__file__), "backend", "app", "data", "games.db")

def get_db_connection():
    if not os.path.exists(DB_PATH):
        console.print(f"[bold red]Database not found at {DB_PATH}[/bold red]")
        exit(1)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def search_games(query=""):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if query:
        cursor.execute("""
            SELECT g.id, g.title, p.name as platform_name, g.current_value, g.item_type
            FROM games g
            LEFT JOIN platforms p ON g.platform_id = p.id
            WHERE g.title LIKE ? OR p.name LIKE ?
            ORDER BY g.title ASC
        """, (f"%{query}%", f"%{query}%"))
    else:
        cursor.execute("""
            SELECT g.id, g.title, p.name as platform_name, g.current_value, g.item_type
            FROM games g
            LEFT JOIN platforms p ON g.platform_id = p.id
            ORDER BY g.title ASC
            LIMIT 50
        """)
        
    games = cursor.fetchall()
    conn.close()
    
    if not games:
        console.print(f"[yellow]No games found matching '{query}'.[/yellow]")
        return
        
    table = Table(title=f"Search Results for '{query}'" if query else "Latest Games (Limit 50)")
    
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Title", style="magenta")
    table.add_column("Platform", style="green")
    table.add_column("Value (€)", justify="right", style="bold yellow")
    table.add_column("Type", justify="center")

    total_value = 0
    for game in games:
        val = game["current_value"]
        val_str = f"{val:.2f}" if val is not None else "—"
        if val is not None:
            total_value += val
            
        table.add_row(
            str(game["id"]),
            game["title"],
            game["platform_name"] or "Unknown",
            val_str,
            game["item_type"] or "Unknown"
        )

    console.print(table)
    
    if query:
        console.print(f"\n[bold]Total Value of Result:[/bold] [yellow]€{total_value:.2f}[/yellow]")

def show_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Total count
    cursor.execute("SELECT COUNT(*) as count FROM games WHERE is_wishlist = 0")
    total_games = cursor.fetchone()["count"]
    
    # Total Value
    cursor.execute("SELECT SUM(current_value) as total FROM games WHERE is_wishlist = 0")
    total_val = cursor.fetchone()["total"] or 0
    
    # Platform counts
    cursor.execute("""
        SELECT p.name, COUNT(g.id) as num
        FROM games g
        JOIN platforms p ON g.platform_id = p.id
        WHERE g.is_wishlist = 0
        GROUP BY p.name
        ORDER BY num DESC
        LIMIT 5
    """)
    top_platforms = cursor.fetchall()
    
    conn.close()
    
    console.print("\n[bold cyan]Collectabase Statistics[/bold cyan]")
    console.print("=" * 30)
    console.print(f"🎮 [bold]Total Collection Size:[/bold] {total_games} Items")
    console.print(f"💰 [bold]Total Estimated Value:[/bold] [yellow]€{total_val:.2f}[/yellow]")
    
    console.print("\n[bold]Top 5 Platforms:[/bold]")
    for p in top_platforms:
        console.print(f" - {p['name']}: {p['num']} items")
    console.print()

def main():
    parser = argparse.ArgumentParser(description="Collectabase CLI - Manage your collection from the terminal")
    parser.add_argument("command", nargs="?", choices=["search", "stats"], help="Command to run")
    parser.add_argument("query", nargs="?", default="", help="Search query (for 'search' command)")
    
    args = parser.parse_args()
    
    if args.command == "search":
        search_games(args.query)
    elif args.command == "stats":
        show_stats()
    else:
        # Interactive mode
        console.print("[bold cyan]Welcome to Collectabase CLI[/bold cyan] 🗃️")
        while True:
            console.print("\nOptions: [1] Search Games, [2] Show Stats, [q] Quit")
            choice = Prompt.ask("Choose an option", choices=["1", "2", "q"], default="q")
            
            if choice == "1":
                query = Prompt.ask("Enter search query (leave blank for all)")
                search_games(query)
            elif choice == "2":
                show_stats()
            elif choice == "q":
                console.print("[green]Goodbye![/green]")
                break

if __name__ == "__main__":
    main()
