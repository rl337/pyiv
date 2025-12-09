#!/usr/bin/env python3
"""Generate index.html for PyIV documentation."""

import os
from datetime import datetime

# Module descriptions
MODULE_DESCRIPTIONS = {
    'pyiv': 'Main package - Core dependency injection framework',
    'pyiv.injector': 'Dependency injection engine - Creates and manages instances',
    'pyiv.config': 'Configuration base class - Register dependencies',
    'pyiv.singleton': 'Singleton lifecycle management - Per-injector or global',
    'pyiv.factory': 'Factory pattern support - Create objects with dependencies',
    'pyiv.clock': 'Time abstraction - RealClock for production, SyntheticClock for testing',
    'pyiv.filesystem': 'File I/O abstraction - RealFilesystem for production, MemoryFilesystem for testing',
    'pyiv.datetime_service': 'DateTime abstraction - PythonDateTimeService for production, MockDateTimeService for testing',
    'pyiv.reflection': 'Reflection-based discovery - Automatically find implementations',
    'pyiv.command': 'Command interface - Build CLI applications with dependency injection'
}

def generate_index_html(html_dir='docs/html'):
    """Generate index.html for documentation."""
    
    # Find all HTML files
    html_files = []
    if os.path.exists(html_dir):
        for filename in sorted(os.listdir(html_dir)):
            if filename.endswith('.html') and filename != 'index.html':
                html_files.append(filename)
    
    # Generate HTML
    html = f'''<!DOCTYPE html>
<html>
<head>
    <title>PyIV Documentation - Python Dependency Injection Library</title>
    <meta charset="utf-8">
    <meta name="description" content="PyIV - A lightweight, type-aware dependency injection library for Python applications">
    <style>
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{ 
            color: #333;
            border-bottom: 3px solid #0066cc;
            padding-bottom: 10px;
            margin-top: 0;
        }}
        h2 {{
            color: #555;
            margin-top: 40px;
            border-bottom: 2px solid #e0e0e0;
            padding-bottom: 8px;
        }}
        h3 {{
            color: #666;
            margin-top: 30px;
        }}
        .description {{
            color: #666;
            font-size: 1.2em;
            margin: 20px 0;
            font-weight: 300;
        }}
        .features {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .feature {{
            padding: 20px;
            background: #f9f9f9;
            border-radius: 6px;
            border-left: 4px solid #0066cc;
        }}
        .feature h4 {{
            margin-top: 0;
            color: #0066cc;
        }}
        .code-block {{
            background: #f5f5f5;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 15px;
            margin: 15px 0;
            overflow-x: auto;
            font-family: 'Monaco', 'Courier New', monospace;
            font-size: 0.9em;
        }}
        .code-block code {{
            color: #333;
        }}
        .modules-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 15px;
            margin: 30px 0;
        }}
        .module-card {{
            padding: 15px;
            background: #f9f9f9;
            border-radius: 6px;
            border: 1px solid #e0e0e0;
            transition: all 0.2s;
        }}
        .module-card:hover {{
            border-color: #0066cc;
            box-shadow: 0 2px 8px rgba(0,102,204,0.1);
            transform: translateY(-2px);
        }}
        .module-card a {{
            color: #0066cc;
            text-decoration: none;
            font-weight: 500;
            display: block;
        }}
        .module-card a:hover {{
            text-decoration: underline;
        }}
        .module-name {{
            font-family: 'Monaco', 'Courier New', monospace;
            color: #333;
            font-size: 0.95em;
        }}
        .module-desc {{
            color: #666;
            font-size: 0.85em;
            margin-top: 5px;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            background: #0066cc;
            color: white;
            border-radius: 4px;
            font-size: 0.85em;
            font-weight: 500;
            margin-right: 10px;
        }}
        .quick-links {{
            margin: 30px 0;
            padding: 20px;
            background: #e8f4f8;
            border-radius: 6px;
            border-left: 4px solid #0066cc;
        }}
        .quick-links a {{
            color: #0066cc;
            text-decoration: none;
            font-weight: 500;
            margin-right: 20px;
        }}
        .quick-links a:hover {{
            text-decoration: underline;
        }}
        hr {{
            border: none;
            border-top: 1px solid #e0e0e0;
            margin: 40px 0;
        }}
        .footer {{
            color: #999;
            font-size: 0.9em;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
        }}
        ul {{
            list-style-type: none;
            padding: 0;
        }}
        li {{
            margin: 10px 0;
            padding: 8px;
            background: #f9f9f9;
            border-left: 3px solid #0066cc;
        }}
        a {{
            color: #0066cc;
            text-decoration: none;
            font-weight: 500;
        }}
        a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>PyIV Documentation</h1>
        <p class="description">
            <span class="badge">v0.2.4</span>
            A lightweight, type-aware dependency injection library for Python applications.
            PyIV provides a simple yet powerful way to manage dependencies, improve testability, and reduce coupling.
        </p>

        <div class="quick-links">
            <strong>Quick Links:</strong>
            <a href="https://github.com/rl337/pyiv">GitHub Repository</a>
            <a href="https://github.com/rl337/pyiv/blob/main/README.md">README</a>
            <a href="https://pypi.org/project/pyiv/">PyPI Package</a>
        </div>

        <h2>Key Features</h2>
        <div class="features">
            <div class="feature">
                <h4>🔧 Type-Based Resolution</h4>
                <p>Automatic dependency resolution using Python type annotations. No manual wiring required.</p>
            </div>
            <div class="feature">
                <h4>🎯 Singleton Management</h4>
                <p>Built-in singleton lifecycle management (per-injector or global) for efficient resource usage.</p>
            </div>
            <div class="feature">
                <h4>🏭 Factory Pattern</h4>
                <p>Factory pattern support for complex object creation with dependency injection.</p>
            </div>
            <div class="feature">
                <h4>🧪 Test-Friendly</h4>
                <p>Built-in abstractions for Clock, Filesystem, and DateTimeService make testing easy.</p>
            </div>
            <div class="feature">
                <h4>📦 Zero Dependencies</h4>
                <p>Pure Python implementation with no external dependencies. Lightweight and fast.</p>
            </div>
            <div class="feature">
                <h4>🔍 Reflection Support</h4>
                <p>Automatic discovery of interface implementations in packages using ReflectionConfig.</p>
            </div>
        </div>

        <h2>Quick Start</h2>
        <p>Get started with PyIV in just a few lines of code:</p>
        <div class="code-block">
            <code>
from pyiv import Config, get_injector<br><br>
# Define your configuration<br>
class MyConfig(Config):<br>
&nbsp;&nbsp;&nbsp;&nbsp;def configure(self):<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;self.register(Database, PostgreSQL)<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;self.register(Logger, FileLogger, singleton=True)<br><br>
# Create injector and resolve dependencies<br>
injector = get_injector(MyConfig)<br>
db = injector.inject(Database)<br>
logger = injector.inject(Logger)
            </code>
        </div>

        <h2>Core Modules</h2>
        <p>Explore the PyIV modules to understand the full capabilities:</p>
        <div class="modules-grid">
'''
    
    # Add module cards
    for filename in html_files:
        modulename = filename.replace('.html', '')
        desc = MODULE_DESCRIPTIONS.get(modulename, 'Module documentation')
        html += f'''            <div class="module-card">
                <a href="{filename}">
                    <div class="module-name">{modulename}</div>
                    <div class="module-desc">{desc}</div>
                </a>
            </div>
'''
    
    html += '''        </div>

        <h2>Example: Testing with Abstractions</h2>
        <p>PyIV makes testing easy with built-in abstractions:</p>
        <div class="code-block">
            <code>
from pyiv.clock import Clock, SyntheticClock<br>
from pyiv.filesystem import Filesystem, MemoryFilesystem<br>
from pyiv import Config, get_injector<br><br>
# Production config<br>
class ProdConfig(Config):<br>
&nbsp;&nbsp;&nbsp;&nbsp;def configure(self):<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;self.register(Clock, RealClock)<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;self.register(Filesystem, RealFilesystem)<br><br>
# Test config<br>
class TestConfig(Config):<br>
&nbsp;&nbsp;&nbsp;&nbsp;def configure(self):<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;self.register(Clock, SyntheticClock, singleton=True)<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;self.register(Filesystem, MemoryFilesystem)<br><br>
# Use in tests<br>
injector = get_injector(TestConfig)<br>
clock = injector.inject(Clock)<br>
clock.set_time(100.0)  # Control time in tests!<br>
filesystem = injector.inject(Filesystem)<br>
filesystem.write_text('test.txt', 'content')  # In-memory filesystem!
            </code>
        </div>

        <h2>Installation</h2>
        <div class="code-block">
            <code>
pip install pyiv<br><br>
# Or with Poetry<br>
poetry add pyiv
            </code>
        </div>

        <hr>

        <h2>API Documentation</h2>
        <p>Browse the complete API documentation for each module:</p>
        <ul>
'''
    
    # Add API links
    for filename in html_files:
        modulename = filename.replace('.html', '')
        html += f'            <li><a href="{filename}"><span class="module-name">{modulename}</span></a></li>\n'
    
    html += f'''        </ul>

        <div class="footer">
            <p>
                Generated on {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")} | 
                <a href="https://github.com/rl337/pyiv">View on GitHub</a> | 
                <a href="https://pypi.org/project/pyiv/">View on PyPI</a>
            </p>
        </div>
    </div>
</body>
</html>
'''
    
    # Write to file
    output_path = os.path.join(html_dir, 'index.html')
    os.makedirs(html_dir, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"Generated index.html at {output_path}")

if __name__ == '__main__':
    import sys
    html_dir = sys.argv[1] if len(sys.argv) > 1 else 'docs/html'
    generate_index_html(html_dir)

