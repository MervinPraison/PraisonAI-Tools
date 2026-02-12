"""
PraisonAI Observability CLI.

Lightweight CLI that lives in praisonai_tools, close to the observability code.
Can be run standalone: python -m praisonai_tools.observability.cli doctor
Or via the praisonai wrapper: praisonai obs doctor
"""

from typing import Optional

import typer


app = typer.Typer(help="Observability diagnostics and management")


def _get_obs():
    """Lazy-import obs singleton."""
    try:
        from praisonai_tools.observability import obs
        return obs
    except ImportError:
        from rich.console import Console
        Console(stderr=True).print(
            "[red]✗ praisonai-tools observability not available.[/red]"
        )
        raise typer.Exit(1)


def _print_doctor_table(results: dict) -> None:
    """Pretty-print doctor results as a Rich table."""
    from rich.console import Console
    from rich.table import Table

    console = Console()
    console.print("\n[bold cyan]🔍 PraisonAI Observability Doctor[/bold cyan]\n")

    table = Table(show_header=True, header_style="bold")
    table.add_column("Check", style="dim", min_width=20)
    table.add_column("Result")

    # Enabled
    enabled = results.get("enabled", False)
    table.add_row(
        "Enabled",
        "[green]✓ Yes[/green]" if enabled else "[yellow]✗ No[/yellow]",
    )

    # Provider
    provider = results.get("provider")
    table.add_row(
        "Active Provider",
        f"[green]{provider}[/green]" if provider else "[dim]None[/dim]",
    )

    # Connection
    conn_status = results.get("connection_status")
    conn_msg = results.get("connection_message", "")
    if conn_status is True:
        table.add_row("Connection", f"[green]✓ {conn_msg}[/green]")
    elif conn_status is False:
        table.add_row("Connection", f"[red]✗ {conn_msg}[/red]")
    else:
        table.add_row("Connection", "[dim]N/A[/dim]")

    # Available providers
    available = results.get("available_providers", [])
    table.add_row(
        "Available Providers",
        ", ".join(available) if available else "[dim]None[/dim]",
    )

    # Registered providers
    registered = results.get("registered_providers", [])
    table.add_row(
        "Registered Providers",
        ", ".join(registered) if registered else "[dim]None[/dim]",
    )

    console.print(table)
    console.print()


@app.command("doctor")
def obs_doctor(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Run observability health checks.

    Checks provider status, connection, and available providers.

    Examples:
        python -m praisonai_tools.observability.cli doctor
        praisonai obs doctor
        praisonai obs doctor --json
    """
    obs = _get_obs()
    results = obs.doctor()

    if json_output:
        import json
        typer.echo(json.dumps(results, indent=2, default=str))
        raise typer.Exit(0)

    _print_doctor_table(results)
    raise typer.Exit(0)


@app.command("verify")
def obs_verify(
    provider: str = typer.Option("langsmith", help="Provider to verify"),
    project: str = typer.Option("default", help="Project name to check"),
    limit: int = typer.Option(5, help="Number of recent runs to check"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Verify traces are recorded in the observability backend.

    Uses the provider's SDK to fetch recent traces and check for
    PraisonAI branding attributes.

    Examples:
        praisonai obs verify --provider langsmith --project "My First App"
        python -m praisonai_tools.observability.cli verify --json
    """
    from rich.console import Console
    from rich.table import Table

    console = Console()

    if provider == "langsmith":
        _verify_langsmith(console, project, limit, json_output)
    else:
        console.print(f"[yellow]Verify not yet supported for provider: {provider}[/yellow]")
        raise typer.Exit(1)


def _verify_langsmith(console, project: str, limit: int, json_output: bool):
    """Verify traces in LangSmith using the LangSmith SDK."""
    import os
    from rich.table import Table

    try:
        from langsmith import Client
    except ImportError:
        console.print("[red]✗ langsmith SDK not installed.[/red]")
        console.print("[dim]Install with: pip install langsmith[/dim]")
        raise typer.Exit(1)

    api_key = os.getenv("LANGSMITH_API_KEY")
    endpoint = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")

    if not api_key:
        console.print("[red]✗ LANGSMITH_API_KEY not set.[/red]")
        raise typer.Exit(1)

    ls = Client(api_url=endpoint, api_key=api_key)

    try:
        runs = list(ls.list_runs(
            project_name=project,
            execution_order=1,  # root runs only
            limit=limit,
        ))
    except Exception as e:
        console.print(f"[red]✗ Failed to fetch runs: {e}[/red]")
        raise typer.Exit(1)

    # Collect results
    results = []
    for run in runs:
        extra = run.extra or {}
        metadata = extra.get("metadata", {})
        results.append({
            "name": run.name,
            "id": str(run.id),
            "status": run.status,
            "run_type": run.run_type,
            "has_inputs": bool(run.inputs),
            "has_outputs": bool(run.outputs),
            "praisonai.version": metadata.get("praisonai.version"),
            "praisonai.framework": metadata.get("praisonai.framework"),
            "start_time": str(run.start_time) if run.start_time else None,
        })

    if json_output:
        import json
        typer.echo(json.dumps({
            "project": project,
            "endpoint": endpoint,
            "runs_checked": len(results),
            "runs": results,
        }, indent=2, default=str))
        raise typer.Exit(0)

    # Pretty print
    console.print(f"\n[bold cyan]🔍 PraisonAI Trace Verification[/bold cyan]")
    console.print(f"[dim]Project: {project} | Endpoint: {endpoint}[/dim]\n")

    if not results:
        console.print("[yellow]No runs found in project.[/yellow]")
        raise typer.Exit(0)

    table = Table(show_header=True, header_style="bold")
    table.add_column("Name", min_width=15)
    table.add_column("Type")
    table.add_column("Status")
    table.add_column("I/O")
    table.add_column("Version")
    table.add_column("Framework")

    branded_count = 0
    for r in results:
        version = r["praisonai.version"]
        framework = r["praisonai.framework"]
        has_branding = version is not None and framework is not None
        if has_branding:
            branded_count += 1

        table.add_row(
            r["name"],
            r["run_type"] or "—",
            f"[green]{r['status']}[/green]" if r["status"] == "success" else r["status"] or "—",
            "[green]✓[/green]" if r["has_inputs"] and r["has_outputs"] else "[yellow]partial[/yellow]",
            f"[green]{version}[/green]" if version else "[dim]—[/dim]",
            f"[green]{framework}[/green]" if framework else "[dim]—[/dim]",
        )

    console.print(table)
    console.print()

    # Summary
    total = len(results)
    if branded_count == total:
        console.print(f"[green]✓ All {total} runs have PraisonAI branding[/green]")
    elif branded_count > 0:
        console.print(f"[yellow]⚠ {branded_count}/{total} runs have PraisonAI branding[/yellow]")
    else:
        console.print(f"[red]✗ No runs have PraisonAI branding[/red]")

    console.print()
    raise typer.Exit(0)


@app.callback(invoke_without_command=True)
def obs_callback(ctx: typer.Context):
    """Observability diagnostics and management."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(obs_doctor)


if __name__ == "__main__":
    app()
