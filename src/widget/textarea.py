from __future__ import annotations

from typing import ClassVar, Set

from rich.cells import cell_len, get_character_cell_size
from rich.console import Console, ConsoleOptions, RenderableType, RenderResult
from rich.highlighter import Highlighter
from rich.syntax import Syntax
from rich.text import Text
from textual import events
from textual.binding import Binding, BindingType
from textual.containers import ScrollableContainer
from textual.events import Blur, Focus, Mount
from textual.geometry import Offset, Size
from textual.message import Message
from textual.reactive import reactive, var
from textual.scroll_view import ScrollView


class _InputRenderable:
    """Render the input content"""

    def __init__(self, input: TextArea, cursor_visible: bool) -> None:
        self.input = input
        self.cursor_visible = cursor_visible

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "RenderResult":
        input = self.input
        result = input._value

        if self.cursor_visible and input.has_focus:
            cursor = input.cursor_position
            line = input.cursor_line + 1
            cursor_style = "underline"
            result.stylize_range(cursor_style, (line, cursor - 1), (line, cursor))

        yield result


class TextArea(ScrollView, can_focus=True):
    """A TextArea widget"""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("left", "cursor_left", "cursor left", show=False),
        Binding("right", "cursor_right", "cursor right", show=False),
        Binding("up", "cursor_up", "cursor up", show=False),
        Binding("down", "cursor_down", "cursor down", show=False),
        Binding("backspace", "delete_left", "delete left", show=False),
        Binding("enter", "cursor_enter", "cursor enter", show=False),
        Binding("home", "home", "home", show=False),
        Binding("end", "end", "end", show=False),
    ]

    COMPONENT_CLASSES: ClassVar[set[str]] = {
        "textarea--cursor",
        "textarea--placeholder",
    }

    DEFAULT_CSS = """

    TextArea {
        background: $boost;
        color: $text;
    }
    TextArea:focus {
        border: tall $accent;
    }
    TextArea>.textarea--cursor {
        background: $surface;
        color: $text;
        text-style: reverse;
    }
    TextArea>.textarea--placeholder {
        color: $text-disabled;
    }
    """

    cursor_blink = reactive(True)
    value = reactive("", layout=True, init=False)
    input_scroll_offset = reactive(0)
    cursor_position = reactive(0)
    cursor_line = reactive(0)
    view_position = reactive(0)
    lines = []
    placeholder = reactive("")
    complete = reactive("")
    width = reactive(1)
    _cursor_visible = reactive(True)
    max_size: reactive[int | None] = reactive(None)
    cursor_offset = var(Offset(0, 0))

    class Changed(Message, bubble=True):
        def __init__(self, input: TextArea, value: str) -> None:
            super().__init__()
            self.input: TextArea = input
            self.value: str = value

        @property
        def control(self) -> TextArea:
            return self.input

    def __init__(
        self,
        value: str | None = None,
        placeholder: str = "",
        name: str | None = None,
        highlighter: Highlighter | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)
        if value is not None:
            self.value = value
        self.placeholder = placeholder
        self.highlighter = highlighter
        self.chat_container: ScrollableContainer | None = None

    def _position_to_cell(self, position: int) -> int:
        cell_offset = cell_len(self.value[:position])
        return cell_offset

    @property
    def _cursor_offset(self) -> int:
        offset = self._position_to_cell(self.cursor_position)
        if self._cursor_at_end:
            offset += 1
        return offset

    @property
    def _cursor_at_end(self) -> bool:
        """Flag to indicate if the cusror is at the end"""
        return self.cursor_position >= len(self.value)

    def validate_cursor_position(self, cursor_position: int) -> int:
        return min(max(0, cursor_position), max(list(map(len, self.value.split("\n")))))

    def validate_cursor_line(self, cursor_line: int) -> int:
        return min(max(0, cursor_line), self.value.count("\n") + 2)

    async def watch_value(self, value: str) -> None:
        self.cursor_line = self.value.count("\n")
        self.refresh(layout=True)
        self.virtual_size = Size(
            max(list(map(len, self.value.split("\n")))), self.cursor_line + 1
        )
        self.scroll_end(animate=False)
        self.post_message(self.Changed(self, value))

    @property
    def cursor_width(self) -> int:
        if self.placeholder and not self.value:
            return cell_line(self.placeholder)
        return self._position_to_cell(len(self.value)) + 1

    def render(self) -> RenderableType:
        self.view_position = self.view_position
        if not self.value:
            placeholder = Text(self.placeholder, justify="left")
            placeholder.stylize(self.get_component_rich_style("textarea--placeholder"))
            if self.has_focus:
                cursor_style = self.get_component_rich_style("textarea--cursor")
                if self._cursor_visible:
                    if len(placeholder) == 0:
                        placeholder = Text(" ")
                    placeholder.stylize(cursor_style, 0, 1)

            return placeholder
        return _InputRenderable(self, self._cursor_visible)

    @property
    def _value(self) -> Syntax:
        cursor_line = self.cursor_line
        syntax = Syntax(
            self.value, "sql", line_numbers=True, highlight_lines=set([cursor_line + 1])
        )
        return syntax

    def _toggle_cusror(self) -> None:
        self._cursor_visible = not self._cursor_visible

    def _on_mount(self, _: Mount) -> None:
        self.blink_timer = self.set_interval(
            0.5, self._toggle_cusror, pause=not (self.cursor_blink and self.has_focus)
        )

    def _on_blur(self, _: Blur) -> None:
        self.blink_timer.pause()

    def _on_focus(self, _: Focus) -> None:
        self.cursor_position = len(self.value)
        if self.cursor_blink:
            self.blink_timer.resume()

    async def _on_key(self, event: events.Key) -> None:
        self._cursor_visible = True
        if self.cursor_blink:
            self.blink_timer.reset()

        # Do key bindings first
        if await self.handle_key(event):
            event.prevent_default()
            event.stop()
            return
        elif event.is_printable:
            event.stop()
            assert event.character is not None
            self.insert_text_at_cursor(event.character)
            event.prevent_default()

    def _on_paste(self, event: events.Paste) -> None:
        lines = "\n".join(event.text.splitlines())
        self.insert_text_at_cursor(lines)
        event.stop()

    async def _on_click(self, event: events.Click) -> None:
        offset = event.get_content_offset(self)
        if offset is None:
            return
        event.stop()
        click_x = offset.x + self.view_position
        cell_offset = 0
        _cell_size = get_character_cell_size
        for index, char in enumerate(self.value):
            if cell_offset >= click_x:
                self.cursor_position = index
                break
            cell_offset += _cell_size(char)
        else:
            self.cursor_position = len(self.value)

    def insert_text_at_cursor(self, text: str) -> None:
        if self.cursor_position > len(self.value):
            self.value += text
            self.cursor_position = len(self.value)
        else:
            value = self.value
            before = value[: self.cursor_position]
            after = value[self.cursor_position :]
            self.value = f"{before}{text}{after}"
            self.cursor_position += len(text)

    def action_cursor_left(self) -> None:
        self.cursor_position -= 1

    def action_cursor_up(self) -> None:
        self.cursor_position -= 1

    def action_cursor_right(self) -> None:
        self.cursor_position += 1

    def action_home(self) -> None:
        self.cursor_position = 0

    def action_end(self) -> None:
        self.cursor_position = len(self.value)

    def action_cursor_enter(self) -> None:
        self.cursor_line += 1
        self.insert_text_at_cursor("\n")

    def action_delete_left(self) -> None:
        if self.cursor_position <= 0:
            return
        if self.cursor_position == len(self.value):
            self.value = self.value[:-1]
            self.cursor_position = len(self.value)
        else:
            value = self.value
            delete_position = self.cursor_position - 1
            before = value[:delete_position]
            after = value[delete_position + 1 :]
            self.value = f"{before}{after}"
            self.cursor_position = delete_position
