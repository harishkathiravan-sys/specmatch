"""Setup Phase 6 imports and fix any dependency issues."""
import os
import re
import shutil
from pathlib import Path

def fix_imports_in_file(filepath):
    """Fix imports in a file to support Phase 6 integration."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Fix common import patterns
    if 'from app.retrieval import' in content and 'PipelineResult' in content:
        # Replace import statements that might cause circular imports
        content = content.replace(
            'from app.retrieval import PipelineResult',
            '# from app.retrieval import PipelineResult  # Import handled in phase6_integration.py'
        )
        # Ensure proper imports
        if 'from .pipeline import' not in content:
            content = content.replace(
                'from app.retrieval.pipeline import',
                'from .pipeline import'
            )

    # Add Phase 6 imports if needed
    if 'run_pipeline' in content and 'from app.retrieval.phase6_integration import' not in content:
        # Add import statement for Phase 6
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'def run_pipeline(' in line:
                # Add import before this line
                lines.insert(i, 'from .phase6_integration import Phase6IntelligenceEngine')
                break
        content = '\n'.join(lines)

    # Write back
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"Fixed imports in {filepath}")

def main():
    backend_dir = Path('d:\\testing2\\backend')

    # List of files that need import fixes
    files_to_fix = [
        backend_dir / 'app\retrieval\pipeline.py',
        backend_dir / 'app\retrieval\query.py',
        backend_dir / 'app\retrieval\requirements.py',
        backend_dir / 'app\retrieval\fusion.py',
        backend_dir / 'app\retrieval\reranker.py',
        backend_dir / 'app\retrieval\confidence.py',
        backend_dir / 'app\retrieval\evidence.py',
        backend_dir / 'app\retrieval\semantic.py',
        backend_dir / 'app\retrieval\lexical.py',
        backend_dir / 'app\retrieval\metadata.py',
    ]

    for filepath in files_to_fix:
        if filepath.exists():
            fix_imports_in_file(filepath)
        else:
            print(f"Warning: File not found: {filepath}")

    print("Import fixes completed")

if __name__ == '__main__':
    main()