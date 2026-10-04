# manager_client/report.py

# Imports -------------------------------------------
from pathlib import Path


# Class -------------------------------------------
class HiringReport:
    """Collect console output and save it as a Markdown hiring-workflow report."""

    def __init__(self):
        """Start an empty report."""
        self.lines = []

    def log(self, message: str):
        """Print and retain a single report message."""
        print(message)
        self.lines.append(message)

    def section(
        self,
        emoji: str,
        title: str,
        message: str,
    ):
        """Add a titled Markdown section and print a compact console version."""
        console_message = f"\n{emoji} {title}\n   {message}"

        print(console_message)

        self.lines.append(
            f"## {emoji} {title}\n\n{message}\n"
        )

    def save(self, path: str):
        """Write the accumulated report to ``path``, creating parent folders."""
        output_path = Path(path)

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        markdown = "# Hiring Workflow Report\n\n"

        markdown += "\n".join(self.lines)

        output_path.write_text(
            markdown,
            encoding="utf-8",
        )
