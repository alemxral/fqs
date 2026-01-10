"""
QueryResult Widget - Displays formatted table results from API queries

Shows a bordered box with the query results in a scrollable container.
Used for displaying 'see' command output.
"""

from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import Static, Label
from textual.reactive import reactive


class QueryResult(Container):
    """
    Widget for displaying query results in a bordered, scrollable box
    
    Features:
    - Bordered container with title
    - Scrollable content area
    - Monospace font for table alignment
    - Auto-sizes to content
    """
    
    DEFAULT_CSS = """
    QueryResult {
        width: 100%;
        height: auto;
        max-height: 30;
        border: solid $primary;
        background: $surface;
        margin: 1 0;
        padding: 0;
    }
    
    QueryResult > .query-result-title {
        width: 100%;
        height: 1;
        background: $primary;
        color: $text;
        content-align: center middle;
        text-style: bold;
        padding: 0 1;
    }
    
    QueryResult > VerticalScroll {
        width: 100%;
        height: auto;
        max-height: 28;
        border: none;
        scrollbar-size-vertical: 1;
    }
    
    QueryResult .query-result-content {
        width: 100%;
        height: auto;
        color: $text;
        padding: 1 2;
    }
    
    QueryResult .query-result-content Static {
        width: 100%;
        height: auto;
    }
    """
    
    # Reactive properties
    title: reactive[str] = reactive("Query Result")
    content: reactive[str] = reactive("")
    
    def __init__(self, title: str = "Query Result", content: str = "", **kwargs):
        """
        Initialize query result widget
        
        Args:
            title: Title displayed in the header
            content: Formatted text content to display
        """
        super().__init__(**kwargs)
        self.title = title
        self.content = content
    
    def compose(self) -> ComposeResult:
        """Compose the widget layout"""
        # Title bar
        yield Label(self.title, classes="query-result-title")
        
        # Scrollable content area
        with VerticalScroll():
            yield Static(self.content, classes="query-result-content")
    
    def update_content(self, content: str, title: str = None) -> None:
        """
        Update the displayed content
        
        Args:
            content: New content text to display
            title: Optional new title (if None, keeps current title)
        """
        if title:
            self.title = title
            title_label = self.query_one(".query-result-title", Label)
            title_label.update(title)
        
        self.content = content
        content_widget = self.query_one(".query-result-content", Static)
        content_widget.update(content)
        
        # Force refresh to update display
        self.refresh(layout=True)
    
    def clear(self) -> None:
        """Clear the content"""
        self.update_content("")
    
    def watch_title(self, new_title: str) -> None:
        """React to title changes"""
        try:
            title_label = self.query_one(".query-result-title", Label)
            title_label.update(new_title)
        except Exception:
            pass
    
    def watch_content(self, new_content: str) -> None:
        """React to content changes"""
        try:
            content_widget = self.query_one(".query-result-content", Static)
            content_widget.update(new_content)
        except Exception:
            pass


class QueryResultBox(Static):
    """
    Simpler static version of query result - just a bordered static with formatted text
    Good for log-style display in a scrolling container
    """
    
    DEFAULT_CSS = """
    QueryResultBox {
        width: 100%;
        height: auto;
        border: solid $accent;
        background: $surface;
        color: $text;
        padding: 1 2;
        margin: 1 0;
    }
    
    QueryResultBox.success {
        border: solid green;
    }
    
    QueryResultBox.error {
        border: solid red;
    }
    """
    
    def __init__(self, content: str, success: bool = True, **kwargs):
        """
        Initialize a simple query result box
        
        Args:
            content: Formatted text to display
            success: Whether query was successful (affects border color)
        """
        super().__init__(content, **kwargs)
        if success:
            self.add_class("success")
        else:
            self.add_class("error")
