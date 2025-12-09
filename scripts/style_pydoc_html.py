#!/usr/bin/env python3
"""Apply consistent styling to pydoc-generated HTML files."""

import os
import re
from pathlib import Path


# CSS that matches the index.html styling
PYDOC_CSS = """
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            line-height: 1.6;
            color: #333;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        /* Navigation bar */
        .nav-bar {
            background: #0066cc;
            color: white;
            padding: 15px 20px;
            margin: -20px -20px 20px -20px;
            border-radius: 8px 8px 0 0;
        }
        .nav-bar a {
            color: white;
            text-decoration: none;
            margin-right: 20px;
            font-weight: 500;
        }
        .nav-bar a:hover {
            text-decoration: underline;
        }
        /* Pydoc-specific styling */
        table.heading {
            width: 100%;
            margin-bottom: 30px;
            border-bottom: 3px solid #0066cc;
            padding-bottom: 15px;
        }
        table.heading .title {
            font-size: 1.8em;
            color: #333;
            font-weight: bold;
        }
        table.heading .extra {
            text-align: right;
            font-size: 0.9em;
        }
        table.heading .extra a {
            color: #0066cc;
            text-decoration: none;
        }
        table.heading .extra a:hover {
            text-decoration: underline;
        }
        table.section {
            width: 100%;
            margin: 30px 0;
            border-collapse: collapse;
        }
        table.section .section-title {
            background: #f9f9f9;
            padding: 12px;
            font-size: 1.3em;
            color: #333;
            border-bottom: 2px solid #e0e0e0;
            font-weight: bold;
        }
        table.section .bigsection {
            color: #0066cc;
        }
        table.section td {
            padding: 8px;
            vertical-align: top;
        }
        table.section .singlecolumn {
            padding-left: 20px;
        }
        /* Code and text styling */
        .code {
            font-family: 'Monaco', 'Courier New', monospace;
            background: #f5f5f5;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.95em;
            color: #333;
        }
        span.code {
            display: block;
            padding: 15px;
            margin: 10px 0;
            border: 1px solid #ddd;
            border-radius: 4px;
            background: #f9f9f9;
            white-space: pre-wrap;
            overflow-x: auto;
        }
        /* Links */
        a {
            color: #0066cc;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
        /* Definition lists */
        dl {
            margin: 15px 0;
        }
        dt {
            font-weight: bold;
            margin-top: 15px;
            color: #333;
        }
        dt.heading-text {
            font-size: 1.1em;
            margin-top: 20px;
        }
        dt.heading-text a {
            color: #0066cc;
        }
        dd {
            margin-left: 20px;
            margin-top: 5px;
            color: #666;
        }
        /* Tables */
        table {
            border-collapse: collapse;
            width: 100%;
        }
        /* Decor elements */
        .decor {
            background: #f9f9f9;
        }
        /* Multi-column layout */
        .multicolumn {
            padding: 5px 15px;
        }
        .multicolumn a {
            color: #0066cc;
            display: block;
            padding: 3px 0;
        }
        /* Paragraphs */
        p {
            margin: 15px 0;
            color: #666;
        }
        /* Strong/bold text */
        strong {
            color: #333;
        }
        /* Responsive */
        @media (max-width: 768px) {
            .container {
                padding: 20px;
            }
            .nav-bar {
                margin: -20px -20px 20px -20px;
                padding: 10px 15px;
            }
        }
    </style>
"""


def add_navigation(html_content, html_dir):
    """Add navigation bar to HTML content."""
    # Check if nav-bar already exists
    if 'nav-bar' in html_content:
        return html_content
    
    nav_html = """    <div class="nav-bar">
        <a href="index.html">← Back to Index</a>
        <a href="https://github.com/rl337/pyiv">GitHub</a>
    </div>
"""
    # Insert navigation after opening body tag
    html_content = re.sub(
        r'(<body[^>]*>)',
        r'\1\n' + nav_html,
        html_content,
        count=1
    )
    return html_content


def inject_css(html_content):
    """Inject CSS into HTML head section."""
    # Check if style tag already exists
    if '<style>' in html_content:
        # Replace existing style
        html_content = re.sub(
            r'<style>.*?</style>',
            PYDOC_CSS,
            html_content,
            flags=re.DOTALL
        )
    else:
        # Insert before closing head tag
        html_content = re.sub(
            r'(</head>)',
            PYDOC_CSS + r'\1',
            html_content,
            count=1
        )
    return html_content


def wrap_content(html_content):
    """Wrap body content in container div, keeping nav-bar outside."""
    # Check if container already exists
    if 'class="container"' in html_content:
        return html_content
    
    # Extract body content
    body_match = re.search(r'<body[^>]*>((?:.|\n)*?)</body>', html_content, re.DOTALL)
    if not body_match:
        return html_content
    
    body_content = body_match.group(1)
    
    # Check if nav-bar is in body_content
    nav_match = re.search(r'(<div class="nav-bar">.*?</div>\s*)', body_content, re.DOTALL)
    if nav_match:
        # Nav-bar exists, keep it outside container
        nav_html = nav_match.group(1)
        rest_content = body_content.replace(nav_html, '').strip()
        wrapped_body = f'<body>\n{nav_html}    <div class="container">\n{rest_content}\n    </div>\n</body>'
    else:
        # No nav-bar, wrap everything in container
        wrapped_body = f'<body>\n    <div class="container">\n{body_content}\n    </div>\n</body>'
    
    html_content = re.sub(
        r'<body[^>]*>.*?</body>',
        wrapped_body,
        html_content,
        flags=re.DOTALL
    )
    return html_content


def fix_index_link(html_content, filename):
    """Fix the index link to point to index.html."""
    # Replace relative index links
    html_content = re.sub(
        r'href="\.?"',
        'href="index.html"',
        html_content
    )
    return html_content


def improve_init_module_display(html_content, filename):
    """Improve display of modules, especially __init__.py packages."""
    module_name = filename.replace('.html', '')
    
    # Clean up all module titles (both "package" and "module")
    # Change "Python: package/module X" to "X - PyIV Documentation"
    html_content = re.sub(
        r'<title>Python: (?:package|module) ([^<]+)</title>',
        r'<title>\1 - PyIV Documentation</title>',
        html_content
    )
    
    # For __init__.py modules (packages), clean up file path references
    if '__init__.py' in html_content:
        # Replace file path references to __init__.py with just the module name
        # Pattern: file:/path/to/module/__init__.py -> module name (package)
        html_content = re.sub(
            r'file:[^<]*__init__\.py',
            f'{module_name} (package)',
            html_content
        )
    
    return html_content


def style_pydoc_html(html_file_path, html_dir):
    """Apply styling to a single pydoc HTML file."""
    try:
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Skip index.html (it has its own styling)
        if os.path.basename(html_file_path) == 'index.html':
            return
        
        # Apply transformations
        html_content = inject_css(html_content)
        html_content = add_navigation(html_content, html_dir)
        html_content = improve_init_module_display(html_content, os.path.basename(html_file_path))
        html_content = wrap_content(html_content)
        html_content = fix_index_link(html_content, os.path.basename(html_file_path))
        
        # Write back
        with open(html_file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"Styled: {html_file_path}")
    except Exception as e:
        print(f"Error styling {html_file_path}: {e}")


def main():
    """Main entry point."""
    import sys
    
    html_dir = sys.argv[1] if len(sys.argv) > 1 else 'docs/html'
    
    if not os.path.exists(html_dir):
        print(f"Directory {html_dir} does not exist")
        return
    
    # Process all HTML files
    html_files = []
    for filename in os.listdir(html_dir):
        if filename.endswith('.html'):
            html_files.append(os.path.join(html_dir, filename))
    
    print(f"Styling {len(html_files)} HTML files...")
    for html_file in html_files:
        style_pydoc_html(html_file, html_dir)
    
    print("Done!")


if __name__ == '__main__':
    main()

