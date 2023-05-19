import json
import logging
import sqlite3
import sys
from typing import List

from rich.syntax import Syntax
from textual import events, on
from textual.app import App, ComposeResult, log
from textual.containers import Container, Vertical, VerticalScroll
from textual.widgets import (
    Button,
    ContentSwitcher,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Static,
    TabbedContent,
    TabPane,
    Tabs,
    TextLog,
)


class SQLiteDB:
    """Connect and query to the DB"""

    def __init__(self, database) -> None:
        self.database = database
        self.conn = sqlite3.connect(database)
        self.conn.row_factory = sqlite3.Row

    def _execute_sql(self, sql: str, args=None):
        with self.conn as conn:
            cur = conn.cursor()
            res = cur.execute(sql)
            return res.fetchall()

    def list_tables(self, filter: str = None) -> List[str]:
        """retrive the list of all tables in the database"""

        res = self._execute_sql("select name from sqlite_master")
        tables = [r[0] for r in res]
        return tables

    def get_table_details(self, table_name: str) -> dict[str, any]:
        """Fetch the details of the table"""

        res = self._execute_sql(f"pragma table_info({table_name})")
        print(res)
        return json.dumps([dict(d) for d in res])


class LabelItem(ListItem):
    def __init__(self, label: str) -> None:
        super().__init__()
        self.label = label

    def compose(self) -> ComposeResult:
        yield Label(self.label)


class TableButtons(Vertical):
    DEFAULT_CSS = """
    TableButtons {
        dock: left;
        width: auto;
        overflow-y: scroll;
    }

    TableButtons > Button {
        width: 100%;
    }
    """

    def __init__(self, tables: List[str]) -> None:
        super().__init__()
        self.tables = tables

    def compose(self) -> ComposeResult:
        for table in self.tables:
            yield Button(table, id=table)


class SQLiteApp(App):
    """App to query SQLite database"""

    CSS = """
        Screen {
            background: $panel;
            layers: notes;
        }

        #table-list {
            scrollbar-gutter: stable;
            overflow: auto;
            width: 20%;
            height: 100%;
            dock: left;
        }

        #side-header {
            width: 20%;
            height: 10%;
            dock: left;
        }

        #table-details {
            width: 100%;
            height: auto;
            align: center middle;
            overflow: auto;
        }
        #details {
            width: auto;
            height: auto;
        }

        ListView {
            width: 30;
            height: auto;
            margin: 2 2;
        }

        Label {
            padding: 1 2;
        }




    TextLog {
        background: $surface;
        color: $text;
        height: 50vh;
        dock: bottom;
        layer: notes;
        border-top: hkey $primary;
        offset-y: 0;
        transition: offset 400ms in_out_cubic;
        padding: 0 1 1 1;
    }


    TextLog:focus {
        offset: 0 0 !important;
    }

    TextLog.-hidden {
        offset-y: 100%;
    }
    """

    BINDINGS = [
        ("f1", "app.toggle_class('TextLog', '-hidden')", "Notes"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger("spam_application")
        self.logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler("spam.log")
        fh.setLevel(logging.DEBUG)
        self.logger.addHandler(fh)

    def compose(self) -> ComposeResult:
        # db_path = sys.argv[1]
        self.db = SQLiteDB(sys.argv[1])
        tables = self.db.list_tables()
        yield Header()
        # yield Input(placeholder="Search for a word")
        with Container():
            yield TextLog(classes="-hidden", wrap=False, highlight=True, markup=True)
            # yield Static("Table list", id="side-header")
            # yield ListView(*[LabelItem(t) for t in tables], id="table-list")
            yield TableButtons(tables)
            with TabbedContent():
                with TabPane("Struture", id="Structure"):
                    with VerticalScroll(id="table-details"):
                        yield DataTable(id="details")

                with TabPane("Data", id="data"):
                    with VerticalScroll(id="table-details"):
                        yield DataTable(id="details1")

        yield Footer()

    def on_mount(self) -> None:
        """called when app starts"""
        pass

    @on(TabbedContent.TabActivated, tab="#data")
    def show_data(self) -> None:
        self.query_one(TextLog).write("message")
        # sys.exit(1)

    def log2(self, msg) -> None:
        self.logger.debug(msg)

    # handle proper class button here
    @on(Button.Pressed)
    def handle_table_button(self, message: Button.Pressed) -> None:
        self.query_one(TextLog).write("message")
        self.log2(message.button.id)
        details = self.query_one("#details")
        self.log2(details)
        x = self.db.get_table_details(message.button.id)
        self.log2(x)
        x = json.loads(x)
        self.log2(x)
        details.clear()
        if not details.columns:
            details.add_columns(*list(x[0].keys()))
        self.log2([tuple(r.values()) for r in x])
        details.add_rows([tuple(r.values()) for r in x])

    def on_list_view_selected(self, event: ListView.Selected):
        details = self.query_one("#details")
        x = self.db.get_table_details(event.item.label)
        x = json.loads(x)
        details.clear()
        if not details.columns:
            details.add_columns(*list(x[0].keys()))
        details.add_rows([tuple(r.values()) for r in x])

    def on_input_changed(self, message: Input.Changed) -> None:
        log(message.value)


if __name__ == "__main__":
    SQLiteApp().run()
