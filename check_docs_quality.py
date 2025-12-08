#!/usr/bin/env python3
"""Check documentation quality for pyiv package.

This script analyzes docstring quality across all modules and provides
a comprehensive score based on multiple quality metrics.
"""

import ast
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


class DocstringAnalyzer(ast.NodeVisitor):
    """AST visitor to analyze docstring quality."""

    def __init__(self, file_path: Optional[Path] = None):
        """Initialize analyzer."""
        self.classes: List[Dict] = []
        self.functions: List[Dict] = []
        self.methods: List[Dict] = []
        self.current_class: Optional[str] = None
        self.file_path: Optional[Path] = file_path
        self.module_docstring: Optional[str] = None
        self.module_name: Optional[str] = None

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definition."""
        old_class = self.current_class
        self.current_class = node.name

        docstring = ast.get_docstring(node)
        class_info = {
            "name": node.name,
            "line": node.lineno,
            "docstring": docstring,
            "has_docstring": docstring is not None,
            "docstring_length": len(docstring) if docstring else 0,
            "is_public": not node.name.startswith("_"),
        }
        self.classes.append(class_info)

        # Analyze docstring quality
        if docstring:
            class_info.update(self._analyze_docstring(docstring))

        # Visit children
        self.generic_visit(node)
        self.current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function or method definition."""
        docstring = ast.get_docstring(node)
        is_method = self.current_class is not None
        is_public = not node.name.startswith("_")

        func_info = {
            "name": node.name,
            "line": node.lineno,
            "class": self.current_class,
            "is_method": is_method,
            "is_public": is_public,
            "docstring": docstring,
            "has_docstring": docstring is not None,
            "docstring_length": len(docstring) if docstring else 0,
            "args": [arg.arg for arg in node.args.args if arg.arg != "self"],
        }

        if is_method:
            self.methods.append(func_info)
        else:
            self.functions.append(func_info)

        # Analyze docstring quality
        if docstring:
            func_info.update(self._analyze_docstring(docstring))
            # Check if all args are documented
            func_info["args_documented"] = self._check_args_documented(
                docstring, func_info["args"]
            )

    def _analyze_docstring(self, docstring: str) -> Dict:
        """Analyze docstring quality metrics."""
        lines = docstring.strip().split("\n")
        doc_lower = docstring.lower()

        return {
            "has_description": len(lines) > 0 and len(lines[0].strip()) > 10,
            "has_args_section": "args:" in doc_lower or "parameters:" in doc_lower,
            "has_returns_section": "returns:" in doc_lower or "return:" in doc_lower,
            "has_raises_section": "raises:" in doc_lower or "exceptions:" in doc_lower,
            "has_example": "example:" in doc_lower or "examples:" in doc_lower,
            "has_note": "note:" in doc_lower or "notes:" in doc_lower,
            "line_count": len([l for l in lines if l.strip()]),
            "word_count": len(docstring.split()),
            "min_length": len(docstring) >= 50,  # At least 50 characters
            "good_length": len(docstring) >= 100,  # Good docstrings are 100+ chars
        }

    def _check_args_documented(self, docstring: str, args: List[str]) -> Dict[str, bool]:
        """Check if all function arguments are documented."""
        if not args:
            return {}
        doc_lower = docstring.lower()
        documented = {}
        for arg in args:
            # Check if arg name appears in Args section
            documented[arg] = f" {arg}:" in doc_lower or f" {arg} " in doc_lower
        return documented

    def visit_Module(self, node: ast.Module) -> None:
        """Visit module node to extract module-level docstring."""
        self.module_docstring = ast.get_docstring(node)
        if self.file_path:
            # Extract module name from file path
            parts = self.file_path.parts
            if "pyiv" in parts:
                idx = parts.index("pyiv")
                self.module_name = ".".join(parts[idx:]).replace(".py", "")
            else:
                self.module_name = self.file_path.stem
        self.generic_visit(node)


def analyze_file(file_path: Path) -> Tuple[DocstringAnalyzer, List[str]]:
    """Analyze a Python file for documentation quality."""
    errors = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(file_path))
        analyzer = DocstringAnalyzer(file_path=file_path)
        analyzer.visit(tree)
        return analyzer, errors
    except SyntaxError as e:
        errors.append(f"Syntax error in {file_path}: {e}")
        return DocstringAnalyzer(file_path=file_path), errors
    except Exception as e:
        errors.append(f"Error analyzing {file_path}: {e}")
        return DocstringAnalyzer(file_path=file_path), errors


def calculate_scores(analyzers: List[DocstringAnalyzer]) -> Dict:
    """Calculate overall documentation quality scores."""
    all_classes = []
    all_functions = []
    all_methods = []
    modules = []

    for analyzer in analyzers:
        all_classes.extend(analyzer.classes)
        all_functions.extend(analyzer.functions)
        all_methods.extend(analyzer.methods)
        # Track module docstrings (skip __init__.py as it's package-level)
        if analyzer.module_docstring is not None or analyzer.file_path:
            module_info = {
                "name": analyzer.module_name or (analyzer.file_path.stem if analyzer.file_path else "unknown"),
                "file_path": str(analyzer.file_path) if analyzer.file_path else None,
                "docstring": analyzer.module_docstring,
                "has_docstring": analyzer.module_docstring is not None,
                "docstring_length": len(analyzer.module_docstring) if analyzer.module_docstring else 0,
                "is_package": analyzer.file_path.name == "__init__.py" if analyzer.file_path else False,
            }
            if analyzer.module_docstring:
                module_info.update(analyzer._analyze_docstring(analyzer.module_docstring))
            modules.append(module_info)

    # Filter to public items only
    public_classes = [c for c in all_classes if c["is_public"]]
    public_functions = [f for f in all_functions if f["is_public"]]
    public_methods = [m for m in all_methods if m["is_public"]]

    # Calculate coverage
    class_coverage = (
        len([c for c in public_classes if c["has_docstring"]]) / len(public_classes)
        if public_classes
        else 1.0
    )
    function_coverage = (
        len([f for f in public_functions if f["has_docstring"]])
        / len(public_functions)
        if public_functions
        else 1.0
    )
    method_coverage = (
        len([m for m in public_methods if m["has_docstring"]])
        / len(public_methods)
        if public_methods
        else 1.0
    )
    # Module coverage - critical for navigation and architecture understanding
    module_coverage = (
        len([m for m in modules if m["has_docstring"]]) / len(modules)
        if modules
        else 1.0
    )

    # Calculate quality metrics for items with docstrings
    documented_classes = [c for c in public_classes if c["has_docstring"]]
    documented_functions = [f for f in public_functions if f["has_docstring"]]
    documented_methods = [m for m in public_methods if m["has_docstring"]]
    documented_modules = [m for m in modules if m["has_docstring"]]

    def avg_quality(items: List[Dict]) -> Dict:
        """Calculate average quality metrics."""
        if not items:
            return {
                "has_description": 1.0,
                "has_args_section": 1.0,
                "has_returns_section": 1.0,
                "has_raises_section": 0.0,
                "has_example": 0.0,
                "min_length": 1.0,
                "good_length": 1.0,
                "avg_word_count": 0,
            }

        return {
            "has_description": sum(1 for i in items if i.get("has_description", False))
            / len(items),
            "has_args_section": sum(
                1 for i in items if i.get("has_args_section", False)
            )
            / len(items),
            "has_returns_section": sum(
                1 for i in items if i.get("has_returns_section", False)
            )
            / len(items),
            "has_raises_section": sum(
                1 for i in items if i.get("has_raises_section", False)
            )
            / len(items),
            "has_example": sum(1 for i in items if i.get("has_example", False))
            / len(items),
            "min_length": sum(1 for i in items if i.get("min_length", False))
            / len(items),
            "good_length": sum(1 for i in items if i.get("good_length", False))
            / len(items),
            "avg_word_count": sum(i.get("word_count", 0) for i in items) / len(items),
        }

    class_quality = avg_quality(documented_classes)
    function_quality = avg_quality(documented_functions)
    method_quality = avg_quality(documented_methods)
    module_quality = avg_quality(documented_modules)

    # Check argument documentation for methods and functions
    all_documented_funcs = documented_functions + documented_methods
    args_documented_ratio = 0.0
    if all_documented_funcs:
        total_args = 0
        documented_args = 0
        for func in all_documented_funcs:
            args_doc = func.get("args_documented", {})
            for arg, is_doc in args_doc.items():
                total_args += 1
                if is_doc:
                    documented_args += 1
        if total_args > 0:
            args_documented_ratio = documented_args / total_args

    # Calculate overall score (weighted)
    # Coverage: 30% weight (modules 10%, classes 8%, functions 4%, methods 8% of total), Quality: 45%, Args: 15%, Module Quality: 10%
    # Module documentation is critical for navigation and architecture understanding
    # Normalize coverage weights to sum to 1.0 for proper percentage calculation
    coverage_weights_sum = 0.10 + 0.08 + 0.04 + 0.08  # = 0.30
    overall_coverage = (
        (module_coverage * 0.10 + class_coverage * 0.08 + function_coverage * 0.04 + method_coverage * 0.08) / coverage_weights_sum
    )
    overall_quality = (
        class_quality["has_description"] * 0.12
        + class_quality["has_example"] * 0.18
        + class_quality["good_length"] * 0.15
        + method_quality["has_args_section"] * 0.15
        + method_quality["has_returns_section"] * 0.15
        + module_quality["has_description"] * 0.10
        + module_quality["good_length"] * 0.15
    )
    # Overall score: Coverage 30%, Quality 45%, Args 15%, Module Quality 10%
    overall_score = overall_coverage * 0.30 + overall_quality * 0.45 + args_documented_ratio * 0.15 + (module_quality["has_description"] * 0.5 + module_quality["good_length"] * 0.5) * 0.10

    return {
        "overall_score": overall_score,
        "overall_coverage": overall_coverage,
        "overall_quality": overall_quality,
        "args_documented_ratio": args_documented_ratio,
        "module_coverage": module_coverage,
        "class_coverage": class_coverage,
        "function_coverage": function_coverage,
        "method_coverage": method_coverage,
        "module_quality": module_quality,
        "class_quality": class_quality,
        "function_quality": function_quality,
        "method_quality": method_quality,
        "stats": {
            "total_modules": len(modules),
            "documented_modules": len(documented_modules),
            "total_classes": len(public_classes),
            "documented_classes": len(documented_classes),
            "total_functions": len(public_functions),
            "documented_functions": len(documented_functions),
            "total_methods": len(public_methods),
            "documented_methods": len(documented_methods),
        },
    }


def find_issues(analyzers: List[DocstringAnalyzer]) -> List[Dict]:
    """Find specific documentation issues."""
    issues = []

    for analyzer in analyzers:
        # Check for missing module-level docstrings
        if analyzer.module_docstring is None and analyzer.file_path:
            module_name = analyzer.module_name or (analyzer.file_path.stem if analyzer.file_path else "unknown")
            is_package = analyzer.file_path.name == "__init__.py"
            issues.append(
                {
                    "type": "missing_module_docstring",
                    "name": module_name,
                    "file": str(analyzer.file_path),
                    "severity": "high",
                    "reason": f"Module-level docstring missing - critical for navigation and architecture understanding",
                    "is_package": is_package,
                }
            )
        elif analyzer.module_docstring and analyzer.file_path:
            # Check module docstring quality
            module_name = analyzer.module_name or (analyzer.file_path.stem if analyzer.file_path else "unknown")
            # Create a temporary analyzer to use the method
            temp_analyzer = DocstringAnalyzer()
            quality = temp_analyzer._analyze_docstring(analyzer.module_docstring)
            if not quality.get("has_description", False) or len(analyzer.module_docstring) < 50:
                issues.append(
                    {
                        "type": "poor_module_docstring",
                        "name": module_name,
                        "file": str(analyzer.file_path),
                        "severity": "high",
                        "reason": "Module docstring too short or missing description - should explain module purpose, architecture, and navigation",
                    }
                )
            elif len(analyzer.module_docstring) < 150:
                issues.append(
                    {
                        "type": "incomplete_module_docstring",
                        "name": module_name,
                        "file": str(analyzer.file_path),
                        "severity": "medium",
                        "reason": "Module docstring could be more comprehensive - should include architecture decisions and usage examples",
                    }
                )
        # Check for undocumented public classes
        for cls in analyzer.classes:
            if cls["is_public"] and not cls["has_docstring"]:
                issues.append(
                    {
                        "type": "missing_class_docstring",
                        "name": cls["name"],
                        "line": cls["line"],
                        "severity": "high",
                    }
                )
            elif cls["is_public"] and cls["has_docstring"]:
                if not cls.get("has_description", False):
                    issues.append(
                        {
                            "type": "poor_class_docstring",
                            "name": cls["name"],
                            "line": cls["line"],
                            "severity": "medium",
                            "reason": "Missing or too short description",
                        }
                    )
                if not cls.get("has_example", False) and cls.get("docstring_length", 0) < 100:
                    issues.append(
                        {
                            "type": "incomplete_class_docstring",
                            "name": cls["name"],
                            "line": cls["line"],
                            "severity": "low",
                            "reason": "Could benefit from examples or more detail",
                        }
                    )

        # Check for undocumented public methods
        for method in analyzer.methods:
            if method["is_public"] and not method["has_docstring"]:
                issues.append(
                    {
                        "type": "missing_method_docstring",
                        "name": f"{method['class']}.{method['name']}",
                        "line": method["line"],
                        "severity": "high",
                    }
                )
            elif method["is_public"] and method["has_docstring"]:
                if method["args"] and not method.get("has_args_section", False):
                    issues.append(
                        {
                            "type": "missing_args_doc",
                            "name": f"{method['class']}.{method['name']}",
                            "line": method["line"],
                            "severity": "medium",
                            "reason": f"Method has arguments but no Args section: {', '.join(method['args'])}",
                        }
                    )
                args_doc = method.get("args_documented", {})
                missing_args = [
                    arg for arg, doc in args_doc.items() if not doc
                ]
                if missing_args:
                    issues.append(
                        {
                            "type": "incomplete_args_doc",
                            "name": f"{method['class']}.{method['name']}",
                            "line": method["line"],
                            "severity": "medium",
                            "reason": f"Arguments not documented: {', '.join(missing_args)}",
                        }
                    )
                if method.get("has_returns_section", False) is False and not method["name"].startswith("_"):
                    # Methods that might return something should document it
                    issues.append(
                        {
                            "type": "missing_returns_doc",
                            "name": f"{method['class']}.{method['name']}",
                            "line": method["line"],
                            "severity": "low",
                            "reason": "Consider adding Returns section",
                        }
                    )

        # Check for undocumented public functions
        for func in analyzer.functions:
            if func["is_public"] and not func["has_docstring"]:
                issues.append(
                    {
                        "type": "missing_function_docstring",
                        "name": func["name"],
                        "line": func["line"],
                        "severity": "high",
                    }
                )
            elif func["is_public"] and func["has_docstring"]:
                if func["args"] and not func.get("has_args_section", False):
                    issues.append(
                        {
                            "type": "missing_args_doc",
                            "name": func["name"],
                            "line": func["line"],
                            "severity": "medium",
                            "reason": f"Function has arguments but no Args section: {', '.join(func['args'])}",
                        }
                    )

    return issues


def main() -> int:
    """Main entry point."""
    pyiv_path = Path("pyiv")
    if not pyiv_path.exists():
        print("Error: pyiv/ directory not found")
        return 1

    # Find all Python files
    python_files = list(pyiv_path.rglob("*.py"))
    python_files = [f for f in python_files if f.name != "__pycache__"]

    if not python_files:
        print("Error: No Python files found in pyiv/")
        return 1

    print(f"Analyzing {len(python_files)} Python files...")
    print()

    # Analyze all files
    analyzers = []
    all_errors = []
    for file_path in sorted(python_files):
        analyzer, errors = analyze_file(file_path)
        analyzers.append(analyzer)
        all_errors.extend(errors)

    if all_errors:
        print("Errors encountered:")
        for error in all_errors:
            print(f"  - {error}")
        print()

    # Calculate scores
    scores = calculate_scores(analyzers)
    issues = find_issues(analyzers)

    # Print results
    print("=" * 70)
    print("DOCUMENTATION QUALITY REPORT")
    print("=" * 70)
    print()
    print(f"Overall Score: {scores['overall_score']:.2%}")
    print(f"  Coverage: {scores['overall_coverage']:.2%}")
    print(f"  Quality: {scores['overall_quality']:.2%}")
    print(f"  Args Documented: {scores['args_documented_ratio']:.2%}")
    print()
    print("Coverage by Type:")
    print(f"  Modules: {scores['module_coverage']:.2%} ({scores['stats']['documented_modules']}/{scores['stats']['total_modules']}) [CRITICAL for navigation]")
    print(f"  Classes: {scores['class_coverage']:.2%} ({scores['stats']['documented_classes']}/{scores['stats']['total_classes']})")
    print(f"  Functions: {scores['function_coverage']:.2%} ({scores['stats']['documented_functions']}/{scores['stats']['total_functions']})")
    print(f"  Methods: {scores['method_coverage']:.2%} ({scores['stats']['documented_methods']}/{scores['stats']['total_methods']})")
    print()
    print("Module Quality Metrics:")
    print(f"    Has description: {scores['module_quality']['has_description']:.2%}")
    print(f"    Good length (100+ chars): {scores['module_quality']['good_length']:.2%}")
    print(f"    Avg word count: {scores['module_quality']['avg_word_count']:.1f}")
    print()
    print("Quality Metrics (for documented items):")
    print("  Classes:")
    print(f"    Has description: {scores['class_quality']['has_description']:.2%}")
    print(f"    Has examples: {scores['class_quality']['has_example']:.2%}")
    print(f"    Good length (100+ chars): {scores['class_quality']['good_length']:.2%}")
    print(f"    Avg word count: {scores['class_quality']['avg_word_count']:.1f}")
    print("  Methods:")
    print(f"    Has Args section: {scores['method_quality']['has_args_section']:.2%}")
    print(f"    Has Returns section: {scores['method_quality']['has_returns_section']:.2%}")
    print(f"    Has Raises section: {scores['method_quality']['has_raises_section']:.2%}")
    print()

    # Print issues
    if issues:
        print("=" * 70)
        print("ISSUES FOUND")
        print("=" * 70)
        print()

        high_issues = [i for i in issues if i["severity"] == "high"]
        medium_issues = [i for i in issues if i["severity"] == "medium"]
        low_issues = [i for i in issues if i["severity"] == "low"]

        if high_issues:
            print(f"High Priority ({len(high_issues)}):")
            for issue in high_issues[:10]:  # Limit output
                location = f"line {issue['line']}" if 'line' in issue else f"file {issue.get('file', 'unknown')}"
                reason = f" - {issue['reason']}" if "reason" in issue else ""
                print(f"  - {issue['type']}: {issue['name']} ({location}){reason}")
            if len(high_issues) > 10:
                print(f"  ... and {len(high_issues) - 10} more")
            print()

        if medium_issues:
            print(f"Medium Priority ({len(medium_issues)}):")
            for issue in medium_issues[:10]:
                location = f"line {issue['line']}" if 'line' in issue else f"file {issue.get('file', 'unknown')}"
                reason = f" - {issue['reason']}" if "reason" in issue else ""
                print(f"  - {issue['type']}: {issue['name']} ({location}){reason}")
            if len(medium_issues) > 10:
                print(f"  ... and {len(medium_issues) - 10} more")
            print()

        if low_issues:
            print(f"Low Priority ({len(low_issues)}):")
            for issue in low_issues[:5]:
                location = f"line {issue['line']}" if 'line' in issue else f"file {issue.get('file', 'unknown')}"
                reason = f" - {issue['reason']}" if "reason" in issue else ""
                print(f"  - {issue['type']}: {issue['name']} ({location}){reason}")
            if len(low_issues) > 5:
                print(f"  ... and {len(low_issues) - 5} more")
            print()

    # Determine pass/fail
    # Pass if overall score >= 0.75 (75%)
    PASS_THRESHOLD = 0.75
    passed = scores["overall_score"] >= PASS_THRESHOLD

    print("=" * 70)
    if passed:
        print(f"✓ PASSED: Documentation quality meets threshold ({PASS_THRESHOLD:.0%})")
        return 0
    else:
        print(f"✗ FAILED: Documentation quality below threshold ({PASS_THRESHOLD:.0%})")
        print(f"  Current score: {scores['overall_score']:.2%}")
        print(f"  Need to improve by: {(PASS_THRESHOLD - scores['overall_score']):.2%}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

