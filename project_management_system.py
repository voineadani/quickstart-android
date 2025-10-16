#!/usr/bin/env python
"""Firebase Android Quickstart Project Management System.

This script provides utilities for managing Firebase Android quickstart projects,
including listing modules, building specific projects, running tests, and managing
configurations.

Example usage:
    $ python project_management_system.py list
    $ python project_management_system.py build --module auth
    $ python project_management_system.py test --module analytics
    $ python project_management_system.py setup-all
"""

import argparse
import os
import subprocess
import sys
import json
from pathlib import Path


class ProjectManager:
    """Manages Firebase Android quickstart projects."""
    
    def __init__(self, root_dir=None):
        """Initialize the project manager.
        
        Args:
            root_dir: Root directory of the quickstart-android repository.
                     Defaults to the directory containing this script.
        """
        if root_dir is None:
            root_dir = os.path.dirname(os.path.abspath(__file__))
        self.root_dir = root_dir
        self.settings_gradle = os.path.join(root_dir, 'settings.gradle')
        self.mock_google_services = os.path.join(root_dir, 'mock-google-services.json')
        self.modules = self._parse_modules()
    
    def _parse_modules(self):
        """Parse modules from settings.gradle file.
        
        Returns:
            List of module names (e.g., ['admob', 'analytics', ...])
        """
        modules = []
        if not os.path.exists(self.settings_gradle):
            print(f"Warning: {self.settings_gradle} not found")
            return modules
        
        with open(self.settings_gradle, 'r') as f:
            content = f.read()
            # Extract module names like ':admob:app' -> 'admob'
            import re
            pattern = r"':([^:]+):app'"
            matches = re.findall(pattern, content)
            # Filter out 'internal' modules
            modules = [m for m in matches if m != 'internal']
        
        return sorted(modules)
    
    def list_modules(self):
        """List all available Firebase quickstart modules."""
        print("Available Firebase Quickstart Modules:")
        print("=" * 50)
        for i, module in enumerate(self.modules, 1):
            module_path = os.path.join(self.root_dir, module)
            if os.path.exists(module_path):
                readme_path = os.path.join(module_path, 'README.md')
                status = "✓" if os.path.exists(readme_path) else "○"
                print(f"{i:2d}. {status} {module}")
            else:
                print(f"{i:2d}. ✗ {module} (missing)")
        print("=" * 50)
        print(f"Total: {len(self.modules)} modules")
    
    def setup_module(self, module):
        """Setup a specific module by copying mock google-services.json.
        
        Args:
            module: Name of the module to setup
            
        Returns:
            True if successful, False otherwise
        """
        if module not in self.modules:
            print(f"Error: Module '{module}' not found")
            print(f"Available modules: {', '.join(self.modules)}")
            return False
        
        module_app_dir = os.path.join(self.root_dir, module, 'app')
        if not os.path.exists(module_app_dir):
            print(f"Error: Module app directory not found: {module_app_dir}")
            return False
        
        if not os.path.exists(self.mock_google_services):
            print(f"Error: Mock google-services.json not found: {self.mock_google_services}")
            return False
        
        dest_path = os.path.join(module_app_dir, 'google-services.json')
        try:
            import shutil
            shutil.copy(self.mock_google_services, dest_path)
            print(f"✓ Copied mock google-services.json to {module}/app/")
            return True
        except Exception as e:
            print(f"Error copying google-services.json: {e}")
            return False
    
    def setup_all(self):
        """Setup all modules by copying mock google-services.json to each."""
        print("Setting up all modules...")
        success_count = 0
        for module in self.modules:
            if self.setup_module(module):
                success_count += 1
        print(f"\nSetup complete: {success_count}/{len(self.modules)} modules configured")
    
    def build_module(self, module, tasks=None):
        """Build a specific module.
        
        Args:
            module: Name of the module to build
            tasks: List of Gradle tasks to run (default: ['assembleDebug'])
            
        Returns:
            True if build successful, False otherwise
        """
        if module not in self.modules:
            print(f"Error: Module '{module}' not found")
            return False
        
        if tasks is None:
            tasks = ['assembleDebug']
        
        # Ensure module is set up
        self.setup_module(module)
        
        # Build the module
        gradle_tasks = [f':{module}:app:{task}' for task in tasks]
        cmd = ['./gradlew'] + gradle_tasks
        
        print(f"Building module '{module}'...")
        print(f"Running: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, cwd=self.root_dir, check=True)
            print(f"✓ Module '{module}' built successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ Build failed for module '{module}': {e}")
            return False
    
    def test_module(self, module):
        """Run tests for a specific module.
        
        Args:
            module: Name of the module to test
            
        Returns:
            True if tests pass, False otherwise
        """
        return self.build_module(module, tasks=['testDebugUnitTest'])
    
    def clean(self):
        """Clean the entire project."""
        cmd = ['./gradlew', 'clean']
        print("Cleaning project...")
        try:
            subprocess.run(cmd, cwd=self.root_dir, check=True)
            print("✓ Project cleaned successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ Clean failed: {e}")
            return False
    
    def ktlint(self):
        """Run ktlint on the project."""
        cmd = ['./gradlew', 'ktlint']
        print("Running ktlint...")
        try:
            subprocess.run(cmd, cwd=self.root_dir, check=True)
            print("✓ Ktlint passed")
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ Ktlint failed: {e}")
            return False
    
    def check_dependencies(self):
        """Check for dependency updates."""
        cmd = ['./gradlew', 'dependencyUpdates']
        print("Checking for dependency updates...")
        try:
            subprocess.run(cmd, cwd=self.root_dir, check=True)
            print("✓ Dependency check complete")
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ Dependency check failed: {e}")
            return False
    
    def info(self):
        """Display project information."""
        print("\nFirebase Android Quickstart Project Info")
        print("=" * 50)
        print(f"Root Directory: {self.root_dir}")
        print(f"Total Modules: {len(self.modules)}")
        print(f"Modules: {', '.join(self.modules)}")
        
        # Check for gradle wrapper
        gradlew = os.path.join(self.root_dir, 'gradlew')
        if os.path.exists(gradlew):
            print(f"Gradle Wrapper: ✓ Found")
        else:
            print(f"Gradle Wrapper: ✗ Not found")
        
        # Check for mock google-services.json
        if os.path.exists(self.mock_google_services):
            print(f"Mock google-services.json: ✓ Found")
        else:
            print(f"Mock google-services.json: ✗ Not found")
        
        print("=" * 50)


def main():
    """Main entry point for the project management system."""
    parser = argparse.ArgumentParser(
        description='Firebase Android Quickstart Project Management System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all modules
  python project_management_system.py list
  
  # Setup all modules with mock google-services.json
  python project_management_system.py setup-all
  
  # Setup a specific module
  python project_management_system.py setup --module auth
  
  # Build a specific module
  python project_management_system.py build --module analytics
  
  # Run tests for a module
  python project_management_system.py test --module database
  
  # Clean the project
  python project_management_system.py clean
  
  # Run ktlint
  python project_management_system.py ktlint
  
  # Check for dependency updates
  python project_management_system.py check-deps
  
  # Display project information
  python project_management_system.py info
        """
    )
    
    parser.add_argument(
        'command',
        choices=['list', 'setup', 'setup-all', 'build', 'test', 'clean', 'ktlint', 'check-deps', 'info'],
        help='Command to execute'
    )
    parser.add_argument(
        '--module',
        help='Specific module to operate on'
    )
    
    args = parser.parse_args()
    
    # Initialize project manager
    pm = ProjectManager()
    
    # Execute command
    if args.command == 'list':
        pm.list_modules()
    elif args.command == 'setup':
        if not args.module:
            print("Error: --module is required for setup command")
            sys.exit(1)
        success = pm.setup_module(args.module)
        sys.exit(0 if success else 1)
    elif args.command == 'setup-all':
        pm.setup_all()
    elif args.command == 'build':
        if not args.module:
            print("Error: --module is required for build command")
            sys.exit(1)
        success = pm.build_module(args.module)
        sys.exit(0 if success else 1)
    elif args.command == 'test':
        if not args.module:
            print("Error: --module is required for test command")
            sys.exit(1)
        success = pm.test_module(args.module)
        sys.exit(0 if success else 1)
    elif args.command == 'clean':
        success = pm.clean()
        sys.exit(0 if success else 1)
    elif args.command == 'ktlint':
        success = pm.ktlint()
        sys.exit(0 if success else 1)
    elif args.command == 'check-deps':
        success = pm.check_dependencies()
        sys.exit(0 if success else 1)
    elif args.command == 'info':
        pm.info()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
