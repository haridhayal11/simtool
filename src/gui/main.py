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
            "theme": "system",
            "window_geometry": "1200x800",
            "auto_load_last_project": True,
            "default_rtl_extensions": [".sv", ".v"],
            "default_tb_extensions": [".py", ".cpp", ".sv"],
            "default_sim_time": "100us",
            "last_selected_files": {},  # project_path -> [file_paths]
            "last_top_modules": {},     # project_path -> top_module
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
    
    def save_project_state(self, project_path: str, selected_files: list, top_module: str, sim_time: str = None):
        """Save project-specific state."""
        self.preferences["last_selected_files"][project_path] = [str(f) for f in selected_files]
        if top_module:
            self.preferences["last_top_modules"][project_path] = top_module
        if sim_time:
            if "last_sim_times" not in self.preferences:
                self.preferences["last_sim_times"] = {}
            self.preferences["last_sim_times"][project_path] = sim_time
        self.save_preferences()
    
    def get_project_state(self, project_path: str) -> tuple:
        """Get project-specific state."""
        selected_files = self.preferences["last_selected_files"].get(project_path, [])
        top_module = self.preferences["last_top_modules"].get(project_path, "")
        sim_time = self.preferences.get("last_sim_times", {}).get(project_path, "")
        return selected_files, top_module, sim_time
    
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


class DesignSystem:
    """Comprehensive design system for visual cohesion."""
    
    # Design tokens
    SPACING = {
        'xs': 4, 's': 8, 'm': 16, 'l': 24, 'xl': 32, 'xxl': 48
    }
    
    TYPOGRAPHY = {
        'title': ('TkDefaultFont', 16, 'bold'),
        'subtitle': ('TkDefaultFont', 12, 'bold'), 
        'body': ('TkDefaultFont', 10, 'normal'),
        'caption': ('TkDefaultFont', 9, 'normal'),
        'mono': ('Monaco' if sys.platform == 'darwin' else 'Consolas', 10, 'normal')
    }
    
    
    
    def __init__(self):
        self.use_system_theme = True
        self._available_colors = self._detect_available_colors()
        self._setup_ttk_styles()
    
    def _detect_available_colors(self):
        """Detect system colors with platform-specific dark mode support."""
        import tkinter as tk
        import sys
        import os
        
        # On macOS, use semantic colors that adapt to dark mode
        if sys.platform == 'darwin':
            return {
                'bg_default': 'systemWindowBackgroundColor',
                'window_bg': 'systemTextBackgroundColor',
                'text_default': 'systemTextColor',
                'window_text': 'systemTextColor', 
                'disabled_text': 'systemDisabledControlTextColor',
                'highlight': 'systemSelectedContentBackgroundColor',
                'shadow': 'systemSeparatorColor'
            }
        
        # For Linux and other platforms
        available = {}
        
        # Try to detect Linux dark theme preference
        dark_mode = self._detect_linux_dark_mode()
        
        if dark_mode:
            # Dark theme fallbacks for Linux
            color_tests = {
                'bg_default': ['SystemButtonFace', '#2d2d2d'],
                'window_bg': ['SystemWindow', '#1e1e1e'],
                'text_default': ['SystemButtonText', '#ffffff'],
                'window_text': ['SystemWindowText', '#ffffff'],
                'disabled_text': ['SystemGrayText', '#888888'],
                'highlight': ['SystemHighlight', '#0078d4'],
                'shadow': ['SystemButtonShadow', '#555555']
            }
        else:
            # Light theme fallbacks
            color_tests = {
                'bg_default': ['SystemButtonFace', '#f0f0f0'],
                'window_bg': ['SystemWindow', '#ffffff'],
                'text_default': ['SystemButtonText', '#000000'],
                'window_text': ['SystemWindowText', '#000000'],
                'disabled_text': ['SystemGrayText', '#808080'],
                'highlight': ['SystemHighlight', '#0078d4'],
                'shadow': ['SystemButtonShadow', '#c0c0c0']
            }
        
        try:
            temp_root = tk.Tk()
            temp_root.withdraw()
            
            for key, color_list in color_tests.items():
                for color in color_list:
                    try:
                        temp_root.configure(bg=color)
                        available[key] = color
                        break
                    except tk.TclError:
                        continue
                if key not in available:
                    available[key] = color_list[-1]
            
            temp_root.destroy()
        except:
            # Ultimate fallback based on detected theme
            if dark_mode:
                available = {
                    'bg_default': '#2d2d2d',
                    'window_bg': '#1e1e1e',
                    'text_default': '#ffffff', 
                    'window_text': '#ffffff',
                    'disabled_text': '#888888',
                    'highlight': '#0078d4',
                    'shadow': '#555555'
                }
            else:
                available = {
                    'bg_default': '#f0f0f0',
                    'window_bg': '#ffffff',
                    'text_default': '#000000', 
                    'window_text': '#000000',
                    'disabled_text': '#808080',
                    'highlight': '#0078d4',
                    'shadow': '#c0c0c0'
                }
        
        return available
    
    def _detect_linux_dark_mode(self):
        """Try to detect if Linux system is using dark theme."""
        import os
        import subprocess
        
        try:
            # Check GNOME dark theme preference
            if 'GNOME_DESKTOP_SESSION_ID' in os.environ or 'GNOME' in os.environ.get('XDG_CURRENT_DESKTOP', ''):
                try:
                    result = subprocess.run(['gsettings', 'get', 'org.gnome.desktop.interface', 'gtk-theme'], 
                                          capture_output=True, text=True, timeout=2)
                    if result.returncode == 0:
                        theme_name = result.stdout.strip().strip("'\"")
                        if any(dark_word in theme_name.lower() for dark_word in ['dark', 'adwaita-dark']):
                            return True
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    pass
            
            # Check KDE dark theme preference
            if 'KDE' in os.environ.get('XDG_CURRENT_DESKTOP', '') or 'PLASMA' in os.environ.get('XDG_CURRENT_DESKTOP', ''):
                try:
                    # Check for dark color scheme in KDE
                    kde_config_path = os.path.expanduser('~/.config/kdeglobals')
                    if os.path.exists(kde_config_path):
                        with open(kde_config_path, 'r') as f:
                            content = f.read()
                            if 'ColorScheme=Breeze Dark' in content or 'ColorScheme=BreezeDark' in content:
                                return True
                except:
                    pass
            
            # Check for common dark theme environment variables
            if os.environ.get('GTK_THEME', '').lower().find('dark') != -1:
                return True
            
        except:
            pass
        
        return False  # Default to light theme if detection fails
    
    def toggle_theme(self):
        # Theme toggle is now disabled - only system native theme supported
        pass
    
    def get_color(self, key: str) -> str:
        # Map UI color roles to detected system colors
        color_mapping = {
            # Background colors
            'bg_primary': 'bg_default',
            'bg_secondary': 'window_bg',
            'bg_tertiary': 'bg_default',
            'surface': 'window_bg',
            'surface_hover': 'bg_default',
            'console_bg': 'window_bg',
            
            # Text colors
            'fg_primary': 'text_default', 
            'fg_secondary': 'window_text',
            'fg_tertiary': 'disabled_text',
            'console_fg': 'window_text',
            
            # Interactive colors
            'accent_primary': 'highlight',
            'accent_hover': 'highlight',
            'accent_active': 'highlight',
            
            # Borders
            'border': 'shadow',
            'border_focus': 'highlight',
            'shadow': 'shadow'
        }
        
        # Status colors - always use these for semantic meaning
        status_colors = {
            'success': '#008000',
            'error': '#FF0000', 
            'warning': '#FFA500',
            'info': '#0000FF'
        }
        
        if key in status_colors:
            return status_colors[key]
        
        mapped_key = color_mapping.get(key)
        if mapped_key and mapped_key in self._available_colors:
            return self._available_colors[mapped_key]
        
        return self._available_colors.get('bg_default', '#f0f0f0')
    
    def get_spacing(self, size: str) -> int:
        return self.SPACING.get(size, 8)
    
    def get_font(self, style: str) -> tuple:
        return self.TYPOGRAPHY.get(style, ('TkDefaultFont', 10, 'normal'))
    
    def _setup_ttk_styles(self):
        """Configure ttk styles for visual cohesion."""
        try:
            import tkinter.ttk as ttk
            style = ttk.Style()
            
            # Configure general ttk styles
            style.configure('Card.TFrame', 
                          background=self.get_color('surface'),
                          relief='flat',
                          borderwidth=1)
            
            style.configure('Toolbar.TFrame',
                          background=self.get_color('bg_secondary'),
                          relief='flat')
            
            style.configure('Primary.TButton',
                          background=self.get_color('accent_primary'),
                          foreground='white',
                          borderwidth=0,
                          focuscolor='none')
            
            style.map('Primary.TButton',
                    background=[('active', self.get_color('accent_hover'))])
                    
        except Exception:
            pass  # Fallback if ttk styling fails


class SimToolGUIStandalone:
    """Standalone SimTool GUI."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("SimTool - Hardware Simulation GUI")
        
        # Set application name and class (fixes "python" showing in dock/taskbar)
        try:
            # Try to set the window class name for better application identification
            if hasattr(self.root, 'wm_class'):
                self.root.wm_class("SimTool", "SimTool")
            # Set application name on macOS
            try:
                self.root.tk.call('tk', 'appname', 'SimTool')
            except tk.TclError:
                pass  # Not supported on this platform
        except Exception:
            pass  # Fallback gracefully if not supported
        
        # Set window icon
        self._set_window_icon()
        
        # Initialize preferences
        self.preferences = PreferencesManager()
        
        # Set window geometry from preferences
        geometry = self.preferences.get("window_geometry", "1200x800")
        self.root.geometry(geometry)
        
        # Initialize design system (system native theme)
        self.design = DesignSystem()
        
        self.project = None
        self.selected_files = set()
        self.file_checkboxes = {}
        self.current_process = None  # Track running processes
        self.has_unsaved_changes = False  # Track unsaved project state
        
        self._create_gui()
        self._try_load_project()
    
    def _create_gui(self):
        """Create the GUI layout with proper visual hierarchy."""
        # Configure root window with design system
        self.root.configure(bg=self.design.get_color('bg_primary'))
        
        # Menu
        self._create_menu()
        
        # Main container with proper padding
        main_container = tk.Frame(self.root, bg=self.design.get_color('bg_primary'))
        main_container.pack(fill=tk.BOTH, expand=True, 
                           padx=self.design.get_spacing('m'), 
                           pady=self.design.get_spacing('s'))
        
        # Toolbar card
        toolbar_card = tk.Frame(main_container,
                               bg=self.design.get_color('bg_primary'),
                               relief='solid',
                               borderwidth=1,
                               bd=1)
        toolbar_card.pack(fill=tk.X, pady=(0, self.design.get_spacing('s')))
        
        # Toolbar content with padding - match main background
        toolbar_content = tk.Frame(toolbar_card, bg=self.design.get_color('bg_primary'))
        toolbar_content.pack(fill=tk.X, padx=self.design.get_spacing('m'),
                           pady=self.design.get_spacing('s'))
        
        self._create_toolbar(toolbar_content)
        
        # Content area with visual separation
        content_container = tk.Frame(main_container, bg=self.design.get_color('bg_primary'))
        content_container.pack(fill=tk.BOTH, expand=True, pady=(self.design.get_spacing('m'), 0))
        
        # Create paned window with custom styling
        paned_container = tk.Frame(content_container, bg=self.design.get_color('bg_primary'))
        paned_container.pack(fill=tk.BOTH, expand=True)
        
        # Manual layout instead of PanedWindow for better control
        self._create_manual_layout(paned_container)
        
        # Status bar
        self._create_status_bar()
        
        # Apply design system
        self._apply_design_system()
        self._update_project_controls_state()
        
        # Force styling after GUI loads
        self.root.after(100, self._apply_design_system)
    
    def _create_manual_layout(self, container):
        """Create manual layout for better visual control."""
        # Left panel (Project Files) - 30% width
        self.left_panel = tk.Frame(container, bg=self.design.get_color('bg_primary'))
        self.left_panel.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, self.design.get_spacing('s')))
        
        # Right panel container - 70% width  
        self.right_container = tk.Frame(container, bg=self.design.get_color('bg_primary'))
        self.right_container.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Create panels
        self._create_file_panel_new(self.left_panel)
        self._create_right_panel_new(self.right_container)
    
    def _create_menu(self):
        """Create menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Project...", command=self._new_project)
        file_menu.add_command(label="Open Project...", command=self._open_project)
        file_menu.add_separator()
        file_menu.add_command(label="Save Project State", command=self._save_project_state, accelerator="Ctrl+S")
        
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
        file_menu.add_command(label="Exit", command=self._exit_application)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Check Installation", command=self._run_doctor)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)
        
        # Keyboard bindings
        self.root.bind_all("<Control-s>", lambda e: self._save_project_state())
    
    def _create_toolbar(self, toolbar):
        """Create toolbar with improved action grouping and primary actions."""
        
        # Primary actions group - transparent to match toolbar
        primary_group = tk.Frame(toolbar)
        primary_group.pack(side=tk.LEFT)
        
        self.open_btn = self._create_modern_button(primary_group, "Open", self._open_project, 
                                                  style="primary")
        self.open_btn.pack(side=tk.LEFT, padx=(0, self.design.get_spacing('xs')))
        
        self.new_btn = self._create_modern_button(primary_group, "New Project", self._new_project,
                                                 style="secondary")
        self.new_btn.pack(side=tk.LEFT, padx=(0, self.design.get_spacing('s')))
        
        # Separator
        sep1 = tk.Frame(toolbar, width=1, bg=self.design.get_color('border'))
        sep1.pack(side=tk.LEFT, fill=tk.Y, padx=self.design.get_spacing('s'))
        
        # Build & Run group - transparent to match toolbar
        build_group = tk.Frame(toolbar)
        build_group.pack(side=tk.LEFT)
        
        self.compile_btn = self._create_modern_button(build_group, "Compile", self._compile, 
                                                     state=tk.DISABLED, style="action")
        self.compile_btn.pack(side=tk.LEFT, padx=(0, self.design.get_spacing('xs')))
        
        self.simulate_btn = self._create_modern_button(build_group, "Simulate", self._simulate, 
                                                      state=tk.DISABLED, style="action")
        self.simulate_btn.pack(side=tk.LEFT, padx=(0, self.design.get_spacing('xs')))
        
        self.stop_button = self._create_modern_button(build_group, "Stop", self._stop_process, 
                                                     state=tk.DISABLED, style="danger")
        self.stop_button.pack(side=tk.LEFT, padx=(0, self.design.get_spacing('s')))
        
        # Separator
        sep2 = tk.Frame(toolbar, width=1, bg=self.design.get_color('border'))
        sep2.pack(side=tk.LEFT, fill=tk.Y, padx=self.design.get_spacing('s'))
        
        # Tools group - transparent to match toolbar
        tools_group = tk.Frame(toolbar)
        tools_group.pack(side=tk.LEFT)
        
        self.waves_btn = self._create_modern_button(tools_group, "Waveforms", self._view_waves,
                                                   state=tk.DISABLED, style="tool")
        self.waves_btn.pack(side=tk.LEFT, padx=(0, self.design.get_spacing('xs')))
        
        self.clean_btn = self._create_modern_button(tools_group, "Clean", self._clean,
                                                   state=tk.DISABLED, style="tool")
        self.clean_btn.pack(side=tk.LEFT, padx=(0, self.design.get_spacing('xs')))
        
        
        # Store buttons for enabling/disabling
        self.project_buttons = [self.compile_btn, self.simulate_btn, self.waves_btn, self.clean_btn]
    
    def _create_modern_button(self, parent, text, command, style="secondary", state=tk.NORMAL):
        """Create a native OS button with ttk styling."""
        # Initialize modern buttons list if it doesn't exist
        if not hasattr(self, 'modern_buttons'):
            self.modern_buttons = []
        
        # Create native TTK button - automatically uses OS styling
        btn = ttk.Button(parent,
                        text=text,
                        command=command,
                        state=state)
        
        # Store button reference for potential future customization
        button_info = {
            'button': btn,
            'style': style,
            'original_command': command
        }
        self.modern_buttons.append(button_info)
        
        return btn
    
    def _create_toolbar_button(self, parent, text, command, bg=None, fg=None, state=tk.NORMAL, primary=False):
        """Create a styled toolbar button."""
        if bg is None:
            bg = self.design.get_color('bg_tertiary')
        if fg is None:
            fg = self.design.get_color('fg_primary')
            
        btn = tk.Button(parent,
                       text=text,
                       command=command,
                       bg=bg,
                       fg=fg,
                       relief='flat',
                       borderwidth=0,
                       padx=self.design.get_spacing('m'),
                       pady=self.design.get_spacing('s'),
                       font=self.design.get_font('body'),
                       cursor='hand2' if state == tk.NORMAL else 'arrow',
                       state=state)
        
        # Add hover effects
        def on_enter(e):
            if btn['state'] != tk.DISABLED:
                btn.configure(bg=self.design.get_color('accent_hover') if primary else self.design.get_color('surface_hover'))
        
        def on_leave(e):
            if btn['state'] != tk.DISABLED:
                btn.configure(bg=bg)
        
        btn.bind('<Enter>', on_enter)
        btn.bind('<Leave>', on_leave)
        
        return btn
    
    def _create_file_panel_new(self, container):
        """Create visually distinct file panel with proper card design."""
        # Main card with shadow effect
        card = tk.Frame(container,
                       bg=self.design.get_color('bg_primary'),
                       relief='solid',
                       borderwidth=1,
                       bd=1)
        card.pack(fill=tk.BOTH, expand=True)
        
        # Card header with background
        header = tk.Frame(card, 
                         bg=self.design.get_color('bg_primary'),
                         height=40)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        # Title in header
        title_label = tk.Label(header,
                              text="Project Files",
                              font=self.design.get_font('subtitle'),
                              bg=self.design.get_color('bg_primary'),
                              fg=self.design.get_color('fg_primary'))
        title_label.pack(side=tk.LEFT, padx=self.design.get_spacing('m'), pady=self.design.get_spacing('s'))
        
        # Content area with scrolling
        content_frame = tk.Frame(card, bg=self.design.get_color('bg_primary'))
        content_frame.pack(fill=tk.BOTH, expand=True, padx=self.design.get_spacing('s'), 
                          pady=self.design.get_spacing('s'))
        
        # Create scrollable frame for file checkboxes
        canvas = tk.Canvas(content_frame, bg=self.design.get_color('bg_primary'),
                          highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(content_frame, orient="vertical", command=canvas.yview)
        self.file_selection_frame = tk.Frame(canvas, bg=self.design.get_color('bg_primary'))
        
        self.file_selection_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.file_selection_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Status footer
        footer = tk.Frame(card, bg=self.design.get_color('bg_primary'))
        footer.pack(fill=tk.X)
        
        self.selection_label = tk.Label(footer,
                                       text="0 files selected",
                                       font=self.design.get_font('caption'),
                                       bg=self.design.get_color('bg_primary'),
                                       fg=self.design.get_color('fg_secondary'))
        self.selection_label.pack(padx=self.design.get_spacing('m'), 
                                 pady=self.design.get_spacing('s'))
    
    def _create_right_panel_new(self, container):
        """Create right panel with distinct visual sections."""
        # Controls card at top
        controls_card = tk.Frame(container,
                                bg=self.design.get_color('bg_primary'),
                                relief='solid',
                                borderwidth=1,
                                bd=1)
        controls_card.pack(fill=tk.X, pady=(0, self.design.get_spacing('m')))
        
        # Controls header
        controls_header = tk.Frame(controls_card, 
                                  bg=self.design.get_color('bg_primary'))
        controls_header.pack(fill=tk.X)
        
        tk.Label(controls_header,
                text="Simulation Controls",
                font=self.design.get_font('subtitle'),
                bg=self.design.get_color('bg_primary'),
                fg=self.design.get_color('fg_primary')).pack(side=tk.LEFT,
                                                             padx=self.design.get_spacing('m'),
                                                             pady=self.design.get_spacing('s'))
        
        # Controls content
        controls_content = tk.Frame(controls_card, bg=self.design.get_color('bg_primary'))
        controls_content.pack(fill=tk.X, padx=self.design.get_spacing('m'), 
                             pady=self.design.get_spacing('m'))
        
        self._create_simulation_controls_new(controls_content)
        
        # Console card - takes remaining space
        console_card = tk.Frame(container,
                               bg=self.design.get_color('bg_primary'),
                               relief='solid',
                               borderwidth=1,
                               bd=1)
        console_card.pack(fill=tk.BOTH, expand=True)
        
        # Console header
        console_header = tk.Frame(console_card,
                                 bg=self.design.get_color('bg_primary'))
        console_header.pack(fill=tk.X)
        
        tk.Label(console_header,
                text="Console Output",
                font=self.design.get_font('subtitle'),
                bg=self.design.get_color('bg_primary'),
                fg=self.design.get_color('fg_primary')).pack(side=tk.LEFT,
                                                             padx=self.design.get_spacing('m'),
                                                             pady=self.design.get_spacing('s'))
        
        # Console content
        console_content = tk.Frame(console_card, bg=self.design.get_color('bg_primary'))
        console_content.pack(fill=tk.BOTH, expand=True, 
                           padx=self.design.get_spacing('s'),
                           pady=self.design.get_spacing('s'))
        
        self._create_console_area_new(console_content)
    
    def _create_simulation_controls_new(self, parent):
        """Create simulation controls with proper spacing and styling."""
        controls = parent
        
        # Top module
        top_frame = tk.Frame(controls, bg=self.design.get_color('bg_primary'))
        top_frame.pack(fill=tk.X, pady=(0, self.design.get_spacing('m')))
        
        tk.Label(top_frame, text="Top Module:", 
                font=self.design.get_font('body'),
                bg=self.design.get_color('bg_primary'),
                fg=self.design.get_color('fg_primary')).pack(side=tk.LEFT)
        
        self.top_module_var = tk.StringVar()
        self.top_combo = ttk.Combobox(top_frame, textvariable=self.top_module_var, width=25)
        self.top_combo.pack(side=tk.LEFT, padx=(self.design.get_spacing('m'), 0), fill=tk.X, expand=True)
        self.top_module_var.trace_add('write', self._on_top_module_change)
        
        # Simulator and TB type
        sim_frame = tk.Frame(controls, bg=self.design.get_color('bg_primary'))
        sim_frame.pack(fill=tk.X, pady=(0, self.design.get_spacing('m')))
        
        # Simulator
        tk.Label(sim_frame, text="Simulator:", 
                font=self.design.get_font('body'),
                bg=self.design.get_color('bg_primary'),
                fg=self.design.get_color('fg_primary')).pack(side=tk.LEFT)
        
        self.sim_var = tk.StringVar(value=self.preferences.get("default_simulator", "verilator"))
        sim_combo = ttk.Combobox(sim_frame, textvariable=self.sim_var, width=12, state="readonly")
        sim_combo['values'] = ["verilator", "icarus", "questa"]
        sim_combo.pack(side=tk.LEFT, padx=(self.design.get_spacing('m'), self.design.get_spacing('xl')))
        
        # TB Type
        tk.Label(sim_frame, text="TB Type:", 
                font=self.design.get_font('body'),
                bg=self.design.get_color('bg_primary'),
                fg=self.design.get_color('fg_primary')).pack(side=tk.LEFT)
        
        self.tb_var = tk.StringVar(value=self.preferences.get("default_tb_type", "auto"))
        tb_combo = ttk.Combobox(sim_frame, textvariable=self.tb_var, width=8, state="readonly")
        tb_combo['values'] = ["auto", "cocotb", "sv"]
        tb_combo.pack(side=tk.LEFT, padx=(self.design.get_spacing('m'), 0))
        
        # Options checkboxes
        options_frame = tk.Frame(controls, bg=self.design.get_color('bg_primary'))
        options_frame.pack(fill=tk.X, pady=(0, self.design.get_spacing('m')))
        
        self.waves_var = tk.BooleanVar(value=self.preferences.get("default_waves", True))
        waves_cb = tk.Checkbutton(options_frame, text="Generate Waves", variable=self.waves_var,
                                 bg=self.design.get_color('bg_primary'),
                                 fg=self.design.get_color('fg_primary'),
                                 activebackground=self.design.get_color('surface'),
                                 font=self.design.get_font('body'))
        waves_cb.pack(side=tk.LEFT, padx=(0, self.design.get_spacing('xl')))
        
        self.gui_var = tk.BooleanVar(value=self.preferences.get("default_gui_waves", False))
        gui_cb = tk.Checkbutton(options_frame, text="Launch GTKWave", variable=self.gui_var,
                               bg=self.design.get_color('bg_primary'),
                               fg=self.design.get_color('fg_primary'),
                               activebackground=self.design.get_color('surface'),
                               font=self.design.get_font('body'))
        gui_cb.pack(side=tk.LEFT)
        
        # Simulation time
        time_frame = tk.Frame(controls, bg=self.design.get_color('bg_primary'))
        time_frame.pack(fill=tk.X)
        
        tk.Label(time_frame, text="Simulation Time:", 
                font=self.design.get_font('body'),
                bg=self.design.get_color('bg_primary'),
                fg=self.design.get_color('fg_primary')).pack(side=tk.LEFT)
        
        # Quick presets
        preset_frame = tk.Frame(time_frame, bg=self.design.get_color('bg_primary'))
        preset_frame.pack(side=tk.LEFT, padx=(self.design.get_spacing('m'), 0))
        
        self.sim_time_var = tk.StringVar(value=self.preferences.get("default_sim_time", "100us"))
        self.sim_time_var.trace_add('write', lambda *args: self._mark_unsaved())
        
        presets = ["100ns", "1us", "10us"]
        self.preset_buttons = []  # Store for theme updates
        for i, preset in enumerate(presets):
            btn = ttk.Button(preset_frame, text=preset, 
                           command=lambda p=preset: self._set_sim_time_preset(p))
            btn.pack(side=tk.LEFT, padx=(0, 4))
            self.preset_buttons.append(btn)
        
        # Custom time entry
        time_entry = tk.Entry(time_frame, textvariable=self.sim_time_var, width=12,
                             bg=self.design.get_color('bg_primary'),
                             fg=self.design.get_color('fg_primary'),
                             relief='solid',
                             borderwidth=1)
        time_entry.pack(side=tk.LEFT, padx=(self.design.get_spacing('m'), self.design.get_spacing('s')))
        
        tk.Label(time_frame, text="(e.g., 1000ns, 10us, 1ms)", 
                font=self.design.get_font('caption'),
                bg=self.design.get_color('bg_primary'),
                fg=self.design.get_color('fg_tertiary')).pack(side=tk.LEFT)
    
    def _create_console_area_new(self, parent):
        """Create console area with proper styling."""
        # Console text with scrollbar
        self.console_text = tk.Text(parent, height=15, wrap=tk.WORD,
                                   bg=self.design.get_color('bg_primary'),
                                   fg=self.design.get_color('console_fg'),
                                   font=self.design.get_font('mono'),
                                   relief='flat',
                                   borderwidth=0,
                                   highlightthickness=0,
                                   selectbackground=self.design.get_color('accent_primary'))
        
        console_scroll = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.console_text.yview)
        self.console_text.configure(yscrollcommand=console_scroll.set)
        
        self.console_text.pack(side="left", fill="both", expand=True)
        console_scroll.pack(side="right", fill="y")
        
        # Console controls at bottom
        controls_frame = tk.Frame(parent.master, bg=self.design.get_color('bg_primary'))
        controls_frame.pack(fill=tk.X, padx=self.design.get_spacing('s'), 
                           pady=(self.design.get_spacing('s'), self.design.get_spacing('s')))
        
        self.clear_console_btn = ttk.Button(controls_frame,
                                          text="Clear Console",
                                          command=self._clear_console)
        self.clear_console_btn.pack(side=tk.RIGHT)
    
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
        # Save state when top module changes
        self.top_module_var.trace_add('write', self._on_top_module_change)
        
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
        
        # Simulation time control
        sim_time_frame = ttk.Frame(controls)
        sim_time_frame.pack(fill=tk.X, pady=5)
        ttk.Label(sim_time_frame, text="Simulation Time:").pack(side=tk.LEFT)
        self.sim_time_var = tk.StringVar(value=self.preferences.get("default_sim_time", "100us"))
        self.sim_time_var.trace_add('write', lambda *args: self._mark_unsaved())
        ttk.Entry(sim_time_frame, textvariable=self.sim_time_var, width=12).pack(side=tk.LEFT, padx=(5, 0))
        ttk.Label(sim_time_frame, text="(e.g., 1000ns, 10us, 1ms)").pack(side=tk.LEFT, padx=(5, 0))
        
        # Verbose option removed - always show output now
        
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
        
        # Configure text tags - will be set in _apply_theme()
        
        ttk.Button(console_frame, text="Clear Console", command=self._clear_console).pack(pady=5)
    
    def _create_status_bar(self):
        """Create status bar with design system styling."""
        self.status_frame = tk.Frame(self.root, 
                                    bg=self.design.get_color('bg_primary'),
                                    relief='solid',
                                    borderwidth=1,
                                    bd=1)
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        # Status with color-coded indicator
        status_container = tk.Frame(self.status_frame, bg=self.design.get_color('bg_primary'))
        status_container.pack(side=tk.LEFT, padx=self.design.get_spacing('m'), 
                             pady=self.design.get_spacing('s'))
        
        self.status_indicator = tk.Label(status_container, 
                                        text="●", 
                                        font=('TkDefaultFont', 12),
                                        bg=self.design.get_color('bg_primary'))
        self.status_indicator.pack(side=tk.LEFT, padx=(0, self.design.get_spacing('s')))
        
        self.status_label = tk.Label(status_container, 
                                   text="Ready",
                                   font=self.design.get_font('body'),
                                   bg=self.design.get_color('bg_primary'),
                                   fg=self.design.get_color('fg_primary'))
        self.status_label.pack(side=tk.LEFT)
        
        # Project info on right
        self.project_label = tk.Label(self.status_frame, 
                                     text="No project",
                                     font=self.design.get_font('body'),
                                     bg=self.design.get_color('bg_primary'),
                                     fg=self.design.get_color('fg_secondary'))
        self.project_label.pack(side=tk.RIGHT, 
                               padx=self.design.get_spacing('m'),
                               pady=self.design.get_spacing('s'))
        
        # Set initial status
        self._update_status("ready")
    
    def _apply_design_system(self):
        """Apply comprehensive design system styling."""
        # Configure root window
        try:
            self.root.configure(bg=self.design.get_color('bg_primary'))
        except tk.TclError:
            pass
        
        # Apply console styling with design system
        if hasattr(self, 'console_text'):
            bg = self.design.get_color('console_bg')
            fg = self.design.get_color('console_fg')
            
            self.console_text.config(
                bg=bg,
                fg=fg, 
                insertbackground=fg,
                font=self.design.get_font('mono'),
                relief='flat',
                borderwidth=0,
                highlightthickness=0,
                selectbackground=self.design.get_color('accent_primary'),
                selectforeground='white'
            )
            
            # Update console tag colors
            self.console_text.tag_config('success', foreground=self.design.get_color('success'))
            self.console_text.tag_config('error', foreground=self.design.get_color('error'))
            self.console_text.tag_config('warning', foreground=self.design.get_color('warning'))
            self.console_text.tag_config('info', foreground=self.design.get_color('info'))
        
        # Apply status bar styling
        if hasattr(self, 'status_frame'):
            self.status_frame.configure(bg=self.design.get_color('bg_primary'))
            
            # Update status container and labels
            for widget in self.status_frame.winfo_children():
                if isinstance(widget, tk.Frame):
                    widget.configure(bg=self.design.get_color('bg_primary'))
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Label):
                            child.configure(bg=self.design.get_color('bg_primary'))
                elif isinstance(widget, tk.Label):
                    widget.configure(bg=self.design.get_color('bg_primary'))
        
        # Native TTK buttons automatically use OS styling - no custom theming needed
        
        # Toolbar buttons also use native styling now - no custom theming needed
        
        # Native TTK buttons handle theming automatically
        
        # Apply consistent theming to all Entry widgets
        self._theme_all_entry_widgets()
        
        # Apply consistent theming to all Label widgets
        self._theme_all_label_widgets()
    
    def _theme_all_entry_widgets(self):
        """Apply consistent theming to all Entry widgets in the application."""
        def theme_entry_recursive(widget):
            for child in widget.winfo_children():
                if isinstance(child, tk.Entry):
                    try:
                        child.configure(
                            bg=self.design.get_color('bg_primary'),
                            fg=self.design.get_color('fg_primary'),
                            insertbackground=self.design.get_color('fg_primary'),
                            relief='solid',
                            borderwidth=1,
                            highlightthickness=1,
                            highlightcolor=self.design.get_color('accent_primary'),
                            highlightbackground=self.design.get_color('border')
                        )
                    except (tk.TclError, AttributeError):
                        # Skip widgets that don't support these options
                        pass
                elif hasattr(child, 'winfo_children'):
                    theme_entry_recursive(child)
        
        theme_entry_recursive(self.root)
    
    def _theme_all_label_widgets(self):
        """Apply consistent theming to all Label widgets in the application."""
        def theme_label_recursive(widget):
            for child in widget.winfo_children():
                if isinstance(child, tk.Label):
                    try:
                        # Skip labels that are already properly themed (like status labels)
                        current_bg = child.cget('bg')
                        if current_bg in ['SystemButtonFace', '', 'white', 'gray90']:  # Default/unthemed colors
                            # Get parent background safely
                            try:
                                parent_bg = widget.cget('bg')
                            except (tk.TclError, AttributeError):
                                parent_bg = self.design.get_color('bg_primary')
                            
                            child.configure(
                                bg=parent_bg,
                                fg=self.design.get_color('fg_primary')
                            )
                    except (tk.TclError, AttributeError):
                        # Skip widgets that don't support these options
                        pass
                elif hasattr(child, 'winfo_children'):
                    theme_label_recursive(child)
        
        theme_label_recursive(self.root)
    
    def _update_all_modern_button_themes(self):
        """Update all modern buttons to use current theme colors."""
        if not hasattr(self, 'modern_buttons'):
            return
        
        # Define button style mappings using current theme colors
        button_styles = {
            "primary": {
                "bg": self.design.get_color('accent_primary'),  # Accent color for primary actions
                "fg": "#ffffff",                                # Pure white text
                "hover_bg": self.design.get_color('accent_hover'),
                "active_bg": self.design.get_color('accent_active')
            },
            "secondary": {
                "bg": self.design.get_color('bg_tertiary'),     # High contrast background
                "fg": self.design.get_color('fg_primary'),      # Pure white text
                "hover_bg": self.design.get_color('surface_hover'),
                "active_bg": "#606060"
            },
            "action": {
                "bg": "#22c55e",                                # Green - semantic color
                "fg": "#ffffff",                                # Pure white text
                "hover_bg": "#16a34a",
                "active_bg": "#15803d"
            },
            "danger": {
                "bg": "#ef4444",                                # Red - semantic color
                "fg": "#ffffff",                                # Pure white text
                "hover_bg": "#dc2626",
                "active_bg": "#b91c1c"
            },
            "tool": {
                "bg": "#3b82f6",                                # Blue - semantic color
                "fg": "#ffffff",                                # Pure white text
                "hover_bg": "#2563eb",
                "active_bg": "#1d4ed8"
            },
            "subtle": {
                "bg": self.design.get_color('bg_tertiary'),     # High contrast background
                "fg": self.design.get_color('fg_primary'),      # Pure white text
                "hover_bg": self.design.get_color('surface_hover'),
                "active_bg": self.design.get_color('surface')
            }
        }
        
        # Update each button
        for button_info in self.modern_buttons:
            try:
                btn = button_info['button']
                style = button_info['style']
                style_config = button_styles.get(style, button_styles["secondary"])
                
                # Update button colors
                btn.configure(
                    bg=style_config["bg"],
                    fg=style_config["fg"],
                    activebackground=style_config.get("hover_bg", style_config["bg"]),
                    activeforeground=style_config["fg"]
                )
                
                # Recreate hover effects with current colors
                self._update_button_hover_effects(btn, style_config)
                
            except (tk.TclError, KeyError):
                # Skip buttons that no longer exist or have issues
                pass
    
    def _update_button_hover_effects(self, btn, style_config):
        """Update button hover effects with current theme colors."""
        try:
            # Unbind old events
            btn.unbind('<Enter>')
            btn.unbind('<Leave>')
            btn.unbind('<Button-1>')
            btn.unbind('<ButtonRelease-1>')
            
            # Rebind with current colors
            original_bg = style_config["bg"]
            original_fg = "#ffffff"  # Always use pure white for enabled buttons 
            hover_bg = style_config["hover_bg"]
            
            def on_enter(e):
                btn.configure(bg=hover_bg, fg=original_fg)
            
            def on_leave(e):
                btn.configure(bg=original_bg, fg=original_fg)
                
            def on_press(e):
                btn.configure(bg=style_config["active_bg"], fg=original_fg)
                
            def on_release(e):
                current_bg = hover_bg if btn.winfo_containing(btn.winfo_pointerx(), btn.winfo_pointery()) == btn else original_bg
                btn.configure(bg=current_bg, fg=original_fg)
            
            btn.bind('<Enter>', on_enter)
            btn.bind('<Leave>', on_leave)
            btn.bind('<Button-1>', on_press)
            btn.bind('<ButtonRelease-1>', on_release)
            
        except (tk.TclError, AttributeError):
            # Skip buttons that don't support hover effects
            pass
    
    def _update_toolbar_button_themes(self):
        """Update toolbar button themes to match high-contrast design system."""
        # Define high-contrast button style mappings
        button_styles = {
            "primary": {
                "bg": self.design.get_color('accent_primary'), 
                "fg": "#ffffff",        # Pure white text
                "activebackground": self.design.get_color('accent_hover'),
                "activeforeground": "#ffffff"
            },
            "secondary": {
                "bg": self.design.get_color('bg_tertiary'),
                "fg": self.design.get_color('fg_primary'),
                "activebackground": self.design.get_color('surface_hover'),
                "activeforeground": self.design.get_color('fg_primary')
            },
            "action": {
                "bg": "#22c55e",        # Green semantic color
                "fg": "#ffffff",        # Pure white text
                "activebackground": "#16a34a",
                "activeforeground": "#ffffff"
            },
            "danger": {
                "bg": "#ef4444",        # Red semantic color
                "fg": "#ffffff",        # Pure white text
                "activebackground": "#dc2626",
                "activeforeground": "#ffffff"
            },
            "tool": {
                "bg": "#3b82f6",        # Blue semantic color
                "fg": "#ffffff",        # Pure white text
                "activebackground": "#2563eb",
                "activeforeground": "#ffffff"
            }
        }
        
        # Update primary actions
        if hasattr(self, 'open_btn'):
            style = button_styles["primary"]
            self.open_btn.configure(bg=style["bg"], fg=style["fg"], 
                                  activebackground=style["activebackground"], 
                                  activeforeground=style["activeforeground"])
        
        if hasattr(self, 'new_btn'):
            style = button_styles["secondary"]
            self.new_btn.configure(bg=style["bg"], fg=style["fg"], 
                                 activebackground=style["activebackground"], 
                                 activeforeground=style["activeforeground"])
        
        # Update build & run group
        if hasattr(self, 'compile_btn'):
            style = button_styles["action"]
            self.compile_btn.configure(bg=style["bg"], fg=style["fg"], 
                                     activebackground=style["activebackground"], 
                                     activeforeground=style["activeforeground"])
        
        if hasattr(self, 'simulate_btn'):
            style = button_styles["action"]
            self.simulate_btn.configure(bg=style["bg"], fg=style["fg"], 
                                      activebackground=style["activebackground"], 
                                      activeforeground=style["activeforeground"])
        
        if hasattr(self, 'stop_button'):
            style = button_styles["danger"]
            self.stop_button.configure(bg=style["bg"], fg=style["fg"], 
                                     activebackground=style["activebackground"], 
                                     activeforeground=style["activeforeground"])
        
        # Update tools group
        if hasattr(self, 'waves_btn'):
            style = button_styles["tool"]
            self.waves_btn.configure(bg=style["bg"], fg=style["fg"], 
                                   activebackground=style["activebackground"], 
                                   activeforeground=style["activeforeground"])
        
        if hasattr(self, 'clean_btn'):
            style = button_styles["tool"]
            self.clean_btn.configure(bg=style["bg"], fg=style["fg"], 
                                   activebackground=style["activebackground"], 
                                   activeforeground=style["activeforeground"])
    
    
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
            
            # Restore previous selections
            self._restore_project_state()
            
            # Update top modules based on any restored file selections
            self._update_top_modules_from_selected_files()
            
            # Mark as saved (freshly loaded project has no unsaved changes)
            self.has_unsaved_changes = False
            self._update_window_title()
            
            self._log_message(f"Loaded project: {project_path}", "success")
            self._update_status("ready")
            self._update_project_controls_state()
            
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
        """Create unified file selection section with improved empty state."""
        # Check if we have a project loaded
        if not self.project:
            # No project loaded, show improved empty state
            message_frame = ttk.Frame(self.file_selection_frame)
            message_frame.pack(fill=tk.BOTH, expand=True, pady=40)
            
            # Empty state card with unified styling
            card_frame = tk.Frame(message_frame,
                                 bg=self.design.get_color('bg_primary'),
                                 relief='solid',
                                 borderwidth=1,
                                 bd=1)
            card_frame.pack(anchor=tk.CENTER, padx=self.design.get_spacing('xl'),
                           pady=self.design.get_spacing('xl'))
            
            # Card content with proper spacing
            card_content = tk.Frame(card_frame, bg=self.design.get_color('bg_primary'))
            card_content.pack(padx=self.design.get_spacing('xl'), 
                             pady=self.design.get_spacing('xl'))
            
            # Welcome title
            welcome_label = tk.Label(card_content,
                                   text="Welcome to SimTool",
                                   font=self.design.get_font('title'),
                                   bg=self.design.get_color('bg_primary'),
                                   fg=self.design.get_color('fg_primary'))
            welcome_label.pack(pady=(0, self.design.get_spacing('m')))
            
            # Description
            desc_label = tk.Label(card_content,
                                text="No project yet — Create a new project or open an existing one.",
                                font=self.design.get_font('body'),
                                bg=self.design.get_color('bg_primary'),
                                fg=self.design.get_color('fg_secondary'),
                                wraplength=350,
                                justify=tk.CENTER)
            desc_label.pack(pady=(0, self.design.get_spacing('l')))
            
            # Action buttons with proper styling
            btn_frame = tk.Frame(card_content, bg=self.design.get_color('bg_primary'))
            btn_frame.pack(pady=(0, self.design.get_spacing('m')))
            
            # Primary button
            new_btn = tk.Button(btn_frame,
                               text="New Project…",
                               command=self._new_project,
                               bg=self.design.get_color('accent_primary'),
                               fg='white',
                               relief='flat',
                               padx=self.design.get_spacing('l'),
                               pady=self.design.get_spacing('s'),
                               font=self.design.get_font('body'),
                               cursor='hand2')
            new_btn.pack(side=tk.LEFT, padx=(0, self.design.get_spacing('m')))
            
            # Secondary button
            open_btn = tk.Button(btn_frame,
                                text="Open…",
                                command=self._open_project,
                                bg=self.design.get_color('bg_primary'),
                                fg=self.design.get_color('fg_primary'),
                                relief='flat',
                                padx=self.design.get_spacing('l'),
                                pady=self.design.get_spacing('s'),
                                font=self.design.get_font('body'),
                                cursor='hand2')
            open_btn.pack(side=tk.LEFT)
            
            # Helpful tip
            tip_label = tk.Label(card_content,
                               text="Tip: You can also drag project folders here",
                               font=self.design.get_font('caption'),
                               bg=self.design.get_color('bg_primary'),
                               fg=self.design.get_color('fg_tertiary'))
            tip_label.pack()
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
        # Update top module dropdown to only show modules from selected files
        self._update_top_modules_from_selected_files()
        # Mark as unsaved when selections change
        self._mark_unsaved()
    
    def _on_top_module_change(self, *args):
        """Handle top module selection change."""
        # Mark as unsaved when top module changes
        self._mark_unsaved()
    
    def _select_all_files(self):
        """Select all files for compilation."""
        for file_path, info in self.file_checkboxes.items():
            info['var'].set(True)
            self.selected_files.add(file_path)
        
        self._update_selection_count()
        self._update_top_modules_from_selected_files()
        self._mark_unsaved()
    
    def _clear_all_files(self):
        """Clear all file selections."""
        for file_path, info in self.file_checkboxes.items():
            info['var'].set(False)
            self.selected_files.discard(file_path)
        
        self._update_selection_count()
        self._update_top_modules_from_selected_files()
        self._mark_unsaved()
    
    
    def _update_selection_count(self):
        """Update the selection count label."""
        count = len(self.selected_files)
        self.selection_label.config(text=f"{count} file{'s' if count != 1 else ''} selected")
    
    def _restore_project_state(self):
        """Restore previously selected files and top module for this project."""
        if not self.project:
            return
        
        project_path = str(self.project.project_path)
        selected_files, top_module, sim_time = self.preferences.get_project_state(project_path)
        
        # Restore selected files
        if selected_files:
            for file_path_str in selected_files:
                file_path = Path(file_path_str)
                if file_path in self.file_checkboxes:
                    self.file_checkboxes[file_path]['var'].set(True)
                    self.selected_files.add(file_path)
            self._update_selection_count()
        
        # Restore top module
        if top_module and hasattr(self, 'top_combo'):
            # Check if the module is still in the list
            if top_module in self.top_combo['values']:
                self.top_module_var.set(top_module)
        
        # Restore simulation time
        if sim_time and hasattr(self, 'sim_time_var'):
            self.sim_time_var.set(sim_time)
    
    def _save_project_state(self):
        """Save current project state."""
        if not self.project:
            return
        
        project_path = str(self.project.project_path)
        selected_files = list(self.selected_files)
        top_module = self.top_module_var.get() if hasattr(self, 'top_module_var') else ""
        sim_time = self.sim_time_var.get() if hasattr(self, 'sim_time_var') else ""
        
        self.preferences.save_project_state(project_path, selected_files, top_module, sim_time)
        # Mark as saved
        self.has_unsaved_changes = False
        self._update_window_title()
        self._log_message("Project state saved", "success")
    
    def _mark_unsaved(self):
        """Mark project state as having unsaved changes."""
        if not self.has_unsaved_changes:
            self.has_unsaved_changes = True
            self._update_window_title()
    
    def _update_window_title(self):
        """Update window title to show project name and unsaved state."""
        base_title = "SimTool - Hardware Simulation GUI"
        if self.project:
            project_name = self.project.project_path.name
            if self.has_unsaved_changes:
                title = f"{base_title} - {project_name} *"
            else:
                title = f"{base_title} - {project_name}"
        else:
            title = base_title
        self.root.title(title)
    
    def _check_unsaved_changes(self) -> bool:
        """Check if there are unsaved changes and prompt user. Returns True if should continue."""
        if not self.has_unsaved_changes:
            return True
        
        result = messagebox.askyesnocancel(
            "Unsaved Changes",
            "You have unsaved changes to your project state.\n\nDo you want to save them before continuing?"
        )
        
        if result is True:  # Yes - save and continue
            self._save_project_state()
            return True
        elif result is False:  # No - discard changes and continue
            return True
        else:  # Cancel - don't continue
            return False
    
    def _exit_application(self):
        """Exit application with unsaved changes check."""
        if self._check_unsaved_changes():
            # Save theme preference (system native)
            self.preferences.set("theme", "system")
            self.preferences.save_preferences()
            self.root.quit()
    
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
        """Update top module dropdown with RTL and testbench modules from ALL project files."""
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
            # Only set default if no previous selection exists
            if not self.top_module_var.get():
                # Prefer testbench modules for simulation
                tb_candidates = [m for m in all_modules if '[TB]' in m]
                if tb_candidates:
                    self.top_module_var.set(tb_candidates[0])
                else:
                    self.top_module_var.set(all_modules[0])
    
    def _update_top_modules_from_selected_files(self):
        """Update top module dropdown to only show modules from selected files."""
        if not self.project or not hasattr(self, 'top_combo'):
            return
        
        # Get current selection to preserve if still valid
        current_selection = self.top_module_var.get()
        
        rtl_modules = []
        tb_modules = []
        
        # Extract modules only from selected files
        for file_path in self.selected_files:
            try:
                if file_path.suffix.lower() in ['.sv', '.v']:  # SystemVerilog files
                    modules = self._extract_modules_from_file(file_path)
                    # Determine if it's RTL or TB based on file location or content
                    if 'tb' in str(file_path).lower() or any('_tb' in m.lower() or 'test' in m.lower() for m in modules):
                        tb_modules.extend(modules)
                    else:
                        rtl_modules.extend(modules)
                elif file_path.suffix.lower() == '.py':  # Python testbenches
                    tb_modules.extend(self._extract_python_modules(file_path))
                elif file_path.suffix.lower() in ['.cpp', '.c']:  # C++ testbenches
                    tb_modules.extend(self._extract_cpp_modules(file_path))
            except Exception:
                pass  # Skip files that can't be parsed
        
        # Combine modules from selected files only
        available_modules = []
        
        # Add RTL modules
        for module in sorted(set(rtl_modules)):
            available_modules.append(f"{module}")
        
        # Add testbench modules with [TB] indicator
        for module in sorted(set(tb_modules)):
            available_modules.append(f"{module} [TB]")
        
        # Update dropdown
        self.top_combo['values'] = available_modules
        
        # Handle current selection
        if available_modules:
            if current_selection in available_modules:
                # Keep current selection if still valid
                self.top_module_var.set(current_selection)
            else:
                # Select a new default - prefer testbench modules
                tb_candidates = [m for m in available_modules if '[TB]' in m]
                if tb_candidates:
                    self.top_module_var.set(tb_candidates[0])
                else:
                    self.top_module_var.set(available_modules[0])
        else:
            # No modules available from selected files
            if self.selected_files:
                # Files selected but no modules found
                self.top_module_var.set("<No modules in selected files>")
                self.top_combo['values'] = ["<No modules in selected files>"]
            else:
                # No files selected
                self.top_module_var.set("<Select files first>")
                self.top_combo['values'] = ["<Select files first>"]
    
    def _extract_modules_from_file(self, file_path: Path) -> list:
        """Extract module names from SystemVerilog/Verilog file."""
        modules = []
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                import re
                # Match module declarations only (not inside comments or strings)
                # Look for "module" at beginning of line or after whitespace
                matches = re.findall(r'^\s*module\s+(\w+)', content, re.IGNORECASE | re.MULTILINE)
                modules.extend(matches)
                # Also look for interface declarations
                interface_matches = re.findall(r'^\s*interface\s+(\w+)', content, re.IGNORECASE | re.MULTILINE)
                modules.extend(interface_matches)
        except Exception as e:
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
        if not self.project:
            messagebox.showwarning("Warning", "No project loaded")
            return
        
        top_module = self.top_module_var.get()
        if not top_module or top_module.startswith('<'):
            if not self.selected_files:
                messagebox.showwarning("Warning", "No files selected for compilation")
            elif top_module == "<No modules in selected files>":
                messagebox.showwarning("Warning", "No modules found in the selected files")
            else:
                messagebox.showwarning("Warning", "No valid top module specified")
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
                self.root.after(0, lambda: self.stop_button.config(state=tk.NORMAL))
                
                # Run command and always show output
                self.current_process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, 
                                                       stderr=subprocess.PIPE, text=True, 
                                                       cwd=self.project.project_path)
                
                stdout, stderr = self.current_process.communicate()
                result_code = self.current_process.returncode
                self.current_process = None
                
                # Always show stdout if available
                if stdout and stdout.strip():
                    self.root.after(0, lambda: self._log_message(stdout, "info"))
                
                # Always show stderr if available
                if stderr and stderr.strip():
                    self.root.after(0, lambda: self._log_message(stderr, "warning" if result_code == 0 else "error"))
                
                if result_code == 0:
                    self.root.after(0, lambda: self._log_message("Compilation completed successfully", "success"))
                elif result_code == -15:  # SIGTERM
                    self.root.after(0, lambda: self._log_message("Compilation stopped by user", "warning"))
                else:
                    self.root.after(0, lambda: self._log_message("Compilation failed", "error"))
                
            except Exception as e:
                self.root.after(0, lambda: self._log_message(f"Compilation error: {e}", "error"))
            finally:
                self.current_process = None
                self.root.after(0, lambda: self.stop_button.config(state=tk.DISABLED))
                self.root.after(0, lambda: self._update_status("ready"))
        
        self._update_status("compiling")
        threading.Thread(target=run_compile, daemon=True).start()
    
    def _simulate(self):
        """Run simulation."""
        if not self.project or not self.top_module_var.get():
            messagebox.showwarning("Warning", "No project loaded or top module not specified")
            return
        
        def run_sim():
            try:
                top_module = self.top_module_var.get().replace(' [TB]', '')
                
                # Based on Verilator documentation and corrected SimTool architecture:
                # --waves is ONLY a compilation flag (enables --trace in verilator)
                # --gui is a simulation flag (launches GTKWave viewer)
                # --time is a simulation flag (sets simulation time limit)
                # The simulation will auto-detect if tracing was enabled during compilation
                
                gui_requested = self.gui_var.get()
                gui_flag = "--gui" if gui_requested else ""
                
                # Add simulation time if specified
                sim_time = self.sim_time_var.get().strip()
                time_flag = f"--time {sim_time}" if sim_time else ""
                
                cmd = f"simtool sim {top_module} {gui_flag} {time_flag}".strip()
                
                self.root.after(0, lambda: self._log_message(f"> {cmd}", "info"))
                self.root.after(0, lambda: self.stop_button.config(state=tk.NORMAL))
                
                self.current_process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, 
                                                       stderr=subprocess.PIPE, text=True, 
                                                       cwd=self.project.project_path)
                
                stdout, stderr = self.current_process.communicate()
                result_code = self.current_process.returncode
                self.current_process = None
                
                # Always show stdout if available
                if stdout and stdout.strip():
                    self.root.after(0, lambda: self._log_message(stdout, "info"))
                
                # Always show stderr if available
                if stderr and stderr.strip():
                    self.root.after(0, lambda: self._log_message(stderr, "warning" if result_code == 0 else "error"))
                
                if result_code == 0:
                    self.root.after(0, lambda: self._log_message("Simulation completed successfully", "success"))
                    if self.waves_var.get():
                        self.root.after(0, lambda: self._log_message("Waveform file generated", "info"))
                elif result_code == -15:  # SIGTERM
                    self.root.after(0, lambda: self._log_message("Simulation stopped by user", "warning"))
                else:
                    self.root.after(0, lambda: self._log_message("Simulation failed", "error"))
                
            except Exception as e:
                self.root.after(0, lambda: self._log_message(f"Simulation error: {e}", "error"))
            finally:
                self.current_process = None
                self.root.after(0, lambda: self.stop_button.config(state=tk.DISABLED))
                self.root.after(0, lambda: self._update_status("ready"))
        
        self._update_status("running")
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
                else:
                    self.root.after(0, lambda: self._log_message(f"Clean failed: {result.stderr}", "error"))
                
            except Exception as e:
                self.root.after(0, lambda: self._log_message(f"Clean error: {e}", "error"))
        
        threading.Thread(target=run_clean, daemon=True).start()
    
    def _stop_process(self):
        """Stop the currently running process."""
        if self.current_process:
            try:
                # Terminate the process gracefully
                self.current_process.terminate()
                self._log_message("Stopping process...", "warning")
                
                # Give it a moment to terminate, then force kill if needed
                threading.Timer(2.0, self._force_kill_process).start()
                
            except Exception as e:
                self._log_message(f"Error stopping process: {e}", "error")
    
    def _force_kill_process(self):
        """Force kill the process if it didn't terminate gracefully."""
        if self.current_process:
            try:
                if self.current_process.poll() is None:  # Still running
                    self.current_process.kill()
                    self._log_message("Process forcefully terminated", "error")
            except Exception:
                pass
    
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
• System native theme interface

Built with Python and tkinter"""
        
        messagebox.showinfo("About SimTool", about_text)
    
    def _set_window_icon(self):
        """Set the window icon for both window and Alt+Tab visibility."""
        import sys
        
        try:
            # Try multiple locations for the icon
            icon_locations = [
                # 1. From GUI package directory (when installed)
                Path(__file__).parent / "simtool_icon.png",
                # 2. From project root (development)
                Path(__file__).parent.parent.parent / "simtool_icon.png",
                # 3. From current working directory
                Path.cwd() / "simtool_icon.png",
            ]
            
            # Try to load from package resources (Python 3.9+)
            try:
                import importlib.resources as resources
                try:
                    # Try to load from GUI package
                    with resources.path('src.gui', 'simtool_icon.png') as icon_path:
                        if icon_path.exists():
                            self._apply_icon(str(icon_path))
                            return
                except (ImportError, FileNotFoundError, ModuleNotFoundError, AttributeError):
                    pass
            except ImportError:
                pass
            
            # Try file system locations
            for icon_path in icon_locations:
                if icon_path.exists():
                    self._apply_icon(str(icon_path))
                    return
                    
        except Exception as e:
            # For debugging, print the error if in development
            if hasattr(self, '_development_mode'):
                print(f"Icon loading failed: {e}")
    
    def _apply_icon(self, icon_path: str):
        """Apply the icon to the window with platform-specific optimizations."""
        import sys
        
        try:
            # Load the icon image
            icon_image = tk.PhotoImage(file=icon_path)
            
            # Set window icon (works on all platforms)
            self.root.iconphoto(True, icon_image)  # True = set as default for all windows
            
            # Platform-specific icon handling
            if sys.platform == 'darwin':  # macOS
                # On macOS, also try to set the app icon
                try:
                    # Keep a reference to prevent garbage collection
                    self._icon_image = icon_image
                    
                    # Set window manager class for better Alt+Tab recognition
                    if hasattr(self.root, 'wm_class'):
                        self.root.wm_class('SimTool', 'SimTool')
                        
                except Exception:
                    pass
                    
            elif sys.platform == 'win32':  # Windows
                # On Windows, iconphoto should be sufficient for Alt+Tab
                try:
                    # Also try the older wm_iconbitmap for Windows compatibility
                    # Convert PNG to ICO if needed (this is basic fallback)
                    self.root.iconphoto(False, icon_image)
                except Exception:
                    pass
                    
            else:  # Linux and others
                # On Linux, iconphoto should work for most window managers
                try:
                    # Set window manager properties
                    if hasattr(self.root, 'wm_class'):
                        self.root.wm_class('simtool', 'SimTool')
                except Exception:
                    pass
            
            # Keep a reference to prevent garbage collection
            self._icon_image = icon_image
            
        except Exception as e:
            if hasattr(self, '_development_mode'):
                print(f"Icon application failed: {e}")
    
    def _update_status(self, status_type: str, message: str = None):
        """Update status indicator with color coding."""
        status_colors = {
            "ready": "#28a745",      # Green
            "compiling": "#007bff",   # Blue
            "running": "#007bff",     # Blue
            "failed": "#dc3545",      # Red
            "warning": "#ffc107",     # Yellow
            "no_project": "#6c757d"   # Gray
        }
        
        status_messages = {
            "ready": "Ready",
            "compiling": "Compiling...",
            "running": "Running simulation...",
            "failed": "Failed",
            "warning": "Warning",
            "no_project": "No project"
        }
        
        color = status_colors.get(status_type, "#6c757d")
        text = message or status_messages.get(status_type, status_type)
        
        self.status_indicator.config(foreground=color)
        self.status_label.config(text=text)
    
    def _update_project_controls_state(self):
        """Enable/disable project-dependent controls based on project state."""
        has_project = self.project is not None
        
        for button in self.project_buttons:
            if has_project:
                button.config(state=tk.NORMAL)  # TTK buttons handle styling automatically
            else:
                button.config(state=tk.DISABLED)  # TTK buttons handle disabled styling automatically
    
    def _set_sim_time_preset(self, preset: str):
        """Set simulation time to preset value."""
        self.sim_time_var.set(preset)
        self._mark_unsaved()
    
    def run(self):
        """Run the application."""
        # Add welcome message
        self._log_message("Welcome to SimTool GUI!", "success")
        self._log_message("Load a project via File → Open Project or create a new one.", "info")
        
        # Save state on window close
        def on_closing():
            # Check for unsaved changes before closing
            if not self._check_unsaved_changes():
                return  # User cancelled, don't close
            
            # Save theme preference (system native)
            self.preferences.set("theme", "system")
            self.preferences.save_preferences()
            self.root.quit()
        
        self.root.protocol("WM_DELETE_WINDOW", on_closing)
        
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
            self.preferences.set("theme", "dark")
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
            # Theme is now fixed to system native
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