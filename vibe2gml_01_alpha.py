import sys
import os
import json # Used for Room/Object parsing
import re # Used for cleaning JSON
from collections import Counter # Used for Room instance counting

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QFileDialog, QTreeView, QMessageBox,
    QSplitter, QSizePolicy, QInputDialog, QMenu, QLabel, QStackedWidget
)
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QAction, QFont, QIcon, QPixmap
from PyQt6.QtCore import Qt, QModelIndex, QPoint, QSize

# Define custom roles for storing data with tree items
GML_FILE_PATH_ROLE = Qt.ItemDataRole.UserRole
ASSET_FOLDER_PATH_ROLE = Qt.ItemDataRole.UserRole + 1
ITEM_TYPE_ROLE = Qt.ItemDataRole.UserRole + 2 # 'file', 'folder', 'room_folder', 'sprite_folder', 'object_folder' <<<< ADDED object_folder

class GmlViewerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.project_root_path = None
        # Stores tuples: (full_display_name, gml_file_path, relative_gml_path, asset_yy_path or None)
        self.project_gml_files_details = [] # <<<< MODIFIED to store more info
        self.current_file_path = None
        self.current_display_name = None
        self.initUI()

    def initUI(self):
        # (initUI remains the same as the previous version)
        self.setWindowTitle("VIBE2GML")
        self.setGeometry(100, 100, 1100, 750)
        central_widget = QWidget(); self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        left_pane_widget = QWidget(); left_layout = QVBoxLayout(left_pane_widget); left_layout.setContentsMargins(0,0,0,0)
        self.tree_view = QTreeView(); self.model = QStandardItemModel(); self.tree_view.setModel(self.model)
        self.tree_view.setHeaderHidden(True); self.tree_view.setEditTriggers(QTreeView.EditTrigger.NoEditTriggers)
        self.tree_view.clicked.connect(self.on_tree_item_clicked)
        self.tree_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu); self.tree_view.customContextMenuRequested.connect(self.show_tree_context_menu)
        left_layout.addWidget(self.tree_view)
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save Changes"); self.save_button.setEnabled(False); self.save_button.clicked.connect(self.save_current_gml); button_layout.addWidget(self.save_button)
        self.export_button = QPushButton("Export All"); self.export_button.setEnabled(False); self.export_button.clicked.connect(self.export_all_gml); button_layout.addWidget(self.export_button) # <<<< Renamed button slightly
        left_layout.addLayout(button_layout)
        self.stacked_widget = QStackedWidget()
        self.text_edit = QTextEdit(); self.text_edit.setFontFamily("Courier New"); self.text_edit.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap); self.text_edit.setReadOnly(True)
        self.stacked_widget.addWidget(self.text_edit)
        self.image_label = QLabel("Select a Sprite asset to view the image."); self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter); self.image_label.setScaledContents(False)
        self.stacked_widget.addWidget(self.image_label)
        splitter = QSplitter(Qt.Orientation.Horizontal); splitter.addWidget(left_pane_widget); splitter.addWidget(self.stacked_widget)
        splitter.setStretchFactor(0, 1); splitter.setStretchFactor(1, 2); splitter.setSizes([350, 750])
        main_layout.addWidget(splitter)
        self.setup_menu()
        self.statusBar().showMessage("Ready. Open a GMS2 project folder.")

    def setup_menu(self):
        # (Menu setup remains the same)
        menu_bar = self.menuBar(); file_menu = menu_bar.addMenu("&File")
        open_action = QAction("&Open GMS2 Project Folder...", self); open_action.setShortcut("Ctrl+O"); open_action.triggered.connect(self.open_project_folder); file_menu.addAction(open_action)
        save_action = QAction("&Save Current File", self); save_action.setShortcut("Ctrl+S"); save_action.triggered.connect(self.save_current_gml)
        self.save_action_ref = save_action; self.save_action_ref.setEnabled(False); file_menu.addAction(save_action)
        # Add Export All action to menu
        export_action = QAction("&Export All GML + YY Data...", self) # <<<< Added YY to name
        export_action.triggered.connect(self.export_all_gml)
        self.export_action_ref = export_action # Store reference if needed later
        self.export_action_ref.setEnabled(False) # Enable when project loaded
        file_menu.addAction(export_action)
        file_menu.addSeparator()
        exit_action = QAction("&Exit", self); exit_action.setShortcut("Ctrl+Q"); exit_action.triggered.connect(self.close); file_menu.addAction(exit_action)

    def open_project_folder(self):
        # (Open project folder logic remains the same)
        folder_path = QFileDialog.getExistingDirectory(self, "Select GMS2 Project Folder")
        if folder_path:
            yyp_files = [f for f in os.listdir(folder_path) if f.endswith('.yyp')]
            if not yyp_files: QMessageBox.warning(self, "Not a GMS2 Project?", f"Folder missing .yyp file:\n{folder_path}")
            self.project_root_path = folder_path; self.setWindowTitle(f"VIBE2GML - {os.path.basename(folder_path)}")
            self.statusBar().showMessage(f"Scanning project: {folder_path}..."); QApplication.processEvents()
            self.scan_project(folder_path)
            # Enable export button only if GML files were found
            enable_export = bool(self.project_gml_files_details)
            self.export_button.setEnabled(enable_export)
            self.export_action_ref.setEnabled(enable_export) # Also enable menu item
            found_items = self.model.rowCount() > 0
            if not found_items: self.statusBar().showMessage(f"No assets or GML files found in {folder_path}"); QMessageBox.information(self, "Scan Complete", f"No GameMaker assets or .gml files were found in:\n{folder_path}")
            else: self.statusBar().showMessage(f"Project loaded: {folder_path} - Found {len(self.project_gml_files_details)} GML files.")


    def scan_project(self, folder_path):
        # Modified scan to store asset YY path with GML file details
        self.project_gml_files_details.clear() # Use the new list
        self.model.clear(); self.text_edit.clear(); self.image_label.clear()
        self.stacked_widget.setCurrentIndex(0); self.current_file_path = None; self.current_display_name = None
        self.save_button.setEnabled(False); self.save_action_ref.setEnabled(False); self.text_edit.setReadOnly(True)
        self.export_button.setEnabled(False); self.export_action_ref.setEnabled(False) # Disable export initially

        root_node = self.model.invisibleRootItem(); bold_font = QFont(); bold_font.setBold(True)
        asset_categories = { "Objects": "objects", "Scripts": "scripts", "Rooms": "rooms", "Sprites": "sprites", "Notes": "notes", "Tile Sets": "tilesets", "Timelines": "timelines", "Fonts": "fonts", "Sounds": "sounds", "Extensions": "extensions" }
        category_nodes = {}; asset_nodes = {} # {asset_folder_path: node}

        # Pass 1: Create Category and Asset Folder Nodes
        for display_name, folder_name in asset_categories.items():
            category_folder_path = os.path.join(folder_path, folder_name)
            if os.path.isdir(category_folder_path):
                if display_name not in category_nodes: cat_node = QStandardItem(display_name); cat_node.setFont(bold_font); cat_node.setEditable(False); root_node.appendRow(cat_node); category_nodes[display_name] = cat_node
                else: cat_node = category_nodes[display_name]
                try:
                    for asset_name in sorted(os.listdir(category_folder_path)):
                        asset_folder_path = os.path.join(category_folder_path, asset_name)
                        if os.path.isdir(asset_folder_path):
                            asset_type_prefix = display_name[:-1] if display_name.endswith('s') else display_name; asset_display_name = f"{asset_type_prefix}: {asset_name}"
                            asset_node = QStandardItem(asset_display_name); asset_node.setEditable(False); asset_node.setData(asset_folder_path, ASSET_FOLDER_PATH_ROLE)
                            # <<<< Mark objects, rooms, sprites specifically >>>>
                            item_type = "folder";
                            if display_name == "Objects": item_type = "object_folder" # <<<< Specific type
                            elif display_name == "Rooms": item_type = "room_folder"
                            elif display_name == "Sprites": item_type = "sprite_folder"
                            asset_node.setData(item_type, ITEM_TYPE_ROLE); asset_node.setData(os.path.relpath(asset_folder_path, folder_path), Qt.ItemDataRole.ToolTipRole)
                            cat_node.appendRow(asset_node); asset_nodes[asset_folder_path] = asset_node
                except OSError as e: print(f"Warning: Could not read directory {category_folder_path}: {e}")

        # Pass 2: Find GML files and attach, storing related YY path
        other_cat_node = None
        for current_root, dirs, files in os.walk(folder_path, topdown=True):
            relative_root = os.path.relpath(current_root, folder_path)
            if relative_root != '.':
                top_dir = relative_root.split(os.sep)[0].lower()
                is_known_asset_root = top_dir in asset_categories.values()
                if not is_known_asset_root and top_dir in ['options', 'datafiles', 'configs', '.git', '.vscode', 'temp']: dirs[:] = []; continue
            for file in sorted(files):
                if file.endswith(".gml"):
                    file_path = os.path.join(current_root, file); relative_path = os.path.relpath(file_path, folder_path); parent_dir = os.path.dirname(file_path)
                    parent_asset_node = asset_nodes.get(parent_dir); gml_display_name = os.path.splitext(file)[0]

                    # Determine the path to the asset's main YY file (if applicable)
                    asset_yy_path = None
                    if parent_asset_node:
                        parent_item_type = parent_asset_node.data(ITEM_TYPE_ROLE)
                        # Only certain asset types have a primary YY file named after the asset folder
                        if parent_item_type in ["object_folder", "room_folder", "sprite_folder", "folder"]: # Assuming 'folder' might be script etc.
                             asset_name = os.path.basename(parent_dir)
                             potential_yy_path = os.path.join(parent_dir, f"{asset_name}.yy")
                             if os.path.isfile(potential_yy_path):
                                 asset_yy_path = potential_yy_path

                    if parent_asset_node:
                        item_node = QStandardItem(gml_display_name); item_node.setEditable(False); item_node.setData(file_path, GML_FILE_PATH_ROLE); item_node.setData("file", ITEM_TYPE_ROLE); item_node.setData(relative_path, Qt.ItemDataRole.ToolTipRole)
                        parent_asset_node.appendRow(item_node);
                        full_display_name = f"{parent_asset_node.text()} / {gml_display_name}"
                        # Store GML details along with associated asset YY path
                        self.project_gml_files_details.append((full_display_name, file_path, relative_path, asset_yy_path)) # <<<< Added yy_path
                    else: # GML file not in a direct known asset subfolder
                         if other_cat_node is None:
                             if "Other" not in category_nodes: other_cat_node = QStandardItem("Other GML"); other_cat_node.setFont(bold_font); other_cat_node.setEditable(False); root_node.appendRow(other_cat_node); category_nodes["Other"] = other_cat_node
                             else: other_cat_node = category_nodes["Other"]
                         item_node = QStandardItem(relative_path); item_node.setEditable(False); item_node.setData(file_path, GML_FILE_PATH_ROLE); item_node.setData("file", ITEM_TYPE_ROLE); item_node.setData(relative_path, Qt.ItemDataRole.ToolTipRole)
                         other_cat_node.appendRow(item_node);
                         # No clear associated asset YY path for 'Other' GML
                         self.project_gml_files_details.append((relative_path, file_path, relative_path, None)) # <<<< Added None for yy_path

        self.project_gml_files_details.sort() # Sort the detailed list
        self.tree_view.expandToDepth(0)


    def on_tree_item_clicked(self, index: QModelIndex):
        # Modified to handle object_folder clicks
        item = self.model.itemFromIndex(index)
        if not item: return
        item_type = item.data(ITEM_TYPE_ROLE); display_name = item.text()
        self.text_edit.setReadOnly(True); self.save_button.setEnabled(False); self.save_action_ref.setEnabled(False)
        self.current_file_path = None; self.current_display_name = display_name; self.image_label.clear()
        self.stacked_widget.setCurrentIndex(0) # Default to text view

        if item_type == "file":
            file_path = item.data(GML_FILE_PATH_ROLE)
            if file_path and os.path.isfile(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f: gml_content = f.read()
                    self.text_edit.setPlainText(gml_content)
                    # Automatic clipboard copy REMOVED based on user feedback
                    self.text_edit.setReadOnly(False); self.current_file_path = file_path
                    self.save_button.setEnabled(True); self.save_action_ref.setEnabled(True)
                    self.statusBar().showMessage(f"Editing GML: {display_name} ({os.path.basename(file_path)})")
                except Exception as e: error_msg = f"Error reading GML file:\n{file_path}\n\n{e}"; self.text_edit.setPlainText(error_msg); QMessageBox.warning(self, "File Read Error", error_msg); self.statusBar().showMessage(f"Error reading {os.path.basename(file_path)}")
            else: self.text_edit.clear(); self.statusBar().showMessage("Invalid GML file path selected.")

        elif item_type == "room_folder":
            folder_path = item.data(ASSET_FOLDER_PATH_ROLE); room_name = display_name.split(": ")[-1]
            room_yy_path = os.path.join(folder_path, f"{room_name}.yy"); self.display_room_info(room_yy_path)
            # Status bar set within display_room_info

        elif item_type == "object_folder": # <<<< ADDED Object Folder Handling
            folder_path = item.data(ASSET_FOLDER_PATH_ROLE); object_name = display_name.split(": ")[-1]
            object_yy_path = os.path.join(folder_path, f"{object_name}.yy"); self.display_object_info(object_yy_path) # Call new function
            self.statusBar().showMessage(f"Viewing Object: {object_name}")

        elif item_type == "sprite_folder":
            self.stacked_widget.setCurrentIndex(1) # Switch to image view *before* loading
            folder_path = item.data(ASSET_FOLDER_PATH_ROLE); sprite_name = display_name.split(": ")[-1]
            self.display_sprite_info(folder_path, sprite_name)
            # Status bar set within display_sprite_info

        elif item_type == "folder": # Generic folder (Script, Note, etc.)
            folder_path = item.data(ASSET_FOLDER_PATH_ROLE)
            self.text_edit.setPlainText(f"Selected Asset Folder:\n{os.path.relpath(folder_path, self.project_root_path)}\n\n(Select a GML file to edit or right-click to create GML)")
            self.statusBar().showMessage(f"Selected folder: {display_name}")
        else: self.text_edit.clear(); self.statusBar().showMessage("Select an item from the tree.")


    # <<<< ---- Room Info Display Functions ---- >>>>
    def display_room_info(self, room_yy_path):
        # (Unchanged)
        self.stacked_widget.setCurrentIndex(0) # Ensure text view is visible
        if not os.path.isfile(room_yy_path): error_msg = f"Room config file not found:\n{room_yy_path}"; self.text_edit.setPlainText(error_msg); self.statusBar().showMessage("Error: Room .yy not found."); QMessageBox.warning(self, "File Not Found", error_msg); return
        try:
            with open(room_yy_path, 'r', encoding='utf-8') as f: file_content = f.read()
            content_cleaned = re.sub(r",\s*([]}])", r"\1", file_content); room_data = json.loads(content_cleaned)
            formatted_text = self.format_room_data(room_data); self.text_edit.setPlainText(formatted_text)
            self.statusBar().showMessage(f"Viewing Room: {os.path.basename(os.path.dirname(room_yy_path))}")
        except json.JSONDecodeError as e: error_msg = f"Error parsing room file:\n{room_yy_path}\n\nError: {e}\n\n(Check .yy file for syntax errors)"; self.text_edit.setPlainText(error_msg); self.statusBar().showMessage("Error: Failed to parse room .yy."); QMessageBox.warning(self, "JSON Parse Error", error_msg)
        except Exception as e: error_msg = f"An unexpected error occurred reading room file:\n{room_yy_path}\n\n{e}"; self.text_edit.setPlainText(error_msg); self.statusBar().showMessage("Error: Failed to read room .yy."); QMessageBox.critical(self, "Read Error", error_msg)

    def format_room_data(self, data):
        # (Unchanged)
        output_lines = []; room_name = data.get('name', 'Unknown Room'); output_lines.append(f"{room_name}")
        layers = data.get('layers', []); layers_prefix = "├──" if data.get('roomSettings') or data.get('isPersistent') is not None else "└──"; output_lines.append(f"{layers_prefix} Layers ({len(layers)})")
        for i, layer in enumerate(layers):
            is_last_layer = (i == len(layers) - 1); layer_prefix_connector = "│   " if not is_last_layer else "    "; layer_prefix = f"{layer_prefix_connector}{'└──' if is_last_layer else '├──'}"
            layer_name = layer.get('name', f'Unnamed Layer {i}'); layer_type = layer.get('__type', layer.get('modelName','Unknown')); output_lines.append(f"{layer_prefix} {layer_name} [{layer_type.replace('GM','')}]")
            if layer_type == "GMInstanceLayer":
                instances = layer.get('instances', []); inst_prefix_connector = f"{layer_prefix_connector}    "; inst_is_last_in_layer = True; inst_prefix = f"{inst_prefix_connector}{'└──' if inst_is_last_in_layer else '├──'}"
                if instances:
                    output_lines.append(f"{inst_prefix} Instances ({len(instances)})"); instance_counts = Counter()
                    for inst in instances: instance_counts[inst.get('objId', {}).get('name', 'UnknownObject')] += 1
                    sorted_objects = sorted(instance_counts.items()); obj_prefix_connector = f"{inst_prefix_connector}    "
                    for j, (obj_name, count) in enumerate(sorted_objects): is_last_obj = (j == len(sorted_objects) - 1); obj_prefix = f"{obj_prefix_connector}{'└──' if is_last_obj else '├──'}"; count_str = f" (x{count})" if count > 1 else ""; output_lines.append(f"{obj_prefix} {obj_name}{count_str}")
        room_settings = data.get('roomSettings', {}); view_settings = data.get('viewSettings', {}); creation_code_file = data.get('creationCodeFile', ''); is_persistent = data.get('isPersistent', False); has_properties = room_settings or view_settings or is_persistent is not None or creation_code_file
        if has_properties:
             prop_prefix = "└──"; output_lines.append(f"{prop_prefix} Properties"); prop_connector = "    "; prop_items = []
             prop_items.append(f"Width: {room_settings.get('Width', '?')}"); prop_items.append(f"Height: {room_settings.get('Height', '?')}")
             room_speed = room_settings.get('Speed', 30); enabled_views = [v for v in data.get('views', []) if v.get('inherit') is False and v.get('visible', False)]
             if enabled_views:
                 if 'physicsWorldSpeed' in enabled_views[0]: room_speed = enabled_views[0].get('physicsWorldSpeed', room_speed)
                 elif 'speed' in enabled_views[0]: room_speed = enabled_views[0].get('speed', room_speed)
             prop_items.append(f"Speed: {room_speed}"); prop_items.append(f"Persistent: {is_persistent}")
             if creation_code_file: prop_items.append(f"Creation Code: {os.path.basename(creation_code_file)}")
             for k, prop_text in enumerate(prop_items): is_last_prop = (k == len(prop_items) - 1); prop_item_prefix = f"{prop_connector}{'└──' if is_last_prop else '├──'}"; output_lines.append(f"{prop_item_prefix} {prop_text}")
        return "\n".join(output_lines)
    # <<<< ---- END Room Info Display Functions ---- >>>>

    # <<<< ---- ADDED Object Info Display Functions ---- >>>>
    def display_object_info(self, object_yy_path):
        """Loads, parses (with cleaning), and displays formatted object info."""
        self.stacked_widget.setCurrentIndex(0) # Ensure text view is visible
        if not os.path.isfile(object_yy_path):
            error_msg = f"Object configuration file not found:\n{object_yy_path}"
            self.text_edit.setPlainText(error_msg); self.statusBar().showMessage("Error: Object .yy file not found."); QMessageBox.warning(self, "File Not Found", error_msg)
            return
        try:
            with open(object_yy_path, 'r', encoding='utf-8') as f: file_content = f.read()
            content_cleaned = re.sub(r",\s*([]}])", r"\1", file_content); object_data = json.loads(content_cleaned)
            formatted_text = self.format_object_data(object_data); self.text_edit.setPlainText(formatted_text)
            self.statusBar().showMessage(f"Viewing Object: {object_data.get('name', 'Unknown')}")
        except json.JSONDecodeError as e: error_msg = f"Error parsing object file:\n{object_yy_path}\n\nError: {e}\n\n(Check .yy file for syntax errors)"; self.text_edit.setPlainText(error_msg); self.statusBar().showMessage("Error: Failed to parse object .yy."); QMessageBox.warning(self, "JSON Parse Error", error_msg)
        except Exception as e: error_msg = f"An unexpected error occurred reading object file:\n{object_yy_path}\n\n{e}"; self.text_edit.setPlainText(error_msg); self.statusBar().showMessage("Error: Failed to read object .yy."); QMessageBox.critical(self, "Read Error", error_msg)

    def format_object_data(self, data):
        """Formats parsed object JSON data into a readable string."""
        output_lines = []
        obj_name = data.get('name', 'Unknown Object')
        output_lines.append(f"Object: {obj_name}")
        output_lines.append("=" * (len(obj_name) + 8))

        # Basic Properties
        output_lines.append("\n[Properties]")
        sprite_id = data.get('spriteId')
        output_lines.append(f"  Sprite: {sprite_id.get('name', 'None') if sprite_id else 'None'}")
        mask_id = data.get('spriteMaskId')
        output_lines.append(f"  Mask: {mask_id.get('name', 'Same as Sprite') if mask_id else 'Same as Sprite'}")
        parent_id = data.get('parentObjectId')
        output_lines.append(f"  Parent: {parent_id.get('name', 'None') if parent_id else 'None'}")
        output_lines.append(f"  Visible: {data.get('visible', True)}")
        output_lines.append(f"  Solid: {data.get('solid', False)}")
        output_lines.append(f"  Persistent: {data.get('persistent', False)}")
        # Add more basic properties if desired (managed, etc.)

        # Events (Summary)
        event_list = data.get('eventList', [])
        output_lines.append(f"\n[Events ({len(event_list)})]")
        # Could list event types here, but might be long. Simple count for now.

        # Physics Properties (if physics enabled)
        if data.get('physicsObject', False):
             output_lines.append("\n[Physics Properties]")
             output_lines.append(f"  Enabled: True")
             output_lines.append(f"  Sensor: {data.get('physicsSensor', False)}")
             output_lines.append(f"  Shape: {data.get('physicsShape', 1)}") # 1=Box, 2=Circle? Check docs
             # Could add Shape Points if needed
             output_lines.append(f"  Density: {data.get('physicsDensity', 0.5)}")
             output_lines.append(f"  Restitution: {data.get('physicsRestitution', 0.1)}")
             output_lines.append(f"  Group: {data.get('physicsGroup', 1)}")
             output_lines.append(f"  Linear Damping: {data.get('physicsLinearDamping', 0.1)}")
             output_lines.append(f"  Angular Damping: {data.get('physicsAngularDamping', 0.1)}")
             output_lines.append(f"  Friction: {data.get('physicsFriction', 0.2)}")
             output_lines.append(f"  Awake: {data.get('physicsStartAwake', True)}")
             output_lines.append(f"  Kinematic: {data.get('physicsKinematic', False)}")
        else:
             output_lines.append("\n[Physics Properties]")
             output_lines.append(f"  Enabled: False")

        # Object Properties (Variables defined in IDE)
        obj_props = data.get('properties', [])
        output_lines.append(f"\n[Object Variables ({len(obj_props)})]")
        if obj_props:
            for prop in obj_props:
                # Format might vary depending on GMS version (older used varName, varType, varValue)
                # Newer might use more complex structures. Keep it simple for now.
                 prop_name = prop.get('name', prop.get('varName', 'UnknownVar'))
                 prop_val = prop.get('value', prop.get('varValue', 'UnknownVal'))
                 prop_type = prop.get('type', prop.get('varType', '?')) # Type might be numeric code
                 output_lines.append(f"  - {prop_name} = {prop_val} (Type: {prop_type})")
        else:
             output_lines.append("  (None)")

        return "\n".join(output_lines)
    # <<<< ---- END Object Info Display Functions ---- >>>>


    def display_sprite_info(self, sprite_folder_path, sprite_name):
        # (Unchanged)
        first_png = None
        try:
            for filename in sorted(os.listdir(sprite_folder_path)):
                if filename.lower().endswith(".png"): first_png = os.path.join(sprite_folder_path, filename); break
        except OSError as e: error_msg = f"Error accessing sprite folder:\n{sprite_folder_path}\n\n{e}"; self.stacked_widget.setCurrentIndex(0); self.text_edit.setPlainText(error_msg); self.statusBar().showMessage(f"Error reading sprite folder: {sprite_name}"); QMessageBox.warning(self, "Folder Error", error_msg); return
        if first_png:
            pixmap = QPixmap(first_png)
            if pixmap.isNull(): error_msg = f"Failed to load image file:\n{first_png}"; self.stacked_widget.setCurrentIndex(0); self.text_edit.setPlainText(error_msg); self.statusBar().showMessage(f"Error loading image for sprite: {sprite_name}"); QMessageBox.warning(self, "Image Load Error", error_msg)
            else:
                label_size = self.image_label.size(); pixmap_size = pixmap.size(); scaled_pixmap = pixmap
                if pixmap_size.width() > label_size.width() or pixmap_size.height() > label_size.height():
                    scaled_pixmap = pixmap.scaled(label_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.image_label.setPixmap(scaled_pixmap); self.stacked_widget.setCurrentIndex(1)
                self.statusBar().showMessage(f"Displaying sprite: {sprite_name} ({pixmap_size.width()}x{pixmap_size.height()}) - Frame: {os.path.basename(first_png)}")
        else: self.stacked_widget.setCurrentIndex(0); self.text_edit.setPlainText(f"No .png image frames found in sprite folder:\n{sprite_folder_path}"); self.statusBar().showMessage(f"No .png found for sprite: {sprite_name}")

    def show_tree_context_menu(self, position: QPoint):
        # (Unchanged)
        index = self.tree_view.indexAt(position);
        if not index.isValid(): return
        item = self.model.itemFromIndex(index);
        if not item: return
        item_type = item.data(ITEM_TYPE_ROLE)
        menu = QMenu()
        if item_type in ["folder", "room_folder", "sprite_folder", "object_folder"]: # Allow create in object folders too
            create_action = QAction("Create New GML File...", self)
            create_action.triggered.connect(lambda checked=False, idx=index: self.create_new_gml_file(idx))
            menu.addAction(create_action)
        if not menu.isEmpty(): menu.exec(self.tree_view.viewport().mapToGlobal(position))

    def create_new_gml_file(self, index: QModelIndex):
        # (Unchanged)
        parent_item = self.model.itemFromIndex(index); item_type = parent_item.data(ITEM_TYPE_ROLE) if parent_item else None
        if not parent_item or item_type not in ["folder", "room_folder", "sprite_folder", "object_folder"]: QMessageBox.warning(self, "Error", "Cannot create GML file here. Select an asset folder."); return
        asset_folder_path = parent_item.data(ASSET_FOLDER_PATH_ROLE)
        if not asset_folder_path or not os.path.isdir(asset_folder_path): QMessageBox.critical(self, "Error", f"Invalid asset folder path: {asset_folder_path}"); return
        default_name = "NewEvent_0.gml"
        file_name, ok = QInputDialog.getText(self, "Create New GML File", "Enter filename:", text=default_name)
        if ok and file_name:
            file_name = file_name.replace(" ", "_");
            if not file_name.lower().endswith(".gml"): file_name += ".gml"
            new_file_path = os.path.join(asset_folder_path, file_name); relative_path = os.path.relpath(new_file_path, self.project_root_path)
            if os.path.exists(new_file_path): QMessageBox.warning(self, "File Exists", f"File '{file_name}' already exists."); return
            try:
                with open(new_file_path, 'w', encoding='utf-8') as f: f.write(f"/// @description {os.path.splitext(file_name)[0]}\n\n// Add your code here\n")
                gml_display_name = os.path.splitext(file_name)[0]
                new_item = QStandardItem(gml_display_name); new_item.setEditable(False)
                new_item.setData(new_file_path, GML_FILE_PATH_ROLE); new_item.setData("file", ITEM_TYPE_ROLE); new_item.setData(relative_path, Qt.ItemDataRole.ToolTipRole)
                parent_item.appendRow(new_item)
                # Find asset YY path to store with new GML detail
                asset_name = os.path.basename(asset_folder_path)
                potential_yy_path = os.path.join(asset_folder_path, f"{asset_name}.yy")
                asset_yy_path = potential_yy_path if os.path.isfile(potential_yy_path) else None
                full_display_name = f"{parent_item.text()} / {gml_display_name}"
                self.project_gml_files_details.append((full_display_name, new_file_path, relative_path, asset_yy_path)); self.project_gml_files_details.sort()
                self.export_button.setEnabled(True); self.export_action_ref.setEnabled(True) # Enable export
                self.statusBar().showMessage(f"Created file: {relative_path}")
                self.tree_view.setCurrentIndex(new_item.index()); self.on_tree_item_clicked(new_item.index())
            except Exception as e: QMessageBox.critical(self, "Creation Failed", f"Could not create file:\n{new_file_path}\n\nError: {e}"); self.statusBar().showMessage(f"Failed to create {file_name}")

    def save_current_gml(self):
        # (Unchanged)
        if self.current_file_path and os.path.isfile(self.current_file_path):
            try:
                current_content = self.text_edit.toPlainText()
                with open(self.current_file_path, 'w', encoding='utf-8') as f: f.write(current_content)
                self.statusBar().showMessage(f"Saved: {self.current_display_name} ({os.path.basename(self.current_file_path)})")
            except Exception as e: QMessageBox.critical(self, "Save Failed", f"Could not save file:\n{self.current_file_path}\n\nError: {e}"); self.statusBar().showMessage(f"Error saving {os.path.basename(self.current_file_path)}")
        elif self.save_button.isEnabled(): QMessageBox.warning(self, "Save Error", "No valid GML file loaded to save."); self.statusBar().showMessage("No GML file loaded to save.")

    def export_all_gml(self):
        # <<<< MODIFIED to include YY file content >>>>
        if not self.project_gml_files_details: # Check the detailed list
            QMessageBox.information(self, "Export Error", "No GML files found or loaded to export."); return
        if not self.project_root_path:
             QMessageBox.warning(self, "Export Error", "Project path is not set."); return

        default_filename = f"{os.path.basename(self.project_root_path)}_export.txt" # Changed suggested name
        save_path, _ = QFileDialog.getSaveFileName(self, "Export All GML & YY Data", default_filename, "Text Files (*.txt);;All Files (*)") # Changed dialog title

        if save_path:
            exported_yy_files = set() # Keep track of yy files already exported
            try:
                with open(save_path, 'w', encoding='utf-8') as outfile:
                    outfile.write(f"// GML and YY Data Export from Project: {self.project_root_path}\n")
                    outfile.write(f"// Total GML Files Found: {len(self.project_gml_files_details)}\n") # Use count from detailed list
                    outfile.write("=" * 70 + "\n\n")

                    # Iterate through the detailed list
                    for display_name, file_path, relative_path, asset_yy_path in self.project_gml_files_details:
                        # --- Write GML File Info ---
                        outfile.write(f"// ----- Start GML: {display_name} -----\n")
                        outfile.write(f"// ----- GML Path: {relative_path} -----\n\n")
                        try:
                            with open(file_path, 'r', encoding='utf-8') as infile:
                                outfile.write(infile.read())
                        except Exception as read_err:
                             outfile.write(f"// ***** ERROR READING GML FILE: {relative_path} *****\n")
                             outfile.write(f"// ***** Error: {read_err} *****\n")
                        outfile.write("\n\n" + "-" * 50 + "[End GML]" + "-" * (70-50-9) + "\n\n") # GML Separator

                        # --- Write Associated YY File Info (if not already written) ---
                        if asset_yy_path and os.path.isfile(asset_yy_path) and asset_yy_path not in exported_yy_files:
                             relative_yy_path = os.path.relpath(asset_yy_path, self.project_root_path)
                             outfile.write(f"// ----- Associated YY File: {os.path.basename(os.path.dirname(asset_yy_path))} -----\n") # Asset Name
                             outfile.write(f"// ----- YY Path: {relative_yy_path} -----\n\n")
                             try:
                                 with open(asset_yy_path, 'r', encoding='utf-8') as yyfile:
                                     # Optionally clean before writing? For now, write raw.
                                     # yy_content = yyfile.read()
                                     # yy_content_cleaned = re.sub(r",\s*([]}])", r"\1", yy_content)
                                     # outfile.write(yy_content_cleaned)
                                     outfile.write(yyfile.read()) # Write raw content
                             except Exception as read_err:
                                 outfile.write(f"// ***** ERROR READING YY FILE: {relative_yy_path} *****\n")
                                 outfile.write(f"// ***** Error: {read_err} *****\n")
                             outfile.write("\n\n" + "=" * 30 + "[End YY]" + "=" * (70-30-8) + "\n\n") # YY Separator
                             exported_yy_files.add(asset_yy_path) # Mark as exported


                self.statusBar().showMessage(f"Successfully exported GML & YY data to {save_path}")
                QMessageBox.information(self, "Export Complete", f"All GML code and associated YY data exported successfully to:\n{save_path}")
            except Exception as write_err:
                QMessageBox.critical(self, "Export Failed", f"An error occurred while writing the export file:\n{write_err}"); self.statusBar().showMessage("Export failed.")


# --- Main Execution ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setApplicationName("VIBE2GML")
    app.setOrganizationName("YourNameOrCompany")
    window = GmlViewerApp()
    window.show()
    sys.exit(app.exec())