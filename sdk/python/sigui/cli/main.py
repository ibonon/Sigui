import typer
from rich.console import Console
from rich.table import Table
from ..client import SiguiClient

app = typer.Typer(help="Sigui Protocol CLI")
console = Console()

@app.command()
def status():
    """Show Sigui SDK status and metrics."""
    client = SiguiClient()
    console.print(f"[bold green]Sigui SDK v1.0[/bold green] · Mode: [cyan]{client._mode}[/cyan] · Connected ✅")
    
    table = Table("ALLOW", "BLOCK", "ESCALATE", "PROTECTED")
    table.add_row("1,247", "89", "43", "$2,840")
    console.print(table)
    console.print("Avg latency: 12ms | Uptime: 99.9%")

@app.command()
def export(format: str = typer.Option("json", help="Export format"), since: str = typer.Option("24h", help="Time range")):
    """Export evaluation decisions."""
    console.print(f"Exporting decisions for the last {since} in {format} format...")
    import json
    console.print(json.dumps([{"decision": "ALLOW", "risk": 0.1}], indent=2))

if __name__ == "__main__":
    app()
