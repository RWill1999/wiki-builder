"""Program in active development, subject to change as imrpovements are made
and features are added.
"""

"""An open-ended personal wiki built with Drafter for CISC106.

Run this single file with Python 3.10+ and Drafter 2.2.1 installed.
All tests run before startup. No local data files or extra packages are needed.
Entries live in this browser session; use Backup to keep them across reloads.
AI assistance: ChatGPT helped design, implement, and test this prototype.
Upload the complete conversation separately, as the course requires.
"""

from dataclasses import dataclass
import json
from drafter import (
    Argument, Button, CheckBox, Div, Header, Label, Link, Page,
    SelectBox, Span, TextArea, TextBox, hide_debug_information,
    route, set_site_information, set_website_title, start_server,
)


@dataclass
class WikiArticle:
    """Store a term's stable identity, editable information, and reading count."""

    article_id: int
    title: str
    description: str
    category: str
    visits: int


@dataclass
class State:
    """Keep the wiki and navigation values together between route calls."""

    articles: list[WikiArticle]
    search_query: str
    selected_category: str
    current_article_id: int
    message: str
    wiki_title: str
    next_id: int


def initial_state() -> State:
    """Return a fresh wiki with editable examples showing how links work."""
    return State([
        WikiArticle(1, "Welcome", "This is your wiki. Try opening [[Connections]] "
                    "or create a term about anything you want to remember.",
                    "Getting started", 0),
        WikiArticle(2, "Connections", "Put double brackets around a term, like "
                    "[[Welcome]], to connect pages. Try [[My first memory]] "
                    "to define a term that does not exist yet.",
                    "Getting started", 0),
    ], "", "All categories", 0, "", "My personal wiki", 3)


def find_article(state: State, article_id: int) -> WikiArticle | None:
    """Find an article by ID, or return None if it was removed."""
    for article in state.articles:
        if article.article_id == article_id:
            return article
    return None


def find_title(state: State, title: str) -> WikiArticle | None:
    """Match whole titles without considering capitalization or outer spaces."""
    for article in state.articles:
        if article.title.lower() == title.strip().lower():
            return article
    return None


def category_options(state: State) -> list[str]:
    """Collect unique categories for filtering without a fixed subject list."""
    categories = []
    for article in state.articles:
        if article.category not in categories:
            categories.append(article.category)
    return ["All categories"] + sorted(categories)


def matching_articles(state: State) -> list[WikiArticle]:
    """Search titles and definitions within the chosen category."""
    results = []
    for article in state.articles:
        category_matches = (state.selected_category == "All categories"
                            or article.category == state.selected_category)
        query_matches = (state.search_query.lower() in article.title.lower()
                         or state.search_query.lower()
                         in article.description.lower())
        if category_matches and query_matches:
            results.append(article)
    return results


def linked_paragraph(state: State, text: str) -> Span:
    """Turn explicit [[term]] references into inline Drafter links.

    String scanning uses find and slicing instead of regular expressions.
    An existing title opens its article; a missing title opens a prefilled
    creation form. Ordinary text stays ordinary text, including raw HTML.
    Unclosed brackets are displayed literally instead of causing an error.
    Span groups strings and Links inline, unlike separate Page paragraphs.
    Inline-flex trims the renderer's whitespace inside each link so that
    underlines do not extend across generated indentation or blank spaces.
    """
    pieces = []
    position = 0
    while position < len(text):
        opening = text.find("[[", position)
        closing = text.find("]]", opening + 2)
        if opening == -1 or closing == -1:
            pieces.append(text[position:])
            break
        pieces.append(text[position:opening])
        term = text[opening + 2:closing].strip()
        article = find_title(state, term)
        if term == "":
            pieces.append(text[opening:closing + 2])
        elif article is None:
            pieces.append(Link(term + " (create)", new_article,
                               Argument("suggested_title", term),
                               style="display: inline-flex; white-space: normal;"))
        else:
            pieces.append(Link(term, show_article,
                               Argument("article_id", article.article_id),
                               style="display: inline-flex; white-space: normal;"))
        position = closing + 2
    return Span(pieces)


def rename_references(text: str, old_title: str, new_title: str) -> str:
    """Update bracketed references on rename while preserving ordinary prose."""
    result = ""
    position = 0
    while position < len(text):
        opening = text.find("[[", position)
        closing = text.find("]]", opening + 2)
        if opening == -1 or closing == -1:
            result += text[position:]
            break
        result += text[position:opening]
        term = text[opening + 2:closing].strip()
        if term.lower() == old_title.lower():
            result += "[[" + new_title + "]]"
        else:
            result += text[opening:closing + 2]
        position = closing + 2
    return result


def form_field(label: str, name: str,
               control: TextBox | TextArea | SelectBox,
               explanation: str = "") -> Div:
    """Keep a field's label, help text, and input together on separate lines."""
    parts = [Div(Label(label, name), style="font-weight: bold;")]
    if explanation:
        parts.append(Div(explanation, style="color: #525866; margin: 0.25rem 0;"))
    parts.append(Div(control))
    return Div(parts, style="margin-bottom: 1.25rem;")


def screen(state: State, title: str, body: list) -> Page:
    """Give each distinct page navigation, search controls, and feedback.

    The list annotation intentionally accepts mixed Drafter components and
    text. Input names exactly match search_wiki's parameter names.
    Inline style keywords are Drafter's documented HTML/CSS attributes.
    """
    content = [
        Header(state.wiki_title),
        Span([Link("Home", index), " | ", Link("Create a term", new_article),
              " | ", Link("Settings", settings), " | ",
              Link("Backup", backup), " | ", Link("Help", help_page)]),
        Div([
            form_field("Search terms and definitions", "query",
                       TextBox("query", state.search_query,
                               style="width: 100%; box-sizing: border-box;")),
            form_field("Filter search by category", "category",
                       SelectBox("category", category_options(state),
                                 state.selected_category),
                       "This filter searches existing terms; it does not set a new term's category."),
            Button("Search", search_wiki),
        ], style="padding: 1rem 0;"),
        Header(title, level=2),
    ]
    if state.message != "":
        content.append(Div(state.message, role="status"))
    # Explicit blocks prevent adjacent strings from running together.
    for item in body:
        if isinstance(item, str):
            content.append(Div(item, style="margin: 0.75rem 0;"))
        else:
            content.append(item)
    content.append(Div("Session only: use Backup before reloading or closing.",
                       style="margin-top: 2rem; color: #525866;"))
    return Page(state, [Div(content, style=(
        "max-width: 900px; margin: auto; padding: 1.5rem; "
        "font-family: system-ui, sans-serif; line-height: 1.6; "
        "overflow-wrap: anywhere;"))])


def article_list(articles: list[WikiArticle]) -> list:
    """Create linked summaries by reading each stored article's attributes."""
    content = []
    for article in articles:
        content.append(Div([
            Link(article.title, show_article,
                 Argument("article_id", article.article_id)),
            " | " + article.category,
            Div(article.description[:160]),
        ], style="padding: 0.8rem 0; border-bottom: 1px solid #ddd;"))
    if not articles:
        content.append("No terms found. Create one to get started.")
    return content


@route
def index(state: State, keep_message: bool = False) -> Page:
    """Show the home page and up to four most-read terms in this session."""
    if not keep_message:
        state.message = ""
    popular = []
    # A small selection loop avoids lambda functions and keeps ties stable.
    for article in state.articles:
        position = 0
        while position < len(popular) and popular[position].visits >= article.visits:
            position += 1
        popular.insert(position, article)
    return screen(state, "Your connected collection", [
        "Collect memories, inside jokes, study notes, or ideas. "
        "Write [[another term]] in a definition to connect your pages.",
        str(len(state.articles)) + " terms in your wiki.",
        Header("Most read", level=3),
    ] + article_list(popular[:4]))


@route
def search_wiki(state: State, query: str, category: str) -> Page:
    """Store submitted search values, then display the results page."""
    state.search_query = query.strip()
    state.selected_category = category
    if category not in category_options(state):
        state.selected_category = "All categories"
    state.message = ""
    return show_search(state)


@route
def show_search(state: State) -> Page:
    """Show all matches, including an explicit empty-results message."""
    results = matching_articles(state)
    return screen(state, "Search results", [
        str(len(results)) + " matches for: " + (state.search_query or "all terms"),
    ] + article_list(results))


@route
def show_article(state: State, article_id: int) -> Page:
    """Open a term, update the current selection, and count this visit."""
    article = find_article(state, article_id)
    if article is None:
        state.message = "That term no longer exists."
        return index(state, True)
    state.current_article_id = article_id
    article.visits += 1
    state.message = ""
    return article_page(state, article)


def article_page(state: State, article: WikiArticle) -> Page:
    """Render a definition without counting an additional reading visit."""
    body = [Link("Category: " + article.category, show_category,
                 Argument("category", article.category))]
    # Drafter indents its generated HTML. pre-wrap would display that
    # indentation and those generated newlines as part of the definition.
    # Each stored line gets one block; normal whitespace hides HTML formatting.
    # A minimum height preserves intentionally empty lines in the description.
    for paragraph in article.description.split("\n"):
        body.append(Div(linked_paragraph(state, paragraph),
                        style="white-space: normal; margin: 0; min-height: 1.6em;"))
    body.extend([
        Button("Edit term", edit_article,
               Argument("article_id", article.article_id)),
        Button("Delete term", confirm_delete,
               Argument("article_id", article.article_id)),
    ])
    return screen(state, article.title, body)


@route
def show_category(state: State, category: str) -> Page:
    """Open a category browse view, independent of the prior search text."""
    state.selected_category = category
    if category not in category_options(state):
        state.selected_category = "All categories"
    state.search_query = ""
    state.message = ""
    return screen(state, "Browse: " + state.selected_category,
                  article_list(matching_articles(state)))


def editor_page(state: State, article_id: int, title: str,
                description: str, category: str) -> Page:
    """Build a populated editor, also used to preserve invalid submissions."""
    heading = "Create a term"
    if article_id != 0:
        heading = "Edit term"
    return screen(state, heading, [
        Div("Fill in the three fields below, then click Save term."),
        form_field("1. Term title (required)", "title",
                   TextBox("title", title, placeholder="Example: Study group",
                           style="width: 100%; box-sizing: border-box;"),
                   "The name of the page you are creating."),
        form_field("2. Definition or description (required)", "description",
                   TextArea("description", description, rows=8,
                            placeholder="Write what this term means or what you want to remember.",
                            style="width: 100%; box-sizing: border-box;"),
                   "Write the page's content here. To link another page, write its title "
                   "in double brackets, such as [[Study group]]."),
        form_field("3. Category (optional)", "article_category",
                   TextBox("article_category", category, placeholder="Example: College life",
                           style="width: 100%; box-sizing: border-box;"),
                   "A group for organizing terms, such as People, Memories, or Study notes. "
                   "Type an existing category name to reuse it, or a new name to create one. "
                   "Leave blank for Uncategorized."),
        Button("Save term", save_article, Argument("article_id", article_id)),
        Link("Cancel", index),
    ])


@route
def new_article(state: State, suggested_title: str = "") -> Page:
    """Open a blank creation form or prefill a missing linked term."""
    state.message = ""
    return editor_page(state, 0, suggested_title, "", "")


@route
def edit_article(state: State, article_id: int) -> Page:
    """Open the editor with the selected term's current information."""
    article = find_article(state, article_id)
    if article is None:
        state.message = "That term no longer exists."
        return index(state, True)
    state.current_article_id = article_id
    state.message = ""
    return editor_page(state, article_id, article.title,
                       article.description, article.category)


@route
def save_article(state: State, title: str, description: str,
                 article_category: str, article_id: int) -> Page:
    """Validate a new or edited term and update references on title changes."""
    title = title.strip()
    category = article_category.strip() or "Uncategorized"
    duplicate = find_title(state, title)
    state.message = ""
    if not title or not description.strip():
        state.message = "A title and definition are required."
    elif "[" in title or "]" in title or "\n" in title or "\r" in title:
        state.message = "Titles cannot contain square brackets or line breaks."
    elif category == "All categories":
        state.message = "Choose a category other than All categories."
    elif duplicate is not None and duplicate.article_id != article_id:
        state.message = "That title already exists. Edit its page or choose another."
    if state.message:
        return editor_page(state, article_id, title, description, article_category)
    article = find_article(state, article_id)
    if article_id == 0:
        article = WikiArticle(state.next_id, title, description, category, 0)
        state.next_id += 1
        state.articles.append(article)
    elif article is None:
        state.message = "That term was removed; create it again instead."
        return index(state, True)
    else:
        old_title = article.title
        article.title = title
        article.description = description
        article.category = category
        for other in state.articles:
            other.description = rename_references(other.description, old_title, title)
    state.current_article_id = article.article_id
    if state.selected_category not in category_options(state):
        state.selected_category = "All categories"
    state.message = "Term saved. Back up your wiki to keep this change."
    return article_page(state, article)


@route
def confirm_delete(state: State, article_id: int) -> Page:
    """Show a separate confirmation page before removing a term."""
    article = find_article(state, article_id)
    if article is None:
        state.message = "That term no longer exists."
        return index(state, True)
    state.message = ""
    return screen(state, "Delete " + article.title + "?", [
        "Links to this title will offer to create it again after deletion.",
        Label("I want to delete this term", "confirmed"),
        CheckBox("confirmed", False),
        Button("Confirm deletion", delete_article,
               Argument("article_id", article_id)),
        Link("Cancel", show_article, Argument("article_id", article_id)),
    ])


@route
def delete_article(state: State, article_id: int, confirmed: bool) -> Page:
    """Remove only the selected article and only after explicit confirmation."""
    if not confirmed:
        state.message = "Check the confirmation box to delete this term."
        return screen(state, "Deletion canceled", [Link("Try deleting again", confirm_delete,
                      Argument("article_id", article_id)), Link("Home", index)])
    remaining = []
    for article in state.articles:
        if article.article_id != article_id:
            remaining.append(article)
    state.articles = remaining
    state.current_article_id = 0
    if state.selected_category not in category_options(state):
        state.selected_category = "All categories"
    state.message = "Term deleted. Back up your wiki to keep this change."
    return index(state, True)


@route
def settings(state: State, keep_message: bool = False) -> Page:
    """Show the wiki-name input on a dedicated settings page."""
    if not keep_message:
        state.message = ""
    return screen(state, "Wiki settings", [
        form_field("Wiki name", "wiki_name",
                   TextBox("wiki_name", state.wiki_title,
                           style="width: 100%; box-sizing: border-box;")),
        Button("Save name", save_settings),
    ])


@route
def save_settings(state: State, wiki_name: str) -> Page:
    """Change the wiki heading while refusing an empty name."""
    if wiki_name.strip():
        state.wiki_title = wiki_name.strip()
        state.message = "Wiki name saved. Include it in your next backup."
    else:
        state.message = "The wiki name cannot be empty."
    return settings(state, True)


def backup_text(state: State) -> str:
    """Serialize reusable wiki data as JSON text, not Python code.

    JSON is a standard-library format for exchanging lists and dictionaries.
    Dataclass instances are explicitly converted into dictionaries, since
    json.dumps cannot encode arbitrary class instances directly. Transient
    navigation values are intentionally reset when restoring a backup.
    """
    articles = []
    for article in state.articles:
        articles.append({"article_id": article.article_id, "title": article.title,
                         "description": article.description,
                         "category": article.category, "visits": article.visits})
    return json.dumps({"version": 1, "wiki_title": state.wiki_title,
                       "articles": articles}, indent=2, ensure_ascii=True)


@route
def backup(state: State, keep_message: bool = False) -> Page:
    """Offer copyable backup text and a separate restore form."""
    if not keep_message:
        state.message = ""
    return screen(state, "Backup and restore", [
        "Copy ALL of the backup text below into a text file on your computer. "
        "Keep it before closing, refreshing, or redeploying this site.",
        form_field("Current wiki backup - copy all of this text", "export_text",
                   TextArea("export_text", backup_text(state), rows=12,
                            style="width: 100%; box-sizing: border-box;")),
        Header("Restore a saved wiki", level=3),
        "Paste a backup below. Restoring REPLACES the current collection. "
        "Back up your current wiki first if you want to keep it.",
        form_field("Paste your saved backup here", "import_text",
                   TextArea("import_text", "", rows=8,
                            style="width: 100%; box-sizing: border-box;")),
        Div([CheckBox("replace_confirmed", False),
             Label("Replace my current collection", "replace_confirmed")]),
        Button("Restore backup", restore),
    ])


def decode_backup(text: str) -> State:
    """Validate a complete backup before returning a replacement state.

    Advanced technique: raise ValueError for invalid structure. The restore
    route catches it and JSON's parsing error, so bad input cannot partially
    overwrite the current wiki. isinstance checks reject unexpected types;
    type(x) is int also rejects booleans, which Python treats as integers.
    This parses data only: eval and executable backup code are never used.
    """
    data = json.loads(text)
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("Use a version 1 wiki backup.")
    title = data.get("wiki_title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("The backup needs a wiki name.")
    records = data.get("articles")
    if not isinstance(records, list):
        raise ValueError("The backup needs an article list.")
    result = State([], "", "All categories", 0, "", title.strip(), 1)
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Each article must be a record.")
        for field in ["title", "description", "category"]:
            if not isinstance(record.get(field), str) or not record[field].strip():
                raise ValueError("Every article needs a title, definition, and category.")
        article_id = record.get("article_id")
        visits = record.get("visits")
        if type(article_id) is not int or article_id < 1:
            raise ValueError("Article IDs must be positive integers.")
        if type(visits) is not int or visits < 0:
            raise ValueError("Visit counts must be nonnegative integers.")
        article_title = record["title"].strip()
        if any(character in article_title for character in ["[", "]", "\n", "\r"]):
            # any with a generator means 'at least one character is present'.
            raise ValueError("An article title contains unsupported characters.")
        if record["category"].strip() == "All categories":
            raise ValueError("All categories is reserved for the search filter.")
        if find_title(result, article_title) is not None or find_article(result, article_id) is not None:
            raise ValueError("Duplicate article title or ID.")
        result.articles.append(WikiArticle(
            article_id, article_title, record["description"],
            record["category"].strip(), visits))
        result.next_id = max(result.next_id, article_id + 1)
    return result


@route
def restore(state: State, import_text: str, replace_confirmed: bool) -> Page:
    """Replace the collection only after confirmation and full validation."""
    if not replace_confirmed:
        state.message = "Check the replacement box before restoring."
        return backup(state, True)
    try:
        replacement = decode_backup(import_text)
    except (ValueError, RecursionError):
        state.message = "Invalid backup. Your current collection was kept."
        return backup(state, True)
    state.articles = replacement.articles
    state.wiki_title = replacement.wiki_title
    state.next_id = replacement.next_id
    state.search_query = ""
    state.selected_category = "All categories"
    state.current_article_id = 0
    state.message = "Backup restored."
    return index(state, True)


@route
def help_page(state: State) -> Page:
    """Explain linking, search, renames, and the prototype's storage model."""
    state.message = ""
    return screen(state, "How to use your wiki", [
        "Create a term with a title, definition, and category of your choosing.",
        "Write [[term title]] anywhere in a definition to insert an inline link. "
        "Matching ignores capitalization. Missing terms open a creation form.",
        "Search matches parts of titles or definitions. An empty search shows "
        "all terms in the chosen category.",
        "Renaming a term updates explicit [[links]] throughout the collection. "
        "Ordinary prose is kept as written. Titles must be unique.",
        "Each browser tab has its own wiki. There are no accounts, shared "
        "database, or automatic permanent saves. Use Backup to copy your data "
        "into a text file, then restore it whenever you return.",
    ])


def run_tests() -> None:
    """Test every route and important branches on independent sample states.

    Python's assert raises AssertionError on a failed expectation; successful
    tests stay quiet. Route tests check visible content or actual resulting
    data, rather than comparing a route with itself. No live wiki is modified.
    Run Python normally (without -O) so assertions remain enabled.
    """
    state = initial_state()
    assert isinstance(index(state), Page)
    assert index(state).state == state
    assert "Your connected collection" in str(index(state).content)
    assert "Search results" in str(show_search(state).content)
    assert "Wiki settings" in str(settings(state).content)
    assert "How to use your wiki" in str(help_page(state).content)
    assert "Backup and restore" in str(backup(state).content)
    assert "Create a term" in str(new_article(state, "Example").content)
    assert "Example" in str(new_article(state, "Example").content)

    search_wiki(state, "  WELCOME  ", "Getting started")
    assert state.search_query == "WELCOME"
    assert state.selected_category == "Getting started"
    assert len(matching_articles(state)) == 2
    search_wiki(state, "nothing matches", "All categories")
    assert "No terms found" in str(show_search(state).content)
    search_wiki(state, "", "nonexistent category")
    assert state.selected_category == "All categories"
    assert len(matching_articles(state)) == 2

    show_article(state, 1)
    assert state.current_article_id == 1
    assert state.articles[0].visits == 1
    assert "Connections" in str(article_page(state, state.articles[0]).content)
    show_article(state, 999)
    assert state.message == "That term no longer exists."
    show_category(state, "Getting started")
    assert state.search_query == ""
    assert state.selected_category == "Getting started"
    assert "Browse: Getting started" in str(show_category(state, "Getting started").content)

    assert "Edit term" in str(edit_article(state, 1).content)
    assert "Welcome" in str(edit_article(state, 1).content)
    edit_article(state, 999)
    assert state.message == "That term no longer exists."
    before = len(state.articles)
    save_article(state, "", "description", "Notes", 0)
    assert len(state.articles) == before
    assert state.message == "A title and definition are required."
    save_article(state, "welcome", "duplicate", "Notes", 0)
    assert len(state.articles) == before
    assert "already exists" in state.message
    save_article(state, "[bad]", "description", "Notes", 0)
    assert len(state.articles) == before
    save_article(state, "Example", "Text", "All categories", 0)
    assert len(state.articles) == before
    save_article(state, "  Example  ", "See [[Welcome]].", "", 0)
    assert state.articles[-1] == WikiArticle(3, "Example", "See [[Welcome]].", "Uncategorized", 0)
    assert state.current_article_id == 3 and state.next_id == 4
    save_article(state, "Introduction", "A self-link: [[welcome]].", "Notes", 1)
    assert state.articles[0].title == "Introduction"
    assert state.articles[0].description == "A self-link: [[Introduction]]."
    assert state.articles[1].description.startswith("Put double brackets")
    assert state.articles[2].description == "See [[Introduction]]."
    save_article(state, "Missing", "Text", "Notes", 999)
    assert len(state.articles) == 3
    assert "removed" in state.message

    assert "Delete Example?" in str(confirm_delete(state, 3).content)
    delete_article(state, 3, False)
    assert find_article(state, 3) is not None
    delete_article(state, 3, True)
    assert find_article(state, 3) is None
    assert state.current_article_id == 0
    confirm_delete(state, 999)
    assert state.message == "That term no longer exists."
    save_settings(state, "  Shared memories  ")
    assert state.wiki_title == "Shared memories"
    save_settings(state, "   ")
    assert state.wiki_title == "Shared memories"
    assert state.message == "The wiki name cannot be empty."

    assert rename_references("[[ WELCOME ]] and Welcome", "Welcome", "New") == "[[New]] and Welcome"
    assert rename_references("Unclosed [[Welcome", "Welcome", "New") == "Unclosed [[Welcome"
    assert "create" in str(linked_paragraph(state, "[[A missing term]]"))
    assert "show_article" in str(linked_paragraph(state, "[[introduction]]"))
    assert "unfinished [[term" in str(linked_paragraph(state, "unfinished [[term"))
    assert "[[]]" in str(linked_paragraph(state, "[[]]"))

    failed_page = save_article(state, "", "", "", 0)
    assert "A title and definition are required." in str(failed_page.content)
    for navigation in [index, settings, backup, help_page]:
        state.message = "A title and definition are required."
        next_page = navigation(state)
        assert "A title and definition are required." not in str(next_page.content)
    form = new_article(state)
    assert "3. Category (optional)" in str(form.content)
    assert "Uncategorized" in str(form.content)

    formatted = article_page(state, WikiArticle(
        99, "Formatting check", "Before [[Introduction]] after.\n\nLast line.", "Notes", 0))
    assert "pre-wrap" not in str(formatted.content)
    assert str(formatted.content).count("min-height: 1.6em") == 3
    assert "inline-flex" in str(formatted.content)

    exported = backup_text(state)
    decoded = decode_backup(exported)
    assert decoded.articles == state.articles
    assert decoded.wiki_title == state.wiki_title
    assert decoded.next_id == 3
    fresh = initial_state()
    restore(fresh, exported, False)
    assert fresh.articles == initial_state().articles
    restore(fresh, exported, True)
    assert fresh.articles == state.articles and fresh.wiki_title == "Shared memories"
    assert fresh.search_query == "" and fresh.current_article_id == 0
    for invalid in ["not json", "[]", "{}", '{"version": 1, "wiki_title": "W", "articles": [null]}']:
        restore(fresh, invalid, True)
        assert fresh.articles == state.articles
        assert fresh.message == "Invalid backup. Your current collection was kept."
    invalid = json.loads(exported)
    invalid["articles"].append(invalid["articles"][0])
    restore(fresh, json.dumps(invalid), True)
    assert fresh.articles == state.articles and "Invalid" in fresh.message
    empty = State([], "", "All categories", 0, "", "Empty wiki", 1)
    restore(fresh, backup_text(empty), True)
    assert fresh.articles == [] and fresh.next_id == 1
    save_article(fresh, "First term", "A definition", "Notes", 0)
    assert fresh.articles[0].article_id == 1


# Configuration calls register metadata; no mutable application data is global.
set_website_title("Personal Wiki Builder")
set_site_information(
    author="Ryan Williamson",
    description="An open-ended personal wiki with linked terms and backups.",
    sources="Drafter documentation and ChatGPT assistance; see AI conversation file.",
    planning="See the original design worksheet and updated scope in README.md.",
    links=["https://drafter-edu.github.io/drafter/"],
)
hide_debug_information()
run_tests()
start_server(initial_state())


