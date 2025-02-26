import os
import ast
import json
import subprocess
from typing import Dict, List
import radon.complexity as radon_cc
import radon.metrics as radon_metrics
from pylint.lint import Run
from pylint.reporters import JSONReporter
from io import StringIO
import bandit.core.manager as bandit_manager
from bandit.core.config import BanditConfig

class CodeAnalyzer:
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.results = {
            'scores': {
                'functionality': 0,
                'code_quality': 0,
                'performance': 0,
                'documentation': 0,
                'security': 0
            },
            'details': {
                'missing_features': [],
                'security_issues': [],
                'code_smells': [],
                'performance_issues': [],
                'documentation_issues': []
            }
        }

    def analyze(self) -> Dict:
        """Perform complete code analysis."""
        try:
            # Analyze Python files
            python_files = self._find_python_files()
            
            if not python_files:
                self.results['details']['missing_features'].append("No Python files found")
                return self.results

            for file_path in python_files:
                self._analyze_file(file_path)

            # Run tests if they exist
            self._run_tests()
            
            # Calculate final scores
            self._calculate_scores()
            
            return self.results
        except Exception as e:
            self.results['details']['missing_features'].append(f"Analysis error: {str(e)}")
            return self.results

    def _find_python_files(self) -> List[str]:
        """Find all Python files in the repository."""
        python_files = []
        for root, _, files in os.walk(self.repo_path):
            for file in files:
                if file.endswith('.py') and not file.startswith('test_'):
                    python_files.append(os.path.join(root, file))
        return python_files

    def _analyze_file(self, file_path: str):
        """Analyze a single Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse AST
            tree = ast.parse(content)
            
            # Analyze code quality
            self._analyze_code_quality(content, file_path)
            
            # Analyze security
            self._analyze_security(file_path)
            
            # Analyze documentation
            self._analyze_documentation(tree)
            
            # Analyze performance
            self._analyze_performance(tree)

        except Exception as e:
            self.results['details']['missing_features'].append(f"Error analyzing {os.path.basename(file_path)}: {str(e)}")

    def _analyze_code_quality(self, content: str, file_path: str):
        """Analyze code quality using various metrics."""
        # Calculate cyclomatic complexity
        cc_results = radon_cc.cc_visit(content)
        avg_complexity = sum(cc.complexity for cc in cc_results) / len(cc_results) if cc_results else 0
        
        # Run pylint
        pylint_output = StringIO()
        reporter = JSONReporter(pylint_output)
        Run([file_path], reporter=reporter, exit=False)
        
        try:
            pylint_score = float(pylint_output.getvalue().strip()) if pylint_output.getvalue().strip() else 0
        except (ValueError, IndexError):
            pylint_score = 0
        
        # Add code smells based on complexity and pylint score
        if avg_complexity > 10:
            self.results['details']['code_smells'].append(f"High complexity in {os.path.basename(file_path)}")
        if pylint_score < 7:
            self.results['details']['code_smells'].append(f"Low code quality score in {os.path.basename(file_path)}")

    def _analyze_security(self, file_path: str):
        """Analyze security using bandit."""
        b_conf = BanditConfig()
        b_mgr = bandit_manager.BanditManager(b_conf, 'file')
        
        b_mgr.discover_files([file_path])
        b_mgr.run_tests()
        
        for issue in b_mgr.get_issue_list():
            self.results['details']['security_issues'].append(
                f"Security issue in {os.path.basename(file_path)}: {issue.text}"
            )

    def _analyze_documentation(self, tree: ast.AST):
        """Analyze documentation completeness."""
        class DocVisitor(ast.NodeVisitor):
            def __init__(self):
                self.has_module_doc = False
                self.funcs_with_docs = 0
                self.total_funcs = 0
                self.classes_with_docs = 0
                self.total_classes = 0

            def visit_Module(self, node):
                self.has_module_doc = ast.get_docstring(node) is not None
                self.generic_visit(node)

            def visit_FunctionDef(self, node):
                self.total_funcs += 1
                if ast.get_docstring(node):
                    self.funcs_with_docs += 1

            def visit_ClassDef(self, node):
                self.total_classes += 1
                if ast.get_docstring(node):
                    self.classes_with_docs += 1

        visitor = DocVisitor()
        visitor.visit(tree)
        
        if not visitor.has_module_doc:
            self.results['details']['documentation_issues'].append("Missing module documentation")
        
        if visitor.total_funcs > 0:
            doc_ratio = visitor.funcs_with_docs / visitor.total_funcs
            if doc_ratio < 0.7:
                self.results['details']['documentation_issues'].append(
                    f"Only {int(doc_ratio * 100)}% of functions are documented"
                )

    def _analyze_performance(self, tree: ast.AST):
        """Analyze code for performance issues."""
        class PerfVisitor(ast.NodeVisitor):
            def __init__(self):
                self.issues = []

            def visit_For(self, node):
                if isinstance(node.iter, ast.Call):
                    if isinstance(node.iter.func, ast.Name) and node.iter.func.id == 'range':
                        if len(node.iter.args) == 1 and isinstance(node.iter.args[0], ast.Call):
                            if isinstance(node.iter.args[0].func, ast.Name) and node.iter.args[0].func.id == 'len':
                                self.issues.append("Inefficient loop using range(len())")
                self.generic_visit(node)

        visitor = PerfVisitor()
        visitor.visit(tree)
        self.results['details']['performance_issues'].extend(visitor.issues)

    def _run_tests(self):
        """Run unit tests if they exist."""
        test_dir = os.path.join(self.repo_path, 'tests')
        if os.path.exists(test_dir):
            try:
                result = subprocess.run(['python', '-m', 'pytest', test_dir], 
                                     capture_output=True, text=True)
                if result.returncode != 0:
                    self.results['details']['missing_features'].append("Some tests failed")
            except Exception:
                self.results['details']['missing_features'].append("Failed to run tests")
        else:
            self.results['details']['missing_features'].append("No tests directory found")

    def _calculate_scores(self):
        """Calculate final scores based on analysis results."""
        scores = self.results['scores']
        
        # Code Quality Score (out of 100)
        code_smells = len(self.results['details']['code_smells'])
        scores['code_quality'] = max(0, 100 - (code_smells * 10))
        
        # Security Score (out of 100)
        security_issues = len(self.results['details']['security_issues'])
        scores['security'] = max(0, 100 - (security_issues * 15))
        
        # Documentation Score (out of 100)
        doc_issues = len(self.results['details']['documentation_issues'])
        scores['documentation'] = max(0, 100 - (doc_issues * 20))
        
        # Performance Score (out of 100)
        perf_issues = len(self.results['details']['performance_issues'])
        scores['performance'] = max(0, 100 - (perf_issues * 15))
        
        # Functionality Score (out of 100)
        missing_features = len(self.results['details']['missing_features'])
        scores['functionality'] = max(0, 100 - (missing_features * 20))

        # Round all scores
        for key in scores:
            scores[key] = round(scores[key], 2)
