#!/usr/bin/env python3
"""
Standalone SimTool GUI that works without complex imports.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sys
import os
import subprocess
import threading
from pathlib import Path
import yaml
import json
from typing import List, Dict, Any, Optional

# Simple constants
DEFAULT_RTL_DIR = "rtl"
DEFAULT_TB_DIR = "tb"
DEFAULT_BUILD_DIR = "work"
DEFAULT_CONFIG_FILE = "simtool.cfg"


class PreferencesManager:
    """Manage user preferences for SimTool GUI."""
    
    def __init__(self):
        self.prefs_file = Path.home() / ".simtool_preferences.json"
        self.defaults = {
            "default_simulator": "verilator",
            "default_tb_type": "auto",
            "default_waves": True,
            "default_gui_waves": False,
            "default_verbose": False,
            "recent_projects": [],
            "max_recent_projects": 10,
            "default_editor": "code",  # VS Code
            "theme": "light",
            "window_geometry": "1200x800",
            "auto_load_last_project": True,
            "default_rtl_extensions": [".sv", ".v"],
            "default_tb_extensions": [".py", ".cpp", ".sv"],
        }
        self.preferences = self._load_preferences()
    
    def _load_preferences(self) -> dict:
        """Load preferences from file."""
        try:
            if self.prefs_file.exists():
                with open(self.prefs_file, 'r') as f:
                    prefs = json.load(f)
                # Merge with defaults to handle new preferences
                merged = self.defaults.copy()
                merged.update(prefs)
                return merged
            else:
                return self.defaults.copy()
        except Exception:
            return self.defaults.copy()
    
    def save_preferences(self):
        """Save preferences to file."""
        try:
            with open(self.prefs_file, 'w') as f:
                json.dump(self.preferences, f, indent=2)
        except Exception as e:
            pass  # Silently fail to save preferences
    
    def get(self, key: str, default=None):
        """Get preference value."""
        return self.preferences.get(key, default)
    
    def set(self, key: str, value):
        """Set preference value."""
        self.preferences[key] = value
    
    def add_recent_project(self, project_path: str):
        """Add project to recent projects list."""
        recent = self.preferences["recent_projects"]
        if project_path in recent:
            recent.remove(project_path)
        recent.insert(0, project_path)
        # Keep only max_recent_projects items
        self.preferences["recent_projects"] = recent[:self.preferences["max_recent_projects"]]
        self.save_preferences()
    
    def get_recent_projects(self) -> list:
        """Get list of recent projects that still exist."""
        recent = []
        for path in self.preferences["recent_projects"]:
            if Path(path).exists():
                recent.append(path)
        return recent


class SimpleProject:
    """Simplified project manager for GUI."""
    
    def __init__(self, project_path: Path = None):
        self.project_path = project_path or Path.cwd()
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load project configuration."""
        config_file = self.project_path / DEFAULT_CONFIG_FILE
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    return yaml.safe_load(f) or {}
            except Exception:
                pass
        return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            'default_simulator': 'verilator',
            'default_waves': True,
            'rtl_paths': ['rtl'],
            'tb_paths': ['tb'],
            'build_dir': 'work'
        }
    
    def get_rtl_files(self) -> List[Path]:
        """Get RTL files in project."""
        files = []
        for path_str in self.config.get('rtl_paths', ['rtl']):
            rtl_path = self.project_path / path_str
            if rtl_path.exists():
                files.extend(rtl_path.glob('*.sv'))
                files.extend(rtl_path.glob('*.v'))
        return files
    
    def get_tb_files(self) -> List[Path]:
        """Get testbench files."""
        files = []
        for path_str in self.config.get('tb_paths', ['tb']):
            tb_path = self.project_path / path_str
            if tb_path.exists():
                files.extend(tb_path.rglob('*.py'))
                files.extend(tb_path.rglob('*.sv'))
                files.extend(tb_path.rglob('*.cpp'))
        return files


class ModernTheme:
    """Theme manager for GUI."""
    
    LIGHT = {
        'bg': '#ffffff', 'fg': '#2d3748', 'select_bg': '#4299e1',
        'console_bg': '#f7fafc', 'console_fg': '#2d3748',
        'success': '#38a169', 'error': '#e53e3e', 'warning': '#dd6b20', 'info': '#3182ce'
    }
    
    DARK = {
        'bg': '#1a202c', 'fg': '#e2e8f0', 'select_bg': '#4299e1', 
        'console_bg': '#2d3748', 'console_fg': '#e2e8f0',
        'success': '#48bb78', 'error': '#f56565', 'warning': '#ed8936', 'info': '#63b3ed'
    }
    
    def __init__(self):
        self.is_dark = False
        self.current = self.LIGHT
    
    def toggle(self):
        self.is_dark = not self.is_dark
        self.current = self.DARK if self.is_dark else self.LIGHT
    
    def get(self, key: str) -> str:
        return self.current.get(key, '#000000')


class SimToolGUIStandalone:
    """Standalone SimTool GUI."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("SimTool - Hardware Simulation GUI")
        
        # Initialize preferences
        self.preferences = PreferencesManager()
        
        # Set window geometry from preferences
        geometry = self.preferences.get("window_geometry", "1200x800")
        self.root.geometry(geometry)
        
        # Initialize theme based on preferences
        theme_setting = self.preferences.get("theme", "light")
        self.theme = ModernTheme()
        if theme_setting == "dark":
            self.theme.toggle()
        
        self.project = None
        self.selected_files = set()
        self.file_checkboxes = {}
        
        self._create_gui()
        self._try_load_project()
    
    def _create_gui(self):
        """Create the GUI layout."""
        # Menu
        self._create_menu()
        
        # Toolbar
        self._create_toolbar()
        
        # Main layout
        self.main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel - File tree
        self._create_file_panel()
        
        # Right panel - Controls and console
        self._create_right_panel()
        
        # Status bar
        self._create_status_bar()
        
        # Apply theme
        self._apply_theme()
    
    def _create_menu(self):
        """Create menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Project...", command=self._new_project)
        file_menu.add_command(label="Open Project...", command=self._open_project)
        
        # Recent projects submenu
        recent_projects = self.preferences.get_recent_projects()
        if recent_projects:
            file_menu.add_separator()
            recent_menu = tk.Menu(file_menu, tearoff=0)
            file_menu.add_cascade(label="Recent Projects", menu=recent_menu)
            for project_path in recent_projects[:5]:  # Show up to 5 recent
                project_name = Path(project_path).name
                recent_menu.add_command(
                    label=project_name,
                    command=lambda p=project_path: self._load_project(Path(p))
                )
        
        file_menu.add_separator()
        file_menu.add_command(label="Preferences...", command=self._show_preferences)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Toggle Theme", command=self._toggle_theme)
        tools_menu.add_command(label="Check Installation", command=self._run_doctor)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)
    
    def _create_toolbar(self):
        """Create toolbar."""
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        ttk.Button(toolbar, text="Open Project", command=self._open_project).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="Refresh", command=self._refresh_project).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, fill=tk.Y)
        ttk.Button(toolbar, text="Compile", command=self._compile).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="Simulate", command=self._simulate).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="View Waves", command=self._view_waves).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="Clean", command=self._clean).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="Toggle Theme", command=self._toggle_theme).pack(side=tk.RIGHT)
    
    def _create_file_panel(self):
        """Create file browser panel with checkboxes."""
        left_frame = ttk.LabelFrame(self.main_paned, text="Project Files")
        self.main_paned.add(left_frame, weight=1)
        
        # Create scrollable frame for file checkboxes
        canvas = tk.Canvas(left_frame)
        scrollbar = ttk.Scrollbar(left_frame, orient="vertical", command=canvas.yview)
        self.file_selection_frame = ttk.Frame(canvas)
        
        self.file_selection_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.file_selection_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y")
        
        # Status at bottom
        status_frame = ttk.Frame(left_frame)
        status_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.selection_label = ttk.Label(status_frame, text="0 files selected")
        self.selection_label.pack()
        
    
    def _create_right_panel(self):
        """Create right panel with controls and console."""
        right_paned = ttk.PanedWindow(self.main_paned, orient=tk.VERTICAL)
        self.main_paned.add(right_paned, weight=2)
        
        # Control panel
        control_frame = ttk.LabelFrame(right_paned, text="Simulation Controls")
        right_paned.add(control_frame, weight=0)
        
        controls = ttk.Frame(control_frame)
        controls.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Top module
        top_frame = ttk.Frame(controls)
        top_frame.pack(fill=tk.X, pady=5)
        ttk.Label(top_frame, text="Top Module:").pack(side=tk.LEFT)
        self.top_module_var = tk.StringVar()
        self.top_combo = ttk.Combobox(top_frame, textvariable=self.top_module_var)
        self.top_combo.pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=True)
        
        # Simulator and options
        sim_frame = ttk.Frame(controls)
        sim_frame.pack(fill=tk.X, pady=5)
        ttk.Label(sim_frame, text="Simulator:").pack(side=tk.LEFT)
        self.sim_var = tk.StringVar(value=self.preferences.get("default_simulator", "verilator"))
        sim_combo = ttk.Combobox(sim_frame, textvariable=self.sim_var, width=12)
        sim_combo['values'] = ["verilator", "icarus", "questa"]
        sim_combo.pack(side=tk.LEFT, padx=(5, 0))
        
        ttk.Label(sim_frame, text="TB Type:").pack(side=tk.LEFT, padx=(20, 0))
        self.tb_var = tk.StringVar(value=self.preferences.get("default_tb_type", "auto"))
        tb_combo = ttk.Combobox(sim_frame, textvariable=self.tb_var, width=8)
        tb_combo['values'] = ["auto", "cocotb", "sv"]
        tb_combo.pack(side=tk.LEFT, padx=(5, 0))
        
        # Checkboxes
        options_frame = ttk.Frame(controls)
        options_frame.pack(fill=tk.X, pady=5)
        
        self.waves_var = tk.BooleanVar(value=self.preferences.get("default_waves", True))
        ttk.Checkbutton(options_frame, text="Generate Waves", variable=self.waves_var).pack(side=tk.LEFT)
        
        self.gui_var = tk.BooleanVar(value=self.preferences.get("default_gui_waves", False))
        ttk.Checkbutton(options_frame, text="Launch GTKWave", variable=self.gui_var).pack(side=tk.LEFT, padx=(20, 0))
        
        self.verbose_var = tk.BooleanVar(value=self.preferences.get("default_verbose", False))
        ttk.Checkbutton(options_frame, text="Verbose Output", variable=self.verbose_var).pack(side=tk.LEFT, padx=(20, 0))
        
        # Action buttons
        
        # Console
        console_frame = ttk.LabelFrame(right_paned, text="Console Output")
        right_paned.add(console_frame, weight=1)
        
        console_inner = ttk.Frame(console_frame)
        console_inner.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.console_text = tk.Text(console_inner, height=10, wrap=tk.WORD)
        console_scroll = ttk.Scrollbar(console_inner, orient=tk.VERTICAL, command=self.console_text.yview)
        self.console_text.configure(yscrollcommand=console_scroll.set)
        
        self.console_text.grid(row=0, column=0, sticky='nsew')
        console_scroll.grid(row=0, column=1, sticky='ns')
        
        console_inner.grid_rowconfigure(0, weight=1)
        console_inner.grid_columnconfigure(0, weight=1)
        
        # Configure text tags
        self.console_text.tag_config('success', foreground=self.theme.get('success'))
        self.console_text.tag_config('error', foreground=self.theme.get('error'))
        self.console_text.tag_config('warning', foreground=self.theme.get('warning'))
        self.console_text.tag_config('info', foreground=self.theme.get('info'))
        
        ttk.Button(console_frame, text="Clear Console", command=self._clear_console).pack(pady=5)
    
    def _create_status_bar(self):
        """Create status bar."""
        self.status_frame = ttk.Frame(self.root)
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_label = ttk.Label(self.status_frame, text="Ready")
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        self.project_label = ttk.Label(self.status_frame, text="No project")
        self.project_label.pack(side=tk.RIGHT, padx=5)
    
    def _apply_theme(self):
        """Apply current theme."""
        bg = self.theme.get('console_bg')
        fg = self.theme.get('console_fg')
        
        self.console_text.config(bg=bg, fg=fg)
        
        # Update tag colors
        self.console_text.tag_config('success', foreground=self.theme.get('success'))
        self.console_text.tag_config('error', foreground=self.theme.get('error'))
        self.console_text.tag_config('warning', foreground=self.theme.get('warning'))
        self.console_text.tag_config('info', foreground=self.theme.get('info'))
    
    def _toggle_theme(self):
        """Toggle between light and dark theme."""
        self.theme.toggle()
        self._apply_theme()
        theme_name = "dark" if self.theme.is_dark else "light"
        self._log_message(f"Switched to {theme_name} theme", "info")
    
    def _try_load_project(self):
        """Try to load project from current directory."""
        current_dir = Path.cwd()
        config_file = current_dir / DEFAULT_CONFIG_FILE
        
        if config_file.exists():
            self._log_message(f"Found SimTool project in: {current_dir}", "info")
            self._load_project(current_dir)
        else:
            # Don't auto-load projects - let user explicitly choose
            self._log_message("No project loaded. Use File > Open Project or File > New Project.", "info")
    
    def _load_project(self, project_path: Path):
        """Load project from path."""
        try:
            self.project = SimpleProject(project_path)
            self.project_label.config(text=f"Project: {project_path.name}")
            
            # Add to recent projects
            self.preferences.add_recent_project(str(project_path))
            
            self._refresh_file_selection()
            self._update_modules()
            
            self._log_message(f"Loaded project: {project_path}", "success")
            
        except Exception as e:
            self._log_message(f"Failed to load project: {e}", "error")
    
    def _new_project(self):
        """Create a new SimTool project."""
        dialog = NewProjectDialog(self.root, self.preferences)
        if dialog.result:
            project_path = Path(dialog.result["project_path"])
            try:
                # Create project directory structure (folders only)
                project_path.mkdir(exist_ok=True)
                (project_path / "rtl").mkdir(exist_ok=True)
                (project_path / "tb").mkdir(exist_ok=True)
                (project_path / "work").mkdir(exist_ok=True)
                (project_path / "scripts").mkdir(exist_ok=True)
                
                # Create minimal simtool.cfg
                config = {
                    "project_name": dialog.result["project_name"],
                    "rtl_paths": ["rtl"],
                    "tb_paths": ["tb"],
                    "build_dir": "work",
                    "default_simulator": dialog.result["simulator"],
                    "default_waves": dialog.result["waves"],
                }
                
                config_file = project_path / DEFAULT_CONFIG_FILE
                with open(config_file, 'w') as f:
                    yaml.dump(config, f, default_flow_style=False)
                
                # Load the new project
                self._load_project(project_path)
                self._log_message(f"Created new project: {project_path}", "success")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create project: {e}")
    
    def _show_preferences(self):
        """Show preferences dialog."""
        dialog = PreferencesDialog(self.root, self.preferences)
        if dialog.result_changed:
            # Apply theme change if needed
            if self.preferences.get("theme") != self.theme.current_theme():
                self._toggle_theme()
            
            # Update window geometry
            geometry = self.preferences.get("window_geometry", "1200x800")
            self.root.geometry(geometry)
            
            # Refresh menu to show recent projects
            self._refresh_menu()
    
    def _refresh_menu(self):
        """Refresh the menu bar."""
        # Clear current menu
        self.root.config(menu="")
        # Recreate menu
        self._create_menu()
    
    def _refresh_file_selection(self):
        """Refresh the file selection panel."""
        if not self.project:
            return
        
        # Clear checkbox panel
        for widget in self.file_selection_frame.winfo_children():
            widget.destroy()
        self.file_checkboxes.clear()
        self.selected_files.clear()
        
        # Create file selection section
        self._create_file_selection_section()
        
        # Update selection count
        self._update_selection_count()
    
    def _create_file_selection_section(self):
        """Create unified file selection section with checkboxes."""
        # Check if we have a project loaded
        if not self.project:
            # No project loaded, show message
            message_frame = ttk.Frame(self.file_selection_frame)
            message_frame.pack(fill=tk.BOTH, expand=True, pady=20)
            
            ttk.Label(message_frame, text="No Project Loaded", 
                     font=('TkDefaultFont', 12, 'bold')).pack(anchor=tk.CENTER)
            ttk.Label(message_frame, text="Use File > Open Project or File > New Project", 
                     font=('TkDefaultFont', 10)).pack(anchor=tk.CENTER, pady=5)
            return
        
        # Section header
        header_frame = ttk.Frame(self.file_selection_frame)
        header_frame.pack(fill=tk.X, pady=(10, 5))
        
        ttk.Label(header_frame, text="Select Files for Compilation", font=('TkDefaultFont', 11, 'bold')).pack(anchor=tk.W)
        
        # Single Select/Deselect all button
        button_frame = ttk.Frame(header_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(button_frame, text="Select All", 
                  command=self._select_all_files).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Clear All", 
                  command=self._clear_all_files).pack(side=tk.LEFT)
        
        # Group files by directory
        for dir_name, dir_label in [('rtl', 'RTL Files'), ('tb', 'Testbench Files')]:
            dir_path = self.project.project_path / dir_name
            if not dir_path.exists():
                continue
                
            # Collect compatible files from this directory
            compatible_files = []
            try:
                # First check if directory exists and is accessible
                if dir_path.exists() and dir_path.is_dir():
                    for file_path in sorted(dir_path.rglob('*')):
                        # Verify file actually exists and is a regular file
                        if file_path.exists() and file_path.is_file():
                            file_type = self._get_file_type(file_path)
                            # Only include compileable files
                            if file_type in ['rtl', 'python', 'cpp']:
                                compatible_files.append(file_path)
                else:
                    # Directory doesn't exist, skip
                    continue
            except (PermissionError, OSError) as e:
                # Log the error but continue
                pass  # Skip inaccessible directories
                continue
            
            # Only create section if there are compatible files
            if compatible_files:
                # Section header
                section_frame = ttk.Frame(self.file_selection_frame)
                section_frame.pack(fill=tk.X, pady=(10, 5))
                
                # Directory label
                ttk.Label(section_frame, text=dir_label, 
                         font=('TkDefaultFont', 10, 'bold')).pack(anchor=tk.W, padx=5)
                
                # Section controls
                controls_frame = ttk.Frame(section_frame)
                controls_frame.pack(fill=tk.X, padx=5, pady=2)
                
                ttk.Button(controls_frame, text=f"Select All {dir_label}", 
                          command=lambda d=dir_name: self._select_all_in_section(d)).pack(side=tk.LEFT, padx=(0, 5))
                ttk.Button(controls_frame, text=f"Clear {dir_label}", 
                          command=lambda d=dir_name: self._clear_all_in_section(d)).pack(side=tk.LEFT)
                
                # Files in this directory
                for file_path in compatible_files:
                    var = tk.BooleanVar()
                    
                    file_frame = ttk.Frame(self.file_selection_frame)
                    file_frame.pack(fill=tk.X, padx=20, pady=1)
                    
                    checkbox = ttk.Checkbutton(
                        file_frame, 
                        text=file_path.name,
                        variable=var,
                        command=lambda p=file_path, v=var: self._on_checkbox_toggle(p, v)
                    )
                    checkbox.pack(side=tk.LEFT)
                    
                    # Store checkbox info
                    self.file_checkboxes[file_path] = {
                        'var': var,
                        'widget': checkbox,
                        'section': dir_name,
                        'type': self._get_file_type(file_path)
                    }
    
    def _on_checkbox_toggle(self, file_path: Path, var: tk.BooleanVar):
        """Handle checkbox toggle."""
        if var.get():
            self.selected_files.add(file_path)
        else:
            self.selected_files.discard(file_path)
        
        self._update_selection_count()
    
    def _select_all_files(self):
        """Select all files for compilation."""
        for file_path, info in self.file_checkboxes.items():
            info['var'].set(True)
            self.selected_files.add(file_path)
        
        self._update_selection_count()
    
    def _clear_all_files(self):
        """Clear all file selections."""
        for file_path, info in self.file_checkboxes.items():
            info['var'].set(False)
            self.selected_files.discard(file_path)
        
        self._update_selection_count()
    
    def _select_all_in_section(self, section: str):
        """Select all files in a specific section."""
        for file_path, info in self.file_checkboxes.items():
            if info['section'] == section:
                info['var'].set(True)
                self.selected_files.add(file_path)
        
        self._update_selection_count()
    
    def _clear_all_in_section(self, section: str):
        """Clear all files in a specific section."""
        for file_path, info in self.file_checkboxes.items():
            if info['section'] == section:
                info['var'].set(False)
                self.selected_files.discard(file_path)
        
        self._update_selection_count()
    
    def _update_selection_count(self):
        """Update the selection count label."""
        count = len(self.selected_files)
        self.selection_label.config(text=f"{count} file{'s' if count != 1 else ''} selected")
    
    
    def _get_file_type(self, file_path: Path) -> str:
        """Get file type from extension."""
        suffix = file_path.suffix.lower()
        if suffix in ['.sv', '.v']:
            return 'rtl'
        elif suffix == '.py':
            return 'python'
        elif suffix in ['.cpp', '.c']:
            return 'cpp'
        elif suffix == '.cfg':
            return 'config'
        else:
            return 'file'
    
    def _update_modules(self):
        """Update top module dropdown with RTL and testbench modules."""
        if not self.project:
            return
            
        rtl_modules = []
        tb_modules = []
        
        # Extract modules from RTL files
        try:
            rtl_files = self.project.get_rtl_files()
            for file_path in rtl_files:
                rtl_modules.extend(self._extract_modules_from_file(file_path))
        except:
            pass
        
        # Extract modules from testbench files
        try:
            tb_files = self.project.get_tb_files()
            for file_path in tb_files:
                # Skip build directories
                if 'sim_build' in str(file_path):
                    continue
                    
                if file_path.suffix.lower() in ['.sv', '.v']:  # SystemVerilog testbenches
                    tb_modules.extend(self._extract_modules_from_file(file_path))
                elif file_path.suffix.lower() == '.py':  # Python testbenches  
                    tb_modules.extend(self._extract_python_modules(file_path))
                elif file_path.suffix.lower() == '.cpp':  # C++ testbenches
                    tb_modules.extend(self._extract_cpp_modules(file_path))
        except Exception as e:
            self._log_message(f"Error loading testbench modules: {e}", "error")
        
        # Combine all modules with indicators
        all_modules = []
        
        # Add RTL modules
        for module in sorted(set(rtl_modules)):
            all_modules.append(f"{module}")
        
        # Add testbench modules with [TB] indicator (show all, even duplicates)
        for module in sorted(set(tb_modules)):
            all_modules.append(f"{module} [TB]")
        
        self.top_combo['values'] = all_modules
        if all_modules:
            # Prefer testbench modules for simulation
            tb_candidates = [m for m in all_modules if '[TB]' in m]
            if tb_candidates:
                self.top_module_var.set(tb_candidates[0])
            else:
                self.top_module_var.set(all_modules[0])
    
    def _extract_modules_from_file(self, file_path: Path) -> list:
        """Extract module names from SystemVerilog/Verilog file."""
        modules = []
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                import re
                # Match module declarations (including testbench modules)
                matches = re.findall(r'module\s+(\w+)', content, re.IGNORECASE)
                modules.extend(matches)
                # Also look for interface declarations
                interface_matches = re.findall(r'interface\s+(\w+)', content, re.IGNORECASE)
                modules.extend(interface_matches)
        except:
            pass
        return modules
    
    def _extract_python_modules(self, file_path: Path) -> list:
        """Extract module names from Python testbench files."""
        modules = []
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                import re
                # Look for cocotb test decorators and dut instantiation
                if 'import cocotb' in content:
                    # Look for dut = or similar patterns
                    dut_matches = re.findall(r'dut\s*=.*?(\w+)\s*\(', content)
                    modules.extend(dut_matches)
                    
                    # Look for explicit DUT specification in comments
                    comment_matches = re.findall(r'#.*?(?:dut|module|top).*?[:\s](\w+)', content, re.IGNORECASE)
                    modules.extend(comment_matches)
                    
                    # Use filename as module name if no explicit DUT found
                    if not modules:
                        name = file_path.stem
                        if name.startswith('test_'):
                            module_name = name[5:]  # Remove 'test_' prefix
                            modules.append(module_name)
        except:
            pass
        return modules
    
    def _extract_cpp_modules(self, file_path: Path) -> list:
        """Extract top-level names from C++ testbench files."""
        modules = []
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                import re
                # Look for Verilator top module instantiations
                v_matches = re.findall(r'V(\w+)\s*\*?\s*\w+', content)
                modules.extend(v_matches)
                
                # Look for cocotb testbench patterns
                cocotb_matches = re.findall(r'dut\s*=\s*[\w\.]*(\w+)\(', content)
                modules.extend(cocotb_matches)
                
                # Look for explicit module names in comments or defines
                comment_matches = re.findall(r'//.*module[:\s]*(\w+)', content, re.IGNORECASE)
                modules.extend(comment_matches)
                
                # Look for #include patterns that might indicate module names
                include_matches = re.findall(r'#include\s*["\']V(\w+)\.h["\']', content)
                modules.extend(include_matches)
        except:
            pass
        return modules
    
    def _log_message(self, message: str, tag: str = None):
        """Add message to console."""
        self.console_text.config(state=tk.NORMAL)
        self.console_text.insert(tk.END, message + '\n', tag)
        self.console_text.see(tk.END)
        self.console_text.config(state=tk.DISABLED)
    
    def _clear_console(self):
        """Clear console output."""
        self.console_text.config(state=tk.NORMAL)
        self.console_text.delete(1.0, tk.END)
        self.console_text.config(state=tk.DISABLED)
    
    # Event handlers
    
    def _toggle_file_selection(self, item):
        """Toggle file selection for compilation."""
        values = self.file_tree.item(item)['values']
        if len(values) >= 1 and values[0] in ['rtl', 'python', 'cpp']:
            text = self.file_tree.item(item)['text']
            
            if item in self.selected_files:
                # Deselect file
                self.selected_files.remove(item)
                # Change [x] back to [ ]
                if text.startswith('[x] '):
                    new_text = '[ ] ' + text[4:]  # Remove [x] and add [ ]
                    self.file_tree.item(item, text=new_text)
                elif text.startswith('[x] '):
                    new_text = '[ ] ' + text[4:]  # Remove [x] and add [ ]
                    self.file_tree.item(item, text=new_text)
            else:
                # Select file
                self.selected_files.add(item)
                # Change [ ] to [x]
                if text.startswith('[ ] '):
                    new_text = '[x] ' + text[4:]  # Remove [ ] and add [x]
                    self.file_tree.item(item, text=new_text)
                elif not text.startswith('[x] '):
                    # Handle case where file doesn't have checkbox yet
                    filename = text.split()[-1]  # Get filename part
                    new_text = f'[x] {filename}'
                    self.file_tree.item(item, text=new_text)
            
            count = len(self.selected_files)
            self.selection_label.config(text=f"{count} files selected")
    
    def _select_all_rtl(self):
        """Select all RTL files."""
        for item in self._get_all_tree_items():
            values = self.file_tree.item(item)['values']
            if len(values) >= 1 and values[0] == 'rtl':
                if item not in self.selected_files:
                    self._toggle_file_selection(item)
    
    def _clear_selection(self):
        """Clear all file selections."""
        for item in list(self.selected_files):
            self._toggle_file_selection(item)
    
    def _get_all_tree_items(self):
        """Get all items in tree."""
        items = []
        def collect(parent=''):
            for item in self.file_tree.get_children(parent):
                items.append(item)
                collect(item)
        collect()
        return items
    
    def _open_in_editor(self, file_path: str):
        """Open file in external editor."""
        try:
            if sys.platform == "darwin":
                subprocess.run(["open", file_path])
            elif sys.platform == "win32":
                os.startfile(file_path)
            else:
                subprocess.run(["xdg-open", file_path])
            
            self._log_message(f"Opened {Path(file_path).name} in editor", "info")
        except Exception as e:
            self._log_message(f"Could not open file: {e}", "error")
    
    # Menu actions
    def _new_project(self):
        """Create new project."""
        directory = filedialog.askdirectory(title="Select directory for new project")
        if directory:
            try:
                project_path = Path(directory)
                
                # Create directories
                for dir_name in ['rtl', 'tb', 'work', 'scripts']:
                    (project_path / dir_name).mkdir(parents=True, exist_ok=True)
                
                # Create config
                config_content = """default_simulator: verilator
default_waves: true
rtl_paths: 
  - rtl
tb_paths:
  - tb
build_dir: work
include_paths: []
defines: {}"""
                
                with open(project_path / DEFAULT_CONFIG_FILE, 'w') as f:
                    f.write(config_content)
                
                self._load_project(project_path)
                self._log_message("New project created successfully", "success")
                
            except Exception as e:
                self._log_message(f"Failed to create project: {e}", "error")
    
    def _open_project(self):
        """Open existing project."""
        directory = filedialog.askdirectory(title="Select project directory")
        if directory:
            self._load_project(Path(directory))
    
    def _refresh_project(self):
        """Refresh current project."""
        if self.project:
            self._load_project(self.project.project_path)
    
    # Simulation actions
    def _compile(self):
        """Compile RTL files."""
        if not self.project or not self.top_module_var.get():
            messagebox.showwarning("Warning", "No project loaded or top module not specified")
            return
        
        def run_compile():
            try:
                # Get selected files from checkboxes
                selected_paths = [str(path) for path in self.selected_files]
                files_arg = " ".join(selected_paths) if selected_paths else "rtl/*.sv"
                top_module = self.top_module_var.get().replace(' [TB]', '')
                waves_flag = "--waves" if self.waves_var.get() else ""
                
                cmd = f"simtool vlog {files_arg} --top {top_module} {waves_flag}"
                
                self.root.after(0, lambda: self._log_message(f"> {cmd}", "info"))
                
                # Run command
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=self.project.project_path)
                
                if result.returncode == 0:
                    self.root.after(0, lambda: self._log_message("Compilation completed successfully", "success"))
                else:
                    self.root.after(0, lambda: self._log_message(f"Compilation failed: {result.stderr}", "error"))
                
            except Exception as e:
                self.root.after(0, lambda: self._log_message(f"Compilation error: {e}", "error"))
        
        self.status_label.config(text="Compiling...")
        threading.Thread(target=run_compile, daemon=True).start()
    
    def _simulate(self):
        """Run simulation."""
        if not self.project or not self.top_module_var.get():
            messagebox.showwarning("Warning", "No project loaded or top module not specified")
            return
        
        def run_sim():
            try:
                top_module = self.top_module_var.get().replace(' [TB]', '')
                waves_flag = "--waves" if self.waves_var.get() else ""
                gui_flag = "--gui" if self.gui_var.get() else ""
                
                cmd = f"simtool sim {top_module} {waves_flag} {gui_flag}".strip()
                
                self.root.after(0, lambda: self._log_message(f"> {cmd}", "info"))
                
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=self.project.project_path)
                
                if result.returncode == 0:
                    self.root.after(0, lambda: self._log_message("Simulation completed successfully", "success"))
                    if self.waves_var.get():
                        self.root.after(0, lambda: self._log_message("Waveform file generated", "info"))
                else:
                    self.root.after(0, lambda: self._log_message(f"Simulation failed: {result.stderr}", "error"))
                
            except Exception as e:
                self.root.after(0, lambda: self._log_message(f"Simulation error: {e}", "error"))
        
        self.status_label.config(text="Running simulation...")
        threading.Thread(target=run_sim, daemon=True).start()
    
    def _view_waves(self):
        """View waveforms."""
        if not self.project:
            return
        
        wave_files = list(self.project.project_path.glob('*.vcd')) + list(self.project.project_path.glob('*.fst'))
        
        if not wave_files:
            self._log_message("No waveform files found", "warning")
            return
        
        latest_file = max(wave_files, key=lambda f: f.stat().st_mtime)
        
        try:
            if sys.platform == "darwin":
                subprocess.run(["open", "-a", "GTKWave", str(latest_file)])
            else:
                subprocess.run(["gtkwave", str(latest_file)])
            
            self._log_message(f"Opened {latest_file.name} in GTKWave", "success")
        except Exception as e:
            self._log_message(f"Failed to open GTKWave: {e}", "error")
    
    def _clean(self):
        """Clean project."""
        if not self.project:
            return
        
        def run_clean():
            try:
                cmd = "simtool clean"
                self.root.after(0, lambda: self._log_message(f"> {cmd}", "info"))
                
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=self.project.project_path)
                
                if result.returncode == 0:
                    self.root.after(0, lambda: self._log_message("Clean completed successfully", "success"))
                    self.root.after(0, self._refresh_project)
                else:
                    self.root.after(0, lambda: self._log_message(f"Clean failed: {result.stderr}", "error"))
                
            except Exception as e:
                self.root.after(0, lambda: self._log_message(f"Clean error: {e}", "error"))
        
        threading.Thread(target=run_clean, daemon=True).start()
    
    def _run_doctor(self):
        """Run system diagnostics."""
        def run_diagnostics():
            try:
                cmd = "simtool doctor"
                self.root.after(0, lambda: self._log_message(f"> {cmd}", "info"))
                
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                
                if result.returncode == 0:
                    self.root.after(0, lambda: self._log_message("System check completed", "success"))
                    if result.stdout:
                        self.root.after(0, lambda: self._log_message(result.stdout, "info"))
                else:
                    self.root.after(0, lambda: self._log_message(f"System check issues: {result.stderr}", "warning"))
                
            except Exception as e:
                self.root.after(0, lambda: self._log_message(f"System check error: {e}", "error"))
        
        threading.Thread(target=run_diagnostics, daemon=True).start()
    
    def _show_about(self):
        """Show about dialog."""
        about_text = """SimTool GUI v1.0

A modern interface for hardware simulation that bridges
ModelSim workflows to open-source tools.

Features:
• Visual project management
• File selection for compilation
• One-click simulation workflow  
• Integrated waveform viewing
• Light/dark theme support

Built with Python and tkinter"""
        
        messagebox.showinfo("About SimTool", about_text)
    
    def run(self):
        """Run the application."""
        # Add welcome message
        self._log_message("Welcome to SimTool GUI!", "success")
        self._log_message("Load a project via File → Open Project or create a new one.", "info")
        
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.root.quit()


def main():
    """Launch the standalone GUI."""
    # Check tkinter
    try:
        import tkinter
    except ImportError:
        sys.stderr.write("Error: tkinter is not available\n")
        sys.stderr.write("Install with: brew install python-tk (macOS)\n")
        sys.exit(1)
    
    # Starting SimTool GUI
    
    try:
        app = SimToolGUIStandalone()
        app.run()
    except Exception as e:
        sys.stderr.write(f"Error starting GUI: {e}\n")
        sys.exit(1)


class NewProjectDialog:
    """Dialog for creating a new project."""
    
    def __init__(self, parent, preferences):
        self.result = None
        self.preferences = preferences
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("New SimTool Project")
        self.dialog.geometry("500x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (
            parent.winfo_rootx() + 50,
            parent.winfo_rooty() + 50
        ))
        
        self._create_dialog()
        
        # Wait for dialog to close
        parent.wait_window(self.dialog)
    
    def _create_dialog(self):
        """Create dialog contents."""
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Project name
        ttk.Label(main_frame, text="Project Name:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.name_var = tk.StringVar(value="my_project")
        ttk.Entry(main_frame, textvariable=self.name_var, width=40).grid(row=0, column=1, sticky=tk.W+tk.E, pady=5)
        
        # Project location
        ttk.Label(main_frame, text="Project Location:").grid(row=1, column=0, sticky=tk.W, pady=5)
        location_frame = ttk.Frame(main_frame)
        location_frame.grid(row=1, column=1, sticky=tk.W+tk.E, pady=5)
        
        self.location_var = tk.StringVar(value=str(Path.home() / "simtool_projects"))
        ttk.Entry(location_frame, textvariable=self.location_var, width=32).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(location_frame, text="Browse", command=self._browse_location).pack(side=tk.RIGHT, padx=(5, 0))
        
        # Simulator choice
        ttk.Label(main_frame, text="Default Simulator:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.simulator_var = tk.StringVar(value=self.preferences.get("default_simulator", "verilator"))
        simulator_combo = ttk.Combobox(main_frame, textvariable=self.simulator_var, 
                                     values=["verilator", "icarus", "questa"], state="readonly")
        simulator_combo.grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # Options
        ttk.Label(main_frame, text="Options:").grid(row=3, column=0, sticky=tk.W, pady=(15, 5))
        options_frame = ttk.Frame(main_frame)
        options_frame.grid(row=3, column=1, sticky=tk.W, pady=(15, 5))
        
        self.waves_var = tk.BooleanVar(value=self.preferences.get("default_waves", True))
        ttk.Checkbutton(options_frame, text="Generate waveforms by default", variable=self.waves_var).pack(anchor=tk.W)
        
        # Template selection
        ttk.Label(main_frame, text="Project Template:").grid(row=4, column=0, sticky=tk.W, pady=(15, 5))
        self.template_var = tk.StringVar(value="basic")
        template_combo = ttk.Combobox(main_frame, textvariable=self.template_var,
                                    values=["basic", "counter", "processor", "custom"], state="readonly")
        template_combo.grid(row=4, column=1, sticky=tk.W, pady=(15, 5))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=(30, 0))
        
        ttk.Button(button_frame, text="Create Project", command=self._create_project).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Cancel", command=self._cancel).pack(side=tk.RIGHT)
        
        # Configure grid weights
        main_frame.columnconfigure(1, weight=1)
    
    def _browse_location(self):
        """Browse for project location."""
        location = filedialog.askdirectory(title="Select Project Location", 
                                         initialdir=self.location_var.get())
        if location:
            self.location_var.set(location)
    
    def _create_project(self):
        """Create the project."""
        name = self.name_var.get().strip()
        location = self.location_var.get().strip()
        
        if not name:
            messagebox.showerror("Error", "Project name is required")
            return
        
        if not location:
            messagebox.showerror("Error", "Project location is required")
            return
        
        project_path = Path(location) / name
        
        if project_path.exists():
            if not messagebox.askyesno("Project Exists", 
                                     f"Directory {project_path} already exists. Continue anyway?"):
                return
        
        self.result = {
            "project_name": name,
            "project_path": str(project_path),
            "simulator": self.simulator_var.get(),
            "waves": self.waves_var.get(),
            "template": self.template_var.get()
        }
        
        self.dialog.destroy()
    
    def _cancel(self):
        """Cancel dialog."""
        self.dialog.destroy()


class PreferencesDialog:
    """Dialog for editing preferences."""
    
    def __init__(self, parent, preferences):
        self.preferences = preferences
        self.result_changed = False
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Preferences")
        self.dialog.geometry("600x500")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (
            parent.winfo_rootx() + 50,
            parent.winfo_rooty() + 50
        ))
        
        self._create_dialog()
        
        # Wait for dialog to close
        parent.wait_window(self.dialog)
    
    def _create_dialog(self):
        """Create dialog contents."""
        # Create notebook for tabs
        notebook = ttk.Notebook(self.dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # General tab
        general_frame = ttk.Frame(notebook)
        notebook.add(general_frame, text="General")
        self._create_general_tab(general_frame)
        
        # Simulation tab
        sim_frame = ttk.Frame(notebook)
        notebook.add(sim_frame, text="Simulation")
        self._create_simulation_tab(sim_frame)
        
        # Interface tab
        interface_frame = ttk.Frame(notebook)
        notebook.add(interface_frame, text="Interface")
        self._create_interface_tab(interface_frame)
        
        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        ttk.Button(button_frame, text="OK", command=self._save_preferences).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Cancel", command=self._cancel).pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="Reset to Defaults", command=self._reset_defaults).pack(side=tk.LEFT)
    
    def _create_general_tab(self, parent):
        """Create general preferences tab."""
        # Default editor
        ttk.Label(parent, text="Default Editor:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.editor_var = tk.StringVar(value=self.preferences.get("default_editor", "code"))
        editor_combo = ttk.Combobox(parent, textvariable=self.editor_var,
                                  values=["code", "vim", "nano", "gedit", "subl"], width=20)
        editor_combo.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # Theme
        ttk.Label(parent, text="Theme:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.theme_var = tk.StringVar(value=self.preferences.get("theme", "light"))
        theme_combo = ttk.Combobox(parent, textvariable=self.theme_var,
                                 values=["light", "dark"], state="readonly", width=20)
        theme_combo.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Auto-load last project
        self.auto_load_var = tk.BooleanVar(value=self.preferences.get("auto_load_last_project", True))
        ttk.Checkbutton(parent, text="Auto-load last project on startup", 
                       variable=self.auto_load_var).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Max recent projects
        ttk.Label(parent, text="Max Recent Projects:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.max_recent_var = tk.IntVar(value=self.preferences.get("max_recent_projects", 10))
        ttk.Spinbox(parent, from_=5, to=20, textvariable=self.max_recent_var, width=10).grid(row=3, column=1, sticky=tk.W, pady=5)
    
    def _create_simulation_tab(self, parent):
        """Create simulation preferences tab."""
        # Default simulator
        ttk.Label(parent, text="Default Simulator:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.simulator_var = tk.StringVar(value=self.preferences.get("default_simulator", "verilator"))
        sim_combo = ttk.Combobox(parent, textvariable=self.simulator_var,
                               values=["verilator", "icarus", "questa"], state="readonly", width=20)
        sim_combo.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # Default testbench type
        ttk.Label(parent, text="Default TB Type:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.tb_type_var = tk.StringVar(value=self.preferences.get("default_tb_type", "auto"))
        tb_combo = ttk.Combobox(parent, textvariable=self.tb_type_var,
                              values=["auto", "cocotb", "sv"], state="readonly", width=20)
        tb_combo.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Default options
        self.waves_var = tk.BooleanVar(value=self.preferences.get("default_waves", True))
        ttk.Checkbutton(parent, text="Generate waveforms by default", 
                       variable=self.waves_var).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        self.gui_waves_var = tk.BooleanVar(value=self.preferences.get("default_gui_waves", False))
        ttk.Checkbutton(parent, text="Launch GTKWave automatically", 
                       variable=self.gui_waves_var).grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        self.verbose_var = tk.BooleanVar(value=self.preferences.get("default_verbose", False))
        ttk.Checkbutton(parent, text="Verbose output by default", 
                       variable=self.verbose_var).grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=5)
    
    def _create_interface_tab(self, parent):
        """Create interface preferences tab."""
        # Window size
        ttk.Label(parent, text="Default Window Size:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.geometry_var = tk.StringVar(value=self.preferences.get("window_geometry", "1200x800"))
        geometry_combo = ttk.Combobox(parent, textvariable=self.geometry_var,
                                    values=["1200x800", "1400x900", "1600x1000", "1920x1080"], width=20)
        geometry_combo.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # File extensions
        ttk.Label(parent, text="RTL Extensions:").grid(row=1, column=0, sticky=tk.W, pady=5)
        rtl_exts = ", ".join(self.preferences.get("default_rtl_extensions", [".sv", ".v"]))
        self.rtl_ext_var = tk.StringVar(value=rtl_exts)
        ttk.Entry(parent, textvariable=self.rtl_ext_var, width=30).grid(row=1, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(parent, text="TB Extensions:").grid(row=2, column=0, sticky=tk.W, pady=5)
        tb_exts = ", ".join(self.preferences.get("default_tb_extensions", [".py", ".cpp", ".sv"]))
        self.tb_ext_var = tk.StringVar(value=tb_exts)
        ttk.Entry(parent, textvariable=self.tb_ext_var, width=30).grid(row=2, column=1, sticky=tk.W, pady=5)
    
    def _save_preferences(self):
        """Save preferences."""
        try:
            # Save all preferences
            self.preferences.set("default_editor", self.editor_var.get())
            self.preferences.set("theme", self.theme_var.get())
            self.preferences.set("auto_load_last_project", self.auto_load_var.get())
            self.preferences.set("max_recent_projects", self.max_recent_var.get())
            self.preferences.set("default_simulator", self.simulator_var.get())
            self.preferences.set("default_tb_type", self.tb_type_var.get())
            self.preferences.set("default_waves", self.waves_var.get())
            self.preferences.set("default_gui_waves", self.gui_waves_var.get())
            self.preferences.set("default_verbose", self.verbose_var.get())
            self.preferences.set("window_geometry", self.geometry_var.get())
            
            # Parse extensions
            rtl_exts = [ext.strip() for ext in self.rtl_ext_var.get().split(",") if ext.strip()]
            tb_exts = [ext.strip() for ext in self.tb_ext_var.get().split(",") if ext.strip()]
            self.preferences.set("default_rtl_extensions", rtl_exts)
            self.preferences.set("default_tb_extensions", tb_exts)
            
            self.preferences.save_preferences()
            self.result_changed = True
            self.dialog.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save preferences: {e}")
    
    def _reset_defaults(self):
        """Reset to default values."""
        if messagebox.askyesno("Reset Preferences", 
                             "Reset all preferences to defaults? This cannot be undone."):
            # Reset to defaults
            defaults = PreferencesManager().defaults
            for key, value in defaults.items():
                self.preferences.set(key, value)
            
            # Update dialog fields
            self.editor_var.set(defaults["default_editor"])
            self.theme_var.set(defaults["theme"])
            self.auto_load_var.set(defaults["auto_load_last_project"])
            self.max_recent_var.set(defaults["max_recent_projects"])
            self.simulator_var.set(defaults["default_simulator"])
            self.tb_type_var.set(defaults["default_tb_type"])
            self.waves_var.set(defaults["default_waves"])
            self.gui_waves_var.set(defaults["default_gui_waves"])
            self.verbose_var.set(defaults["default_verbose"])
            self.geometry_var.set(defaults["window_geometry"])
            
            rtl_exts = ", ".join(defaults["default_rtl_extensions"])
            tb_exts = ", ".join(defaults["default_tb_extensions"])
            self.rtl_ext_var.set(rtl_exts)
            self.tb_ext_var.set(tb_exts)
    
    def _cancel(self):
        """Cancel dialog."""
        self.dialog.destroy()


if __name__ == '__main__':
    main()