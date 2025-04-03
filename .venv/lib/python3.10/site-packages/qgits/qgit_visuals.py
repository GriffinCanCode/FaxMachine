#!/usr/bin/env python3
"""3D Git repository visualizer for QGit.

This module provides a 3D visualization of Git repository structure and history. It shows file and directory relationships,
commit history, and file modifications over time.
"""

import asyncio
import gc
import logging
import os
import subprocess
import sys
import time
import venv
from typing import List, Set

import numpy as np
import pygame
from OpenGL.GL import (
    GL_BLEND,
    GL_COLOR_BUFFER_BIT,
    GL_DEPTH_BUFFER_BIT,
    GL_DEPTH_TEST,
    GL_LIGHTING,
    GL_LINE_LOOP,
    GL_LINEAR,
    GL_LINES,
    GL_MODELVIEW,
    GL_ONE_MINUS_SRC_ALPHA,
    GL_POLYGON,
    GL_PROJECTION,
    GL_QUADS,
    GL_RGBA,
    GL_SRC_ALPHA,
    GL_TEXTURE_2D,
    GL_TEXTURE_MAG_FILTER,
    GL_TEXTURE_MIN_FILTER,
    GL_UNSIGNED_BYTE,
    glBegin,
    glBindTexture,
    glBlendFunc,
    glClear,
    glClearColor,
    glColor4f,
    glDeleteTextures,
    glDisable,
    glEnable,
    glEnd,
    glGenTextures,
    glLineWidth,
    glLoadIdentity,
    glMatrixMode,
    glOrtho,
    glPopMatrix,
    glPushMatrix,
    glTexCoord2f,
    glTexImage2D,
    glTexParameteri,
    glVertex2f,
)
from pygame.locals import (
    DOUBLEBUF,
    K_ESCAPE,
    K_SPACE,
    KEYDOWN,
    MOUSEBUTTONDOWN,
    MOUSEBUTTONUP,
    OPENGL,
    QUIT,
    K_c,
    K_i,
    K_r,
)

from internal.resource_manager import get_resource_manager

from qgits.qgit_core import (
    format_size,
    get_current_branch,
    get_modified_files,
    get_staged_files,
    is_git_repo,
)


# Configure logging
def setup_logging():
    """Configure logging for the QGit visualizer."""
    log_dir = os.path.join(os.path.expanduser("~"), ".qgit", "logs")
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, "qgit_visual.log")

    # Configure logging format and handlers
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
    )

    # Log system information
    logging.info("Starting QGit Visualizer")
    logging.info(f"Python version: {sys.version}")
    logging.info(f"Operating System: {sys.platform}")
    logging.info(f"Pygame version: {pygame.version.ver}")
    logging.info(f"NumPy version: {np.__version__}")


# Initialize logging
setup_logging()


def install_requirements():
    """Install required packages into a local virtual environment."""
    logging.info("Installing required packages into virtual environment")
    try:
        # Create virtual environment
        venv_dir = os.path.join(os.path.dirname(__file__), "venv")
        logging.info(f"Creating virtual environment at {venv_dir}")
        venv.create(venv_dir, with_pip=True)

        # Get path to pip in virtual environment
        if sys.platform == "win32":
            pip_path = os.path.join(venv_dir, "Scripts", "pip.exe")
        else:
            pip_path = os.path.join(venv_dir, "bin", "pip")

        # Install required packages
        requirements = ["pygame", "numpy", "PyOpenGL", "PyOpenGL-accelerate"]

        for package in requirements:
            logging.info(f"Installing package: {package}")
            if sys.platform == "darwin":  # macOS
                subprocess.check_call([pip_path, "install", "--user", package])
            else:
                subprocess.check_call([pip_path, "install", package])

        logging.info("Successfully installed all requirements in virtual environment")

    except Exception as e:
        logging.error(f"Failed to install requirements: {str(e)}", exc_info=True)
        sys.exit(1)


class Node:
    """Represents a file or directory node in the 3D space."""

    def __init__(self, name: str, is_dir: bool, depth: int = 0, parent=None):
        self.name = name
        self.is_dir = is_dir
        self.children: List[Node] = []
        self.depth = depth
        self.parent = parent
        self.position = np.array([0.0, 0.0, 0.0])
        self.target_position = np.array([0.0, 0.0, 0.0])
        self.color = np.array([0.0, 0.0, 0.0, 1.0])
        self.size = 1.0 if is_dir else 0.5
        self.selected = False
        self.visible = True  # Show all nodes by default
        self.expanded = False  # Track if directory contents are shown
        self.last_modified = None
        self.creation_time = time.time()
        self.animation_progress = 0.0
        self.staged = False
        self.modified = False
        self.commit_count = 0
        self.last_commit_message = ""
        self.file_size = 0
        self.contributors: Set[str] = set()
        self.subtree_width = 0

    def add_child(self, child: "Node"):
        """Add a child node."""
        child.parent = self
        child.depth = self.depth + 1
        child.visible = True  # Make all nodes visible by default
        self.children.append(child)

    def toggle_expand(self):
        """Toggle visibility of child files."""
        if not self.is_dir:
            return

        self.expanded = not self.expanded
        for child in self.children:
            child.visible = True  # Make all nodes visible when expanding

    def collapse_all(self):
        """Collapse this directory and all subdirectories."""
        if self.is_dir:
            self.expanded = False
            for child in self.children:
                child.visible = (
                    True if child.is_dir else False
                )  # Keep directories visible
                child.collapse_all()

    def update_position(self, dt: float):
        """Smoothly interpolate position."""
        diff = self.target_position - self.position
        self.position += diff * min(1.0, dt * 5.0)
        self.animation_progress = min(1.0, self.animation_progress + dt * 2.0)


class GitVisualizer:
    """2D Git repository visualizer with 3D-like effects for directory structure."""

    def __init__(self, repo_path: str):
        """Initialize the Git visualizer."""
        logging.info(f"Initializing GitVisualizer for repository: {repo_path}")
        if not is_git_repo():
            logging.error("Not a Git repository")
            raise ValueError("Not a Git repository")

        self.repo_path = repo_path
        self.root_node = None
        self.nodes = []
        self.selected_node = None
        self.zoom_level = 1.0
        self.show_info = True
        self.pan_offset = np.array([600.0, 400.0])  # Center of screen
        self.min_zoom = 0.3
        self.max_zoom = 3.0
        self.initial_center = True  # Flag to center on first layout

        # Font cache for better text rendering
        self.font_cache = {}

        # Cache Git information
        logging.info("Caching Git repository information")
        self.current_branch = get_current_branch()
        self.staged_files = set(get_staged_files())
        self.modified_files = set(get_modified_files())
        logging.info(f"Current branch: {self.current_branch}")
        logging.info(
            f"Found {len(self.staged_files)} staged files and {len(self.modified_files)} modified files"
        )

        # Cache for Git history
        self._git_history_cache = {}

        # Animation properties
        self.last_time = time.time()
        self.animation_speed = 1.0

        # Initialize Pygame
        logging.info("Initializing Pygame and OpenGL")
        pygame.init()
        pygame.font.init()

        # Set up display with proper flags for macOS
        if sys.platform == "darwin":
            logging.info("Configuring macOS-specific display settings")
            # macOS specific initialization
            os.environ["SDL_VIDEO_DRIVER"] = "cocoa"  # Force Cocoa driver
            pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 2)
            pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 1)
            pygame.display.gl_set_attribute(
                pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_COMPATIBILITY
            )
            pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE, 16)
            pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1)
            pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, 4)

        try:
            logging.info("Creating OpenGL display window")
            self.screen = pygame.display.set_mode((1200, 800), DOUBLEBUF | OPENGL)
        except pygame.error as e:
            logging.critical(f"Failed to create OpenGL context: {e}", exc_info=True)
            raise RuntimeError(
                "Failed to initialize display. Please ensure OpenGL is supported on your system."
            )

        pygame.display.set_caption(f"QGit Visualizer - {self.current_branch}")

        # OpenGL initialization
        self._setup_opengl()

        # Build initial tree structure
        self.build_tree()
        self.layout_nodes()
        logging.info("GitVisualizer initialization complete")

    def _setup_opengl(self):
        """Initialize OpenGL settings for 2D rendering with 3D effects."""
        logging.info("Setting up OpenGL configuration")
        try:
            # Basic OpenGL setup
            glClearColor(0.06, 0.06, 0.08, 1.0)  # Darker background

            # Enable blending
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

            # Set up projection matrix
            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()

            # Use a simpler projection for macOS
            if sys.platform == "darwin":
                logging.debug("Using simplified projection for macOS")
                glOrtho(-600, 600, -400, 400, -1, 1)
            else:
                glOrtho(0, 1200, 800, 0, -1, 1)

            # Set up modelview matrix
            glMatrixMode(GL_MODELVIEW)
            glLoadIdentity()

            # Additional settings for better rendering
            glDisable(GL_DEPTH_TEST)
            glDisable(GL_LIGHTING)
            logging.info("OpenGL setup completed successfully")

        except Exception as e:
            logging.critical(f"OpenGL initialization failed: {e}", exc_info=True)
            raise RuntimeError(
                "Failed to initialize OpenGL. Please check your graphics drivers."
            )

    def _get_cached_font(self, size: int) -> pygame.font.Font:
        """Get a cached font instance with the specified size."""
        if size not in self.font_cache:
            try:
                # Try to use a high-quality font if available
                font_paths = [
                    "/System/Library/Fonts/SFNSMono.ttf",  # macOS
                ]
                font_file = None
                for path in font_paths:
                    if os.path.exists(path):
                        font_file = path
                        break

                if font_file:
                    self.font_cache[size] = pygame.font.Font(font_file, size)
                else:
                    self.font_cache[size] = pygame.font.Font(None, size)
            except:
                self.font_cache[size] = pygame.font.Font(None, size)

        return self.font_cache[size]

    def layout_nodes(self):
        """Calculate 2D positions for all nodes using a hierarchical block layout."""
        PADDING = 20  # Increased base padding
        MIN_NODE_WIDTH = 250  # Wider nodes for better readability
        MIN_NODE_HEIGHT = 40  # Taller nodes for better visibility
        GROUP_PADDING = 40  # More padding between groups
        LEVEL_PADDING = 60  # Vertical padding between levels

        def calculate_node_size(node):
            """Calculate the size needed for a node and its children."""
            if not node.visible:
                return 0, 0

            font = self._get_cached_font(14)
            text_width = font.size(node.name)[0]
            node_width = max(
                text_width + 120, MIN_NODE_WIDTH
            )  # More space for icons/details
            node_height = MIN_NODE_HEIGHT

            if node.children and node.is_dir:
                # Sort children by type and importance
                node.children.sort(
                    key=lambda x: (
                        -int(x.is_dir),  # Directories first
                        -(x.staged or x.modified),  # Active files next
                        (
                            -len(x.children) if x.is_dir else -x.commit_count
                        ),  # Sort by size/activity
                        x.name.lower(),  # Then alphabetically
                    )
                )

                # Only process visible children
                visible_children = [c for c in node.children if c.visible]

                if not visible_children:
                    node.total_width = node_width
                    node.total_height = node_height
                    return node_width, node_height

                # Calculate sizes recursively
                child_sizes = []
                total_width = 0
                max_child_height = 0

                # Process visible children
                row_width = 0
                row_items = []
                for child in visible_children:
                    child_width, child_height = calculate_node_size(child)
                    if row_width + child_width + PADDING > 1100:
                        # Start new row
                        if row_items:  # Only process if row has items
                            total_width = max(total_width, row_width)
                            max_child_height += (
                                max(h for _, _, h in row_items) + PADDING
                            )
                            child_sizes.extend(row_items)
                        row_items = [(child, child_width, child_height)]
                        row_width = child_width + PADDING
                    else:
                        row_items.append((child, child_width, child_height))
                        row_width += child_width + PADDING

                # Process last row if it has items
                if row_items:
                    total_width = max(total_width, row_width)
                    max_child_height += max(h for _, _, h in row_items) + PADDING
                    child_sizes.extend(row_items)

                # Store layout information
                node.child_sizes = child_sizes
                node.total_width = max(total_width + PADDING * 2, node_width)
                node.total_height = max_child_height + node_height + LEVEL_PADDING
                return node.total_width, node.total_height
            else:
                node.total_width = node_width
                node.total_height = node_height
                return node_width, node_height

        def position_nodes(node, x, y):
            """Position a node and its children with improved organization."""
            if not node.visible:
                return

            # Position the node itself
            node.target_position = np.array([x, 800 - y, 0.0])

            if hasattr(node, "child_sizes") and node.child_sizes:
                current_y = y + MIN_NODE_HEIGHT + LEVEL_PADDING
                current_x = x + PADDING

                row_items = []
                row_width = 0
                row_height = 0

                for child, child_width, child_height in node.child_sizes:
                    if (
                        row_width + child_width + PADDING
                        > node.total_width - PADDING * 2
                    ):
                        # Position current row if it has items
                        if row_items:
                            position_row(row_items, x, current_y, node.total_width)
                            current_y += row_height + PADDING
                        row_items = []
                        row_width = 0
                        row_height = 0

                    row_items.append((child, child_width, child_height))
                    row_width += child_width + PADDING
                    row_height = max(row_height, child_height)

                # Position last row if it has items
                if row_items:
                    position_row(row_items, x, current_y, node.total_width)

        def position_row(row_items, x, y, total_width):
            """Position a row of items with even spacing."""
            if not row_items:
                return

            total_item_width = sum(w for _, w, _ in row_items)
            spacing = min(
                PADDING, (total_width - total_item_width) / (len(row_items) + 1)
            )
            current_x = x + spacing

            for child, child_width, child_height in row_items:
                if child.visible:
                    position_nodes(child, current_x, y)
                current_x += child_width + spacing

        # Calculate sizes starting from root
        calculate_node_size(self.root_node)

        # Position nodes starting from root
        window_width = 1200
        window_height = 800
        start_x = (window_width - self.root_node.total_width) / 2
        start_y = PADDING
        position_nodes(self.root_node, start_x, start_y)

        # Center the visualization on first layout
        if self.initial_center:
            self.pan_offset = np.array(
                [
                    (window_width - self.root_node.total_width) / 2,
                    (window_height - self.root_node.total_height) / 2,
                ]
            )
            self.initial_center = False

    def draw_node(self, node: Node):
        """Draw a node with enhanced visual styling."""
        # Calculate screen position and size
        pos = node.position[:2] + self.pan_offset
        font = self._get_cached_font(int(14 * self.zoom_level))
        text_width = font.size(node.name)[0]
        width = max(text_width + 120 * self.zoom_level, 250 * self.zoom_level)
        height = 40 * self.zoom_level

        # Draw enhanced shadow with stronger depth effect
        shadow_offset = 6 * self.zoom_level
        for i in range(5):  # More shadow layers
            alpha = 0.25 - i * 0.04
            offset = (i + 1) * shadow_offset
            glColor4f(0.0, 0.0, 0.0, alpha)
            self._draw_rounded_rect(
                pos[0] + offset,
                pos[1] + offset,
                width,
                height,
                10 * self.zoom_level,  # More rounded corners
            )

        # Get node color with enhanced gradients
        if node.selected:
            base_color = np.array([1.0, 0.9, 0.2, 0.95])
        else:
            base_color = node.color.copy()

        # Create enhanced gradient effect
        gradient_top = base_color * 1.5  # Stronger gradient
        gradient_top = np.minimum(gradient_top, [1.0, 1.0, 1.0, 1.0])
        gradient_bottom = base_color * 0.5  # Darker bottom

        # Draw main block with enhanced gradient
        glBegin(GL_QUADS)
        glColor4f(*gradient_top)
        glVertex2f(pos[0], pos[1])
        glVertex2f(pos[0] + width, pos[1])
        glColor4f(*gradient_bottom)
        glVertex2f(pos[0] + width, pos[1] + height)
        glVertex2f(pos[0], pos[1] + height)
        glEnd()

        # Draw enhanced border
        glLineWidth(3.0 * self.zoom_level)  # Thicker border
        if node.selected:
            glColor4f(1.0, 1.0, 1.0, 0.95)  # Brighter selected border
        else:
            glColor4f(1.0, 1.0, 1.0, 0.5)  # More visible default border
        self._draw_rounded_rect_outline(
            pos[0], pos[1], width, height, 10 * self.zoom_level
        )

        # Draw enhanced icon
        icon_size = 24 * self.zoom_level  # Larger icons
        icon_x = pos[0] + 12 * self.zoom_level
        icon_y = pos[1] + (height - icon_size) / 2
        if node.is_dir:
            self._draw_folder_icon(icon_x, icon_y, icon_size)
        else:
            self._draw_file_icon(icon_x, icon_y, icon_size)

        # Draw node name with enhanced visibility
        text = font.render(node.name, True, (255, 255, 255))
        shadow = font.render(node.name, True, (0, 0, 0))
        texture_shadow = self._surface_to_texture(shadow)
        texture = self._surface_to_texture(text)

        text_x = pos[0] + icon_size + 18 * self.zoom_level
        text_y = pos[1] + (height - text.get_height()) / 2

        # Draw enhanced text shadow
        self._draw_texture_quad(
            texture_shadow,
            text_x + self.zoom_level,
            text_y + self.zoom_level,
            text.get_width(),
            text.get_height(),
        )
        # Draw main text
        self._draw_texture_quad(
            texture, text_x, text_y, text.get_width(), text.get_height()
        )

        glDeleteTextures([texture, texture_shadow])

        # Draw enhanced status indicators
        if not node.is_dir:
            indicator_size = 14 * self.zoom_level  # Larger indicators
            indicator_x = pos[0] + width - indicator_size - 12 * self.zoom_level
            indicator_y = pos[1] + (height - indicator_size) / 2
            if node.staged:
                self._draw_status_indicator(
                    indicator_x, indicator_y, indicator_size, [0.3, 0.9, 0.3]
                )
            elif node.modified:
                self._draw_status_indicator(
                    indicator_x, indicator_y, indicator_size, [0.9, 0.3, 0.3]
                )

        # Draw enhanced connections to children
        if node.children:
            glLineWidth(max(2.0, 2.5 * self.zoom_level))
            glBegin(GL_LINES)

            for child in node.children:
                if child.visible:
                    child_pos = child.position[:2] + self.pan_offset
                    # Draw enhanced connection lines
                    steps = 40  # More steps for smoother curves
                    for i in range(steps):
                        t = i / (steps - 1)
                        # Calculate enhanced control points
                        cp1 = pos + np.array([width / 2, height])
                        cp2 = child_pos + np.array([width / 2, 0])

                        p1 = self._bezier_point(
                            pos + np.array([width / 2, height]),
                            cp1,
                            cp2,
                            child_pos + np.array([width / 2, 0]),
                            t,
                        )
                        t_next = (i + 1) / (steps - 1)
                        p2 = self._bezier_point(
                            pos + np.array([width / 2, height]),
                            cp1,
                            cp2,
                            child_pos + np.array([width / 2, 0]),
                            t_next,
                        )

                        # Draw with enhanced gradient
                        alpha = 0.4 * (1 - t)  # Higher base opacity
                        glColor4f(0.9, 0.9, 0.9, alpha)  # Brighter lines
                        glVertex2f(*p1)
                        glVertex2f(*p2)

            glEnd()

    def _bezier_point(self, p0, p1, p2, p3, t):
        """Calculate point on a cubic bezier curve."""
        return (
            (1 - t) ** 3 * p0
            + 3 * (1 - t) ** 2 * t * p1
            + 3 * (1 - t) * t**2 * p2
            + t**3 * p3
        )

    def _draw_folder_icon(self, x, y, size):
        """Draw a folder icon."""
        glColor4f(0.9, 0.7, 0.2, 0.9)  # Folder color
        self._draw_rounded_rect(x, y, size, size, 2)
        glColor4f(1.0, 0.8, 0.3, 0.9)  # Tab color
        self._draw_rounded_rect(x, y - size / 4, size / 2, size / 3, 1)

        # Draw expansion indicator
        node = (
            self.selected_node
            if self.selected_node and self.selected_node.is_dir
            else None
        )
        if (
            node
            and node.position[0] == x - 12 * self.zoom_level
            and node.position[1] == y - (40 * self.zoom_level - size) / 2
        ):
            glColor4f(1.0, 1.0, 1.0, 0.9)
            glLineWidth(2.0 * self.zoom_level)
            glBegin(GL_LINES)
            # Horizontal line
            glVertex2f(x + size * 0.25, y + size * 0.5)
            glVertex2f(x + size * 0.75, y + size * 0.5)
            # Vertical line (only if not expanded)
            if not node.expanded:
                glVertex2f(x + size * 0.5, y + size * 0.25)
                glVertex2f(x + size * 0.5, y + size * 0.75)
            glEnd()

    def _draw_file_icon(self, x, y, size):
        """Draw a file icon."""
        glColor4f(0.8, 0.8, 0.8, 0.9)
        self._draw_rounded_rect(x, y, size * 0.8, size, 2)
        # Draw lines representing text
        glColor4f(0.6, 0.6, 0.6, 0.5)
        for i in range(3):
            glBegin(GL_LINES)
            glVertex2f(x + size * 0.2, y + size * (0.3 + i * 0.2))
            glVertex2f(x + size * 0.6, y + size * (0.3 + i * 0.2))
            glEnd()

    def _draw_status_indicator(
        self, x: float, y: float, size: float, color: List[float]
    ):
        """Draw a status indicator dot."""
        glColor4f(*color, 0.9)
        segments = 20
        glBegin(GL_POLYGON)
        for i in range(segments):
            angle = 2 * np.pi * i / segments
            glVertex2f(
                x + size / 2 + np.cos(angle) * size / 2,
                y + size / 2 + np.sin(angle) * size / 2,
            )
        glEnd()
        # Draw highlight
        glColor4f(1.0, 1.0, 1.0, 0.3)
        glBegin(GL_POLYGON)
        for i in range(segments // 2):
            angle = -np.pi / 2 + np.pi * i / (segments // 2)
            glVertex2f(
                x + size / 2 + np.cos(angle) * size / 3,
                y + size / 2 + np.sin(angle) * size / 3,
            )
        glEnd()

    def _draw_rounded_rect(self, x: float, y: float, w: float, h: float, r: float):
        """Draw a filled rounded rectangle."""
        segments = 30  # Number of segments for corners

        glBegin(GL_POLYGON)

        # Top edge
        glVertex2f(x + r, y)
        glVertex2f(x + w - r, y)

        # Top-right corner
        for i in range(segments + 1):
            angle = i * np.pi / (2 * segments)
            glVertex2f(x + w - r + r * np.cos(angle), y + r - r * np.sin(angle))

        # Right edge
        glVertex2f(x + w, y + r)
        glVertex2f(x + w, y + h - r)

        # Bottom-right corner
        for i in range(segments + 1):
            angle = i * np.pi / (2 * segments)
            glVertex2f(
                x + w - r + r * np.cos(angle + np.pi / 2),
                y + h - r + r * np.sin(angle + np.pi / 2),
            )

        # Bottom edge
        glVertex2f(x + w - r, y + h)
        glVertex2f(x + r, y + h)

        # Bottom-left corner
        for i in range(segments + 1):
            angle = i * np.pi / (2 * segments)
            glVertex2f(
                x + r - r * np.cos(angle + np.pi), y + h - r + r * np.sin(angle + np.pi)
            )

        # Left edge
        glVertex2f(x, y + h - r)
        glVertex2f(x, y + r)

        # Top-left corner
        for i in range(segments + 1):
            angle = i * np.pi / (2 * segments)
            glVertex2f(
                x + r - r * np.cos(angle + 3 * np.pi / 2),
                y + r - r * np.sin(angle + 3 * np.pi / 2),
            )

        glEnd()

    def _draw_rounded_rect_outline(
        self, x: float, y: float, w: float, h: float, r: float
    ):
        """Draw a rounded rectangle outline."""
        segments = 30  # Number of segments for corners

        glBegin(GL_LINE_LOOP)

        # Top edge
        glVertex2f(x + r, y)
        glVertex2f(x + w - r, y)

        # Top-right corner
        for i in range(segments + 1):
            angle = i * np.pi / (2 * segments)
            glVertex2f(x + w - r + r * np.cos(angle), y + r - r * np.sin(angle))

        # Right edge
        glVertex2f(x + w, y + r)
        glVertex2f(x + w, y + h - r)

        # Bottom-right corner
        for i in range(segments + 1):
            angle = i * np.pi / (2 * segments)
            glVertex2f(
                x + w - r + r * np.cos(angle + np.pi / 2),
                y + h - r + r * np.sin(angle + np.pi / 2),
            )

        # Bottom edge
        glVertex2f(x + w - r, y + h)
        glVertex2f(x + r, y + h)

        # Bottom-left corner
        for i in range(segments + 1):
            angle = i * np.pi / (2 * segments)
            glVertex2f(
                x + r - r * np.cos(angle + np.pi), y + h - r + r * np.sin(angle + np.pi)
            )

        # Left edge
        glVertex2f(x, y + h - r)
        glVertex2f(x, y + r)

        # Top-left corner
        for i in range(segments + 1):
            angle = i * np.pi / (2 * segments)
            glVertex2f(
                x + r - r * np.cos(angle + 3 * np.pi / 2),
                y + r - r * np.sin(angle + 3 * np.pi / 2),
            )

        glEnd()

    def handle_input(self) -> bool:
        """Handle user input for navigation."""
        for event in pygame.event.get():
            if event.type == QUIT:
                return False
            elif event.type == MOUSEBUTTONDOWN:
                if event.button == 4:  # Mouse wheel up
                    old_zoom = self.zoom_level
                    self.zoom_level = min(self.max_zoom, self.zoom_level * 1.1)
                    # Adjust pan to zoom towards mouse position
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    self.pan_offset[0] = mouse_x - (mouse_x - self.pan_offset[0]) * 1.1
                    self.pan_offset[1] = mouse_y - (mouse_y - self.pan_offset[1]) * 1.1
                    # Update visibility based on zoom level
                    if old_zoom < 1.0 and self.zoom_level >= 1.0:
                        self._update_visibility(True)
                elif event.button == 5:  # Mouse wheel down
                    old_zoom = self.zoom_level
                    self.zoom_level = max(self.min_zoom, self.zoom_level / 1.1)
                    # Adjust pan to zoom towards mouse position
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    self.pan_offset[0] = mouse_x - (mouse_x - self.pan_offset[0]) / 1.1
                    self.pan_offset[1] = mouse_y - (mouse_y - self.pan_offset[1]) / 1.1
                    # Update visibility based on zoom level
                    if old_zoom >= 1.0 and self.zoom_level < 1.0:
                        self._update_visibility(False)
                elif event.button == 1:  # Left click
                    self._handle_click(event.pos)
                elif event.button == 3:  # Right click - Pan
                    pygame.mouse.get_rel()
                    pygame.event.set_grab(True)
            elif event.type == MOUSEBUTTONUP:
                if event.button == 3:
                    pygame.event.set_grab(False)
            elif event.type == pygame.MOUSEMOTION:
                if pygame.mouse.get_pressed()[2]:  # Right mouse button
                    rel_x, rel_y = pygame.mouse.get_rel()
                    self.pan_offset += np.array([rel_x, rel_y])
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    return False
                elif event.key == K_i:
                    self.show_info = not self.show_info
                elif event.key == K_r:
                    # Schedule refresh in the event loop
                    asyncio.create_task(self._refresh_git_status())
                elif event.key == K_SPACE:  # Reset view
                    self.zoom_level = 1.0
                    self.pan_offset = np.array(
                        [
                            (1200 - self.root_node.total_width) / 2,
                            (800 - self.root_node.total_height) / 2,
                        ]
                    )
                    self._update_visibility(True)
                elif event.key == K_c:  # Collapse all directories
                    self.root_node.collapse_all()
                    self.layout_nodes()
        return True

    def _update_visibility(self, show_all: bool):
        """Update visibility of all nodes based on zoom level."""
        for node in self.nodes:
            if not node.is_dir:
                node.visible = show_all
            else:
                node.visible = True  # Always show directories

    def _handle_click(self, pos: tuple):
        """Handle mouse click for node selection in 2D space."""
        x, y = pos
        closest_node = None
        min_dist = float("inf")

        for node in self.nodes:
            if not node.visible:
                continue

            node_pos = node.position[:2] + self.pan_offset
            dist = np.sqrt((x - node_pos[0]) ** 2 + (y - node_pos[1]) ** 2)

            if dist < min_dist and dist < node.size * 20 * self.zoom_level:
                min_dist = dist
                closest_node = node

        if closest_node:
            if closest_node.is_dir:
                # Toggle directory expansion
                closest_node.toggle_expand()
                self.layout_nodes()  # Relayout to account for visibility changes
            self.selected_node = closest_node

    async def _refresh_git_status(self):
        """Refresh Git status information asynchronously."""
        logging.info("Refreshing Git repository status")
        try:
            self.staged_files = set(get_staged_files())
            self.modified_files = set(get_modified_files())
            self.current_branch = get_current_branch()
            pygame.display.set_caption(f"QGit Ancestry - {self.current_branch}")

            # Prepare nodes for batch processing
            nodes_to_update = [
                (node, self._get_relative_path(node))
                for node in self.nodes
                if not node.is_dir
            ]

            # Process nodes in batches
            BATCH_SIZE = 50
            updated_count = 0

            for i in range(0, len(nodes_to_update), BATCH_SIZE):
                batch = nodes_to_update[i : i + BATCH_SIZE]
                batch_tasks = []
                for node, rel_path in batch:
                    task = asyncio.create_task(
                        self._update_node_git_info(node, rel_path)
                    )
                    batch_tasks.append(task)

                # Wait for batch to complete
                await asyncio.gather(*batch_tasks)
                updated_count += len(batch)

                # Allow events to be processed between batches
                pygame.event.pump()

            logging.info(
                f"Updated {updated_count} files, found {len(self.staged_files)} staged and {len(self.modified_files)} modified files"
            )

        except Exception as e:
            logging.error(f"Error refreshing Git status: {e}", exc_info=True)

    def _get_relative_path(self, node: Node) -> str:
        """Get relative path for a node."""
        path_parts = []
        current = node
        while current and current != self.root_node:
            path_parts.append(current.name)
            current = current.parent
        return os.path.join(*reversed(path_parts))

    def update(self) -> bool:
        """Update visualization state."""
        current_time = time.time()
        dt = current_time - self.last_time
        self.last_time = current_time

        # Handle input
        if not self.handle_input():
            return False

        # Update node positions
        for node in self.nodes:
            node.update_position(dt)

        return True

    def draw(self):
        """Draw the visualization with 3D-like effects."""
        glClear(GL_COLOR_BUFFER_BIT)
        glLoadIdentity()

        # Draw all nodes
        for node in reversed(self.nodes):  # Draw from back to front
            if node.visible:
                self.draw_node(node)

        # Draw info panel
        self.draw_info_panel()

        pygame.display.flip()

    def draw_info_panel(self):
        """Draw information panel for selected node."""
        if not self.selected_node or not self.show_info:
            return

        node = self.selected_node
        info_lines = [
            f"Name: {node.name}",
            f"Type: {'Directory' if node.is_dir else 'File'}",
        ]

        if not node.is_dir:
            info_lines.extend(
                [
                    f"Size: {format_size(node.file_size)}",
                    f"Commits: {node.commit_count}",
                    f"Contributors: {len(node.contributors)}",
                    f"Status: {'Staged' if node.staged else 'Modified' if node.modified else 'Unchanged'}",
                    (
                        f"Last commit: {node.last_commit_message[:40]}..."
                        if node.last_commit_message
                        else "No commits"
                    ),
                ]
            )

        self._render_text_overlay(info_lines)

    def _render_text_overlay(self, lines: List[str]):
        """Render text overlay in 2D."""
        # Switch to orthographic projection for 2D rendering
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, 1200, 800, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        # Disable 3D features
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)

        # Draw semi-transparent background
        glColor4f(0.0, 0.0, 0.0, 0.7)
        glBegin(GL_QUADS)
        glVertex2f(10, 10)
        glVertex2f(400, 10)
        glVertex2f(400, 30 * len(lines) + 20)
        glVertex2f(10, 30 * len(lines) + 20)
        glEnd()

        # Render text
        font = pygame.font.Font(None, 24)
        for i, line in enumerate(lines):
            surface = font.render(line, True, (255, 255, 255))
            texture = self._surface_to_texture(surface)
            self._draw_texture_quad(texture, 20, 20 + i * 30, *surface.get_size())
            glDeleteTextures([texture])

        # Restore 3D state
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()

    def _surface_to_texture(self, surface: pygame.Surface) -> int:
        """Convert Pygame surface to OpenGL texture."""
        texture_data = pygame.image.tostring(surface, "RGBA", True)
        texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture)
        glTexImage2D(
            GL_TEXTURE_2D,
            0,
            GL_RGBA,
            surface.get_width(),
            surface.get_height(),
            0,
            GL_RGBA,
            GL_UNSIGNED_BYTE,
            texture_data,
        )
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        return texture

    def _draw_texture_quad(self, texture: int, x: float, y: float, w: float, h: float):
        """Draw a textured quad at specified position."""
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, texture)
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0)
        glVertex2f(x, y)
        glTexCoord2f(1, 0)
        glVertex2f(x + w, y)
        glTexCoord2f(1, 1)
        glVertex2f(x + w, y + h)
        glTexCoord2f(0, 1)
        glVertex2f(x, y + h)
        glEnd()
        glDisable(GL_TEXTURE_2D)

    def run(self):
        """Main visualization loop."""
        logging.info("Starting visualization loop")
        try:
            running = True
            frames = 0
            start_time = time.time()

            while running:
                running = self.update()
                self.draw()
                pygame.time.wait(10)

                frames += 1
                if frames % 100 == 0:  # Log FPS every 100 frames
                    current_time = time.time()
                    fps = frames / (current_time - start_time)
                    logging.debug(f"Current FPS: {fps:.2f}")
                    frames = 0
                    start_time = current_time

        except Exception as e:
            logging.error(f"Error in visualization loop: {e}", exc_info=True)
        finally:
            logging.info("Shutting down visualization")
            pygame.quit()

    async def _update_node_git_info(self, node: Node, rel_path: str):
        """Update Git-related information for a node asynchronously."""
        try:
            # Check cache first
            if rel_path in self._git_history_cache:
                cached_data = self._git_history_cache[rel_path]
                node.commit_count = cached_data["commit_count"]
                node.last_modified = cached_data["last_modified"]
                node.last_commit_message = cached_data["last_commit_message"]
                node.contributors = cached_data["contributors"]
                node.color = self._get_node_color(node)
                return

            # Use a more efficient Git command that combines all needed info
            try:
                process = await asyncio.create_subprocess_exec(
                    "git",
                    "log",
                    "--follow",
                    "--max-count=3",  # Reduced from 5 to 3
                    "--format=%H%x00%an%x00%at%x00%s",
                    "--",
                    rel_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=self.repo_path,
                )

                try:
                    stdout, _ = await asyncio.wait_for(
                        process.communicate(), timeout=0.2
                    )  # Reduced timeout
                    if process.returncode == 0:
                        commits = []
                        contributors = set()
                        for line in stdout.decode().strip().split("\n"):
                            if line:
                                hash_, author, timestamp, msg = line.split("\0")
                                commits.append((hash_, author, float(timestamp), msg))
                                contributors.add(author)

                        if commits:
                            # Update cache with processed data
                            cache_data = {
                                "commit_count": len(commits),
                                "last_modified": commits[0][2],
                                "last_commit_message": commits[0][3],
                                "contributors": contributors,
                            }
                            self._git_history_cache[rel_path] = cache_data

                            # Update node directly from processed data
                            node.commit_count = len(commits)
                            node.last_modified = commits[0][2]
                            node.last_commit_message = commits[0][3]
                            node.contributors = contributors
                            node.color = self._get_node_color(node)
                            return

                except asyncio.TimeoutError:
                    pass

            except Exception:
                pass

            # Default color for files without history
            node.color = np.array([0.5, 0.5, 0.5, 1.0])

        except Exception:
            node.color = np.array([0.5, 0.5, 0.5, 1.0])

    def _get_node_color(self, node: Node) -> np.ndarray:
        """Get node color based on its state and history."""
        if node.staged:
            return np.array([0.3, 0.9, 0.3, 0.95])  # Vivid green for staged
        elif node.modified:
            return np.array([0.9, 0.3, 0.3, 0.95])  # Vivid red for modified
        elif node.is_dir:
            if len(node.children) > 5:
                return np.array(
                    [0.3, 0.4, 0.9, 0.95]
                )  # Vivid blue for large directories
            else:
                return np.array(
                    [0.3, 0.5, 0.8, 0.95]
                )  # Lighter blue for small directories
        else:
            # Enhanced color scheme for files based on activity
            if node.commit_count > 10:
                return np.array([0.7, 0.4, 0.7, 0.95])  # Vivid purple for high activity
            elif node.commit_count > 5:
                return np.array(
                    [0.7, 0.5, 0.3, 0.95]
                )  # Vivid orange for medium activity
            else:
                return np.array(
                    [0.4, 0.6, 0.7, 0.95]
                )  # Vivid blue-gray for low activity

    def build_tree(self):
        """Synchronous version of tree building for compatibility."""
        try:
            logging.info("Starting synchronous tree building")
            asyncio.run(self.build_tree_async())
            logging.info("Synchronous tree building complete")
        except Exception as e:
            logging.error(f"Error in synchronous tree building: {e}", exc_info=True)
            raise


def show_loading_screen(progress: float, message: str) -> bool:
    """Display a loading screen with progress bar and message.
    Returns False if the user cancels, True otherwise."""
    try:
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Set up orthographic projection for 2D rendering
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, 1200, 800, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        # Disable 3D features during loading
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)

        # Draw progress bar background
        glColor4f(0.2, 0.2, 0.2, 1.0)
        glBegin(GL_QUADS)
        glVertex2f(300, 390)
        glVertex2f(900, 390)
        glVertex2f(900, 410)
        glVertex2f(300, 410)
        glEnd()

        # Draw progress bar fill
        glColor4f(0.0, 0.7, 0.0, 1.0)
        glBegin(GL_QUADS)
        glVertex2f(300, 390)
        glVertex2f(300 + 600 * progress, 390)
        glVertex2f(300 + 600 * progress, 410)
        glVertex2f(300, 410)
        glEnd()

        # Render text using Pygame
        try:
            font = pygame.font.Font(None, 36)
            text = font.render(message, True, (255, 255, 255))
            text_surface = pygame.image.tostring(text, "RGBA", True)

            # Create OpenGL texture
            texture = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, texture)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexImage2D(
                GL_TEXTURE_2D,
                0,
                GL_RGBA,
                text.get_width(),
                text.get_height(),
                0,
                GL_RGBA,
                GL_UNSIGNED_BYTE,
                text_surface,
            )

            # Draw text
            glEnable(GL_TEXTURE_2D)
            glColor4f(1.0, 1.0, 1.0, 1.0)
            glBegin(GL_QUADS)
            glTexCoord2f(0, 0)
            glVertex2f(600 - text.get_width() / 2, 350)
            glTexCoord2f(1, 0)
            glVertex2f(600 + text.get_width() / 2, 350)
            glTexCoord2f(1, 1)
            glVertex2f(600 + text.get_width() / 2, 350 + text.get_height())
            glTexCoord2f(0, 1)
            glVertex2f(600 - text.get_width() / 2, 350 + text.get_height())
            glEnd()
            glDisable(GL_TEXTURE_2D)

            glDeleteTextures([texture])
        except Exception as e:
            logging.warning(f"Error rendering text: {str(e)}")
            # Continue even if text rendering fails

        pygame.display.flip()

        # Handle events during loading
        for event in pygame.event.get():
            if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
                pygame.quit()
                return False
        return True

    except Exception as e:
        logging.error(f"Error in loading screen: {str(e)}")
        return False


class LoadingVisualizer(GitVisualizer):
    def __init__(self, repo_path: str):
        try:
            logging.info(f"Initializing LoadingVisualizer for repository: {repo_path}")
            # Initialize resource manager
            self.resource_manager = get_resource_manager(
                os.path.join(repo_path, ".qgit_cache")
            )
            logging.info("Resource manager initialized")

            # Initialize base class but skip tree building
            self.repo_path = repo_path
            if not is_git_repo():
                logging.error("Not a Git repository")
                raise ValueError("Not a Git repository")

            # Initialize basic properties
            self.root_node = None
            self.nodes = []
            self.selected_node = None
            self.zoom_level = 1.0
            self.show_info = True
            self.pan_offset = np.array([600.0, 400.0])
            self.min_zoom = 0.3
            self.max_zoom = 3.0
            self.initial_center = True
            self.font_cache = {}

            # Cache Git information
            logging.info("Caching Git repository information")
            self.current_branch = get_current_branch()
            self.staged_files = set(get_staged_files())
            self.modified_files = set(get_modified_files())
            self._git_history_cache = {}

            logging.info(f"Current branch: {self.current_branch}")
            logging.info(
                f"Found {len(self.staged_files)} staged files and {len(self.modified_files)} modified files"
            )

            # Animation properties
            self.last_time = time.time()
            self.animation_speed = 1.0

            # Initialize Pygame and OpenGL
            logging.info("Initializing Pygame and OpenGL")
            pygame.init()
            pygame.font.init()

            # Set up display with proper flags for macOS
            if sys.platform == "darwin":
                logging.info("Configuring macOS-specific display settings")
                os.environ["SDL_VIDEO_DRIVER"] = "cocoa"
                pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 2)
                pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 1)
                pygame.display.gl_set_attribute(
                    pygame.GL_CONTEXT_PROFILE_MASK,
                    pygame.GL_CONTEXT_PROFILE_COMPATIBILITY,
                )
                pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE, 16)
                pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1)
                pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, 4)

            try:
                logging.info("Creating OpenGL display window")
                self.screen = pygame.display.set_mode((1200, 800), DOUBLEBUF | OPENGL)
            except pygame.error as e:
                logging.critical(f"Failed to create OpenGL context: {e}", exc_info=True)
                raise RuntimeError(
                    "Failed to initialize display. Please ensure OpenGL is supported on your system."
                )

            pygame.display.set_caption("QGit Visualizer - Loading...")

            # Set up basic OpenGL for loading screen
            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()
            glOrtho(0, 1200, 800, 0, -1, 1)
            glMatrixMode(GL_MODELVIEW)
            glLoadIdentity()

        except Exception as e:
            logging.critical(
                f"Failed to initialize LoadingVisualizer: {e}", exc_info=True
            )
            pygame.quit()
            raise RuntimeError(f"Failed to initialize visualizer: {str(e)}")

    async def build_tree_async(self):
        """Build the repository tree structure asynchronously with loading screen."""
        try:
            logging.info("Starting asynchronous tree building")

            # Create root node
            self.root_node = Node(os.path.basename(self.repo_path), True)
            self.nodes = [self.root_node]

            # Directory node cache for faster lookups
            dir_node_cache = {".": self.root_node}

            # First pass: collect all paths and count files
            all_paths = []
            total_files = 0

            # Use os.walk with topdown=True for better memory efficiency
            for root, dirs, files in os.walk(self.repo_path, topdown=True):
                if ".git" in dirs:  # Skip .git directory
                    dirs.remove(".git")

                rel_root = os.path.relpath(root, self.repo_path)

                # Add directory to paths if not root
                if rel_root != ".":
                    all_paths.append((rel_root, True))  # True indicates directory

                    # Create and cache directory node structure
                    current_path = []
                    for part in rel_root.split(os.sep):
                        current_path.append(part)
                        dir_path = os.path.join(*current_path)
                        if dir_path not in dir_node_cache:
                            parent_path = os.path.dirname(dir_path) or "."
                            parent_node = dir_node_cache[parent_path]
                            new_node = Node(part, True, parent_node.depth + 1)
                            parent_node.add_child(new_node)
                            self.nodes.append(new_node)
                            dir_node_cache[dir_path] = new_node

                # Add files
                for file in files:
                    rel_path = os.path.join(rel_root, file).replace("\\", "/")
                    if rel_root == ".":
                        rel_path = file
                    all_paths.append((rel_path, False))  # False indicates file
                    total_files += 1

            processed_files = 0
            DIR_BATCH_SIZE = 25  # Smaller batch size for directory processing
            FILE_BATCH_SIZE = 50  # Moderate batch size for file processing
            CHUNK_SIZE = 1000  # Keep chunk size for memory management
            UPDATE_FREQUENCY = 4  # Keep update frequency

            # Process directories first in smaller batches
            dir_nodes = []
            for rel_path, is_dir in all_paths:
                if is_dir:
                    current_path = []
                    for part in rel_path.split(os.sep):
                        current_path.append(part)
                        dir_path = os.path.join(*current_path)
                        if dir_path not in dir_node_cache:
                            parent_path = os.path.dirname(dir_path) or "."
                            parent_node = dir_node_cache[parent_path]
                            new_node = Node(part, True, parent_node.depth + 1)
                            parent_node.add_child(new_node)
                            self.nodes.append(new_node)
                            dir_node_cache[dir_path] = new_node
                            dir_nodes.append(new_node)

                            # Process directory batch
                            if len(dir_nodes) >= DIR_BATCH_SIZE:
                                await asyncio.sleep(0.01)  # Allow UI updates
                                pygame.event.pump()
                                dir_nodes = []

            # Process remaining directories
            if dir_nodes:
                await asyncio.sleep(0.01)
                pygame.event.pump()

            # Pre-create all file nodes with status checks
            file_nodes = []
            for rel_path, is_dir in all_paths:
                if not is_dir:
                    dir_path = os.path.dirname(rel_path) or "."
                    file_name = os.path.basename(rel_path)
                    parent_node = dir_node_cache[dir_path]
                    file_node = Node(file_name, False, parent_node.depth + 1)
                    parent_node.add_child(file_node)
                    self.nodes.append(file_node)

                    # Quick status check without Git commands
                    file_node.staged = rel_path in self.staged_files
                    file_node.modified = rel_path in self.modified_files
                    try:
                        file_node.file_size = os.path.getsize(
                            os.path.join(self.repo_path, rel_path)
                        )
                    except (OSError, IOError):
                        pass

                    file_nodes.append((file_node, rel_path))

                    # Process file batch
                    if len(file_nodes) >= FILE_BATCH_SIZE:
                        # Create tasks for batch processing
                        batch_tasks = [
                            self._update_node_git_info(node, rel_path)
                            for node, rel_path in file_nodes
                        ]

                        # Process batch concurrently
                        await asyncio.gather(*batch_tasks)
                        processed_files += len(file_nodes)

                        # Update progress
                        progress = processed_files / total_files
                        if not show_loading_screen(
                            progress,
                            f"Processing files... ({processed_files}/{total_files})",
                        ):
                            raise KeyboardInterrupt

                        # Allow UI updates and event processing
                        pygame.event.pump()
                        await asyncio.sleep(0.01)

                        # Garbage collection if needed
                        if processed_files % CHUNK_SIZE == 0:
                            gc.collect(0)  # Only collect youngest generation
                            await asyncio.sleep(0.01)

                        file_nodes = []

            # Process remaining files
            if file_nodes:
                batch_tasks = [
                    self._update_node_git_info(node, rel_path)
                    for node, rel_path in file_nodes
                ]
                await asyncio.gather(*batch_tasks)
                processed_files += len(file_nodes)

            logging.info(f"Tree building complete. Processed {processed_files} files.")

            # Set up OpenGL for visualization after tree building
            pygame.display.set_caption(f"QGit Visualizer - {self.current_branch}")
            self._setup_opengl()
            self.layout_nodes()
            logging.info("LoadingVisualizer initialization complete")

        except KeyboardInterrupt:
            logging.info("Tree building cancelled by user")
            raise
        except Exception as e:
            logging.error(f"Error building tree: {e}", exc_info=True)
            raise

    def draw(self):
        """Draw the visualization with 3D-like effects."""
        glClear(GL_COLOR_BUFFER_BIT)
        glLoadIdentity()

        # Draw all nodes
        for node in reversed(self.nodes):  # Draw from back to front
            if node.visible:
                self.draw_node(node)

        # Draw info panel
        self.draw_info_panel()

        pygame.display.flip()

    def draw_info_panel(self):
        """Draw information panel for selected node."""
        if not self.selected_node or not self.show_info:
            return

        node = self.selected_node
        info_lines = [
            f"Name: {node.name}",
            f"Type: {'Directory' if node.is_dir else 'File'}",
        ]

        if not node.is_dir:
            info_lines.extend(
                [
                    f"Size: {format_size(node.file_size)}",
                    f"Commits: {node.commit_count}",
                    f"Contributors: {len(node.contributors)}",
                    f"Status: {'Staged' if node.staged else 'Modified' if node.modified else 'Unchanged'}",
                    (
                        f"Last commit: {node.last_commit_message[:40]}..."
                        if node.last_commit_message
                        else "No commits"
                    ),
                ]
            )

        self._render_text_overlay(info_lines)

    def _render_text_overlay(self, lines: List[str]):
        """Render text overlay in 2D."""
        # Switch to orthographic projection for 2D rendering
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, 1200, 800, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        # Disable 3D features
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)

        # Draw semi-transparent background
        glColor4f(0.0, 0.0, 0.0, 0.7)
        glBegin(GL_QUADS)
        glVertex2f(10, 10)
        glVertex2f(400, 10)
        glVertex2f(400, 30 * len(lines) + 20)
        glVertex2f(10, 30 * len(lines) + 20)
        glEnd()

        # Render text
        font = pygame.font.Font(None, 24)
        for i, line in enumerate(lines):
            surface = font.render(line, True, (255, 255, 255))
            texture = self._surface_to_texture(surface)
            self._draw_texture_quad(texture, 20, 20 + i * 30, *surface.get_size())
            glDeleteTextures([texture])

        # Restore 3D state
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()

    def _surface_to_texture(self, surface: pygame.Surface) -> int:
        """Convert Pygame surface to OpenGL texture."""
        texture_data = pygame.image.tostring(surface, "RGBA", True)
        texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture)
        glTexImage2D(
            GL_TEXTURE_2D,
            0,
            GL_RGBA,
            surface.get_width(),
            surface.get_height(),
            0,
            GL_RGBA,
            GL_UNSIGNED_BYTE,
            texture_data,
        )
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        return texture

    def _draw_texture_quad(self, texture: int, x: float, y: float, w: float, h: float):
        """Draw a textured quad at specified position."""
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, texture)
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0)
        glVertex2f(x, y)
        glTexCoord2f(1, 0)
        glVertex2f(x + w, y)
        glTexCoord2f(1, 1)
        glVertex2f(x + w, y + h)
        glTexCoord2f(0, 1)
        glVertex2f(x, y + h)
        glEnd()
        glDisable(GL_TEXTURE_2D)

    def run(self):
        """Main visualization loop."""
        logging.info("Starting visualization loop")
        try:
            running = True
            frames = 0
            start_time = time.time()

            while running:
                running = self.update()
                self.draw()
                pygame.time.wait(10)

                frames += 1
                if frames % 100 == 0:  # Log FPS every 100 frames
                    current_time = time.time()
                    fps = frames / (current_time - start_time)
                    logging.debug(f"Current FPS: {fps:.2f}")
                    frames = 0
                    start_time = current_time

        except Exception as e:
            logging.error(f"Error in visualization loop: {e}", exc_info=True)
        finally:
            logging.info("Shutting down visualization")
            pygame.quit()

    def build_tree(self):
        """Synchronous version of tree building for compatibility."""
        try:
            logging.info("Starting synchronous tree building")
            asyncio.run(self.build_tree_async())
            logging.info("Synchronous tree building complete")
        except Exception as e:
            logging.error(f"Error in synchronous tree building: {e}", exc_info=True)
            raise


def visualize_repo(repo_path: str = None):
    """Create and run the visualizer for a repository."""
    try:
        if not is_git_repo():
            logging.error("Not a Git repository")
            print("Error: Not a Git repository")
            return

        if repo_path is None:
            repo_path = os.getcwd()

        logging.info(f"Starting Git visualization for repository: {repo_path}")
        print("\nInitializing Git visualization...")
        print("This may take a few moments for large repositories.")
        print("Press Ctrl+C to cancel at any time.\n")

        try:
            # Run everything in an async context
            async def init_and_run():
                visualizer = LoadingVisualizer(repo_path)
                await visualizer.build_tree_async()  # Build tree asynchronously
                visualizer.run()  # Run main loop

            # Use asyncio to run the async initialization
            asyncio.run(init_and_run())

        except RuntimeError as e:
            error_msg = str(e)
            logging.error(f"Runtime error during visualization: {error_msg}")
            print(f"\nError: {error_msg}")
            print(
                "Please ensure you have OpenGL support and up-to-date graphics drivers."
            )
            if sys.platform == "darwin":
                logging.info("Providing macOS-specific troubleshooting information")
                print("\nOn macOS, you might need to:")
                print("1. Install XQuartz (https://www.xquartz.org)")
                print("2. Ensure pygame is installed with: pip install pygame --user")
                print(
                    "3. Try running in a different terminal or after restarting your machine"
                )

    except KeyboardInterrupt:
        logging.info("Visualization cancelled by user")
        print("\nVisualization cancelled by user.")
    except Exception as e:
        logging.error("Unexpected error in visualization", exc_info=True)
        print(f"Error launching visualization: {str(e)}")
    finally:
        pygame.quit()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        repo_path = sys.argv[1]
    else:
        repo_path = os.getcwd()
    visualize_repo(repo_path)
