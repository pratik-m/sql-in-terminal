import json
import sqlite3
import time
from pathlib import Path

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import DataTable, Footer, Header, Static

from src.widget.textarea import TextArea

PATH = r"database3.db"


class SQLDB:
    def __init__(self, database) -> None:
        self.database = database
        self.conn = sqlite3.connect(self.database)
        self.conn.row_factory = sqlite3.Row

    def execute_sql(self, sql):
        with self.conn as conn:
            cur = conn.cursor()
            res = cur.execute(sql)
            return json.dumps([dict(x) for x in res.fetchall()])


class ResultInfoBar(Widget):
    def compose(self) -> ComposeResult:
        yield Static("Infobar", id="result-info")


class ResultsArea(Widget):
    def compose(self) -> ComposeResult:
        with ScrollableContainer():
            yield DataTable(id="sql-results")


class ResultsPanel(Widget):
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Result")
            yield ResultsArea()
            yield ResultInfoBar()


class SQLEditor(Widget):
    def compose(self) -> ComposeResult:
        yield TextArea(placeholder="Editor", id="sql-editor")


class EditorScreen(Screen):
    BINDINGS = [
        Binding(
            "ctrl+e", action="execute_sql", description="Execute SQL", priority=True
        ),
        Binding("f1", action="focus('sql-editor')", description="Focus Editor"),
        Binding(
            "f2",
            action="focus('sql-results')",
            description="Focus Result",
            priority=True,
        ),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield SQLEditor()
            yield ResultsPanel()
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#sql-editor").focus()
        self._db = SQLDB(PATH)

    def action_execute_sql(self) -> None:
        query = self.query_one("#sql-editor").value
        table = self.query_one(DataTable)
        info_bar = self.query_one("#result-info")

        try:
            start_time = time.time()
            result = self._db.execute_sql(query)
            result = json.loads(result)
            end_time = time.time()
            time_taken = f"{end_time - start_time}:.2f"
            info_bar.update(
                f"Rows Fetched: {len(result)} | Execution Time: {time_taken}"
            )
            table.zebra_stripes = True
            table.cursor_type = "row"
            table.clear()
            if not table.columns:
                table.add_columns(*list(result[0].keys()))
            for i, row in enumerate(result, start=1):
                table.add_row(*tuple(row.values()), label=str(i))
            table.focus()

        except sqlite3.OperationalError as e:
            info_bar.update(Text(f"Error Occured: {e}", style="bold red"))
        except Exception as e:
            raise


class Ara(App):
    CSS_PATH = Path(__file__).parent / "ara.scss"

    def on_mount(self) -> None:
        self.push_screen(EditorScreen())


if __name__ == "__main__":
    app = Ara()
    app.run()
