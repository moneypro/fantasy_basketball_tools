"""Styling utilities for HTML generation."""


def get_table_css() -> str:
    """Get the CSS link tag for table styling.
    
    Returns:
        HTML link tag for the main CSS stylesheet
    """
    return """<link rel="stylesheet" href="/assets/css/main.css" />"""