#!/usr/bin/env python3

import curses
import logging
import math
import os
import random
import subprocess
import sys
import time
from itertools import cycle

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)

def load_environment():
    """Load environment variables from .env file"""
    try:
        from dotenv.main import load_dotenv
    except ImportError:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "python-dotenv==1.0.1"]
        )
        from dotenv.main import load_dotenv

    # Get the real path of the script, following symlinks
    script_path = os.path.realpath(__file__)
    script_dir = os.path.dirname(script_path)

    # Look for .env in the script's actual directory
    env_path = os.path.join(script_dir, ".env")

    if not os.path.exists(env_path):
        print(f"Error: .env file not found at {env_path}")
        sys.exit(1)

    # Load the .env file
    load_dotenv(env_path)


# Import QGitConfig from qgit_config
try:
    script_dir = os.path.dirname(os.path.realpath(__file__))
    sys.path.insert(0, script_dir)
    from qgits.qgit_config import QGitConfig
except ImportError:
    print(
        "Error: Could not import QGitConfig. Please ensure qgits/qgit_config.py exists."
    )
    sys.exit(1)

QGIT_LOGO = """\
     ██████╗█╗██████╗ ██╗████████╗
    ██╔═══██╗██╔════╝ ██║╚══██╔══╝
    ██║   ██║██║  ███╗██║   ██║   
    ██║▄▄ ██║██║   ██║██║   ██║   
    ╚██████╔╝╚██████╔╝██║   ██║   
     ╚══▀▀═╝▄╚═════╝ ╚═╝   ╚═╝   """


class LoadingAnimation:
    """Class to handle various loading animations."""

    SPINNERS = {
        "dots": ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"],
        "line": ["|", "/", "-", "\\"],
        "braille": ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"],
        "pulse": ["█", "▉", "▊", "▋", "▌", "▍", "▎", "▏", "▎", "▍", "▌", "▋", "▊", "▉"],
    }

    TOOLKIT_FRAMES = [
        "⟦ Griffin's Toolkit ⟧",
        "⟪ Griffin's Toolkit ⟫",
        "『 Griffin's Toolkit 』",
        "《 Griffin's Toolkit 》",
        "【 Griffin's Toolkit 】",
        "《 Griffin's Toolkit 》",
        "『 Griffin's Toolkit 』",
        "⟪ Griffin's Toolkit ⟫",
    ]

    QGIT_LOGO = QGIT_LOGO

    def __init__(self, stdscr, style="dots"):
        self.stdscr = stdscr
        self.spinner = cycle(self.SPINNERS[style])
        self.toolkit_spinner = cycle(self.TOOLKIT_FRAMES)
        self.running = False
        self.thread = None


class SecretSauceWindow:
    """Hidden window showing repository insights from SecretSauce."""

    def __init__(self, stdscr):
        self.stdscr = stdscr


    def draw_border(self, y, x, height, width):
        """Draw a stylish border around the window."""
        # Top border with title
        self.stdscr.addstr(y, x, "╭" + "─" * (width - 2) + "╮", curses.color_pair(6))
        # Side borders
        for i in range(height - 2):
            self.stdscr.addstr(y + i + 1, x, "│", curses.color_pair(6))
            self.stdscr.addstr(y + i + 1, x + width - 1, "│", curses.color_pair(6))
        # Bottom border
        self.stdscr.addstr(
            y + height - 1, x, "╰" + "─" * (width - 2) + "╯", curses.color_pair(6)
        )

    def show(self):
        """Display the secret sauce window with animations."""
        sauce_data = self.sauce.read_sauce()
        if not sauce_data:
            return

        max_y, max_x = self.stdscr.getmaxyx()
        window_height = 20
        window_width = 60
        start_y = (max_y - window_height) // 2
        start_x = (max_x - window_width) // 2

        # Animation for window appearance
        for i in range(window_height):
            self.stdscr.clear()
            current_height = min(i + 1, window_height)
            self.draw_border(start_y, start_x, current_height, window_width)

            if i >= 2:
                # Draw title
                title = "🔮 Secret Repository Insights 🔮"
                title_x = start_x + (window_width - len(title)) // 2
                self.stdscr.addstr(
                    start_y + 1, title_x, title, curses.color_pair(3) | curses.A_BOLD
                )

            if i >= 4:
                self._draw_content(
                    sauce_data, start_y + 3, start_x + 2, min(i - 3, window_height - 4)
                )

            self.stdscr.refresh()
            time.sleep(0.05)

        # Wait for key press
        while True:
            key = self.stdscr.getch()
            if key in [27, ord("q")]:  # ESC or 'q'
                break

    def _draw_content(self, sauce_data, start_y, start_x, max_lines):
        """Draw the secret sauce content with animations."""
        current_y = start_y
        width = 56

        def add_section(title, content, color=4):
            nonlocal current_y
            if current_y - start_y >= max_lines:
                return
            self.stdscr.addstr(
                current_y, start_x, title, curses.color_pair(6) | curses.A_BOLD
            )
            current_y += 1

            if isinstance(content, dict):
                for key, value in content.items():
                    if current_y - start_y >= max_lines:
                        return
                    text = f"• {key}: {value}"
                    if len(text) > width:
                        text = text[: width - 3] + "..."
                    self.stdscr.addstr(
                        current_y, start_x + 2, text, curses.color_pair(color)
                    )
                    current_y += 1
            elif isinstance(content, list):
                for item in content:
                    if current_y - start_y >= max_lines:
                        return
                    if isinstance(item, dict):
                        text = f"{item['emoji']} {item['title']}: {item['value']}"
                    else:
                        text = f"• {item}"
                    if len(text) > width:
                        text = text[: width - 3] + "..."
                    self.stdscr.addstr(
                        current_y, start_x + 2, text, curses.color_pair(color)
                    )
                    current_y += 1
            current_y += 1

        # Draw insights sections
        if "insights" in sauce_data:
            add_section(
                "🎯 Repository Insights",
                {
                    "Peak Activity": sauce_data["insights"]["peak_productivity"][
                        "peak_period"
                    ].title(),
                    "Commit Style": sauce_data["insights"]["commit_style"][
                        "style"
                    ].title(),
                },
            )

        if "fun_facts" in sauce_data:
            add_section("✨ Fun Facts", sauce_data["fun_facts"], color=3)

        if "easter_eggs" in sauce_data:
            eggs = sauce_data["easter_eggs"]
            if eggs:
                add_section(
                    "🥚 Easter Eggs",
                    [
                        egg["reason"] if "reason" in egg else egg["content"]
                        for egg in eggs
                    ],
                    color=2,
                )


class MatrixRain:
    """Digital rain effect in the background."""

    CHARS = (
        # Japanese Hiragana
        "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん"
        # Japanese Katakana
        "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン"
        # Japanese Kanji (common ones)
        "日月火水木金土年月日時分秒天地人子女山川海空雨雪"
        # Rare Unicode symbols and box drawing
        "⌘⌥⇧⌃⎋⌫⏎⌦⇪⇥⌤⏏⎄⎆⎇⎈⎉⎊⎋⎌⎍⎎⎏⎐⎑⎒⎓⎔⎕"
        # Mathematical symbols
        "∀∁∂∃∄∅∆∇∈∉∊∋∌∍∎∏∐∑−∓∔∕∖∗∘∙√∛∜∝∞∟∠∡∢∣"
        # Currency and other symbols
        "₿¢£¥€₹₽¤฿₪₨₩₮₱₭₲₴₳₵₸₺₼₽₾₿"
        # Arrows and geometric shapes
        "←↑→↓↔↕↖↗↘↙▲▼◄►◆◇○●◐◑◒◓◔◕"
        # Block elements and shades
        "█▀▄▌▐░▒▓■□▢▣▤▥▦▧▨▩▪▫▬▭▮▯▰▱▲▼◄►◆◇○●"
        # Braille patterns (for texture)
        "⠁⠂⠃⠄⠅⠆⠇⠈⠉⠊⠋⠌⠍⠎⠏⠐⠑⠒⠓⠔⠕⠖⠗⠘⠙⠚⠛⠜⠝⠞⠟"
        # Ancient symbols and runes
        "ᚠᚡᚢᚣᚤᚥᚦᚧᚨᚩᚪᚫᚬᚭᚮᚯᚰᚱᚲᚳᚴᚵᚶᚷᚸᚹᚺᚻᚼᚽᚾᚿ"
        # Alchemical symbols
        "🜀🜁🜂🜃🜄🜅🜆🜇🜈🜉🜊🜋🜌🜍🜎🜏🜐🜑🜒🜓🜔🜕🜖🜗"
        # Numbers
        "0123456789"
    )

    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.drops = []
        self.last_update = time.time()
        self.frame_time = 1.0 / 20.0  # Reduced to 20 FPS for smoother animation
        self.accumulated_time = 0.0

        # Initialize fewer drops for less visual noise
        width = curses.COLS
        for x in range(0, width, 3):  # More spacing between drops
            if random.random() < 0.3:  # Reduced probability for fewer drops
                self.drops.append(
                    {
                        "x": x,
                        "y": random.randint(-20, 0),
                        "speed": random.uniform(0.2, 0.6),  # Slower speeds
                        "length": random.randint(3, 8),  # Shorter trails
                        "chars": [random.choice(self.CHARS) for _ in range(8)],
                        "intensity": random.uniform(0.4, 0.8),  # Reduced intensity
                        "color_shift": random.randint(0, 3),  # Less color variation
                        "last_y": None,
                    }
                )

    def update(self):
        """Update and draw matrix rain with improved smoothness."""
        current_time = time.time()
        delta_time = current_time - self.last_update
        self.accumulated_time += delta_time

        if self.accumulated_time < self.frame_time:
            return

        self.last_update = current_time
        self.accumulated_time = 0.0
        height = curses.LINES

        # Update each drop with smoother motion
        for drop in self.drops:
            # Update position with smooth motion
            drop["y"] += drop["speed"]

            # Reset if drop goes off screen
            if drop["y"] > height + drop["length"]:
                drop["y"] = random.randint(-20, 0)
                drop["chars"] = [random.choice(self.CHARS) for _ in range(8)]
                drop["speed"] = random.uniform(0.2, 0.6)  # Randomize speed on reset

            # Draw the drop with smoother fade
            y = int(drop["y"])
            for i in range(drop["length"]):
                if 0 <= y - i < height:
                    try:
                        char = drop["chars"][i % len(drop["chars"])]
                        intensity = 1.0 - (i / drop["length"])

                        # Smoother intensity transitions
                        if intensity > 0.8:
                            attr = curses.color_pair(2) | curses.A_DIM
                        elif intensity > 0.4:
                            attr = curses.color_pair(2) | curses.A_DIM
                        else:
                            attr = curses.color_pair(2) | curses.A_DIM

                        # Only draw if we're not overlapping with other UI elements
                        self.stdscr.addstr(y - i, drop["x"], char, attr)
                    except curses.error:
                        continue


class BoxAnimation:
    """Creates a simple animated box effect around the selected menu item."""

    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.current_y = 0
        self.width = 0
        self.is_animating = False
        self.frame_time = 1.0 / 30.0  # 30 FPS is enough for this effect
        self.last_update = time.time()
        self.box_chars = ["┏━┓", "┃ ┃", "┗━┛"]  # Simple box characters
        self.animation_phase = 0

    def start_animation(self, y, target_width):
        """Start a new box animation."""
        self.current_y = y
        # Only use width for the first word (action) plus emoji
        self.width = min(target_width, 12)  # Limit width to just cover the first word
        self.is_animating = True
        self.animation_phase = 0

    def update(self, menu_start_x):
        """Update and draw the animated box."""
        if not self.is_animating:
            return

        current_time = time.time()
        if current_time - self.last_update < self.frame_time:
            return

        self.last_update = current_time

        # Update animation phase (0-3)
        self.animation_phase = (self.animation_phase + 1) % 4

        try:
            max_y, max_x = self.stdscr.getmaxyx()
            x = menu_start_x - 2  # Add some padding
            y = self.current_y
            width = min(self.width + 4, max_x - x - 1)

            if y < 0 or y >= max_y - 2:
                return

            # Draw top border
            self.stdscr.addstr(
                y - 1, x, self.box_chars[0][0], curses.color_pair(1) | curses.A_BOLD
            )
            for i in range(1, width - 1):
                self.stdscr.addstr(
                    y - 1,
                    x + i,
                    self.box_chars[0][1],
                    curses.color_pair(1) | curses.A_BOLD,
                )
            self.stdscr.addstr(
                y - 1,
                x + width - 1,
                self.box_chars[0][2],
                curses.color_pair(1) | curses.A_BOLD,
            )

            # Draw side borders with animation
            attr = curses.color_pair(1)
            if self.animation_phase < 2:
                attr |= curses.A_BOLD
            self.stdscr.addstr(y, x, self.box_chars[1][0], attr)
            self.stdscr.addstr(y, x + width - 1, self.box_chars[1][2], attr)

            # Draw bottom border
            self.stdscr.addstr(
                y + 1, x, self.box_chars[2][0], curses.color_pair(1) | curses.A_BOLD
            )
            for i in range(1, width - 1):
                self.stdscr.addstr(
                    y + 1,
                    x + i,
                    self.box_chars[2][1],
                    curses.color_pair(1) | curses.A_BOLD,
                )
            self.stdscr.addstr(
                y + 1,
                x + width - 1,
                self.box_chars[2][2],
                curses.color_pair(1) | curses.A_BOLD,
            )

        except curses.error:
            # Silently handle any drawing errors
            pass


class DecryptionEffect:
    """Creates a decryption animation effect for text with enhanced visual effects."""

    CIPHER_CHARS = (
        "!@#$%^&*()_+-=[]{}|;:,.<>?/~`⚡✦✧⭒⭑∴∵⋆★☆✬"
        "⌘⌥⇧⌃⎋⌫⏎⌦⇪⇥⌤⏏⎄⎆⎇⎈⎉⎊⎋⎌⎍⎎⎏⎐⎑⎒⎓⎔⎕"
        "∀∁∂∃∄∅∆∇∈∉∊∋∌∍∎∏∐∑−∓∔∕∖∗∘∙√∛∜∝∞∟∠∡∢∣"
        "⠁⠂⠃⠄⠅⠆⠇⠈⠉⠊⠋⠌⠍⠎⠏⠐⠑⠒⠓⠔⠕⠖⠗⠘⠙⠚⠛⠜⠝⠞⠟"
    )

    REVEAL_SPEED = 0.05  # Slightly slower for smoother transitions
    WORD_DELAY = 0.15  # Slightly longer delay between words
    SCRAMBLE_RATE = 0.3  # Less frequent scrambling
    RIPPLE_SPEED = 0.35  # Slower ripple speed
    PARTICLE_LIFE = 0.2  # Longer particle life

    def __init__(self):
        self.decrypting_texts = {}
        self.revealed_positions = set()
        self.last_scramble = time.time()
        self.scrambled_chars = {}
        self.highlighted_positions = set()
        self.all_revealed = False
        self.particles = []
        self.ripples = []
        self.glow_effects = {}
        self.last_effect_time = time.time()
        self.decryption_states = {}
        self.frame_time = 1.0 / 30.0  # Reduced to 30 FPS for smoother animation
        self.last_update = time.time()
        self.accumulated_time = 0.0
        self.prev_states = {}
        self.decrypted_positions = set()  # Track permanently decrypted positions

        # Simplified visual effects
        self.PARTICLE_CHARS = ["·", "∙", "○"]  # Fewer particle characters
        self.RIPPLE_CHARS = ["·", "○", "◌"]  # Simpler ripple chars
        self.GLOW_LEVELS = [
            curses.A_DIM,
            curses.A_NORMAL,
            curses.A_NORMAL,  # Removed A_BOLD for less intensity
            curses.A_DIM,
        ]

    def create_particle_burst(self, x, y, num_particles=3):
        """Create a burst of particles from a point."""
        for _ in range(num_particles):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(3, 6)  # Reduced speed
            self.particles.append(
                {
                    "x": x,
                    "y": y,
                    "dx": math.cos(angle) * speed,
                    "dy": math.sin(angle) * speed * 0.2,  # Reduced vertical spread
                    "char": random.choice(self.PARTICLE_CHARS),
                    "life": self.PARTICLE_LIFE,
                    "color": 2,  # Fixed color for consistency
                }
            )

    def create_ripple(self, x, y):
        """Create a ripple effect from a point."""
        self.ripples.append(
            {
                "x": x,
                "y": y,
                "radius": 0,
                "max_radius": 4,  # Smaller max radius
                "life": 0.5,  # Shorter life
                "start_time": time.time(),
            }
        )

    def add_glow_effect(self, x, y, duration=0.4):
        """Add a glowing effect to a position."""
        self.glow_effects[(x, y)] = {
            "start_time": time.time(),
            "duration": duration,
            "level_index": 0,
            "update_time": time.time(),
        }

    def start_decryption(self, x, y, text, delay=0, permanent=False):
        """Start decryption effect with enhanced visuals and smoother transitions."""
        words, word_positions = self._split_into_words(text)
        pos = (x, y)

        # Create initial effects with reduced intensity
        self.create_ripple(x + len(text) // 2, y)
        self.add_glow_effect(x, y)

        # Initialize decryption state with smoother transitions
        self.decryption_states[pos] = {
            "decrypted": False,
            "time": time.time(),
            "progress": 0.0,
            "word_progress": [0.0] * len(words),
            "transition_state": "starting",  # Track transition state
            "permanent": permanent,  # Track if this should stay decrypted
        }

        # Initialize text state with consistent scrambling
        initial_scramble = [random.choice(self.CIPHER_CHARS) for _ in range(len(text))]
        self.decrypting_texts[pos] = {
            "target": text,
            "current": [""] * len(text),
            "start_time": time.time() + delay,
            "words": words,
            "word_positions": word_positions,
            "word_index": 0,
            "permanent": permanent,
            "effect_chars": initial_scramble,
            "effect_time": time.time(),
            "transition_progress": 0.0,  # Track transition progress
        }

        # Initialize scrambled chars with consistent values
        self.scrambled_chars[pos] = {
            i: initial_scramble[i] for i in range(len(text)) if not text[i].isspace()
        }

        # If permanent, add to decrypted positions
        if permanent:
            self.decrypted_positions.add(pos)

    def start_reencryption(self, x, y, text):
        """Start re-encryption effect with smoother transitions."""
        pos = (x, y)

        # Initialize re-encryption state with smooth transition
        self.decryption_states[pos] = {
            "decrypted": False,
            "time": time.time(),
            "progress": 1.0,  # Start from fully decrypted
            "word_progress": [1.0] * len(text.split()),
            "transition_state": "reencrypting",
        }

        # Keep current scrambled chars for consistency
        current_scramble = self.scrambled_chars.get(pos, {})

        # Initialize new scrambled chars while preserving existing ones
        self.scrambled_chars[pos] = {
            i: current_scramble.get(i, random.choice(self.CIPHER_CHARS))
            for i in range(len(text))
            if not text[i].isspace()
        }

        # Create subtle visual effects
        self.create_ripple(x + len(text) // 2, y)

        # Start with decrypted text and gradually re-encrypt
        if pos in self.decrypting_texts:
            self.decrypting_texts[pos].update(
                {
                    "current": list(text),
                    "effect_time": time.time(),
                    "transition_progress": 0.0,
                    "target": text,
                }
            )

    def get_text(self, x, y, default_text):
        """Get the current state of text with enhanced visual effects."""
        pos = (x, y)
        current_time = time.time()

        # Start decryption if needed
        if pos not in self.decrypting_texts:
            self.start_decryption(x, y, default_text)

        data = self.decrypting_texts.get(pos)
        if not data:
            return default_text

        # Check if position is highlighted
        is_highlighted = pos in self.highlighted_positions or self.all_revealed

        # If highlighted, show decrypted or decrypting text
        if is_highlighted:
            if "".join(data["current"]).strip():
                text = "".join(data["current"])
            else:
                text = default_text

            # Apply glow effect if active
            if pos in self.glow_effects:
                effect = self.glow_effects[pos]
                glow_attr = self.GLOW_LEVELS[effect["level_index"]]
                return (text, glow_attr)

            return text

        # If not highlighted, show encrypted text with less frequent updates
        if pos not in self.scrambled_chars:
            self.scrambled_chars[pos] = {
                i: random.choice(self.CIPHER_CHARS)
                for i in range(len(default_text))
                if not default_text[i].isspace()
            }

        # Update scrambled characters less frequently
        if current_time - data.get("effect_time", 0) > self.SCRAMBLE_RATE:
            self.scrambled_chars[pos] = {
                i: random.choice(self.CIPHER_CHARS)
                for i in range(len(default_text))
                if not default_text[i].isspace()
            }
            data["effect_time"] = current_time

        # Return scrambled text
        scrambled = []
        for i, char in enumerate(default_text):
            if char.isspace():
                scrambled.append(char)
            else:
                scrambled.append(
                    self.scrambled_chars[pos].get(i, random.choice(self.CIPHER_CHARS))
                )
        return "".join(scrambled)

    def update(self):
        """Update decryption effects and animations with improved smoothness."""
        current_time = time.time()
        delta_time = current_time - self.last_update
        self.accumulated_time += delta_time

        if self.accumulated_time < self.frame_time:
            return

        self.last_update = current_time
        self.accumulated_time = 0.0

        # Store previous states for interpolation
        self._store_prev_states()

        # Update decryption animations
        for pos, data in list(self.decrypting_texts.items()):
            if current_time < data["start_time"]:
                continue

            # Check if position should be permanently decrypted
            is_permanent = pos in self.decrypted_positions

            if (
                not is_permanent
                and pos not in self.highlighted_positions
                and not self.all_revealed
            ):
                data["current"] = [""] * len(data["target"])
                continue

            target = data["target"]
            words = data["words"]
            word_positions = data["word_positions"]

            # Calculate time elapsed for animation timing
            time_elapsed = current_time - data["start_time"]

            # Determine word_index based on state
            if is_permanent or self.all_revealed:
                # Show all words when permanent or all revealed
                word_index = len(words)
            elif pos in self.highlighted_positions:
                # Normal decryption animation for highlighted positions
                word_index = min(int(time_elapsed / self.WORD_DELAY), len(words))
            else:
                # Default to first word only
                word_index = 0

            data["word_index"] = word_index

            # Update each word with smoother transitions
            for w_idx in range(word_index):
                word = words[w_idx]
                positions = word_positions[w_idx]

                if word.isspace():
                    data["current"][positions[0]] = word
                    continue

                # Calculate progress for each character with full word coverage
                word_time = time_elapsed - (w_idx * self.WORD_DELAY)
                chars_to_reveal = min(
                    len(positions),
                    int((word_time / self.REVEAL_SPEED) * len(positions)),
                )

                # For permanent states, reveal all characters immediately
                if is_permanent or self.all_revealed:
                    chars_to_reveal = len(positions)

                # Update characters with smoother transitions
                for i, pos_idx in enumerate(positions):
                    if i < chars_to_reveal:
                        data["current"][pos_idx] = target[pos_idx]
                    else:
                        # Use consistent scrambling for unrevealed characters
                        if pos_idx not in self.scrambled_chars.get(pos, {}):
                            self.scrambled_chars.setdefault(pos, {})[pos_idx] = (
                                random.choice(self.CIPHER_CHARS)
                            )
                        data["current"][pos_idx] = self.scrambled_chars[pos][pos_idx]

            # Only scramble remaining text if not permanent and not all revealed
            if not is_permanent and not self.all_revealed:
                for w_idx2 in range(word_index, len(words)):
                    for pos_idx in word_positions[w_idx2]:
                        if not words[w_idx2].isspace():
                            if pos_idx not in self.scrambled_chars.get(pos, {}):
                                self.scrambled_chars.setdefault(pos, {})[pos_idx] = (
                                    random.choice(self.CIPHER_CHARS)
                                )
                            data["current"][pos_idx] = self.scrambled_chars[pos][
                                pos_idx
                            ]

        # Update visual effects with interpolation
        dt = current_time - self.last_effect_time
        self.last_effect_time = current_time

        self.update_particles(current_time, dt)
        self.update_ripples(current_time)
        self.update_glow_effects(current_time)

        # Interpolate between states
        alpha = min(1.0, self.accumulated_time / self.frame_time)
        self._interpolate_effects(alpha)

    def draw_effects(self, stdscr):
        """Draw all visual effects with reduced intensity."""
        current_time = time.time()

        # Draw particles with smoother fade
        for particle in self.particles:
            try:
                x, y = int(particle["x"]), int(particle["y"])
                if 0 <= y < curses.LINES - 1 and 0 <= x < curses.COLS - 1:
                    attr = curses.color_pair(particle["color"]) | curses.A_DIM
                    fade = particle["life"] / self.PARTICLE_LIFE
                    if fade < 0.3:
                        attr = curses.color_pair(particle["color"]) | curses.A_DIM
                    stdscr.addstr(y, x, particle["char"], attr)
            except curses.error:
                continue

        # Draw ripples with reduced intensity
        for ripple in self.ripples:
            try:
                radius = int(ripple["radius"])
                if radius <= 0:  # Skip if radius is 0 or negative
                    continue

                # Calculate step size based on radius, with minimum step size
                step = min(30, max(10, 360 // (radius * 2)))  # Adjusted calculation

                for angle in range(0, 360, step):
                    rad = math.radians(angle)
                    x = int(ripple["x"] + radius * math.cos(rad))
                    y = int(ripple["y"] + radius * math.sin(rad) * 0.5)

                    if 0 <= y < curses.LINES - 1 and 0 <= x < curses.COLS - 1:
                        char_idx = int(
                            (1 - ripple["life"]) * (len(self.RIPPLE_CHARS) - 1)
                        )
                        char = self.RIPPLE_CHARS[char_idx]

                        attr = curses.color_pair(6) | curses.A_DIM
                        stdscr.addstr(y, x, char, attr)
            except curses.error:
                continue

    def highlight_position(self, x, y, delay=0):
        """Highlight a position with enhanced effects."""
        pos = (x, y)
        if pos not in self.decrypting_texts:
            self.start_decryption(x, y, "", delay, True)

        if pos not in self.highlighted_positions:
            self.highlighted_positions.add(pos)
            # Reset decryption state and start time for new highlight
            if pos in self.decrypting_texts:
                self.decrypting_texts[pos]["start_time"] = time.time() + delay
                self.decrypting_texts[pos]["current"] = [""] * len(
                    self.decrypting_texts[pos]["target"]
                )
            # Create visual effects
            self.create_ripple(x, y)
            self.add_glow_effect(x, y, 0.8)

    def unhighlight_position(self, x, y):
        """Remove highlight from a position and start re-encryption."""
        pos = (x, y)
        if pos in self.highlighted_positions:
            self.highlighted_positions.discard(pos)
            # Only start re-encryption if it was previously decrypted
            if (
                pos in self.decryption_states
                and self.decryption_states[pos]["decrypted"]
            ):
                # Get the current text to re-encrypt
                text = self.decrypting_texts[pos]["target"]
                self.start_reencryption(x, y, text)
            self.create_ripple(x, y)  # Create a final ripple effect
            self.add_glow_effect(x, y, 0.3)  # Quick fade-out glow

    def _split_into_words(self, text):
        """Split text into words and track their positions."""
        words = []
        positions = []
        current_word = []
        current_positions = []

        for i, char in enumerate(text):
            if char.isspace():
                if current_word:
                    words.append("".join(current_word))
                    positions.append(current_positions)
                    current_word = []
                    current_positions = []
                words.append(char)
                positions.append([i])
            else:
                current_word.append(char)
                current_positions.append(i)

        if current_word:
            words.append("".join(current_word))
            positions.append(current_positions)

        return words, positions

    def _store_prev_states(self):
        """Store previous states for interpolation."""
        self.prev_states = {
            "particles": [(p["x"], p["y"]) for p in self.particles],
            "ripples": [(r["radius"], r["life"]) for r in self.ripples],
        }

    def _interpolate_effects(self, alpha):
        """Interpolate visual effects between frames."""
        if not self.prev_states:
            return

        # Interpolate particle positions
        for i, particle in enumerate(self.particles):
            if i < len(self.prev_states["particles"]):
                prev_x, prev_y = self.prev_states["particles"][i]
                particle["x"] = prev_x * (1 - alpha) + particle["x"] * alpha
                particle["y"] = prev_y * (1 - alpha) + particle["y"] * alpha

        # Interpolate ripple effects
        for i, ripple in enumerate(self.ripples):
            if i < len(self.prev_states["ripples"]):
                prev_radius, prev_life = self.prev_states["ripples"][i]
                ripple["radius"] = prev_radius * (1 - alpha) + ripple["radius"] * alpha
                ripple["life"] = prev_life * (1 - alpha) + ripple["life"] * alpha

    def update_particles(self, current_time, dt):
        """Update particle positions and lifetimes."""
        # Update existing particles
        for particle in self.particles[
            :
        ]:  # Create a copy of the list to safely remove items
            # Update position
            particle["x"] += particle["dx"] * dt
            particle["y"] += particle["dy"] * dt

            # Update lifetime
            particle["life"] -= dt

            # Remove dead particles
            if particle["life"] <= 0:
                self.particles.remove(particle)

    def update_ripples(self, current_time):
        """Update ripple animations."""
        for ripple in self.ripples[
            :
        ]:  # Create a copy of the list to safely remove items
            time_alive = current_time - ripple["start_time"]

            # Update radius based on time
            progress = time_alive / ripple["life"]
            ripple["radius"] = ripple["max_radius"] * progress

            # Remove completed ripples
            if time_alive >= ripple["life"]:
                self.ripples.remove(ripple)

    def update_glow_effects(self, current_time):
        """Update glow effect levels."""
        for pos, effect in list(self.glow_effects.items()):
            time_elapsed = current_time - effect["start_time"]

            if time_elapsed >= effect["duration"]:
                del self.glow_effects[pos]
                continue

            # Update glow level based on time
            progress = time_elapsed / effect["duration"]
            effect["level_index"] = min(
                len(self.GLOW_LEVELS) - 1, int(progress * len(self.GLOW_LEVELS))
            )


class LandingPage:
    """Interactive landing page for qgit."""

    MENU_ITEMS = QGitConfig.MENU_ITEMS

    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.height, self.width = stdscr.getmaxyx()
        self.selected_item = 0
        self.loading_animation = LoadingAnimation(stdscr)
        self.matrix_rain = MatrixRain(stdscr)  # Initialize matrix rain
        self.box_animation = BoxAnimation(stdscr)
        self.decryption_effect = DecryptionEffect()
        self.last_click_time = 0
        self.last_click_pos = None
        self.help_text_visible = False
        self.help_page = None
        self.menu_revealed = False
        self.easter_egg_activated = False  # Add this line to track easter egg state

        # Enable keypad and hide cursor
        self.stdscr.keypad(1)
        curses.curs_set(0)

        # Initialize color pairs with -1 as background for transparency
        curses.start_color()
        curses.use_default_colors()  # Allow using terminal's default colors
        curses.init_pair(1, curses.COLOR_GREEN, -1)  # Green on default background
        curses.init_pair(2, curses.COLOR_CYAN, -1)  # Cyan on default background
        curses.init_pair(3, curses.COLOR_BLUE, -1)  # Blue on default background
        curses.init_pair(4, curses.COLOR_YELLOW, -1)  # Yellow on default background
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)  # Magenta on default background
        curses.init_pair(6, curses.COLOR_WHITE, -1)  # White on default background

        # Clear screen with black background
        self.stdscr.bkgd(" ", curses.color_pair(0))
        self.stdscr.clear()

        # Enable mouse events
        curses.mousemask(curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION)

        # Show initial loading screen
        self.show_loading_screen()

        # Configure terminal settings
        os.environ.setdefault("TERM", "xterm-256color")

        # Enable mouse support
        curses.mousemask(curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION)
        print("\033[?1003h")  # Enable mouse movement events

        # Initialize other settings
        self.current_selection = 0
        self.effects_enabled = False  # Track if effects should be shown
        self.logo_click_time = 0
        self.logo_bounds = {"y1": 0, "y2": 0, "x1": 0, "x2": 0}
        self.menu_bounds = {"y1": 0, "y2": 0, "x1": 0, "x2": 0}
        self.last_click_time = 0
        self.click_cooldown = 0.2
        self.frame_time = 1.0 / 60.0  # 60 FPS for main loop
        self.last_frame = time.time()
        self.accumulated_time = 0.0

    def get_menu_y(self):
        """Calculate and return the starting Y position for the menu."""
        max_y, _ = self.stdscr.getmaxyx()
        menu_height = len(self.MENU_ITEMS) * 2 + 4
        return min(14, max_y - menu_height - 4)  # Ensure menu fits vertically

    def show_loading_screen(self):
        """Show an animated loading screen."""
        start_time = time.time()
        spinner = cycle(LoadingAnimation.SPINNERS["dots"])
        toolkit_spinner = cycle(LoadingAnimation.TOOLKIT_FRAMES)
        loading_duration = 1.5  # seconds

        while time.time() - start_time < loading_duration:
            self.stdscr.clear()

            # Draw logo
            logo_lines = [
                line for line in LoadingAnimation.QGIT_LOGO.split("\n") if line
            ]
            logo_height = len(logo_lines)
            logo_width = len(logo_lines[0])
            logo_y = (curses.LINES - logo_height) // 2 - 2
            logo_x = (curses.COLS - logo_width) // 2

            # Draw border around logo
            self.draw_border(logo_y - 1, logo_x - 2, logo_height + 2, logo_width + 4)

            # Draw logo with pulsing effect
            pulse = abs(math.sin((time.time() - start_time) * 4))
            color_pair = (
                curses.color_pair(2) | curses.A_BOLD
                if pulse > 0.5
                else curses.color_pair(2)
            )

            for i, line in enumerate(logo_lines):
                self.stdscr.addstr(logo_y + i, logo_x, line, color_pair)

            # Draw toolkit text with animation
            toolkit_frame = next(toolkit_spinner)
            toolkit_y = logo_y - 2
            toolkit_x = (curses.COLS - len(toolkit_frame)) // 2
            toolkit_color = curses.color_pair(6) | (curses.A_BOLD if pulse > 0.5 else 0)
            self.stdscr.addstr(toolkit_y, toolkit_x, toolkit_frame, toolkit_color)

            # Draw loading spinner and text
            spinner_frame = next(spinner)
            loading_text = "Initializing qgit"
            dots = "." * (int((time.time() - start_time) * 4) % 4)
            full_text = f"{spinner_frame} {loading_text}{dots}"

            loading_y = logo_y + logo_height + 2
            loading_x = (curses.COLS - len(full_text)) // 2
            self.stdscr.addstr(
                loading_y, loading_x, full_text, curses.color_pair(7) | curses.A_BOLD
            )

            self.stdscr.refresh()
            time.sleep(0.1)

    def draw_border(self, y, x, height, width):
        """Draw a stylish border around a region."""
        max_y, max_x = self.stdscr.getmaxyx()

        # Ensure we're not drawing outside the terminal
        if y < 0 or x < 0 or y + height > max_y or x + width > max_x:
            return

        try:
            # Corners
            self.stdscr.addstr(y, x, "╭", curses.color_pair(5))
            self.stdscr.addstr(y, x + width - 1, "╮", curses.color_pair(5))
            self.stdscr.addstr(y + height - 1, x, "╰", curses.color_pair(5))
            self.stdscr.addstr(y + height - 1, x + width - 1, "╯", curses.color_pair(5))

            # Top and bottom borders
            for i in range(1, width - 1):
                self.stdscr.addstr(y, x + i, "─", curses.color_pair(5))
                self.stdscr.addstr(y + height - 1, x + i, "─", curses.color_pair(5))

            # Left and right borders
            for i in range(1, height - 1):
                self.stdscr.addstr(y + i, x, "│", curses.color_pair(5))
                self.stdscr.addstr(y + i, x + width - 1, "│", curses.color_pair(5))
        except curses.error:
            # If we still get an error, silently fail
            pass

    def draw_logo(self):
        """Draw the QGit logo with animation and improved click detection."""
        logo_lines = [line for line in LoadingAnimation.QGIT_LOGO.split("\n") if line]
        logo_height = len(logo_lines)
        logo_width = len(logo_lines[0])
        start_y = 2
        start_x = (curses.COLS - logo_width - 4) // 2  # -4 for border padding

        # Store logo boundaries with padding for better click detection
        self.logo_bounds = {
            "y1": start_y - 1,  # Include border in clickable area
            "y2": start_y + logo_height,
            "x1": start_x - 2,  # Include border in clickable area
            "x2": start_x + logo_width + 2,
        }

        # Draw border around logo
        self.draw_border(start_y - 1, start_x - 2, logo_height + 2, logo_width + 4)

        # Draw logo with highlight effect if clicked recently
        highlight = self.effects_enabled and (time.time() - self.last_click_time < 0.5)
        for i, line in enumerate(logo_lines):
            attr = curses.color_pair(6 if highlight else 2) | curses.A_BOLD
            self.stdscr.addstr(start_y + i, start_x, line, attr)

    def handle_mouse_click(self, x, y):
        """Handle mouse click events with improved tracking."""
        current_time = time.time()

        # Enforce click cooldown to prevent accidental double clicks
        if current_time - self.last_click_time < self.click_cooldown:
            return

        # Check if click is within logo bounds (with small buffer)
        logo_buffer = 2
        is_logo_click = (
            self.logo_bounds["y1"] - logo_buffer
            <= y
            <= self.logo_bounds["y2"] + logo_buffer
            and self.logo_bounds["x1"] - logo_buffer
            <= x
            <= self.logo_bounds["x2"] + logo_buffer
        )

        if is_logo_click:
            self.last_click_time = current_time
            self.effects_enabled = not self.effects_enabled  # Toggle effects

            if (
                self.effects_enabled and not self.easter_egg_activated
            ):  # Only do full setup on first activation
                self.easter_egg_activated = True

                # Reset decryption state for all menu items
                max_y, max_x = self.stdscr.getmaxyx()
                menu_start_y = min(14, max_y - len(self.MENU_ITEMS) * 2 - 8)
                menu_start_x = max(2, (max_x - 60) // 2)

                # Set all_revealed state based on effects_enabled
                self.decryption_effect.all_revealed = True

                # Handle menu items based on effects_enabled state
                for i in range(len(self.MENU_ITEMS)):
                    y = menu_start_y + i * 2
                    action, description, emoji = self.MENU_ITEMS[i]

                    # Prepare text for both action and description
                    item_text = f"{emoji}  {action.ljust(10)}"
                    delay = i * 0.05  # Cascading delay

                    # Start decryption for all items with permanent state
                    self.decryption_effect.start_decryption(
                        menu_start_x, y, item_text, delay=delay, permanent=True
                    )
                    self.decryption_effect.start_decryption(
                        menu_start_x + 20, y, description, delay=delay, permanent=True
                    )
                    self.decryption_effect.highlight_position(menu_start_x, y, delay)
                    self.decryption_effect.highlight_position(
                        menu_start_x + 20, y, delay
                    )
            elif not self.effects_enabled:
                # When effects are disabled, only keep current selection highlighted
                max_y, max_x = self.stdscr.getmaxyx()
                menu_start_y = min(14, max_y - len(self.MENU_ITEMS) * 2 - 8)
                menu_start_x = max(2, (max_x - 60) // 2)

                for i in range(len(self.MENU_ITEMS)):
                    y = menu_start_y + i * 2
                    if i != self.current_selection:
                        self.decryption_effect.unhighlight_position(menu_start_x, y)
                        self.decryption_effect.unhighlight_position(
                            menu_start_x + 20, y
                        )
                    else:
                        self.decryption_effect.highlight_position(menu_start_x, y)
                        self.decryption_effect.highlight_position(menu_start_x + 20, y)

    def draw_menu(self):
        """Draw the interactive menu."""
        max_y, max_x = self.stdscr.getmaxyx()

        # Calculate menu dimensions
        menu_width = min(60, max_x - 6)  # Leave room for borders
        menu_height = len(self.MENU_ITEMS) * 2 + 4

        # Ensure menu fits in terminal
        if menu_height > max_y - 16:  # Account for logo and margins
            menu_height = max_y - 16

        # Calculate starting positions
        menu_start_y = min(14, max_y - menu_height - 4)  # Ensure menu fits vertically
        menu_start_x = max(2, (max_x - menu_width) // 2)  # Center menu horizontally

        try:
            # Draw border around menu
            self.draw_border(
                menu_start_y - 3, menu_start_x - 2, menu_height + 2, menu_width + 4
            )

            # Draw menu title with decryption effect
            title = "Select an action:"
            title_x = menu_start_x + (menu_width - len(title)) // 2
            if menu_start_y - 2 >= 0:
                if not self.menu_revealed:
                    self.decryption_effect.start_decryption(
                        title_x, menu_start_y - 2, title
                    )
                title_text = self.decryption_effect.get_text(
                    title_x, menu_start_y - 2, title
                )
                if isinstance(title_text, tuple):
                    text, attr = title_text
                    self.stdscr.addstr(
                        menu_start_y - 2, title_x, text, curses.color_pair(6) | attr
                    )
                else:
                    self.stdscr.addstr(
                        menu_start_y - 2,
                        title_x,
                        title_text,
                        curses.color_pair(6) | curses.A_BOLD,
                    )

            # Start decryption effect for menu items if not already started
            if not self.menu_revealed:
                for i, (action, description, emoji) in enumerate(self.MENU_ITEMS):
                    y = menu_start_y + i * 2
                    item_text = f"{emoji}  {action.ljust(10)}"
                    self.decryption_effect.start_decryption(
                        menu_start_x, y, item_text, delay=i * 0.1, permanent=True
                    )
                    self.decryption_effect.start_decryption(
                        menu_start_x + 20, y, description, delay=i * 0.1, permanent=True
                    )
                self.menu_revealed = True

            # Draw visible menu items
            visible_items = (menu_height - 4) // 2  # Calculate how many items can fit
            start_idx = max(
                0,
                min(
                    self.current_selection - visible_items // 2,
                    len(self.MENU_ITEMS) - visible_items,
                ),
            )

            for i in range(
                start_idx, min(start_idx + visible_items, len(self.MENU_ITEMS))
            ):
                action, description, emoji = self.MENU_ITEMS[i]
                y = menu_start_y + (i - start_idx) * 2

                if y + 1 >= max_y:  # Skip if we're at the bottom of the screen
                    break

                # Update highlighted positions based on selection and effects_enabled state
                if i == self.current_selection or self.effects_enabled:
                    self.decryption_effect.highlight_position(menu_start_x, y)
                    self.decryption_effect.highlight_position(menu_start_x + 20, y)
                else:
                    # Only unhighlight if easter egg is not activated
                    if not self.effects_enabled:
                        self.decryption_effect.unhighlight_position(menu_start_x, y)
                        self.decryption_effect.unhighlight_position(
                            menu_start_x + 20, y
                        )

                # Draw menu item with decryption effect
                item_text = f"{emoji}  {action.ljust(10)}"
                current_text = self.decryption_effect.get_text(
                    menu_start_x, y, item_text
                )

                # Determine if this item should be decrypted
                should_decrypt = i == self.current_selection or self.effects_enabled

                if isinstance(current_text, tuple):
                    text, attr = current_text
                    if should_decrypt:
                        self.stdscr.addstr(
                            y, menu_start_x, text, curses.color_pair(1) | attr
                        )
                        desc_text = self.decryption_effect.get_text(
                            menu_start_x + 20, y, description
                        )
                        if isinstance(desc_text, tuple):
                            desc, desc_attr = desc_text
                            self.stdscr.addstr(
                                y,
                                menu_start_x + 20,
                                desc,
                                curses.color_pair(3) | desc_attr,
                            )
                        else:
                            self.stdscr.addstr(
                                y,
                                menu_start_x + 20,
                                desc_text,
                                curses.color_pair(3) | curses.A_BOLD,
                            )
                    else:
                        self.stdscr.addstr(
                            y, menu_start_x, text, curses.color_pair(4) | attr
                        )
                        desc_text = self.decryption_effect.get_text(
                            menu_start_x + 20, y, description
                        )
                        if isinstance(desc_text, tuple):
                            desc, desc_attr = desc_text
                            self.stdscr.addstr(
                                y,
                                menu_start_x + 20,
                                desc,
                                curses.color_pair(5) | desc_attr,
                            )
                        else:
                            self.stdscr.addstr(
                                y, menu_start_x + 20, desc_text, curses.color_pair(5)
                            )
                else:
                    if should_decrypt:
                        self.stdscr.addstr(
                            y,
                            menu_start_x,
                            current_text,
                            curses.color_pair(1) | curses.A_BOLD,
                        )
                        desc_text = self.decryption_effect.get_text(
                            menu_start_x + 20, y, description
                        )
                        self.stdscr.addstr(
                            y,
                            menu_start_x + 20,
                            desc_text,
                            curses.color_pair(3) | curses.A_BOLD,
                        )
                    else:
                        self.stdscr.addstr(
                            y, menu_start_x, current_text, curses.color_pair(4)
                        )
                        desc_text = self.decryption_effect.get_text(
                            menu_start_x + 20, y, description
                        )
                        self.stdscr.addstr(
                            y, menu_start_x + 20, desc_text, curses.color_pair(5)
                        )

            # Draw all visual effects
            self.decryption_effect.draw_effects(self.stdscr)

        except curses.error:
            # If we still get an error, silently fail
            pass

    def draw_footer(self):
        """Draw footer with controls help."""
        footer_text = "↑/↓: Navigate   ⏎ Enter: Select   q: Quit"
        y = curses.LINES - 3
        x = (curses.COLS - len(footer_text)) // 2

        # Draw border around footer
        self.draw_border(y - 1, x - 2, 3, len(footer_text) + 4)

        # Draw footer text
        self.stdscr.addstr(y, x, footer_text, curses.color_pair(5) | curses.A_DIM)

    def show_help(self):
        """Show the help page with detailed information."""
        while True:
            self.stdscr.clear()

            # Draw matrix rain in background with reduced intensity
            self.matrix_rain.update()

            max_y, max_x = self.stdscr.getmaxyx()

            # Calculate dimensions
            help_width = min(80, max_x - 4)
            help_height = len(self.HELP_TEXT) + 4
            help_start_x = (max_x - help_width) // 2
            help_start_y = 2

            # Draw border around help content
            self.draw_border(
                help_start_y - 1, help_start_x - 1, help_height, help_width + 2
            )

            # Draw title
            title = "QGit Help"
            title_x = help_start_x + (help_width - len(title)) // 2
            self.stdscr.addstr(
                help_start_y, title_x, title, curses.color_pair(6) | curses.A_BOLD
            )

            # Draw help content
            current_y = help_start_y + 2
            for command, description in self.HELP_TEXT:
                if current_y >= max_y - 2:  # Prevent drawing outside screen
                    break

                if not command and not description:  # Empty line
                    current_y += 1
                    continue

                if not description:  # Section header
                    self.stdscr.addstr(
                        current_y,
                        help_start_x,
                        command,
                        curses.color_pair(3) | curses.A_BOLD,
                    )
                    current_y += 1
                    # Draw separator line
                    self.stdscr.addstr(
                        current_y, help_start_x, "─" * help_width, curses.color_pair(5)
                    )
                    current_y += 1
                else:  # Command description
                    # Draw command
                    self.stdscr.addstr(
                        current_y,
                        help_start_x,
                        command.ljust(15),
                        curses.color_pair(2) | curses.A_BOLD,
                    )
                    # Draw description
                    desc_x = help_start_x + 20
                    max_desc_width = help_width - 20
                    if len(description) > max_desc_width:
                        description = description[: max_desc_width - 3] + "..."
                    self.stdscr.addstr(
                        current_y, desc_x, description, curses.color_pair(4)
                    )
                    current_y += 1

            # Draw footer
            footer_text = "Press 'q' or ESC to return to menu"
            footer_x = (max_x - len(footer_text)) // 2
            footer_y = max_y - 2
            self.stdscr.addstr(
                footer_y, footer_x, footer_text, curses.color_pair(5) | curses.A_DIM
            )

            # Update effects
            self.box_animation.update()  # Use actual menu x position instead of width//4
            self.decryption_effect.update()
            self.decryption_effect.draw_effects(self.stdscr)

            self.stdscr.refresh()

            # Handle input
            try:
                key = self.stdscr.getch()
                if key in [ord("q"), 27]:  # q or ESC
                    return
            except curses.error:
                continue

    def run(self):
        """Main loop for the landing page with improved frame timing."""
        try:
            while True:
                current_time = time.time()
                delta_time = current_time - self.last_frame
                self.accumulated_time += delta_time

                # Skip frame if we're ahead of schedule
                if self.accumulated_time < self.frame_time:
                    time.sleep(max(0, self.frame_time - self.accumulated_time))
                    continue

                self.last_frame = current_time
                self.accumulated_time = 0.0

                # Clear screen
                self.stdscr.clear()

                # Get terminal dimensions for menu positioning
                max_y, max_x = self.stdscr.getmaxyx()
                menu_width = min(60, max_x - 6)  # Leave room for borders
                menu_start_x = max(
                    2, (max_x - menu_width) // 2
                )  # Center menu horizontally

                # Update matrix rain first for background effect
                self.matrix_rain.update()

                # Draw border
                self.draw_border(0, 0, self.height, self.width)

                # Draw logo
                self.draw_logo()

                # Draw menu
                self.draw_menu()

                # Draw footer
                self.draw_footer()

                # Update and draw effects
                self.box_animation.update(
                    menu_start_x
                )  # Use actual menu x position instead of width//4
                self.decryption_effect.update()
                self.decryption_effect.draw_effects(self.stdscr)

                # Refresh screen
                self.stdscr.refresh()

                # Adjust input timeout based on remaining frame time
                timeout_ms = int((self.frame_time - self.accumulated_time) * 1000)
                self.stdscr.timeout(max(1, timeout_ms))

                # Get input with timeout
                try:
                    key = self.stdscr.getch()
                except curses.error:
                    continue

                if key == curses.KEY_MOUSE:
                    try:
                        _, mx, my, _, button_state = curses.getmouse()
                        self.handle_mouse_click(mx, my)
                    except curses.error:
                        continue
                elif key == ord("q"):
                    return None
                elif key == ord("h"):
                    self.show_help_page()
                elif key == curses.KEY_UP and self.current_selection > 0:
                    # Unhighlight current selection before moving
                    menu_start_y = self.get_menu_y()
                    menu_start_x = max(2, (self.width - 60) // 2)
                    y = menu_start_y + self.current_selection * 2
                    self.decryption_effect.unhighlight_position(menu_start_x, y)
                    self.decryption_effect.unhighlight_position(menu_start_x + 20, y)

                    self.current_selection -= 1
                    # Highlight new selection
                    y = menu_start_y + self.current_selection * 2
                    self.decryption_effect.highlight_position(menu_start_x, y)
                    self.decryption_effect.highlight_position(menu_start_x + 20, y)

                    # Only animate around the first word
                    action = self.MENU_ITEMS[self.current_selection][0]
                    first_word_width = (
                        len(action.split()[0]) + 4
                    )  # Add padding for emoji
                    self.box_animation.start_animation(
                        menu_start_y + self.current_selection * 2, first_word_width
                    )
                elif (
                    key == curses.KEY_DOWN
                    and self.current_selection < len(self.MENU_ITEMS) - 1
                ):
                    # Unhighlight current selection before moving
                    menu_start_y = self.get_menu_y()
                    menu_start_x = max(2, (self.width - 60) // 2)
                    y = menu_start_y + self.current_selection * 2
                    self.decryption_effect.unhighlight_position(menu_start_x, y)
                    self.decryption_effect.unhighlight_position(menu_start_x + 20, y)

                    self.current_selection += 1
                    # Highlight new selection
                    y = menu_start_y + self.current_selection * 2
                    self.decryption_effect.highlight_position(menu_start_x, y)
                    self.decryption_effect.highlight_position(menu_start_x + 20, y)

                    # Only animate around the first word
                    action = self.MENU_ITEMS[self.current_selection][0]
                    first_word_width = (
                        len(action.split()[0]) + 4
                    )  # Add padding for emoji
                    self.box_animation.start_animation(
                        menu_start_y + self.current_selection * 2, first_word_width
                    )
                elif key == ord("\n"):
                    return self.MENU_ITEMS[self.current_selection][0].lower()

        except KeyboardInterrupt:
            return None

    def __del__(self):
        """Clean up mouse settings on exit."""
        print("\033[?1003l")  # Disable mouse movement events

    def get_menu_y(self):
        """Calculate and return the starting Y position for the menu."""
        max_y, _ = self.stdscr.getmaxyx()
        menu_height = len(self.MENU_ITEMS) * 2 + 4
        return min(14, max_y - menu_height - 4)  # Ensure menu fits vertically


class HelpPage:
    """Enhanced help page with tabs and scrolling support."""

    def __init__(self, stdscr):
        self.stdscr = stdscr
        logging.info("Initializing HelpPage")
        self.current_tab = 0
        self.scroll_position = 0
        self.search_mode = False
        self.search_query = ""
        self.search_results = []
        self.search_index = 0
        self.max_scroll = 0
        self.content_width = 0
        self.content_height = 0
        self.selected_item = 0
        self.CONTENT = {"Commands": [], "Options": [], "Examples": []}

        # Initialize tabs and content from qgit_dict
        try:
            from qgits.qgit_dict import get_all_commands

            commands = get_all_commands()
            logging.info("Successfully loaded commands from qgit_dict")

            # Define the tabs structure
            self.TABS = ["Commands", "Options", "Examples"]
            logging.info(f"Initialized TABS with {len(self.TABS)} items: {self.TABS}")

            # Populate Commands tab
            for cmd, details in commands.items():
                # Add command with description
                self.CONTENT["Commands"].append(
                    (f"qgit {cmd}", details["description"], details["usage"])
                )

            # Populate Options tab
            for cmd, details in commands.items():
                if details["options"]:
                    # Add command header
                    self.CONTENT["Options"].append(
                        (f"qgit {cmd}", "", "Available options:")
                    )
                    # Add each option
                    for opt, opt_desc in details["options"].items():
                        self.CONTENT["Options"].append(("", opt, opt_desc))

            # Populate Examples tab with common usage patterns
            self.CONTENT["Examples"] = [
                ("Quick Commit", "qgit commit", "Stage and commit all changes"),
                (
                    "Custom Message",
                    "qgit commit -m 'Fix bug'",
                    "Commit with specific message",
                ),
                ("Sync Changes", "qgit sync", "Pull and push changes"),
                ("Save All", "qgit save", "Commit and sync in one step"),
                ("New Repository", "qgit first", "Initialize new git repository"),
                ("Security Scan", "qgit benedict", "Scan for sensitive files"),
                ("Quick Undo", "qgit undo", "Safely undo last operation"),
                ("Create Snapshot", "qgit snapshot", "Save current state"),
                ("View Stats", "qgit stats", "Show repository analytics"),
            ]

        except ImportError:
            logging.error("Failed to import qgit_dict.get_all_commands", exc_info=True)
            # Fallback content
            self.TABS = ["Basic Help"]
            logging.info("Using fallback TABS configuration")
            self.CONTENT = {
                "Basic Help": [
                    (
                        "Error",
                        "Could not load command definitions",
                        "Please ensure qgits/qgit_dict.py is available",
                    )
                ]
            }

    def draw_tabs(self, start_y, width):
        """Draw the tab bar with modern styling."""
        logging.info(f"Drawing tabs at y={start_y}, width={width}")
        logging.info(f"Number of tabs: {len(self.TABS) if self.TABS else 0}")

        if not self.TABS:
            logging.warning("No tabs to draw, returning early")
            return

        try:
            tab_width = width // len(self.TABS)
            logging.info(
                f"Calculated tab_width={tab_width} (width={width} / num_tabs={len(self.TABS)})"
            )

            if tab_width < 1:
                logging.warning(f"Tab width {tab_width} is less than 1, setting to 1")
                tab_width = 1

            for i, tab_name in enumerate(self.TABS):
                logging.debug(f"Drawing tab {i}: {tab_name}")
                x = i * tab_width
                is_current = i == self.current_tab

                # Draw tab background
                for j in range(min(tab_width, width - x)):
                    attr = curses.color_pair(1 if is_current else 5)
                    attr |= curses.A_BOLD if is_current else curses.A_DIM
                    try:
                        self.stdscr.addstr(start_y, x + j, " ", attr)
                    except curses.error as e:
                        logging.error(
                            f"Failed to draw tab background at ({start_y}, {x + j}): {str(e)}"
                        )
                        continue

                # Draw tab content
                tab_text = f" {tab_name} "
                tab_x = x + (min(tab_width, width - x) - len(tab_text)) // 2
                logging.debug(f"Tab text position: x={tab_x}, text='{tab_text}'")

                if tab_x >= 0 and tab_x + len(tab_text) <= width:
                    attr = curses.color_pair(6 if is_current else 4)
                    attr |= curses.A_BOLD if is_current else 0
                    try:
                        self.stdscr.addstr(start_y, tab_x, tab_text, attr)
                    except curses.error as e:
                        logging.error(
                            f"Failed to draw tab text at ({start_y}, {tab_x}): {str(e)}"
                        )
                        continue

                # Draw separator
                if i < len(self.TABS) - 1 and x + tab_width < width:
                    try:
                        self.stdscr.addstr(
                            start_y, x + tab_width - 1, "│", curses.color_pair(5)
                        )
                    except curses.error as e:
                        logging.error(
                            f"Failed to draw separator at ({start_y}, {x + tab_width - 1}): {str(e)}"
                        )
                        continue

        except Exception as e:
            logging.critical(f"Unexpected error in draw_tabs: {str(e)}", exc_info=True)
            raise

    def draw_search_bar(self, y, width):
        """Draw the search interface."""
        if not self.search_mode:
            return

        # Draw search box
        self.stdscr.addstr(y, 0, "╭" + "─" * (width - 2) + "╮", curses.color_pair(5))
        self.stdscr.addstr(y + 1, 0, "│", curses.color_pair(5))
        self.stdscr.addstr(
            y + 1, 1, f" 🔍 {self.search_query}", curses.color_pair(6) | curses.A_BOLD
        )
        self.stdscr.addstr(y + 1, width - 1, "│", curses.color_pair(5))
        self.stdscr.addstr(
            y + 2, 0, "╰" + "─" * (width - 2) + "╯", curses.color_pair(5)
        )

        # Draw search status if we have results
        if self.search_results:
            status = f" [{self.search_index + 1}/{len(self.search_results)}] "
            self.stdscr.addstr(
                y + 1, width - len(status) - 2, status, curses.color_pair(3)
            )

    def draw_content(self, start_y, height, width):
        """Draw the content of the current tab with scrolling support."""
        current_tab_name = self.TABS[self.current_tab]
        current_content = self.CONTENT[current_tab_name]
        self.content_height = len(current_content) * 3  # 3 lines per item
        self.content_width = width - 4
        self.max_scroll = max(0, self.content_height - height)

        # Draw scrollbar if needed
        if self.max_scroll > 0:
            scrollbar_height = max(3, int(height * (height / self.content_height)))
            scrollbar_pos = int(
                (height - scrollbar_height) * (self.scroll_position / self.max_scroll)
            )
            for i in range(height):
                if scrollbar_pos <= i < scrollbar_pos + scrollbar_height:
                    self.stdscr.addstr(
                        start_y + i, width - 1, "█", curses.color_pair(5)
                    )
                else:
                    self.stdscr.addstr(
                        start_y + i, width - 1, "│", curses.color_pair(5) | curses.A_DIM
                    )

        # Draw content
        y = start_y
        for i, item in enumerate(current_content):
            item_y = y - self.scroll_position
            if item_y + 2 < start_y:
                y += 3
                continue
            if item_y > start_y + height - 1:
                break

            is_selected = i == self.selected_item

            if isinstance(item, tuple):
                if len(item) == 3:
                    command, short_desc, long_desc = item
                    if 0 <= item_y < start_y + height:
                        self.stdscr.addstr(
                            item_y,
                            2,
                            command,
                            curses.color_pair(1 if is_selected else 2) | curses.A_BOLD,
                        )
                    if 0 <= item_y + 1 < start_y + height:
                        self.stdscr.addstr(
                            item_y + 1,
                            4,
                            short_desc,
                            curses.color_pair(3 if is_selected else 4),
                        )
                    if 0 <= item_y + 2 < start_y + height:
                        self.stdscr.addstr(
                            item_y + 2,
                            4,
                            long_desc,
                            curses.color_pair(5)
                            | (curses.A_BOLD if is_selected else curses.A_DIM),
                        )
                else:
                    category, shortcut, desc = item
                    if category:  # Category header
                        if 0 <= item_y < start_y + height:
                            self.stdscr.addstr(
                                item_y,
                                2,
                                category,
                                curses.color_pair(6) | curses.A_BOLD,
                            )
                    if 0 <= item_y + 1 < start_y + height:
                        if shortcut:
                            self.stdscr.addstr(
                                item_y + (0 if not category else 1),
                                4,
                                f"{shortcut.ljust(12)}{desc}",
                                curses.color_pair(1 if is_selected else 4),
                            )
            y += 3

    def handle_input(self, key):
        """Handle user input for navigation and search."""
        if key == curses.KEY_MOUSE:
            try:
                _, mx, my, _, button_state = curses.getmouse()
                self.handle_mouse_click(mx, my)
            except curses.error:
                pass
        elif key == ord("q"):
            return None
        elif key == curses.KEY_UP and self.selected_item > 0:
            self.selected_item -= 1
            # Adjust scroll position if needed
            if self.selected_item * 3 < self.scroll_position:
                self.scroll_position = max(0, self.selected_item * 3)
        elif key == curses.KEY_DOWN and self.selected_item < len(self.CONTENT[self.TABS[self.current_tab]]) - 1:
            self.selected_item += 1
            # Adjust scroll position if needed
            if (self.selected_item + 1) * 3 > self.scroll_position + self.content_height:
                self.scroll_position = min(
                    self.max_scroll,
                    (self.selected_item + 1) * 3 - self.content_height
                )
        elif key == ord("\n"):
            # Handle selection
            current_content = self.CONTENT[self.TABS[self.current_tab]]
            if 0 <= self.selected_item < len(current_content):
                item = current_content[self.selected_item]
                if isinstance(item, tuple) and len(item) == 3:
                    command = item[0]
                    if command.startswith("qgit "):
                        return command[5:]  # Return command without "qgit " prefix
        return True

    def handle_mouse_click(self, x, y):
        """Handle mouse click events."""
        # Get terminal dimensions
        height, width = self.stdscr.getmaxyx()
        
        # Check if click is in tab area
        if y == 1:
            tab_width = width // len(self.TABS)
            clicked_tab = x // tab_width
            if 0 <= clicked_tab < len(self.TABS):
                self.current_tab = clicked_tab
                self.scroll_position = 0
                self.selected_item = 0
                return
        
        # Check if click is in content area
        content_start_y = 4  # Start after tabs
        if y >= content_start_y:
            item_index = (y - content_start_y + self.scroll_position) // 3
            current_content = self.CONTENT[self.TABS[self.current_tab]]
            if 0 <= item_index < len(current_content):
                self.selected_item = item_index
                # Adjust scroll position if needed
                if (self.selected_item + 1) * 3 > self.scroll_position + self.content_height:
                    self.scroll_position = min(
                        self.max_scroll,
                        (self.selected_item + 1) * 3 - self.content_height
                    )
                elif self.selected_item * 3 < self.scroll_position:
                    self.scroll_position = max(0, self.selected_item * 3)

    def run(self):
        """Main loop for the help page."""
        while True:
            # Get terminal dimensions
            height, width = self.stdscr.getmaxyx()

            # Clear screen
            self.stdscr.clear()

            # Draw tabs at the top
            self.draw_tabs(1, width)

            # Draw search bar if in search mode
            search_height = 3 if self.search_mode else 0
            self.draw_search_bar(3, width)

            # Calculate content area
            content_start_y = 4 + search_height
            content_height = height - content_start_y - 1

            # Draw content
            self.draw_content(content_start_y, content_height, width)

            # Draw footer
            footer_text = (
                "q: Back   ←/→: Switch tabs   ↑/↓: Navigate   /: Search   Enter: Select"
            )
            footer_x = (width - len(footer_text)) // 2
            self.stdscr.addstr(
                height - 1, footer_x, footer_text, curses.color_pair(5) | curses.A_DIM
            )

            # Refresh screen
            self.stdscr.refresh()

            # Handle input
            try:
                key = self.stdscr.getch()
                if key == ord("q"):
                    break
                elif key == curses.KEY_LEFT and self.current_tab > 0:
                    self.current_tab -= 1
                    self.scroll_position = 0
                elif key == curses.KEY_RIGHT and self.current_tab < len(self.TABS) - 1:
                    self.current_tab += 1
                    self.scroll_position = 0
                elif key == curses.KEY_UP and self.scroll_position > 0:
                    self.scroll_position = max(0, self.scroll_position - 1)
                elif key == curses.KEY_DOWN and self.scroll_position < self.max_scroll:
                    self.scroll_position = min(
                        self.max_scroll, self.scroll_position + 1
                    )
                elif key == ord("/"):
                    self.search_mode = not self.search_mode
                    if not self.search_mode:
                        self.search_query = ""
                        self.search_results = []
                elif self.search_mode:
                    if key == 27:  # ESC
                        self.search_mode = False
                        self.search_query = ""
                        self.search_results = []
                    elif key == curses.KEY_BACKSPACE or key == 127:
                        self.search_query = self.search_query[:-1]
                    elif key == ord("n"):
                        if self.search_results:
                            self.search_index = (self.search_index + 1) % len(
                                self.search_results
                            )
                    elif key == ord("N"):
                        if self.search_results:
                            self.search_index = (self.search_index - 1) % len(
                                self.search_results
                            )
                    elif 32 <= key <= 126:  # Printable characters
                        self.search_query += chr(key)
            except curses.error:
                continue


def run_gui():
    """Run the qgit GUI interface."""
    logging.info("Starting qgit GUI")

    def _run_landing_page(stdscr):
        try:
            landing_page = LandingPage(stdscr)
            result = landing_page.run()
            logging.info(f"GUI completed with result: {result}")
            return result
        except Exception as e:
            logging.critical(f"Error in GUI: {str(e)}", exc_info=True)
            raise

    try:
        return curses.wrapper(_run_landing_page)
    except Exception as e:
        logging.critical(f"Error launching GUI: {str(e)}", exc_info=True)
        print(f"Error launching GUI: {str(e)}")
        return None


def show_help():
    """Show the help page directly."""
    logging.info("Showing help page")

    def _run_help_page(stdscr):
        try:
            help_page = HelpPage(stdscr)
            help_page.run()
            logging.info("Help page closed")
        except Exception as e:
            logging.critical(f"Error in help page: {str(e)}", exc_info=True)
            raise

    try:
        curses.wrapper(_run_help_page)
    except Exception as e:
        logging.critical(f"Error showing help: {str(e)}", exc_info=True)
        print(f"Error showing help: {str(e)}")


def show_author_screen():
    """Display the author information screen."""
    logging.info("Showing author screen")
    try:
        # Import author data
        from .qgit_author_data import (
            GRIFFIN_FACTS, GRIFFIN_QUOTES, DAILY_ADVICE, GRIFFIN_LOGO, SEIZE_MODE_TEXT
        )
        
        curses.wrapper(_run_author_screen)
    except Exception as e:
        logging.critical(f"Error showing author screen: {str(e)}", exc_info=True)
        # Fallback to plain text if GUI fails
        print("\n" + "=" * 40)
        print("  GRIFFIN: THE PROGRAMMING GOD")
        print("=" * 40)
        
        try:
            from .qgit_author_data import get_random_facts, get_random_quote, get_random_advice
            print("\nFun Facts:")
            for i, fact in enumerate(get_random_facts(3), 1):
                print(f"{i}. {fact}")
            
            print("\nWords of Wisdom:")
            print(f'"{get_random_quote()}"')
            
            print("\nDaily Advice:")
            print(get_random_advice())
        except ImportError:
            print("\nCouldn't load author data, but Griffin is still a programming god.")
            
        print("\n" + "=" * 40 + "\n")

def _run_author_screen(stdscr):
    """Internal function to run the author screen with curses."""
    try:
        # Import author data
        from .qgit_author_data import (
            GRIFFIN_FACTS, GRIFFIN_QUOTES, DAILY_ADVICE, 
            GRIFFIN_LOGO, SEIZE_MODE_TEXT
        )
        
        # Initialize screen
        curses.curs_set(0)  # Hide cursor
        stdscr.clear()
        
        # Get screen dimensions
        height, width = stdscr.getmaxyx()
        
        # Check terminal size is adequate
        min_height, min_width = 24, 60
        if height < min_height or width < min_width:
            _show_terminal_too_small(stdscr)
            return
        
        # Initialize colors
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)     # Title
        curses.init_pair(2, curses.COLOR_YELLOW, -1)   # Subtitle
        curses.init_pair(3, curses.COLOR_WHITE, -1)    # Text
        curses.init_pair(4, curses.COLOR_GREEN, -1)    # Highlight
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)  # Quote
        curses.init_pair(6, curses.COLOR_RED, -1)      # Warning
        
        # Set up animation
        particles = []
        last_time = time.time()
        
        # Content state
        author_name = "Griffin"
        author_title = "Programming God & QGit Creator"
        selected_fact = random.randint(0, len(GRIFFIN_FACTS) - 1)
        selected_quote = random.randint(0, len(GRIFFIN_QUOTES) - 1)
        advice = random.choice(DAILY_ADVICE)
        seize_mode_active = False
        exit_requested = False
        
        # Enhanced animation class using matrix rain effect
        matrix_rain = MatrixRain(stdscr)
        
        # Main loop
        while not exit_requested:
            # Get terminal dimensions (check for resize)
            height, width = stdscr.getmaxyx()
            
            # Clear screen
            stdscr.clear()
            
            # Update matrix rain for background effect
            if seize_mode_active:
                matrix_rain.update()
            
            # Draw content based on state
            if seize_mode_active:
                _draw_seize_mode(stdscr, SEIZE_MODE_TEXT, particles, height, width)
                seize_mode_active = False  # Automatically reset after showing
            else:
                # Draw main display
                _draw_author_display(
                    stdscr, 
                    GRIFFIN_LOGO, 
                    author_name, 
                    author_title,
                    GRIFFIN_FACTS,
                    GRIFFIN_QUOTES,
                    advice,
                    selected_fact,
                    selected_quote,
                    particles,
                    height, 
                    width
                )
                
            # Update particle animations
            _update_particles(stdscr, particles, last_time, height, width)
            last_time = time.time()
            
            # Add controls info
            controls_y = height - 2
            controls_text = "N: New fact | Q: New quote | G: SEIZE MODE | ESC: Exit"
            if len(controls_text) > width - 2:
                controls_text = "N/Q/G/ESC"
            _center_text(stdscr, controls_y, controls_text, 4, width)
            
            # Refresh the screen
            stdscr.refresh()
            
            # Handle user input with timeout for animations
            stdscr.timeout(50)
            key = stdscr.getch()
            
            if key == 27:  # ESC key
                exit_requested = True
            elif key == ord('n') or key == ord('N'):
                # New random fact
                new_fact = random.randint(0, len(GRIFFIN_FACTS) - 1)
                while new_fact == selected_fact and len(GRIFFIN_FACTS) > 1:
                    new_fact = random.randint(0, len(GRIFFIN_FACTS) - 1)
                selected_fact = new_fact
                # Add particle effects
                _add_particle_burst(particles, width // 2, height // 3, 10)
            elif key == ord('q') or key == ord('Q'):
                # New random quote
                new_quote = random.randint(0, len(GRIFFIN_QUOTES) - 1)
                while new_quote == selected_quote and len(GRIFFIN_QUOTES) > 1:
                    new_quote = random.randint(0, len(GRIFFIN_QUOTES) - 1)
                selected_quote = new_quote
                # Add particle effects
                _add_particle_burst(particles, width // 2, height // 2, 10)
            elif key == ord('g') or key == ord('G'):
                # Activate GOD MODE
                seize_mode_active = True
                # Add lots of particles
                for _ in range(20):
                    _add_particle_burst(particles, 
                                      random.randint(0, width-1), 
                                      random.randint(0, height-1), 
                                      count=5)
            elif key == curses.KEY_RESIZE:
                # Terminal was resized
                if height < min_height or width < min_width:
                    _show_terminal_too_small(stdscr)
    
    except Exception as e:
        logging.error(f"Error in author screen: {str(e)}", exc_info=True)
        curses.endwin()
        raise e

def _draw_author_display(stdscr, logo, name, title, facts, quotes, advice, 
                        selected_fact, selected_quote, particles, height, width):
    """Draw the main author display with all content."""
    # Draw logo with enhanced border
    logo_lines = logo.strip().split('\n')
    start_y = 2
    
    # Make sure logo fits in the terminal
    if len(logo_lines) > height - 10:
        # Use a simpler logo if needed
        logo_lines = ["Griffin, the Programming God"]
    
    # Draw animated cosmic border around the logo
    logo_width = max(len(line) for line in logo_lines)
    border_width = logo_width + 8
    border_height = len(logo_lines) + 4
    border_x = (width - border_width) // 2
    
    # Draw cosmic border with animated effects
    _draw_cosmic_border(stdscr, start_y - 2, border_x, border_height, border_width, time.time())
    
    # Draw logo with glow effect
    glow = abs(math.sin(time.time() * 2))
    logo_color = 1 if glow > 0.5 else 6  # Alternate between cyan and white
    
    for i, line in enumerate(logo_lines):
        if start_y + i < height:
            _center_text(stdscr, start_y + i, line, logo_color | curses.A_BOLD, width)
    
    # Calculate positions
    logo_height = len(logo_lines)
    content_start_y = min(logo_height + 6, height // 4)
    
    # Draw border around content area with enhanced styling
    try:
        content_width = min(width - 10, 70)
        content_height = height - content_start_y - 3
        content_x = (width - content_width) // 2
        _draw_fancy_border(stdscr, content_start_y - 1, content_x, content_height, content_width, time.time())
    except curses.error:
        pass  # Ignore drawing errors
    
    # Author name and title with pulsing effect
    if content_start_y < height - 10:
        name_attr = curses.color_pair(1) | curses.A_BOLD if glow > 0.5 else curses.color_pair(1)
        title_attr = curses.color_pair(2) | curses.A_BOLD if glow < 0.5 else curses.color_pair(2)
        
        _center_text_with_attr(stdscr, content_start_y, name, name_attr, width)
        _center_text_with_attr(stdscr, content_start_y + 1, title, title_attr, width)
    
    # Animated separator
    separator_width = min(width - 20, 40)
    separator_chars = "═♦═"
    separator_pos = int(time.time() * 4) % len(separator_chars)
    separator = separator_chars[separator_pos] * separator_width
    
    if content_start_y + 3 < height - 8:
        _center_text(stdscr, content_start_y + 3, separator, 4, width)
    
    # Random fact with enhanced styling
    fact_y = content_start_y + 5
    if fact_y < height - 6:
        # Draw header with pulsing effect
        header_attr = curses.color_pair(2) | (curses.A_BOLD if glow > 0.7 else 0)
        _center_text_with_attr(stdscr, fact_y, "DID YOU KNOW?", header_attr, width)
        
        fact_text = facts[selected_fact]
        # Wrap the fact text if it's too long
        max_line_width = min(width - 20, 60)
        wrapped_text = _wrap_text(fact_text, max_line_width)
        
        # Draw fact with subtle highlight
        for i, line in enumerate(wrapped_text):
            if fact_y + 2 + i < height - 4:
                _center_text(stdscr, fact_y + 2 + i, line, 3, width)
    
    # Quote instead of advice with enhanced styling
    quote_y = min(fact_y + 2 + len(_wrap_text(facts[selected_fact], min(width - 20, 60))) + 1,
                  height - 10)
    if quote_y < height - 4:
        # Draw header with pulsing effect
        header_attr = curses.color_pair(2) | (curses.A_BOLD if glow < 0.3 else 0)
        _center_text_with_attr(stdscr, quote_y, "WORDS OF WISDOM", header_attr, width)
        
        quote_text = f'"{quotes[selected_quote]}"'
        max_line_width = min(width - 20, 60)
        wrapped_text = _wrap_text(quote_text, max_line_width)
        
        # Draw quote with enhanced styling
        for i, line in enumerate(wrapped_text):
            if quote_y + 2 + i < height - 2:
                line_pos = i / len(wrapped_text)  # Position within quote (0-1)
                # Color gradient effect based on position in quote
                color = 5 if line_pos < 0.5 else 1
                _center_text(stdscr, quote_y + 2 + i, line, color, width)
                
                # Add subtle star particles around the quote
                if random.random() < 0.1:
                    star_x = random.randint(content_x + 5, content_x + content_width - 5)
                    star_char = random.choice(['✦', '✧', '⋆', '✴'])
                    try:
                        stdscr.addstr(quote_y + 2 + i, star_x, star_char, curses.color_pair(4))
                    except curses.error:
                        pass

def _draw_seize_mode(stdscr, text, particles, height, width):
    """Transform the UI into dramatic SEIZE MODE with enhanced visual effects."""
    # Don't clear the screen, transform it
    
    # Create intense background effect
    for y in range(height):
        for x in range(0, width, 4):  # Skip characters for performance
            if random.random() < 0.05:  # Sparse matrix effect
                char = random.choice(['✧', '✦', '✵', '✴', '✸', '⚡', '⭒', '⭑', '∴'])
                try:
                    stdscr.addstr(y, x, char, curses.color_pair(random.choice([1, 2, 4, 6])))
                except curses.error:
                    pass
    
    # Draw dramatic god mode text with pulsing effect
    seize_mode_lines = text.strip().split('\n')
    
    # Make sure text fits in the terminal
    if len(seize_mode_lines) > height - 2:
        seize_mode_lines = ["SEIZE MODE ACTIVATED!"]
        
    start_y = max(0, (height - len(seize_mode_lines)) // 2)
    
    # Dramatic border around SEIZE MODE text
    border_width = max(len(line) for line in seize_mode_lines) + 10
    border_height = len(seize_mode_lines) + 4
    border_x = (width - border_width) // 2
    
    # Draw dramatic pulsing border
    pulse = abs(math.sin(time.time() * 6))  # Faster pulsing
    border_color = 6 if pulse > 0.5 else 1  # Alternate colors
    
    try:
        # Top and bottom borders with zig-zag pattern
        zigzag = "≈" * (border_width - 2)
        stdscr.addstr(start_y - 2, border_x, "╔" + zigzag + "╗", curses.color_pair(border_color) | curses.A_BOLD)
        stdscr.addstr(start_y + border_height - 2, border_x, "╚" + zigzag + "╝", curses.color_pair(border_color) | curses.A_BOLD)
        
        # Side borders with lightning pattern
        for i in range(border_height - 2):
            left_char = "⚡" if i % 2 == 0 else "║"
            right_char = "⚡" if i % 2 == 1 else "║"
            stdscr.addstr(start_y - 1 + i, border_x, left_char, curses.color_pair(border_color) | curses.A_BOLD)
            stdscr.addstr(start_y - 1 + i, border_x + border_width - 1, right_char, curses.color_pair(border_color) | curses.A_BOLD)
    except curses.error:
        pass
    
    # Draw SEIZE MODE text with dramatic color alternation
    for i, line in enumerate(seize_mode_lines):
        if start_y + i < height:
            line_color = 6 if i % 2 == 0 else 1
            _center_text_with_attr(stdscr, start_y + i, line, curses.color_pair(line_color) | curses.A_BOLD, width)
    
    # Add intense particle effects
    for _ in range(min(30, width // 3)):
        _add_particle_burst(
            particles,
            random.randint(0, width - 1),
            random.randint(0, height - 1),
            count=8
        )
    
    # Show dramatic message below SEIZE MODE text
    message_y = start_y + len(seize_mode_lines) + 2
    if message_y < height - 1:
        message = "⚡ UNLIMITED POWER! ⚡"
        message_x = (width - len(message)) // 2
        try:
            # Alternate the colors for each character
            for j, char in enumerate(message):
                char_color = 1 if j % 2 == 0 else 6
                stdscr.addstr(message_y, message_x + j, char, curses.color_pair(char_color) | curses.A_BOLD)
        except curses.error:
            pass

def _draw_cosmic_border(stdscr, y, x, height, width, current_time):
    """Draw an animated cosmic border with stars and particles."""
    try:
        # Define corner and edge characters
        corners = ["╔", "╗", "╚", "╝"]
        
        # Animated edge characters that change over time
        edge_chars = ["═", "≡", "≈", "≣"]
        edge_index = int(current_time * 2) % len(edge_chars)
        edge_char = edge_chars[edge_index]
        
        # Side characters
        side_chars = ["║", "│", "┃"]
        side_index = int(current_time * 1.5) % len(side_chars)
        side_char = side_chars[side_index]
        
        # Draw corners
        stdscr.addstr(y, x, corners[0], curses.color_pair(5) | curses.A_BOLD)
        stdscr.addstr(y, x + width - 1, corners[1], curses.color_pair(5) | curses.A_BOLD)
        stdscr.addstr(y + height - 1, x, corners[2], curses.color_pair(5) | curses.A_BOLD)
        stdscr.addstr(y + height - 1, x + width - 1, corners[3], curses.color_pair(5) | curses.A_BOLD)
        
        # Draw top and bottom edges with animation
        for i in range(1, width - 1):
            stdscr.addstr(y, x + i, edge_char, curses.color_pair(5) | curses.A_BOLD)
            stdscr.addstr(y + height - 1, x + i, edge_char, curses.color_pair(5) | curses.A_BOLD)
        
        # Draw sides with animation
        for i in range(1, height - 1):
            stdscr.addstr(y + i, x, side_char, curses.color_pair(5) | curses.A_BOLD)
            stdscr.addstr(y + i, x + width - 1, side_char, curses.color_pair(5) | curses.A_BOLD)
            
        # Add cosmic particles inside the border
        if random.random() < 0.3:  # Only occasionally add stars for performance
            star_x = random.randint(x + 1, x + width - 2)
            star_y = random.randint(y + 1, y + height - 2)
            star = random.choice(['✦', '✧', '⋆', '★', '☆', '*'])
            stdscr.addstr(star_y, star_x, star, curses.color_pair(4))
    except curses.error:
        pass  # Ignore drawing errors outside the window

def _draw_fancy_border(stdscr, y, x, height, width, current_time=None):
    """Draw a stylish border around the specified area with animation if current_time is provided."""
    # Ensure we're within bounds
    if y < 0 or x < 0 or y + height > curses.LINES or x + width > curses.COLS:
        return
    
    # Choose border style based on time for animation
    if current_time:
        phase = (current_time * 2) % 4
        if phase < 1:
            h_char, v_char = "═", "║"
            tl, tr, bl, br = "╔", "╗", "╚", "╝"
        elif phase < 2:
            h_char, v_char = "─", "│"
            tl, tr, bl, br = "┌", "┐", "└", "┘"
        elif phase < 3:
            h_char, v_char = "━", "┃"
            tl, tr, bl, br = "┏", "┓", "┗", "┛"
        else:
            h_char, v_char = "═", "║"
            tl, tr, bl, br = "╔", "╗", "╚", "╝"
    else:
        h_char, v_char = "═", "║"
        tl, tr, bl, br = "╔", "╗", "╚", "╝"
    
    # Get color based on time for animation
    color = 4  # Default color
    if current_time:
        colors = [4, 6, 1, 5]  # Cycle through different colors
        color_idx = int(current_time * 1.5) % len(colors)
        color = colors[color_idx]
        
    try:
        # Top and bottom borders
        for i in range(1, width - 1):
            if 0 <= y < curses.LINES and 0 <= x + i < curses.COLS:
                stdscr.addstr(y, x + i, h_char, curses.color_pair(color))
            if 0 <= y + height - 1 < curses.LINES and 0 <= x + i < curses.COLS:
                stdscr.addstr(y + height - 1, x + i, h_char, curses.color_pair(color))
        
        # Left and right borders
        for i in range(1, height - 1):
            if 0 <= y + i < curses.LINES and 0 <= x < curses.COLS:
                stdscr.addstr(y + i, x, v_char, curses.color_pair(color))
            if 0 <= y + i < curses.LINES and 0 <= x + width - 1 < curses.COLS:
                stdscr.addstr(y + i, x + width - 1, v_char, curses.color_pair(color))
        
        # Corners
        if 0 <= y < curses.LINES and 0 <= x < curses.COLS:
            stdscr.addstr(y, x, tl, curses.color_pair(color))
        if 0 <= y < curses.LINES and 0 <= x + width - 1 < curses.COLS:
            stdscr.addstr(y, x + width - 1, tr, curses.color_pair(color))
        if 0 <= y + height - 1 < curses.LINES and 0 <= x < curses.COLS:
            stdscr.addstr(y + height - 1, x, bl, curses.color_pair(color))
        if 0 <= y + height - 1 < curses.LINES and 0 <= x + width - 1 < curses.COLS:
            stdscr.addstr(y + height - 1, x + width - 1, br, curses.color_pair(color))
    except curses.error:
        pass  # Ignore drawing errors

def _center_text_with_attr(stdscr, row, text, attr, width):
    """Center text on the specified row with the given attribute."""
    if row < 0 or row >= curses.LINES:
        return
        
    x = max(0, (width - len(text)) // 2)
    try:
        if 0 <= row < curses.LINES and 0 <= x < curses.COLS:
            # Truncate if necessary
            max_width = curses.COLS - x
            if len(text) > max_width:
                text = text[:max_width]
            stdscr.addstr(row, x, text, attr)
    except curses.error:
        pass  # Ignore errors when writing outside bounds

def _show_terminal_too_small(stdscr):
    """Show a message when terminal is too small."""
    stdscr.clear()
    try:
        height, width = stdscr.getmaxyx()
        
        message1 = "Terminal too small!"
        message2 = "Please resize and press any key to continue"
        
        y1 = height // 2 - 1
        y2 = height // 2
        
        if 0 <= y1 < height and width > len(message1):
            x1 = (width - len(message1)) // 2
            stdscr.addstr(y1, x1, message1, curses.color_pair(6) | curses.A_BOLD)
            
        if 0 <= y2 < height and width > len(message2):
            x2 = (width - len(message2)) // 2
            stdscr.addstr(y2, x2, message2, curses.color_pair(3))
            
        stdscr.refresh()
        stdscr.timeout(-1)  # Wait indefinitely
        stdscr.getch()
    except curses.error:
        pass

def _center_text(stdscr, row, text, color_pair, width):
    """Center text on the specified row with the given color pair index."""
    if row < 0 or row >= curses.LINES:
        return
        
    x = max(0, (width - len(text)) // 2)
    try:
        if 0 <= row < curses.LINES and 0 <= x < curses.COLS:
            # Truncate if necessary
            max_width = curses.COLS - x
            if len(text) > max_width:
                text = text[:max_width]
            stdscr.addstr(row, x, text, curses.color_pair(color_pair))
    except curses.error:
        pass  # Ignore errors when writing outside bounds

def _wrap_text(text, width):
    """Wrap text to fit within the given width."""
    import textwrap
    return textwrap.wrap(text, width=width, break_long_words=True, replace_whitespace=True)

def _add_particle_burst(particles, x, y, count=5):
    """Add a burst of particles from a position."""
    for _ in range(count):
        particle = {
            'x': x,
            'y': y,
            'dx': random.uniform(-1.5, 1.5),
            'dy': random.uniform(-0.8, 0.8),
            'life': random.uniform(0.3, 0.8),
            'char': random.choice(['*', '+', '.', '•', '✦', '✧', '⋆', '★']),
            'color': random.randint(1, 5)
        }
        particles.append(particle)

def _update_particles(stdscr, particles, last_time, height, width):
    """Update and draw all particle effects."""
    current_time = time.time()
    dt = current_time - last_time
    
    remaining_particles = []
    for p in particles[:]:
        p['life'] -= dt
        if p['life'] > 0:
            p['x'] += p['dx'] * dt * 10
            p['y'] += p['dy'] * dt * 8
            
            # Only draw if within screen bounds
            x_pos, y_pos = int(p['x']), int(p['y'])
            if 0 <= y_pos < height - 1 and 0 <= x_pos < width - 1:
                try:
                    stdscr.addstr(y_pos, x_pos, p['char'], curses.color_pair(p['color']))
                except curses.error:
                    pass  # Ignore if we can't draw
            
            remaining_particles.append(p)
    
    particles.clear()
    particles.extend(remaining_particles)


class LeaderboardPage:
    """Interactive leaderboard page showing repository contributors and their changes."""
    
    COLUMN_LAYOUT = {
        "rank": {"x": 6, "width": 8},
        "name": {"x": 16, "width": 25},
        "commits": {"x": 43, "width": 12},
        "changes": {"x": 57, "width": 20},
        "impact": {"x": 79, "width": 10}
    }
    
    def __init__(self, stdscr, stats):
        """Initialize the leaderboard page."""
        self.stdscr = stdscr
        self.stats = stats
        self.selected_author = 0
        self.show_files = False
        self.decryption = DecryptionEffect()
        self.particles = []
        self.matrix_rain = MatrixRain(stdscr)
        self.last_time = time.time()
        self.frame_time = 1.0 / 30.0  # 30 FPS
        self.accumulated_time = 0.0
        self.animation_offset = 0.0  # For smooth animations
        
        # Initialize color pairs
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_GREEN, -1)   # For additions
        curses.init_pair(2, curses.COLOR_RED, -1)     # For deletions
        curses.init_pair(3, curses.COLOR_YELLOW, -1)  # For highlights
        curses.init_pair(4, curses.COLOR_CYAN, -1)    # For headers
        curses.init_pair(5, curses.COLOR_MAGENTA, -1) # For borders
        curses.init_pair(6, curses.COLOR_WHITE, -1)   # For text
        
    def draw_header(self):
        """Draw the leaderboard header with cosmic effects."""
        height, width = self.stdscr.getmaxyx()
        
        # Draw title box with cosmic border
        title_height = 3
        title_width = 50
        title_x = (width - title_width) // 2
        _draw_cosmic_border(self.stdscr, 1, title_x, title_height, title_width, time.time())
        
        # Draw title with pulsing animation
        title = "🏆 Repository Leaderboard 🏆"
        pulse = abs(math.sin(time.time() * 2))
        title_attr = curses.color_pair(4 if pulse > 0.5 else 1) | curses.A_BOLD
        _center_text_with_attr(self.stdscr, 2, title, title_attr, width)
        
        # Add particle effects around title
        if random.random() < 0.1:
            for _ in range(2):
                _add_particle_burst(
                    self.particles,
                    title_x + random.randint(0, title_width),
                    2,
                    count=2
                )
        
    def draw_author_list(self, start_y, height, width):
        """Draw the list of authors with cosmic effects."""
        if not self.stats["authors"]:
            self.draw_empty_state(start_y, height, width)
            return
            
        # Draw container box with cosmic border
        list_height = min(len(self.stats["authors"]) * 2 + 3, height - start_y - 3)  # Reduced spacing
        list_width = width - 4
        _draw_cosmic_border(self.stdscr, start_y, 2, list_height, list_width, time.time())
        
        # Draw column headers with pulsing effect
        headers = {
            "rank": "Rank",
            "name": "Author",
            "commits": "Commits",
            "changes": "Changes",
            "impact": "Impact"
        }
        
        header_y = start_y + 1
        pulse = abs(math.sin(time.time() * 2))
        header_attr = curses.color_pair(4) | (curses.A_BOLD if pulse > 0.5 else 0)
        
        # Draw headers with proper spacing
        for col, header in headers.items():
            x = self.COLUMN_LAYOUT[col]["x"]
            self.stdscr.addstr(header_y, x, header.ljust(self.COLUMN_LAYOUT[col]["width"]), header_attr)
        
        # Draw animated separator
        separator_chars = ["═", "═", "═", "═", "═", "═", "═", "═"]  # Smoother animation
        separator_pos = int((time.time() * 4 + self.animation_offset) % len(separator_chars))
        separator = separator_chars[separator_pos] * (list_width - 2)
        self.stdscr.addstr(header_y + 1, 3, separator, curses.color_pair(5) | curses.A_BOLD)
        
        # Draw author entries with enhanced effects
        visible_authors = min(10, len(self.stats["authors"]))
        for i, author in enumerate(self.stats["authors"][:visible_authors]):
            y = start_y + 3 + (i * 2)  # Reduced vertical spacing
            if y >= start_y + list_height - 1:
                break
                
            # Calculate smooth animation effects
            is_selected = i == self.selected_author
            pulse = abs(math.sin(time.time() * 2 + i * 0.3))
            row_offset = math.sin(time.time() * 1.5 + i * 0.5) * 0.3  # Subtle floating effect
            
            # Base attributes with smooth transitions
            base_attr = curses.A_REVERSE if is_selected else (curses.A_BOLD if pulse > 0.7 else 0)
            
            # Draw rank with medals and effects
            rank_x = self.COLUMN_LAYOUT["rank"]["x"]
            if i < 3:
                rank_symbols = ["🥇 ", "🥈 ", "🥉 "]
                rank_symbol = rank_symbols[i]
                if pulse > 0.8:
                    rank_symbol = f"✨{rank_symbol[0]}✨"
            else:
                rank_symbol = f" {i+1}.".ljust(4)
            
            rank_attr = curses.color_pair(3) | base_attr
            self.stdscr.addstr(y, rank_x, rank_symbol.ljust(self.COLUMN_LAYOUT["rank"]["width"]), rank_attr)
            
            # Draw author name with cosmic glow
            name_x = self.COLUMN_LAYOUT["name"]["x"]
            name = author.get("name", "Unknown")
            if len(name) > self.COLUMN_LAYOUT["name"]["width"] - 3:
                name = name[:self.COLUMN_LAYOUT["name"]["width"] - 5] + "..."
            name_attr = curses.color_pair(6) | base_attr
            if is_selected:
                name_attr |= curses.A_BOLD
            self.stdscr.addstr(y, name_x, name.ljust(self.COLUMN_LAYOUT["name"]["width"]), name_attr)
            
            # Draw commit count with dynamic formatting
            commits_x = self.COLUMN_LAYOUT["commits"]["x"]
            commits = author.get("commits", 0)
            commit_str = f"{commits:,}".rjust(self.COLUMN_LAYOUT["commits"]["width"] - 2)
            commit_attr = curses.color_pair(4) | base_attr
            if commits > 100:
                commit_attr |= curses.A_BOLD
            self.stdscr.addstr(y, commits_x, commit_str, commit_attr)
            
            # Draw changes with color gradient
            changes_x = self.COLUMN_LAYOUT["changes"]["x"]
            additions = author.get('additions', 0)
            deletions = author.get('deletions', 0)
            changes = f"+{additions:,} -{deletions:,}"
            if len(changes) > self.COLUMN_LAYOUT["changes"]["width"]:
                changes = f"+{additions//1000}k -{deletions//1000}k"
            changes_attr = curses.color_pair(1) | base_attr
            self.stdscr.addstr(y, changes_x, changes.ljust(self.COLUMN_LAYOUT["changes"]["width"]), changes_attr)
            
            # Draw impact score with dynamic effects
            impact_x = self.COLUMN_LAYOUT["impact"]["x"]
            impact = (additions + deletions) / max(commits, 1)
            impact_str = f"{impact:.1f}".rjust(self.COLUMN_LAYOUT["impact"]["width"] - 2)
            impact_attr = curses.color_pair(3) | base_attr
            if impact > 100:
                impact_attr |= curses.A_BOLD
            self.stdscr.addstr(y, impact_x, impact_str, impact_attr)
            
            # Add subtle row highlight for selected item
            if is_selected:
                highlight_char = "·" if pulse > 0.5 else "∙"
                self.stdscr.addstr(y, 3, highlight_char, curses.color_pair(4) | curses.A_BOLD)
                self.stdscr.addstr(y, list_width, highlight_char, curses.color_pair(4) | curses.A_BOLD)
            
            # Add particle effects for top contributors
            if (i < 3 or is_selected) and random.random() < 0.1:
                _add_particle_burst(
                    self.particles,
                    random.randint(4, width-4),
                    y,
                    count=2
                )
        
        # Update animation offset
        self.animation_offset += 0.1
        
    def draw_empty_state(self, start_y, height, width):
        """Draw an enhanced empty state message with cosmic effects."""
        messages = [
            "✨ No Commit History Found ✨",
            "",
            "This could be because:",
            "• The repository is new with no commits",
            "• No commits have been made yet",
            "• Git history is not accessible",
            "",
            "Make some commits to see your achievements!"
        ]
        
        # Draw message box with cosmic border
        box_height = len(messages) + 4
        box_width = 50
        box_x = (width - box_width) // 2
        _draw_cosmic_border(self.stdscr, start_y, box_x, box_height, box_width, time.time())
        
        # Draw messages with enhanced effects
        for i, message in enumerate(messages):
            if start_y + 2 + i >= height:
                break
                
            # Choose color based on message type with pulsing effects
            pulse = abs(math.sin(time.time() * 2 + i * 0.5))
            if i == 0:  # Main message
                color = curses.color_pair(4) | curses.A_BOLD
                if pulse > 0.7:
                    color |= curses.A_REVERSE
            elif i == 2:  # "This could be because:"
                color = curses.color_pair(3) | (curses.A_BOLD if pulse > 0.5 else 0)
            elif message.startswith("•"):  # Bullet points
                color = curses.color_pair(6) | (curses.A_BOLD if pulse > 0.6 else 0)
            elif message == "":  # Empty lines
                continue
            else:  # Call to action
                color = curses.color_pair(1) | curses.A_BOLD
            
            # Add sparkle animation to the main message
            if i == 0:
                sparkle = "⭐" if pulse > 0.5 else "✨"
                message = f"{sparkle} {message.strip('✨')} {sparkle}"
            
            _center_text_with_attr(self.stdscr, start_y + 2 + i, message, color, width)
        
        # Add cosmic particle effects
        if random.random() < 0.1:
            for _ in range(2):
                _add_particle_burst(
                    self.particles,
                    random.randint(box_x, box_x + box_width),
                    start_y + random.randint(0, box_height),
                    count=4
                )
            
    def draw_footer(self, height, width):
        """Draw an enhanced footer with cosmic effects."""
        footer_y = height - 2
        footer_text = "↑/↓: Navigate   F: Toggle Files   Q: Quit"
        
        # Draw footer box with cosmic border
        footer_width = len(footer_text) + 4
        footer_x = (width - footer_width) // 2
        _draw_cosmic_border(self.stdscr, footer_y - 1, footer_x, 3, footer_width, time.time())
        
        # Draw footer text with pulsing effect
        pulse = abs(math.sin(time.time() * 1.5))
        footer_attr = curses.color_pair(6) | (curses.A_BOLD if pulse > 0.7 else curses.A_DIM)
        _center_text_with_attr(self.stdscr, footer_y, footer_text, footer_attr, width)
        
    def run(self):
        """Run the leaderboard page with smooth animations."""
        try:
            curses.curs_set(0)  # Hide cursor
            
            while True:
                # Handle frame timing
                current_time = time.time()
                delta_time = current_time - self.last_time
                self.accumulated_time += delta_time
                
                if self.accumulated_time < self.frame_time:
                    time.sleep(max(0, self.frame_time - self.accumulated_time))
                    continue
                
                self.last_time = current_time
                self.accumulated_time = 0.0
                
                # Clear and get dimensions
                self.stdscr.clear()
                height, width = self.stdscr.getmaxyx()
                
                # Draw matrix rain in background
                self.matrix_rain.update()
                
                # Draw components
                self.draw_header()
                self.draw_author_list(5, height - 8, width)
                self.draw_footer(height, width)
                
                # Update effects
                self.decryption.update()
                _update_particles(self.stdscr, self.particles, current_time, height, width)
                
                # Refresh screen
                self.stdscr.refresh()
                
                # Handle input
                try:
                    key = self.stdscr.getch()
                    if key == ord('q'):
                        break
                    elif key == curses.KEY_UP and self.selected_author > 0:
                        self.selected_author -= 1
                        _add_particle_burst(self.particles, width // 2, 5 + self.selected_author * 2)
                    elif key == curses.KEY_DOWN and self.selected_author < len(self.stats.get("authors", [])) - 1:
                        self.selected_author += 1
                        _add_particle_burst(self.particles, width // 2, 5 + self.selected_author * 2)
                    elif key == ord('f'):
                        self.show_files = not self.show_files
                        # Add effect for toggle
                        _add_particle_burst(self.particles, width - 10, height - 2)
                except curses.error:
                    continue
                
            return True
            
        except Exception as e:
            logging.error(f"Error running leaderboard GUI: {str(e)}")
            return False


if __name__ == "__main__":
    logging.info("qgit_gui.py started")
    if len(sys.argv) > 1 and sys.argv[1] == "help":
        logging.info("Showing help page")
        show_help()
    else:
        logging.info("Running main GUI")
        action = run_gui()
        if action:
            logging.info(f"Selected action: {action}")
            print(f"Selected action: {action}")
