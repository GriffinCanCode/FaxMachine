#!/usr/bin/env python3
"""
Faxmachine - File Template Manager
A utility for storing and injecting commonly used files and templates.
"""

import os
import sys
import shutil
import argparse
import json
from pathlib import Path
import readline  # For better command line editing
import tempfile
import difflib
import subprocess
import re
from datetime import datetime
import csv
import importlib.util
import textwrap

# Constants
VERSION = "1.1.0"
CONFIG_DIR = os.path.expanduser("~/.faxmachine")
DB_DIR = os.path.join(CONFIG_DIR, "db")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
METADATA_DIR = os.path.join(CONFIG_DIR, "metadata")

# ANSI colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    BG_GREEN = '\033[42m'  # Green background
    BG_BLUE = '\033[44m'   # Blue background
    BG_YELLOW = '\033[43m' # Yellow background
    BG_GREY = '\033[47m'   # Grey background
    BLACK = '\033[30m'     # Black text

def print_colored(text, color):
    """Print text with color"""
    print(f"{color}{text}{Colors.ENDC}")

def print_header(text):
    """Print a nicely formatted header"""
    try:
        width = min(os.get_terminal_size().columns, 80)
    except (OSError, AttributeError):
        width = 80  # Default width if not in a terminal
    print_colored("=" * width, Colors.BOLD)
    print_colored(f"{text.center(width)}", Colors.BOLD + Colors.BLUE)
    print_colored("=" * width, Colors.BOLD)

def create_default_config():
    """Create default configuration"""
    config = {
        "version": VERSION,
        "aliases": {},
        "last_accessed": [],
        "settings": {
            "default_editor": os.environ.get("EDITOR", "vi"),
            "search_content": True,
            "preview_before_inject": True
        }
    }
    return config

def load_config():
    """Load or create configuration"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print_colored("Config file corrupted, creating new one", Colors.RED)
            config = create_default_config()
            save_config(config)
            return config
    else:
        config = create_default_config()
        save_config(config)
        return config

def save_config(config):
    """Save configuration to file"""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def init_db():
    """Initialize the database directory structure"""
    os.makedirs(DB_DIR, exist_ok=True)
    os.makedirs(METADATA_DIR, exist_ok=True)
    
    # Create some default categories
    for category in ["git", "web", "python", "config", "other"]:
        os.makedirs(os.path.join(DB_DIR, category), exist_ok=True)
    
    # Add some example files if db is empty
    if not os.listdir(os.path.join(DB_DIR, "git")):
        example_gitignore = os.path.join(DB_DIR, "git", "python-gitignore")
        with open(example_gitignore, 'w') as f:
            f.write("""# Python gitignore
__pycache__/
*.py[cod]
*$py.class
.env
venv/
ENV/
.vscode/
""")
        
        # Add metadata for example file
        save_metadata("git/python-gitignore", {
            "description": "Standard gitignore for Python projects",
            "added_date": datetime.now().isoformat(),
            "tags": ["python", "git", "ignore"]
        })

def get_metadata_path(file_path):
    """Get the path to the metadata file for a given file"""
    rel_path = os.path.relpath(file_path, DB_DIR) if os.path.isabs(file_path) else file_path
    safe_path = rel_path.replace("/", "_").replace("\\", "_")
    return os.path.join(METADATA_DIR, f"{safe_path}.json")

def save_metadata(file_path, metadata):
    """Save metadata for a file"""
    os.makedirs(METADATA_DIR, exist_ok=True)
    metadata_path = get_metadata_path(file_path)
    
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

def load_metadata(file_path):
    """Load metadata for a file"""
    metadata_path = get_metadata_path(file_path)
    
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def list_items(path=None, indent=0):
    """List items in the database with tree-like structure"""
    if path is None:
        path = DB_DIR
    
    items = sorted(os.listdir(path))
    for i, item in enumerate(items):
        item_path = os.path.join(path, item)
        is_last = i == len(items) - 1
        
        if os.path.isdir(item_path):
            # Print directory
            prefix = "   " * (indent-1) + "└── " if is_last and indent > 0 else "   " * (indent-1) + "├── " if indent > 0 else ""
            print_colored(f"{prefix}{item}/", Colors.BLUE + Colors.BOLD)
            list_items(item_path, indent + 1)
        else:
            # Print file
            prefix = "   " * (indent-1) + "└── " if is_last and indent > 0 else "   " * (indent-1) + "├── " if indent > 0 else ""
            rel_path = os.path.relpath(item_path, DB_DIR)
            metadata = load_metadata(rel_path)
            description = metadata.get('description', '')
            description_text = f" - {description}" if description else ""
            print(f"{prefix}{item}{description_text}")

def smart_preview_file(file_path):
    """
    Generate a smart preview of file contents with NLP analysis
    Returns a tuple of (summary, suggested_tags, full_preview, error_message)
    """
    file_ext = os.path.splitext(file_path)[1].lower()
    summary = ""
    suggested_tags = []
    full_preview = ""
    error_message = None
    
    # Check if we have required dependencies
    nltk_available = importlib.util.find_spec("nltk") is not None
    pdf_available = importlib.util.find_spec("pdfplumber") is not None
    spacy_available = importlib.util.find_spec("spacy") is not None
    yake_available = importlib.util.find_spec("yake") is not None
    
    # Try to use the most efficient yet effective NLP stack
    if not nltk_available and not spacy_available and not yake_available:
        try:
            print_colored("Installing lightweight NLP library for text analysis...", Colors.YELLOW)
            
            # First try to install YAKE for keyword extraction (lightweight)
            subprocess.check_call([sys.executable, "-m", "pip", "install", "yake"])
            yake_available = True
            
            # If that works, try spaCy with small model as second priority
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "spacy"])
                subprocess.check_call([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
                spacy_available = True
            except:
                # If spaCy fails, fall back to NLTK
                subprocess.check_call([sys.executable, "-m", "pip", "install", "nltk"])
                nltk_available = True
        except Exception as e:
            error_message = f"NLP library installation failed: {str(e)}"
    
    if file_ext == '.pdf' and not pdf_available:
        try:
            print_colored("Installing pdfplumber for PDF analysis...", Colors.YELLOW)
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pdfplumber"])
            pdf_available = True
        except Exception as e:
            error_message = f"PDF library installation failed: {str(e)}"
    
    try:
        # Extract text content based on file type
        if file_ext == '.json':
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                data = json.load(f)
                content = json.dumps(data, indent=2)
                
                # Create summary for JSON
                keys = list(data.keys()) if isinstance(data, dict) else []
                if keys:
                    summary = f"JSON with {len(keys)} keys: {', '.join(keys[:5])}"
                    if len(keys) > 5:
                        summary += f" and {len(keys) - 5} more"
                else:
                    summary = f"JSON array with {len(data)} items" if isinstance(data, list) else "JSON data"
                
                # Suggest tags for JSON
                suggested_tags = ["json"]
                if isinstance(data, dict):
                    # More sophisticated JSON analysis
                    all_keys = _get_all_json_keys(data)
                    if len(all_keys) > 0:
                        # Get the most common/important keys as potential tags
                        for key in sorted(set(all_keys))[:5]:
                            if len(key) > 3 and key.isalpha() and key.lower() not in suggested_tags:
                                suggested_tags.append(key.lower())
                    
                    # Check for specific patterns in keys
                    key_str = " ".join(all_keys).lower()
                    if "config" in key_str:
                        suggested_tags.append("config")
                    if "settings" in key_str:
                        suggested_tags.append("settings")
                    if "api" in key_str:
                        suggested_tags.append("api")
                
                # Generate preview
                full_preview = content[:1000] + "..." if len(content) > 1000 else content
        
        elif file_ext == '.csv':
            rows = []
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                csv_reader = csv.reader(f)
                headers = next(csv_reader, [])
                for i, row in enumerate(csv_reader):
                    rows.append(row)
                    if i >= 10:  # Read just enough rows for preview
                        break
            
            # Create summary for CSV
            row_count = len(rows)
            summary = f"CSV with {len(headers)} columns: {', '.join(headers[:5])}"
            if len(headers) > 5:
                summary += f" and {len(headers) - 5} more"
            summary += f". Contains {row_count}+ rows."
            
            # Suggest tags for CSV
            suggested_tags = ["csv", "data"]
            
            # More sophisticated CSV analysis
            header_str = " ".join(headers).lower()
            if any(date_term in header_str for date_term in ["date", "time", "year", "month"]):
                suggested_tags.append("temporal")
            if any(geo_term in header_str for geo_term in ["country", "city", "location", "address", "state"]):
                suggested_tags.append("geographic")
            if any(fin_term in header_str for fin_term in ["price", "cost", "revenue", "sales", "profit"]):
                suggested_tags.append("financial")
                
            # Generate preview
            preview_rows = [headers] + rows[:5]
            full_preview = "\n".join([", ".join(row) for row in preview_rows])
            if row_count > 5:
                full_preview += f"\n... and {row_count - 5} more rows"
        
        elif file_ext == '.pdf':
            if pdf_available:
                try:
                    import pdfplumber
                    
                    # Suppress the CropBox warnings by redirecting stderr temporarily
                    import io
                    from contextlib import redirect_stderr
                    
                    # Use context manager to suppress pdfplumber warnings
                    with redirect_stderr(io.StringIO()):
                        with pdfplumber.open(file_path) as pdf:
                            pages = len(pdf.pages)
                            text = ""
                            page_texts = []
                            
                            # Extract text from more pages for better analysis
                            for i in range(min(8, pages)):
                                try:
                                    page_text = pdf.pages[i].extract_text() or ""
                                    if page_text:
                                        # Deep text cleaning
                                        # Fix common PDF extraction issues with duplicate characters
                                        page_text = re.sub(r'([A-Za-z])\1{2,}', r'\1', page_text)
                                        # Fix common spacing issues
                                        page_text = re.sub(r'(?<=[a-zA-Z])- (?=[a-zA-Z])', '', page_text)
                                        # Fix common character errors
                                        page_text = page_text.replace('|', 'I').replace('l', 'l')
                                        page_texts.append(page_text)
                                        text += page_text + "\n\n"
                                except Exception:
                                    # Skip pages that fail to extract
                                    continue
                            
                            # If we couldn't extract text from any pages, bail out
                            if not text.strip():
                                summary = f"PDF document with {pages} pages (No readable text content)"
                                suggested_tags = ["pdf", "document"]
                                full_preview = "This PDF doesn't contain extractable text content and may be image-based or secured."
                                return (summary, suggested_tags, full_preview, None)
                            
                            # Get filename for context
                            filename = os.path.basename(file_path)
                            filename_without_ext = os.path.splitext(filename)[0]
                            
                            # Extract title using multiple approaches
                            title = ""
                            
                            # 1. Try to use the first page's significant text
                            first_page_text = page_texts[0] if page_texts else ""
                            
                            # Split into lines and clean
                            lines = [line.strip() for line in first_page_text.split('\n') if line.strip()]
                            candidate_titles = []
                            
                            # Look for title candidates in the first 5 lines
                            for line in lines[:5]:
                                # Clean the line
                                clean_line = re.sub(r'\s+', ' ', line).strip()
                                # Skip dates, URLs, very short text, or very long text
                                if (len(clean_line) < 5 or len(clean_line) > 100 or
                                    re.search(r'\d{1,2}[/\.-]\d{1,2}[/\.-]\d{2,4}', clean_line) or
                                    re.search(r'http|www|\.com|github|colab', clean_line.lower())):
                                    continue
                                candidate_titles.append(clean_line)
                            
                            # Use the first good candidate as title
                            if candidate_titles:
                                title = candidate_titles[0]
                            # If no good candidates, try using the filename as title
                            elif filename_without_ext and len(filename_without_ext) > 3:
                                # Clean up the filename to make it more readable
                                title_from_filename = filename_without_ext.replace('_', ' ').replace('-', ' ')
                                title_from_filename = re.sub(r'\s+', ' ', title_from_filename).strip()
                                if len(title_from_filename) < 100:
                                    title = title_from_filename
                            
                            # Collect core content for summary generation
                            # Focus on the first few pages where important info usually appears
                            content_for_summary = "\n".join(page_texts[:3] if page_texts else [])
                            
                            # Clean up text for better processing
                            clean_content = re.sub(r'\s+', ' ', content_for_summary).strip()
                            
                            # Extract potential document type/category
                            doc_type = ""
                            doc_type_patterns = [
                                r'\b(?:user guide|manual|tutorial|documentation|white paper|research paper|article|report|case study|thesis|dissertation|review|analysis)\b',
                                r'\b(?:handbook|guide|overview|introduction to|reference|journal|publication)\b'
                            ]
                            for pattern in doc_type_patterns:
                                doc_type_match = re.search(pattern, clean_content.lower())
                                if doc_type_match:
                                    doc_type = doc_type_match.group(0).capitalize()
                                    break
                            
                            # Extract key topics from text (look for repeated significant terms)
                            # First, clean and normalize text
                            word_extraction_text = re.sub(r'[^\w\s]', ' ', clean_content.lower())
                            words = word_extraction_text.split()
                            
                            # Filter out common words that don't help identify document topics
                            common_words = set(['the', 'and', 'for', 'this', 'that', 'with', 'from', 'your', 'their',
                                              'have', 'has', 'had', 'not', 'are', 'were', 'was', 'will', 'would',
                                              'should', 'can', 'could', 'been', 'being', 'they', 'them', 'there',
                                              'then', 'than', 'this', 'who', 'what', 'where', 'when', 'why', 'how',
                                              'which', 'some', 'many', 'much', 'very', 'every', 'only', 'also'])
                            
                            # Count word frequencies (only for words of reasonable length)
                            word_counts = {}
                            for word in words:
                                if len(word) > 3 and word not in common_words:
                                    word_counts[word] = word_counts.get(word, 0) + 1
                            
                            # Get top repeating terms
                            key_terms = [word for word, count in sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:8] if count > 2]
                            
                            # Extract proper sections from the document
                            section_candidates = []
                            
                            # Look for patterns that suggest section headings
                            section_patterns = [
                                # Numbered sections like "1. Introduction"
                                r'\n\s*\d+\.\s+([A-Z][a-zA-Z0-9\s\-]{2,40})\s*\n',
                                # Capital letter sections like "INTRODUCTION"
                                r'\n\s*([A-Z][A-Z\s\-]{2,40}[A-Z])\s*\n',
                                # Title case sections like "Introduction to Topic"
                                r'\n\s*([A-Z][a-zA-Z0-9\s\-]{2,40})\s*\n'
                            ]
                            
                            for pattern in section_patterns:
                                matches = re.findall(pattern, '\n' + text + '\n')
                                section_candidates.extend(matches)
                            
                            # Clean and filter the section candidates
                            clean_sections = []
                            for section in section_candidates:
                                # Clean the section name
                                clean_section = re.sub(r'\s+', ' ', section).strip()
                                
                                # Apply filters to exclude false positives
                                if (len(clean_section) >= 4 and len(clean_section) <= 50 and
                                    not re.search(r'http|www|\.com|github|colab', clean_section.lower()) and
                                    not clean_section.isdigit() and
                                    # Avoid duplicates
                                    clean_section not in clean_sections and
                                    # Avoid common headers/footers
                                    not re.match(r'page \d+|\d+ of \d+|copyright|all rights reserved', clean_section.lower())):
                                    clean_sections.append(clean_section)
                            
                            # Build the summary
                            summary_parts = []
                            
                            # Add title if we have one
                            if title:
                                summary_parts.append(title)
                            
                            # Add document type if we identified one
                            if doc_type:
                                summary_parts.append(f"{doc_type} with {pages} pages")
                            else:
                                summary_parts.append(f"PDF document with {pages} pages")
                            
                            # Add key topics if we found any
                            if key_terms:
                                topics_text = "Key topics: " + ", ".join([term.capitalize() for term in key_terms[:5]])
                                summary_parts.append(topics_text)
                            
                            # Add sections if we found any
                            if clean_sections:
                                # Limit to top sections to avoid overwhelming
                                section_text = "Sections include: " + ", ".join(clean_sections[:5])
                                if len(clean_sections) > 5:
                                    section_text += f" and {len(clean_sections) - 5} more"
                                summary_parts.append(section_text)
                            
                            # Look for an abstract or summary paragraph
                            abstract = ""
                            abstract_patterns = [
                                r'(?:abstract|summary|overview|introduction)[\s\:]+([^\.]+\.[^\.]+\.[^\.]+\.)',
                                r'(?:this paper|this document|this guide|this report)[\s\:]?([^\.]+\.[^\.]+\.)'
                            ]
                            
                            for pattern in abstract_patterns:
                                abstract_match = re.search(pattern, clean_content.lower())
                                if abstract_match:
                                    abstract_text = abstract_match.group(1).strip()
                                    # Clean up the abstract text
                                    abstract = re.sub(r'\s+', ' ', abstract_text).strip().capitalize()
                                    if len(abstract) > 40:
                                        break
                            
                            # Include abstract if found
                            if abstract and len(abstract) < 300:
                                summary_parts.append(abstract)
                            
                            # Combined formatted summary
                            summary = "\n".join(summary_parts)
                            
                            # Generate clean preview (first page usually contains important context)
                            first_page_preview = first_page_text[:2000] if first_page_text else text[:2000]
                            full_preview = re.sub(r'\s+', ' ', first_page_preview).strip()
                            if len(full_preview) > 2000:
                                full_preview = full_preview[:2000] + "..."
                            
                            # Enhanced tag generation
                            suggested_tags = ["pdf"]
                            
                            # Include document type as a tag if we found one
                            if doc_type and doc_type.lower() not in suggested_tags:
                                suggested_tags.append(doc_type.lower())
                            
                            # Include key terms as tags
                            for term in key_terms:
                                if len(term) > 3 and term not in suggested_tags:
                                    suggested_tags.append(term)
                            
                            # Extract additional technology/domain terms
                            domain_terms = re.findall(r'\b(?:API|SDK|AI|ML|NLP|GPU|CPU|HTTP|REST|Cloud|React|Angular|Vue|Node|Python|Java|SQL|NoSQL|MongoDB|Docker|Kubernetes|AWS|Azure|GCP|IoT|blockchain|data science|machine learning|deep learning|neural network|analytics|visualization)\b', text, re.IGNORECASE)
                            for term in set(domain_terms):
                                term_lower = term.lower()
                                if term_lower not in suggested_tags:
                                    suggested_tags.append(term_lower)
                            
                            # If we have title words, add those that aren't covered yet
                            if title:
                                title_words = [w.lower() for w in re.findall(r'\b[A-Za-z]{4,}\b', title)
                                              if w.lower() not in common_words]
                                for word in title_words:
                                    if word not in suggested_tags and len(word) > 3:
                                        suggested_tags.append(word)
                            
                            # Limit tags to a reasonable number
                            suggested_tags = suggested_tags[:12]
                            
                except Exception as e:
                    error_message = f"PDF parsing error: {str(e)}"
                    summary = f"PDF document with {pages} pages (parsing error)"
                    suggested_tags = ["pdf"]
                    full_preview = "Error extracting content from PDF."
            else:
                summary = "PDF document (PDF library not available)"
                suggested_tags = ["pdf"]
                error_message = "PDF processing requires pdfplumber library"
        
        else:
            # For other text files, read as regular text
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(10000)  # Read first 10000 chars
                
                lines = content.split('\n')
                line_count = len(lines)
                
                # Basic summary
                summary = f"Text file with {line_count} lines"
                
                # Generate preview
                full_preview = content[:1000] + "..." if len(content) > 1000 else content
                
                # Simple file type detection and tagging
                suggested_tags = []
                
                # Check for programming languages
                if file_ext in ['.py', '.pyc']:
                    suggested_tags.extend(["python", "code"])
                elif file_ext in ['.js', '.jsx', '.ts', '.tsx']:
                    suggested_tags.extend(["javascript", "code"])
                elif file_ext == '.html':
                    suggested_tags.extend(["html", "web"])
                elif file_ext == '.css':
                    suggested_tags.extend(["css", "web"])
                elif file_ext == '.md':
                    suggested_tags.extend(["markdown", "documentation"])
                elif file_ext in ['.sh', '.bash']:
                    suggested_tags.extend(["shell", "script"])
                elif file_ext == '.txt':
                    suggested_tags.append("text")
                    
                # Process the text for additional tags using the best available NLP tool
                if len(content.strip()) > 0:
                    additional_tags = _extract_keywords(content[:5000])
                    for tag in additional_tags:
                        if tag not in suggested_tags:
                            suggested_tags.append(tag)
            except:
                summary = f"Binary or non-text file"
                suggested_tags = ["binary"]
    
    except Exception as e:
        error_message = f"Error analyzing file: {str(e)}"
        summary = "File analysis error"
    
    return (summary, suggested_tags, full_preview, error_message)

def _get_all_json_keys(json_obj, prefix="", keys=None):
    """Recursively extract all keys from a JSON object"""
    if keys is None:
        keys = []
    
    if isinstance(json_obj, dict):
        for key, value in json_obj.items():
            full_key = f"{prefix}.{key}" if prefix else key
            keys.append(key)
            _get_all_json_keys(value, full_key, keys)
    elif isinstance(json_obj, list):
        for item in json_obj:
            _get_all_json_keys(item, prefix, keys)
    
    return keys

def _extract_keywords(text, max_keywords=5):
    """Extract keywords from text using the best available NLP model"""
    keywords = []
    
    # Check if YAKE is available (lightweight keyword extraction)
    if importlib.util.find_spec("yake") is not None:
        try:
            import yake
            # Configure YAKE with optimal settings for efficiency
            language = "en"
            max_ngram_size = 1
            deduplication_threshold = 0.3
            kw_extractor = yake.KeywordExtractor(
                lan=language, 
                n=max_ngram_size,
                dedupLim=deduplication_threshold,
                top=max_keywords
            )
            keywords = [kw[0] for kw in kw_extractor.extract_keywords(text)]
            return keywords
        except Exception:
            pass # Fall back to next method
    
    # Check if spaCy is available (better quality, medium weight)
    if importlib.util.find_spec("spacy") is not None:
        try:
            import spacy
            try:
                nlp = spacy.load("en_core_web_sm")
            except:
                # Try download if not found
                subprocess.check_call([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
                nlp = spacy.load("en_core_web_sm")
                
            # Process the text efficiently with spaCy
            doc = nlp(text[:5000])  # Limit to first 5000 chars for efficiency
            
            # Extract nouns and proper nouns as keywords
            pos_tags = ["NOUN", "PROPN"]
            keywords = []
            
            # Get lemmatized forms of important words
            for token in doc:
                if token.pos_ in pos_tags and len(token.text) > 3 and token.lemma_.isalpha():
                    keywords.append(token.lemma_.lower())
            
            # Get unique keywords
            keywords = list(set(keywords))[:max_keywords]
            return keywords
        except Exception:
            pass  # Fall back to NLTK
            
    # Fall back to NLTK if other methods failed
    if importlib.util.find_spec("nltk") is not None:
        try:
            import nltk
            from nltk.tokenize import word_tokenize
            from nltk.corpus import stopwords
            
            # Download necessary NLTK data if not already present
            try:
                nltk.data.find('tokenizers/punkt')
            except LookupError:
                nltk.download('punkt', quiet=True)
            
            try:
                nltk.data.find('corpora/stopwords')
            except LookupError:
                nltk.download('stopwords', quiet=True)
            
            # Process content for keyword extraction
            tokens = word_tokenize(text.lower())
            stop_words = set(stopwords.words('english'))
            filtered_tokens = [w for w in tokens if w.isalpha() and len(w) > 3 and w not in stop_words]
            
            # Count frequency
            freq_dist = nltk.FreqDist(filtered_tokens)
            
            # Get most common words as tags
            keywords = [word for word, _ in freq_dist.most_common(max_keywords)]
            return keywords
        except Exception:
            pass
    
    # If all methods failed, extract simple keywords
    words = text.split()
    candidates = [w.lower() for w in words if len(w) > 3 and w.isalpha()]
    word_counts = {}
    for word in candidates:
        word_counts[word] = word_counts.get(word, 0) + 1
    
    sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
    keywords = [word for word, _ in sorted_words[:max_keywords]]
    
    return keywords

def vim_view_with_preview(file_path):
    """View a file with Vim, showing smart preview first"""
    # Generate smart preview
    summary, suggested_tags, preview, error = smart_preview_file(file_path)
    
    # Show the preview and summary
    print_header(f"Smart Preview: {os.path.basename(file_path)}")
    
    if error:
        print_colored(f"Warning: {error}", Colors.YELLOW)
    
    print_colored("Summary:", Colors.BOLD)
    print(summary)
    
    print_colored("\nSuggested Tags:", Colors.BOLD)
    print(", ".join(suggested_tags))
    
    print_colored("\nPreview:", Colors.BOLD)
    print(preview)
    
    # Ask if user wants to view the full content in Vim
    view_choice = input("\nView full content in Vim? [y/N] ")
    if view_choice.lower() == 'y':
        # Create a temporary script to set up Vim with syntax highlighting
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_script:
            temp_script.write(f"""#!/bin/sh
vim "{file_path}"
""")
            temp_path = temp_script.name
        
        os.chmod(temp_path, 0o755)
        
        try:
            subprocess.call(temp_path, shell=True)
        finally:
            os.unlink(temp_path)
    
    return summary, suggested_tags

def add_file(source, category=None, name=None, subcategory=None, description=None, tags=None, preview_content=True):
    """Add a file to the database"""
    if not os.path.exists(source):
        print_colored(f"Error: Source file '{source}' not found", Colors.RED)
        return False
    
    # Handle relative paths
    source = os.path.abspath(source)
    
    # Generate smart preview and tag suggestions if requested
    auto_summary = None
    suggested_tags = []
    
    if preview_content:
        file_ext = os.path.splitext(source)[1].lower()
        if file_ext in ['.pdf', '.csv', '.json'] or os.path.getsize(source) < 1000000:  # Skip large files
            try:
                summary, suggested_tags, preview, error = smart_preview_file(source)
                
                if error:
                    print_colored(f"Warning: {error}", Colors.YELLOW)
                
                if not description and summary:
                    auto_summary = summary
                
                if summary:
                    print_colored("\nFile Analysis:", Colors.BOLD)
                    print(f"Summary: {summary}")
                    
                    if suggested_tags:
                        print(f"Suggested tags: {', '.join(suggested_tags)}")
                    
                    # Ask if user wants to see content preview
                    if preview:
                        preview_choice = input("Show content preview? [y/N] ")
                        if preview_choice.lower() == 'y':
                            print_colored("\nContent Preview:", Colors.BOLD)
                            print(preview)
            except Exception as e:
                print_colored(f"Warning: Preview generation failed: {str(e)}", Colors.YELLOW)
    
    # If no name provided, use source filename
    if name is None:
        name = os.path.basename(source)
    
    # If no category provided, ask user
    if category is None:
        print_header("Select Category")
        categories = [d for d in os.listdir(DB_DIR) 
                    if os.path.isdir(os.path.join(DB_DIR, d))]
        categories.append("+ Create new category")
        
        for i, cat in enumerate(categories):
            print(f"{i+1}. {cat}")
        
        choice = input("\nEnter category number: ")
        try:
            idx = int(choice) - 1
            if idx == len(categories) - 1:
                category = input("Enter new category name: ")
            else:
                category = categories[idx]
        except (ValueError, IndexError):
            print_colored("Invalid selection", Colors.RED)
            return False
    
    # Create category if it doesn't exist
    category_path = os.path.join(DB_DIR, category)
    os.makedirs(category_path, exist_ok=True)
    
    # Handle subcategory if provided
    if subcategory:
        category_path = os.path.join(category_path, subcategory)
        os.makedirs(category_path, exist_ok=True)
    
    # Determine destination path
    dest_path = os.path.join(category_path, name)
    
    # Ask for description if not provided
    if description is None:
        if auto_summary:
            description = input(f"Enter description (suggested: '{auto_summary}'): ")
            if not description:
                description = auto_summary
        else:
            description = input("Enter description (optional): ")
    
    # Ask for tags if not provided
    if tags is None:
        if suggested_tags:
            tags_input = input(f"Enter tags (suggested: {', '.join(suggested_tags)}): ")
            if not tags_input:
                tags = suggested_tags
            else:
                tags = [t.strip() for t in tags_input.split(',')]
        else:
            tags_input = input("Enter tags (comma-separated, optional): ")
            tags = [t.strip() for t in tags_input.split(',')] if tags_input else []
    
    # Copy the file
    try:
        shutil.copy2(source, dest_path)
        rel_path = os.path.relpath(dest_path, DB_DIR)
        
        # Create metadata
        metadata = {
            "description": description or "",
            "source_path": source,
            "added_date": datetime.now().isoformat(),
            "tags": tags or []
        }
        
        save_metadata(rel_path, metadata)
        
        print_colored(f"Added file '{name}' to {category}" + 
                     (f"/{subcategory}" if subcategory else ""), Colors.GREEN)
        if description:
            print_colored(f"Description: {description}", Colors.GREEN)
        if tags and len(tags) > 0:
            print_colored(f"Tags: {', '.join(tags)}", Colors.GREEN)
        return True
    except Exception as e:
        print_colored(f"Error adding file: {e}", Colors.RED)
        return False

def find_file(query, content_search=False, tags=None):
    """Find files in the database that match the query"""
    results = []
    
    # First search by filename
    for root, dirs, files in os.walk(DB_DIR):
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, DB_DIR)
            
            # Check if filename matches
            if query.lower() in file.lower():
                results.append((rel_path, "Filename match"))
                continue
                
            # Check if metadata matches
            metadata = load_metadata(rel_path)
            
            # Check description
            if metadata.get('description') and query.lower() in metadata.get('description').lower():
                results.append((rel_path, "Description match"))
                continue
                
            # Check tags
            if metadata.get('tags') and query.lower() in [tag.lower() for tag in metadata.get('tags')]:
                results.append((rel_path, "Tag match"))
                continue
                
            # If requested, search in content
            if content_search:
                try:
                    with open(file_path, 'r', errors='ignore') as f:
                        content = f.read()
                        if query.lower() in content.lower():
                            results.append((rel_path, "Content match"))
                except Exception:
                    # Skip files that can't be read as text
                    pass
    
    # If tags are specified, filter results by tags
    if tags:
        tag_list = [t.strip().lower() for t in tags.split(',')]
        filtered_results = []
        for rel_path, match_type in results:
            metadata = load_metadata(rel_path)
            file_tags = [t.lower() for t in metadata.get('tags', [])]
            if any(tag in file_tags for tag in tag_list):
                filtered_results.append((rel_path, match_type))
        results = filtered_results
    
    return results

def delete_file(file_path):
    """Delete a file from the database"""
    # Handle full paths and relative paths within the database
    if os.path.isabs(file_path):
        source_path = file_path
    else:
        source_path = os.path.join(DB_DIR, file_path)
    
    if not os.path.exists(source_path):
        print_colored(f"Error: File '{file_path}' not found in database", Colors.RED)
        return False
    
    try:
        # Delete the file
        os.remove(source_path)
        
        # Delete metadata
        metadata_path = get_metadata_path(file_path)
        if os.path.exists(metadata_path):
            os.remove(metadata_path)
            
        # Update last accessed in config
        config = load_config()
        rel_path = os.path.relpath(source_path, DB_DIR) if os.path.isabs(source_path) else file_path
        if rel_path in config["last_accessed"]:
            config["last_accessed"].remove(rel_path)
        save_config(config)
        
        print_colored(f"Deleted '{os.path.basename(source_path)}' from database", Colors.GREEN)
        return True
    except Exception as e:
        print_colored(f"Error deleting file: {e}", Colors.RED)
        return False

def preview_diff(source_path, dest_path):
    """Show a preview diff between source and destination files"""
    if os.path.exists(dest_path):
        with open(source_path, 'r', errors='ignore') as f:
            source_lines = f.readlines()
        with open(dest_path, 'r', errors='ignore') as f:
            dest_lines = f.readlines()
            
        diff = difflib.unified_diff(
            dest_lines, source_lines,
            fromfile=f'current: {os.path.basename(dest_path)}',
            tofile=f'template: {os.path.basename(source_path)}',
        )
        
        # Convert diff to string and colorize it
        diff_text = ""
        for line in diff:
            if line.startswith('+'):
                diff_text += Colors.GREEN + line + Colors.ENDC
            elif line.startswith('-'):
                diff_text += Colors.RED + line + Colors.ENDC
            elif line.startswith('^'):
                diff_text += Colors.BLUE + line + Colors.ENDC
            else:
                diff_text += line
                
        return diff_text
    else:
        # If destination doesn't exist, show the full source content
        with open(source_path, 'r', errors='ignore') as f:
            content = f.read()
        return f"New file: {os.path.basename(dest_path)}\n\n{content}"

def inject_file(file_path, dest_name=None, preview=True):
    """Inject a file from the database to the current directory"""
    # Handle full paths and relative paths within the database
    if os.path.isabs(file_path):
        source_path = file_path
    else:
        source_path = os.path.join(DB_DIR, file_path)
    
    if not os.path.exists(source_path):
        print_colored(f"Error: File '{file_path}' not found in database", Colors.RED)
        return False
    
    # Determine destination filename
    if dest_name is None:
        dest_name = os.path.basename(source_path)
    
    dest_path = os.path.join(os.getcwd(), dest_name)
    
    # Show preview if requested and file exists
    if preview and os.path.exists(dest_path):
        print_header("File Comparison Preview")
        diff_text = preview_diff(source_path, dest_path)
        print(diff_text)
        
        confirm = input(f"File '{dest_name}' already exists. Overwrite? [y/N] ")
        if confirm.lower() != 'y':
            print_colored("Operation cancelled", Colors.YELLOW)
            return False
    elif os.path.exists(dest_path):
        confirm = input(f"File '{dest_name}' already exists. Overwrite? [y/N] ")
        if confirm.lower() != 'y':
            print_colored("Operation cancelled", Colors.YELLOW)
            return False
    
    # Copy the file
    try:
        shutil.copy2(source_path, dest_path)
        print_colored(f"Injected '{os.path.basename(source_path)}' to current directory", Colors.GREEN)
        
        # Update last accessed in config
        config = load_config()
        rel_path = os.path.relpath(source_path, DB_DIR)
        if rel_path in config["last_accessed"]:
            config["last_accessed"].remove(rel_path)
        config["last_accessed"].insert(0, rel_path)
        config["last_accessed"] = config["last_accessed"][:10]  # Keep only 10 most recent
        save_config(config)
        
        return True
    except Exception as e:
        print_colored(f"Error injecting file: {e}", Colors.RED)
        return False

def show_file(file_path):
    """Show the contents of a file"""
    # Handle full paths and relative paths within the database
    if os.path.isabs(file_path):
        source_path = file_path
    else:
        source_path = os.path.join(DB_DIR, file_path)
    
    if not os.path.exists(source_path):
        print_colored(f"Error: File '{file_path}' not found in database", Colors.RED)
        return False
    
    try:
        # Show metadata if available
        rel_path = os.path.relpath(source_path, DB_DIR) if os.path.isabs(source_path) else file_path
        metadata = load_metadata(rel_path)
        
        print_header(f"File: {os.path.basename(source_path)}")
        
        if metadata:
            print_colored("Metadata:", Colors.BOLD)
            if metadata.get('description'):
                print(f"Description: {metadata['description']}")
            if metadata.get('added_date'):
                print(f"Added on: {metadata['added_date'].split('T')[0]}")
            if metadata.get('tags'):
                print(f"Tags: {', '.join(metadata['tags'])}")
            print()
        
        print_colored("Content:", Colors.BOLD)
        with open(source_path, 'r') as f:
            content = f.read()
        print(content)
        return True
    except Exception as e:
        print_colored(f"Error reading file: {e}", Colors.RED)
        return False

def get_system_shortcuts():
    """Get common system directory shortcuts based on OS"""
    shortcuts = []
    home = os.path.expanduser("~")
    
    # Common shortcuts across platforms
    shortcuts.append(("Home", home))
    
    # Platform-specific shortcuts
    if os.name == 'posix':  # macOS or Linux
        shortcuts.append(("Desktop", os.path.join(home, "Desktop")))
        shortcuts.append(("Documents", os.path.join(home, "Documents")))
        shortcuts.append(("Downloads", os.path.join(home, "Downloads")))
        
        # macOS specific
        if sys.platform == 'darwin':
            shortcuts.append(("Applications", "/Applications"))
            shortcuts.append(("Pictures", os.path.join(home, "Pictures")))
            shortcuts.append(("Music", os.path.join(home, "Music")))
        
        # Linux specific
        else:
            if os.path.exists("/mnt"):
                shortcuts.append(("Mounts", "/mnt"))
            if os.path.exists("/media"):
                shortcuts.append(("Media", "/media"))
    
    elif os.name == 'nt':  # Windows
        shortcuts.append(("Desktop", os.path.join(home, "Desktop")))
        shortcuts.append(("Documents", os.path.join(home, "Documents")))
        shortcuts.append(("Downloads", os.path.join(home, "Downloads")))
        shortcuts.append(("Pictures", os.path.join(home, "Pictures")))
        shortcuts.append(("Music", os.path.join(home, "Music")))
        
        # Windows drives
        import string
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                shortcuts.append((f"Drive {letter}:", drive))
    
    return [s for s in shortcuts if os.path.exists(s[1])]

def interactive_file_browser():
    """
    Interactive file browser that allows user to navigate filesystem and select files
    for smart document viewing.
    """
    print_header("Smart Document Browser")
    
    # Get system shortcuts
    shortcuts = get_system_shortcuts()
    
    # Prompt for search location first
    print_colored("Where would you like to browse?", Colors.BOLD)
    print("1. System files (current directory)")
    print("2. Faxmachine database")
    
    browser_choice = input("\nEnter choice (1/2): ")
    
    # Start in the user's current directory or database based on choice
    if browser_choice == '2':
        current_path = DB_DIR
        in_database = True
    else:
        current_path = os.getcwd()
        in_database = False
    
    history = []
    
    # Try to use TUI if available for better navigation
    ncurses_available = importlib.util.find_spec("curses") is not None
    
    if ncurses_available:
        return _curses_file_browser(in_db=in_database, shortcuts=shortcuts)
    
    # For simple browser: add select multiple mode
    selected_files = []
    select_multiple_mode = False
    
    # For dropdown summaries
    expanded_file_idx = None
    
    while True:
        # Clear screen
        os.system('cls' if os.name == 'nt' else 'clear')
        print_header("Smart Document Browser")
        
        # Show current path and mode
        if in_database:
            print("Mode: Database Browser")
            rel_path = os.path.relpath(current_path, DB_DIR)
            if rel_path and rel_path != ".":
                print(f"Location: {rel_path}")
            else:
                print("Location: (root)")
        else:
            print("Mode: System Browser")
            print(f"Current directory: {current_path}")
        
        # Show selection mode status
        if select_multiple_mode:
            multiselect_header = f"MULTI-SELECT MODE: {len(selected_files)} files selected"
            print_colored("=" * len(multiselect_header), Colors.BG_BLUE + Colors.BOLD)
            print_colored(multiselect_header, Colors.BG_BLUE + Colors.BOLD + Colors.BLACK)
            print_colored("=" * len(multiselect_header), Colors.BG_BLUE + Colors.BOLD)
            print_colored("Select files using their numbers. Press 'a' to process selected files.", Colors.BLUE)
            
        # Get items in current directory
        try:
            items = os.listdir(current_path)
            dirs = sorted([d for d in items if os.path.isdir(os.path.join(current_path, d))])
            files = sorted([f for f in items if os.path.isfile(os.path.join(current_path, f))])
        except PermissionError:
            print_colored("Permission denied to access this directory", Colors.RED)
            current_path = os.path.dirname(current_path) or os.getcwd()
            continue
        except Exception as e:
            print_colored(f"Error: {str(e)}", Colors.RED)
            current_path = os.path.dirname(current_path) or os.getcwd()
            continue
        
        # Show shortcuts if in system mode
        if not in_database:
            print_colored("\nShortcuts:", Colors.BOLD)
            for i, (name, path) in enumerate(shortcuts):
                print(f"  #{i+1}. {name}")
        
        # Show directories
        print_colored("\nDirectories:", Colors.BOLD)
        if not dirs:
            print("  (No directories)")
        for i, d in enumerate(dirs):
            print(f"  {i+1}. {d}/")
        
        # Show files
        print_colored("\nFiles:", Colors.BOLD)
        if not files:
            print("  (No files)")
        for i, f in enumerate(files):
            # Get file size
            try:
                size = os.path.getsize(os.path.join(current_path, f))
                size_str = _format_size(size)
            except:
                size_str = "?"
            
            # Get file extension
            _, ext = os.path.splitext(f)
            ext = ext.lower()[1:] if ext else ""
            ext_str = f"[{ext}]" if ext else ""
            
            # Determine if this file is selected in multi-select mode
            selected_marker = ""
            if select_multiple_mode:
                file_path = os.path.join(current_path, f)
                if file_path in selected_files:
                    selected_marker = Colors.BG_GREEN + Colors.BLACK + " [✓] " + Colors.ENDC
            
            # Get display index for file
            file_idx = i + len(dirs) + 1
            
            # Show metadata if in DB mode
            if in_database:
                rel_path = os.path.relpath(os.path.join(current_path, f), DB_DIR)
                metadata = load_metadata(rel_path)
                desc = f" - {metadata.get('description')}" if metadata.get('description') else ""
                print(f"  {file_idx}. {selected_marker}{f} {ext_str} ({size_str}){desc}")
            else:
                print(f"  {file_idx}. {selected_marker}{f} {ext_str} ({size_str})")
                
            # If this is the expanded file, show its summary underneath
            if expanded_file_idx is not None and file_idx == expanded_file_idx:
                file_path = os.path.join(current_path, f)
                try:
                    # Get a summary for the file
                    summary, tags, preview, error = smart_preview_file(file_path)
                    
                    # Create a box for the summary
                    width = min(os.get_terminal_size().columns - 5, 100)
                    print(Colors.BLUE + "  ┌" + "─" * (width - 4) + "┐" + Colors.ENDC)
                    
                    # Show summary
                    if summary:
                        summary_lines = textwrap.wrap(summary, width - 6)
                        for line in summary_lines:
                            print(Colors.BLUE + "  │ " + Colors.ENDC + line + Colors.BLUE + " │" + Colors.ENDC)
                    
                    # Show tags if available
                    if tags and len(tags) > 0:
                        tags_str = "Tags: " + ", ".join(tags)
                        tags_lines = textwrap.wrap(tags_str, width - 6)
                        for line in tags_lines:
                            print(Colors.BLUE + "  │ " + Colors.ENDC + line + Colors.BLUE + " │" + Colors.ENDC)
                    
                    # Show a snippet of content if available
                    if preview:
                        preview_lines = preview.split('\n')[:3]  # Show first 3 lines max
                        print(Colors.BLUE + "  │ " + Colors.ENDC + "Preview:" + Colors.BLUE + " │" + Colors.ENDC)
                        for line in preview_lines:
                            if len(line) > width - 6:
                                line = line[:width - 9] + "..."
                            print(Colors.BLUE + "  │ " + Colors.ENDC + line + Colors.BLUE + " │" + Colors.ENDC)
                    
                    # Close the box
                    print(Colors.BLUE + "  └" + "─" * (width - 4) + "┘" + Colors.ENDC)
                except Exception as e:
                    print(Colors.BLUE + "  ┌" + "─" * 46 + "┐" + Colors.ENDC)
                    print(Colors.BLUE + "  │ " + Colors.ENDC + f"Error generating preview: {str(e)}" + Colors.BLUE + " │" + Colors.ENDC)
                    print(Colors.BLUE + "  └" + "─" * 46 + "┘" + Colors.ENDC)
        
        # Navigation options
        print_colored("\nNavigation:", Colors.BOLD)
        print("  b. Go back")
        print("  h. Go to home directory")
        print("  p. Go to parent directory")
        print("  /. Search in current directory")
        print("  s. System-wide search")
        if not in_database:
            print("  #. Jump to shortcut (e.g., #1 for first shortcut)")
        print("  g. Go to specific path")
        print("  v. Vim-like directory navigation")
        
        # Additional actions
        print_colored("\nActions:", Colors.BOLD)
        if select_multiple_mode:
            print("  space. Toggle selection of a file (with number)")
            print("  a. Process all selected files")
            print("  c. Clear all selections")
        else:
            print("  d. Show/hide dropdown summary for a file (with number)")
        print("  m. Mass add files to Faxmachine")
        print("  t. Toggle between system files and database")
        print("  *. Toggle multi-select mode")
        print("  q. Quit browser")
        
        choice = input("\nEnter choice (number for file/directory): ")
        
        if choice == 'q':
            return None
        elif choice.startswith('#') and not in_database:
            # Handle shortcut navigation
            try:
                shortcut_idx = int(choice[1:]) - 1
                if 0 <= shortcut_idx < len(shortcuts):
                    history.append(current_path)
                    current_path = shortcuts[shortcut_idx][1]
                else:
                    print_colored("Invalid shortcut number", Colors.RED)
                    input("\nPress Enter to continue...")
            except ValueError:
                print_colored("Invalid shortcut format", Colors.RED)
                input("\nPress Enter to continue...")
        elif choice == 't':
            # Toggle between system files and database
            if in_database:
                in_database = False
                current_path = os.getcwd()
            else:
                in_database = True
                current_path = DB_DIR
            history = []
            # Clear selections when switching modes
            selected_files = []
            expanded_file_idx = None  # Reset expanded file
        elif choice == '*' or choice == 'm' or choice == 'M':
            # Toggle multi-select mode
            select_multiple_mode = not select_multiple_mode
            if select_multiple_mode:
                expanded_file_idx = None  # Close any expanded summaries
                print_colored("\n" + "=" * 40, Colors.BG_BLUE + Colors.BOLD)
                print_colored(" MULTI-SELECT MODE ACTIVATED ", Colors.BG_BLUE + Colors.BOLD + Colors.BLACK)
                print_colored("=" * 40, Colors.BG_BLUE + Colors.BOLD)
                print_colored("• Use file numbers to select/deselect files", Colors.BLUE + Colors.BOLD)
                print_colored("• Press 'a' to perform actions on selected files", Colors.BLUE + Colors.BOLD)
                print_colored("• Press 'c' to clear all selections", Colors.BLUE + Colors.BOLD)
                print_colored("• Press '*' or 'm' again to exit multi-select", Colors.BLUE + Colors.BOLD)
                input("\nPress Enter to continue...")
            else:
                selected_files = []  # Clear selections when exiting mode
                print_colored("\n" + "=" * 40, Colors.BG_YELLOW + Colors.BOLD)
                print_colored(" MULTI-SELECT MODE DEACTIVATED ", Colors.BG_YELLOW + Colors.BOLD + Colors.BLACK)
                print_colored("=" * 40, Colors.BG_YELLOW + Colors.BOLD)
                input("Press Enter to continue...")
        elif choice.lower().startswith('d') and not select_multiple_mode:
            # Toggle dropdown summary for a file
            try:
                # Extract the file number from the input (e.g., "d5" or "d 5")
                file_num_str = choice[1:].strip()
                if file_num_str:
                    file_num = int(file_num_str)
                    # Check if valid file number
                    if len(dirs) < file_num <= len(dirs) + len(files):
                        # Toggle the dropdown
                        if expanded_file_idx == file_num:
                            expanded_file_idx = None  # Close dropdown
                        else:
                            expanded_file_idx = file_num  # Open dropdown
                    else:
                        print_colored("Invalid file number", Colors.RED)
                        input("\nPress Enter to continue...")
                else:
                    print_colored("Please provide a file number with 'd', like 'd5'", Colors.YELLOW)
                    input("\nPress Enter to continue...")
            except ValueError:
                print_colored("Invalid file number format", Colors.RED)
                input("\nPress Enter to continue...")
        elif choice.startswith(' ') and select_multiple_mode:
            # Toggle selection for a specific file
            try:
                file_num = int(choice.strip())
                if len(dirs) < file_num <= len(dirs) + len(files):
                    file_idx = file_num - len(dirs) - 1
                    file_path = os.path.join(current_path, files[file_idx])
                    if file_path in selected_files:
                        selected_files.remove(file_path)
                    else:
                        selected_files.append(file_path)
                else:
                    print_colored("Invalid file number", Colors.RED)
                    input("\nPress Enter to continue...")
            except ValueError:
                print_colored("Invalid file number", Colors.RED)
                input("\nPress Enter to continue...")
        elif choice == 'a' and select_multiple_mode and selected_files:
            # Process all selected files
            if len(selected_files) > 0:
                print_colored(f"\nProcessing {len(selected_files)} selected files", Colors.BOLD)
                if in_database:
                    # Actions for database files
                    print("1. View all selected files")
                    print("2. Inject all selected files to current directory")
                    action = input("\nSelect action: ")
                    
                    if action == '1':
                        for file_path in selected_files:
                            vim_view_with_preview(file_path)
                    elif action == '2':
                        for file_path in selected_files:
                            inject_file(file_path)
                else:
                    # Actions for system files
                    print("1. Add all selected files to Faxmachine")
                    print("2. View all selected files")
                    action = input("\nSelect action: ")
                    
                    if action == '1':
                        # Mass add all selected files
                        category = input("Enter category for all files: ")
                        if not category:
                            print_colored("Category required for adding files", Colors.RED)
                        else:
                            for file_path in selected_files:
                                add_file(file_path, category)
                    elif action == '2':
                        for file_path in selected_files:
                            vim_view_with_preview(file_path)
                
                # Clear selections after processing
                selected_files = []
                input("\nPress Enter to continue...")
        elif choice == 'c' and select_multiple_mode:
            # Clear all selections
            selected_files = []
        elif choice == 'm':
            # Mass add files
            if in_database:
                print_colored("Cannot mass add from database mode. Toggle to system mode first.", Colors.YELLOW)
                input("\nPress Enter to continue...")
                continue
            
            mass_add_files()
        elif choice == 'b' and history:
            current_path = history.pop()
        elif choice == 'h':
            history.append(current_path)
            current_path = os.path.expanduser("~")
        elif choice == 'p':
            history.append(current_path)
            parent = os.path.dirname(current_path)
            current_path = parent if parent else current_path
        elif choice == '/':
            search_term = input("Search for: ")
            if search_term:
                found_items = []
                try:
                    for root, dirs, files in os.walk(current_path):
                        for item in dirs + files:
                            if search_term.lower() in item.lower():
                                found_items.append(os.path.join(root, item))
                        if len(found_items) > 20:  # Limit search results
                            break
                except:
                    pass
                
                if found_items:
                    print_colored("\nSearch results:", Colors.BOLD)
                    for i, item in enumerate(found_items[:20]):
                        rel_path = os.path.relpath(item, current_path)
                        print(f"  {i+1}. {rel_path}")
                    
                    search_choice = input("\nSelect item (number) or Enter to cancel: ")
                    if search_choice.isdigit() and 0 < int(search_choice) <= len(found_items[:20]):
                        selected = found_items[int(search_choice)-1]
                        if os.path.isdir(selected):
                            history.append(current_path)
                            current_path = selected
                        else:
                            # View the file
                            vim_view_with_preview(selected)
                            input("\nPress Enter to continue...")
                else:
                    print_colored("No items found", Colors.YELLOW)
                    input("\nPress Enter to continue...")
        elif choice == 'g':
            path = input("Enter path: ")
            if path and os.path.exists(os.path.expanduser(path)):
                history.append(current_path)
                current_path = os.path.expanduser(path)
            else:
                print_colored("Invalid path", Colors.RED)
                input("\nPress Enter to continue...")
        elif choice == 'v':
            # Vim-like navigation mode
            print_colored("\nVim navigation mode (h/j/k/l, q to exit)", Colors.BOLD)
            
            # Track current position
            dir_items = dirs + files
            cursor_pos = 0
            
            while True:
                # Redraw the screen
                os.system('cls' if os.name == 'nt' else 'clear')
                print_header("Vim Navigation Mode")
                print(f"Current directory: {current_path}")
                
                # Show items with cursor
                for i, item in enumerate(dir_items):
                    is_dir = item in dirs
                    prefix = "  > " if i == cursor_pos else "    "
                    suffix = "/" if is_dir else ""
                    print(f"{prefix}{item}{suffix}")
                
                print_colored("\nNavigate: j/k (down/up), h (parent), l (enter), q (quit vim mode)", Colors.BOLD)
                
                # Get keystroke
                key = input().lower()
                
                if key == 'q':
                    break
                elif key == 'j' and cursor_pos < len(dir_items) - 1:
                    cursor_pos += 1
                elif key == 'k' and cursor_pos > 0:
                    cursor_pos -= 1
                elif key == 'h':
                    # Go to parent
                    parent = os.path.dirname(current_path)
                    if parent and parent != current_path:
                        history.append(current_path)
                        current_path = parent
                        dir_items = sorted([d for d in os.listdir(current_path) if os.path.isdir(os.path.join(current_path, d))]) + \
                                   sorted([f for f in os.listdir(current_path) if os.path.isfile(os.path.join(current_path, f))])
                        cursor_pos = 0
                elif key == 'l':
                    # Enter directory or view file
                    selected = dir_items[cursor_pos]
                    full_path = os.path.join(current_path, selected)
                    
                    if os.path.isdir(full_path):
                        try:
                            history.append(current_path)
                            current_path = full_path
                            dir_items = sorted([d for d in os.listdir(current_path) if os.path.isdir(os.path.join(current_path, d))]) + \
                                       sorted([f for f in os.listdir(current_path) if os.path.isfile(os.path.join(current_path, f))])
                            cursor_pos = 0
                        except PermissionError:
                            print_colored("Permission denied to access this directory", Colors.RED)
                            input("\nPress Enter to continue...")
                        except Exception as e:
                            print_colored(f"Error: {str(e)}", Colors.RED)
                            input("\nPress Enter to continue...")
                    else:
                        # View the file with smart preview
                        vim_view_with_preview(full_path)
                        input("\nPress Enter to continue...")
                        # Refresh directory items after viewing
                        dir_items = sorted([d for d in os.listdir(current_path) if os.path.isdir(os.path.join(current_path, d))]) + \
                                   sorted([f for f in os.listdir(current_path) if os.path.isfile(os.path.join(current_path, f))])
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(dirs):
                    # Navigate to directory
                    history.append(current_path)
                    current_path = os.path.join(current_path, dirs[idx])
                elif len(dirs) <= idx < len(dirs) + len(files):
                    # View file
                    file_idx = idx - len(dirs)
                    file_path = os.path.join(current_path, files[file_idx])
                    
                    # If in multi-select mode, toggle selection
                    if select_multiple_mode:
                        if file_path in selected_files:
                            selected_files.remove(file_path)
                        else:
                            selected_files.append(file_path)
                        continue
                    
                    # Generate quick summary before asking for action
                    try:
                        summary, _, _, _ = smart_preview_file(file_path)
                        print_colored(f"\nFile: {files[file_idx]}", Colors.BOLD)
                        print(f"Summary: {summary}")
                    except:
                        pass
                    
                    print_colored("\nActions:", Colors.BOLD)
                    print("  v. View with smart preview")
                    print("  e. Edit in Vim")
                    print("  a. Add to Faxmachine")
                    print("  c. Cancel")
                    
                    file_action = input("\nEnter action: ")
                    
                    if file_action == 'v':
                        vim_view_with_preview(file_path)
                        input("\nPress Enter to continue...")
                    elif file_action == 'e':
                        editor = os.environ.get("EDITOR", "vim")
                        subprocess.call([editor, file_path])
                    elif file_action == 'a':
                        # Add to Faxmachine
                        add_file(file_path)
                        input("\nPress Enter to continue...")
                else:
                    print_colored("Invalid choice", Colors.RED)
                    input("\nPress Enter to continue...")
            except ValueError:
                print_colored("Invalid choice", Colors.RED)
                input("\nPress Enter to continue...")
    
    return None

def _curses_file_browser(in_db=False, shortcuts=None):
    """Interactive file browser using curses for better UI"""
    try:
        import curses
        import textwrap
        
        # Track expanded file with dropdown summary
        expanded_info = None  # (index, summary, tags, preview) or None
        
        def draw_menu(stdscr, current_path, items, cursor_pos, starting_row=0, shortcuts=None, in_db=False, 
                      selected_files=None, select_multiple_mode=False, expanded_info=None):
            height, width = stdscr.getmaxyx()
            
            # Clear screen
            stdscr.clear()
            
            # Draw header
            stdscr.addstr(0, 0, "Smart Document Browser", curses.A_BOLD)
            mode_text = "Database Browser" if in_db else "System Browser"
            stdscr.addstr(1, 0, f"Mode: {mode_text} | Path: {current_path}", curses.A_NORMAL)
            
            # Show multi-select mode status if active
            if select_multiple_mode:
                select_status = f"MULTI-SELECT MODE: {len(selected_files)} files selected"
                try:
                    # Use background highlight colors if available
                    stdscr.addstr(2, 0, select_status, curses.A_BOLD | curses.A_REVERSE)
                    stdscr.addstr(3, 0, "Press SPACE to select/deselect | 'a' to process | 'm' to exit", curses.A_NORMAL)
                except:
                    # Fallback if attributes combination fails
                    stdscr.addstr(2, 0, select_status, curses.A_BOLD)
                    stdscr.addstr(3, 0, "Press SPACE to select/deselect | 'a' to process | 'm' to exit", curses.A_NORMAL)
                
            stdscr.addstr(4, 0, "=" * (width - 1), curses.A_NORMAL)
            
            # Draw shortcuts if available and in system mode
            row = 5
            if shortcuts and not in_db:
                stdscr.addstr(row, 0, "Shortcuts:", curses.A_BOLD)
                row += 1
                shortcut_line = ""
                for i, (name, _) in enumerate(shortcuts[:5]):  # Show first 5 shortcuts
                    shortcut_text = f"#{i+1}:{name} "
                    if len(shortcut_line) + len(shortcut_text) < width - 1:
                        shortcut_line += shortcut_text
                    else:
                        stdscr.addstr(row, 0, shortcut_line, curses.A_NORMAL)
                        row += 1
                        shortcut_line = shortcut_text
                if shortcut_line:
                    stdscr.addstr(row, 0, shortcut_line, curses.A_NORMAL)
                    row += 1
                
                # Separator after shortcuts
                stdscr.addstr(row, 0, "-" * (width - 1), curses.A_NORMAL)
                row += 1
            
            # Get visible range based on screen size
            visible_items = height - row - 5  # Account for header and footer
            start_idx = max(0, cursor_pos - visible_items // 2)
            end_idx = min(len(items), start_idx + visible_items)
            
            # Draw items
            for i in range(start_idx, end_idx):
                item_name = items[i][0]
                is_dir = items[i][1]
                
                # Format item
                display_name = item_name + ("/" if is_dir else "")
                
                # Check if this file is selected in multi-select mode
                is_selected = False
                if select_multiple_mode and not is_dir:
                    full_path = os.path.join(current_path, item_name)
                    is_selected = full_path in selected_files
                
                # Selected item indicator
                selected_prefix = "" if not is_selected else "✓ "
                
                # Ensure display name isn't too long
                if len(display_name) > width - 10:  # Account for selection mark
                    display_name = display_name[:width-13] + "..."
                
                # Final display string with selection mark if needed
                display_str = f"{selected_prefix}{display_name}"
                
                # Highlight current selection
                if i == cursor_pos:
                    # Current cursor position gets highlighted
                    if is_selected:
                        try:
                            stdscr.addstr(row + i - start_idx, 0, f"> {display_str}", curses.A_REVERSE | curses.A_BOLD)
                        except:
                            # Fallback if attribute combination fails
                            stdscr.addstr(row + i - start_idx, 0, f"> {display_str}", curses.A_REVERSE)
                    else:
                        stdscr.addstr(row + i - start_idx, 0, f"> {display_str}", curses.A_REVERSE)
                        
                    # If this is the expanded item and not a directory, show its summary
                    if expanded_info and expanded_info[0] == i and not is_dir:
                        summary_row = row + i - start_idx + 1
                        
                        # Check if we have enough room to display summary
                        available_rows = min(5, height - summary_row - 3)  # Leave some space for footer
                        
                        if available_rows > 0:
                            # Draw summary box
                            _, summary, tags, preview = expanded_info
                            summary_width = min(width - 4, 80)
                            
                            # Draw top border
                            if summary_row < height:
                                try:
                                    stdscr.addstr(summary_row, 2, "┌" + "─" * (summary_width - 2) + "┐", curses.A_NORMAL)
                                except:
                                    pass  # Skip if can't draw
                            
                            summary_row += 1
                            rows_used = 1
                            
                            # Draw summary content
                            if summary and summary_row < height and rows_used < available_rows:
                                # Wrap summary text to fit box
                                wrapped_summary = textwrap.wrap(summary, summary_width - 4)
                                if wrapped_summary:
                                    try:
                                        stdscr.addstr(summary_row, 2, "│ " + wrapped_summary[0][:summary_width-6] + 
                                                    " " * (summary_width - len(wrapped_summary[0]) - 6) + " │", curses.A_NORMAL)
                                    except:
                                        pass
                                    summary_row += 1
                                    rows_used += 1
                            
                            # Draw tags
                            if tags and summary_row < height and rows_used < available_rows:
                                tags_str = "Tags: " + ", ".join(tags[:5])
                                if len(tags) > 5:
                                    tags_str += "..."
                                if len(tags_str) > summary_width - 6:
                                    tags_str = tags_str[:summary_width-9] + "..."
                                try:
                                    stdscr.addstr(summary_row, 2, "│ " + tags_str + 
                                                " " * (summary_width - len(tags_str) - 6) + " │", curses.A_NORMAL)
                                except:
                                    pass
                                summary_row += 1
                                rows_used += 1
                            
                            # Draw preview
                            if preview and summary_row < height and rows_used < available_rows:
                                preview_line = preview.split('\n')[0][:summary_width-12] + "..."
                                try:
                                    stdscr.addstr(summary_row, 2, "│ " + preview_line + 
                                                " " * (summary_width - len(preview_line) - 6) + " │", curses.A_NORMAL)
                                except:
                                    pass
                                summary_row += 1
                                rows_used += 1
                            
                            # Draw bottom border
                            if summary_row < height:
                                try:
                                    stdscr.addstr(summary_row, 2, "└" + "─" * (summary_width - 2) + "┘", curses.A_NORMAL)
                                except:
                                    pass
                                summary_row += 1
                else:
                    # Normal items
                    if is_selected:
                        try:
                            stdscr.addstr(row + i - start_idx, 0, f"  {display_str}", curses.A_BOLD)
                        except:
                            stdscr.addstr(row + i - start_idx, 0, f"  {display_str}", curses.A_NORMAL)
                    else:
                        stdscr.addstr(row + i - start_idx, 0, f"  {display_str}", curses.A_NORMAL)
            
            # Draw footer
            footer_y = height - 3
            stdscr.addstr(footer_y, 0, "=" * (width - 1), curses.A_NORMAL)
            
            # Basic controls
            basic_keys = "j/k: Navigate | l: Open | h: Parent | q: Quit | v: View"
            
            # Add multi-select controls or dropdown controls
            if select_multiple_mode:
                multi_keys = "SPACE: Toggle selection | a: Process selected | m: Exit multi-select"
                # Show basic controls on first line, multi-select controls on second line
                stdscr.addstr(footer_y + 1, 0, basic_keys, curses.A_BOLD)
                stdscr.addstr(footer_y + 2, 0, multi_keys, curses.A_BOLD)
            else:
                # Show expanded basic controls when not in multi-select mode
                full_keys = basic_keys + " | d: Toggle summary | *: Multi-select mode"
                if shortcuts and not in_db:
                    full_keys += " | #: Shortcuts"
                stdscr.addstr(footer_y + 1, 0, full_keys, curses.A_BOLD)
            
            # Refresh screen
            stdscr.refresh()
        
        def main(stdscr):
            # Hide cursor
            curses.curs_set(0)
            
            # Start in current directory or DB
            current_path = DB_DIR if in_db else os.getcwd()
            history = []
            cursor_pos = 0
            
            # For multi-select mode
            select_multiple_mode = False
            selected_files = []
            
            # For expanded dropdowns
            expanded_info = None
            
            while True:
                # Get directory contents
                try:
                    dirs = sorted([d for d in os.listdir(current_path) if os.path.isdir(os.path.join(current_path, d))])
                    files = sorted([f for f in os.listdir(current_path) if os.path.isfile(os.path.join(current_path, f))])
                    items = [(d, True) for d in dirs] + [(f, False) for f in files]
                except PermissionError:
                    current_path = os.path.dirname(current_path) or os.getcwd()
                    continue
                except Exception:
                    current_path = os.path.dirname(current_path) or os.getcwd()
                    continue
                
                # Reset cursor position when changing directories
                if cursor_pos >= len(items):
                    cursor_pos = 0 if items else -1
                    expanded_info = None  # Reset expanded state when directory changes
                
                # Draw the menu
                draw_menu(stdscr, current_path, items, cursor_pos, shortcuts=shortcuts, in_db=in_db, 
                          selected_files=selected_files, select_multiple_mode=select_multiple_mode,
                          expanded_info=expanded_info)
                
                # Get user input
                key = stdscr.getch()
                
                if key == ord('q'):
                    break
                elif key == ord('j') and items and cursor_pos < len(items) - 1:
                    cursor_pos += 1
                    # Automatically close expanded info when moving
                    expanded_info = None
                elif key == ord('k') and items and cursor_pos > 0:
                    cursor_pos -= 1
                    # Automatically close expanded info when moving
                    expanded_info = None
                elif key == ord('d') and items and cursor_pos >= 0 and not select_multiple_mode:
                    # Toggle dropdown info for current item - only for files
                    item_name, is_dir = items[cursor_pos]
                    
                    if not is_dir:  # Only show dropdowns for files, not directories
                        if expanded_info and expanded_info[0] == cursor_pos:
                            # If already expanded, close it
                            expanded_info = None
                        else:
                            # Get file info to show in dropdown
                            full_path = os.path.join(current_path, item_name)
                            try:
                                summary, tags, preview, _ = smart_preview_file(full_path)
                                expanded_info = (cursor_pos, summary, tags, preview)
                            except Exception as e:
                                # If error, still show dropdown with error message
                                expanded_info = (cursor_pos, f"Error: {str(e)}", [], "")
                elif key == ord('*') or key == ord('m') or key == ord('M'):
                    # Toggle multi-select mode
                    select_multiple_mode = not select_multiple_mode
                    if select_multiple_mode:
                        expanded_info = None  # Close any expanded summaries
                    if not select_multiple_mode:
                        selected_files = []  # Clear selections when exiting mode
                    # Force screen refresh to reflect the mode change
                    stdscr.clear()
                elif key == ord('m') and select_multiple_mode:
                    # Exit multi-select mode
                    select_multiple_mode = False
                    selected_files = []
                    # Force screen refresh
                    stdscr.clear()
                elif key == ord(' ') and items and cursor_pos >= 0:
                    # Toggle selection for current item (only for files, not directories)
                    item_name, is_dir = items[cursor_pos]
                    
                    if not is_dir:  # Only select files, not directories
                        full_path = os.path.join(current_path, item_name)
                        
                        if full_path in selected_files:
                            selected_files.remove(full_path)
                        else:
                            selected_files.append(full_path)
                            
                        # Move cursor down after selection if possible
                        if cursor_pos < len(items) - 1:
                            cursor_pos += 1
                elif key == ord('a') and select_multiple_mode and selected_files:
                    # Process all selected files
                    curses.endwin()  # Exit curses temporarily
                    
                    print_colored(f"\nProcessing {len(selected_files)} selected files", Colors.BOLD)
                    if in_db:
                        # Actions for database files
                        print("1. View all selected files")
                        print("2. Inject all selected files to current directory")
                        action = input("\nSelect action: ")
                        
                        if action == '1':
                            for file_path in selected_files:
                                vim_view_with_preview(file_path)
                        elif action == '2':
                            for file_path in selected_files:
                                inject_file(file_path)
                    else:
                        # Actions for system files
                        print("1. Add all selected files to Faxmachine")
                        print("2. View all selected files")
                        action = input("\nSelect action: ")
                        
                        if action == '1':
                            # Mass add all selected files
                            category = input("Enter category for all files: ")
                            if not category:
                                print_colored("Category required for adding files", Colors.RED)
                            else:
                                for file_path in selected_files:
                                    add_file(file_path, category)
                        elif action == '2':
                            for file_path in selected_files:
                                vim_view_with_preview(file_path)
                    
                    # Clear selections after processing
                    selected_files = []
                    select_multiple_mode = False
                    
                    input("Press Enter to continue...")
                    stdscr.clear()
                    curses.curs_set(0)
                elif key in [ord(str(i)) for i in range(1, 10)] and shortcuts and not in_db:
                    # Number keys 1-9 for shortcuts
                    shortcut_idx = int(chr(key)) - 1
                    if 0 <= shortcut_idx < len(shortcuts):
                        history.append(current_path)
                        current_path = shortcuts[shortcut_idx][1]
                        cursor_pos = 0
                elif key == ord('h'):
                    # Go to parent directory
                    parent = os.path.dirname(current_path)
                    if in_db and (parent == os.path.dirname(DB_DIR) or parent == os.path.dirname(os.path.dirname(DB_DIR))):
                        current_path = DB_DIR
                    elif parent and parent != current_path:
                        history.append(current_path)
                        current_path = parent
                        cursor_pos = 0
                elif key == ord('#') and shortcuts and not in_db:
                    # Show shortcut selection menu
                    curses.endwin()
                    
                    print_colored("Available Shortcuts:", Colors.BOLD)
                    for i, (name, path) in enumerate(shortcuts):
                        print(f"  #{i+1}. {name}: {path}")
                    
                    shortcut_choice = input("\nEnter shortcut number: ")
                    try:
                        shortcut_idx = int(shortcut_choice) - 1
                        if 0 <= shortcut_idx < len(shortcuts):
                            history.append(current_path)
                            current_path = shortcuts[shortcut_idx][1]
                        else:
                            print("Invalid shortcut number")
                    except ValueError:
                        print("Invalid input")
                    
                    input("Press Enter to continue...")
                    stdscr.clear()
                    curses.curs_set(0)
                elif key == ord('l') and items and cursor_pos >= 0:
                    # Enter directory or view file
                    selected = items[cursor_pos]
                    name, is_dir = selected
                    
                    full_path = os.path.join(current_path, name)
                    
                    # If in multi-select mode and this is a file, toggle selection instead of opening
                    if select_multiple_mode and not is_dir:
                        if full_path in selected_files:
                            selected_files.remove(full_path)
                        else:
                            selected_files.append(full_path)
                        # Move cursor down after selection if possible
                        if cursor_pos < len(items) - 1:
                            cursor_pos += 1
                        continue
                        
                    if is_dir:
                        try:
                            history.append(current_path)
                            current_path = full_path
                            cursor_pos = 0
                        except:
                            pass
                    else:
                        # Exit curses temporarily
                        curses.endwin()
                        
                        # Show quick summary
                        try:
                            summary, tags, _, _ = smart_preview_file(full_path)
                            print_header(f"File: {name}")
                            print(f"Summary: {summary}")
                            print(f"Tags: {', '.join(tags)}")
                            
                            print_colored("\nOptions:", Colors.BOLD)
                            print("v: View with smart preview")
                            print("e: Edit in Vim")
                            print("a: Add to Faxmachine")
                            print("c: Cancel")
                            
                            action = input("Action: ")
                            
                            if action == 'v':
                                vim_view_with_preview(full_path)
                            elif action == 'e':
                                editor = os.environ.get("EDITOR", "vim")
                                subprocess.call([editor, full_path])
                            elif action == 'a':
                                add_file(full_path)
                        except:
                            print_colored(f"Error previewing {name}", Colors.RED)
                        
                        input("Press Enter to continue...")
                        
                        # Restart curses
                        stdscr.clear()
                        curses.curs_set(0)
                elif key == ord('b') and history:
                    # Go back in history
                    current_path = history.pop()
                    cursor_pos = 0
                elif key == ord('v') and items and cursor_pos >= 0:
                    # View file with smart preview
                    selected = items[cursor_pos]
                    name, is_dir = selected
                    
                    if not is_dir:
                        full_path = os.path.join(current_path, name)
                        
                        # Exit curses temporarily
                        curses.endwin()
                        
                        # Show preview
                        vim_view_with_preview(full_path)
                        
                        input("Press Enter to continue...")
                        
                        # Restart curses
                        stdscr.clear()
                        curses.curs_set(0)
                elif key == ord('a') and items and cursor_pos >= 0 and not select_multiple_mode:
                    # Add file to Faxmachine
                    selected = items[cursor_pos]
                    name, is_dir = selected
                    
                    if not is_dir:
                        full_path = os.path.join(current_path, name)
                        
                        # Exit curses temporarily
                        curses.endwin()
                        
                        # Add file
                        add_file(full_path)
                        
                        input("Press Enter to continue...")
                        
                        # Restart curses
                        stdscr.clear()
                        curses.curs_set(0)
        
        # Start the curses application
        curses.wrapper(main)
        return None
    except Exception as e:
        print_colored(f"Error in curses interface: {str(e)}", Colors.RED)
        print("Falling back to simple browser...")
        input("Press Enter to continue...")
        return None

def _format_size(size_bytes):
    """Format file size in human-readable format"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

def process_search_command(args):
    """Process the search command with additional flags"""
    if args.list_only:
        # List results without prompting
        results = find_file(args.query, args.content_search, args.tags)
        if results:
            for i, (result, match_type) in enumerate(results):
                print(f"{i+1}. {result} ({match_type})")
            return 0
        else:
            return 1
    elif args.show_index is not None:
        # Show specific file by index
        results = find_file(args.query, args.content_search, args.tags)
        try:
            idx = int(args.show_index) - 1
            if 0 <= idx < len(results):
                show_file(results[idx][0])
                return 0
            else:
                print_colored("Invalid index", Colors.RED)
                return 1
        except (ValueError, IndexError):
            print_colored("Invalid index", Colors.RED)
            return 1
    elif args.inject_index is not None:
        # Inject specific file by index
        results = find_file(args.query, args.content_search, args.tags)
        try:
            idx = int(args.inject_index) - 1
            if 0 <= idx < len(results):
                inject_file(results[idx][0], args.name)
                return 0
            else:
                print_colored("Invalid index", Colors.RED)
                return 1
        except (ValueError, IndexError):
            print_colored("Invalid index", Colors.RED)
            return 1
    elif args.delete_index is not None:
        # Delete specific file by index
        results = find_file(args.query, args.content_search, args.tags)
        try:
            idx = int(args.delete_index) - 1
            if 0 <= idx < len(results):
                delete_file(results[idx][0])
                return 0
            else:
                print_colored("Invalid index", Colors.RED)
                return 1
        except (ValueError, IndexError):
            print_colored("Invalid index", Colors.RED)
            return 1
    else:
        # Regular search with prompting
        results = find_file(args.query, args.content_search, args.tags)
        if results:
            print_header(f"Search Results for '{args.query}'")
            for i, (result, match_type) in enumerate(results):
                print(f"{i+1}. {result} ({match_type})")
            
            choice = input("\nEnter number to inject file, v+number to view, or Enter to cancel: ")
            
            if choice.startswith('v') and choice[1:].isdigit():
                idx = int(choice[1:]) - 1
                if 0 <= idx < len(results):
                    show_file(results[idx][0])
            elif choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(results):
                    dest_name = input("Enter destination filename (leave blank for original): ")
                    if not dest_name:
                        dest_name = None
                    inject_file(results[idx][0], dest_name)
        else:
            print_colored(f"No files matching '{args.query}' found", Colors.YELLOW)
            return 1
        return 0

def mass_add_files():
    """Interactive mass file addition utility"""
    print_header("Mass Add Files")
    
    # First, determine the destination category/subcategory
    current_path = DB_DIR
    breadcrumb = []
    
    print("First, select the destination category/subcategory:")
    
    while True:
        # Get items in current directory
        items = sorted([d for d in os.listdir(current_path) 
                      if os.path.isdir(os.path.join(current_path, d))])
        
        # Show current location
        if breadcrumb:
            print(f"Current location: {' > '.join(breadcrumb)}")
        else:
            print("Current location: (root)")
        
        # Show directories
        print_colored("\nAvailable categories:", Colors.BOLD)
        for i, d in enumerate(items):
            print(f"  {i+1}. {d}/")
        
        print("\n  n. Create new category")
        if breadcrumb:
            print("  u. Up one level")
        print("  c. Confirm this location")
        
        choice = input("\nEnter your choice: ")
        
        if choice == 'c':
            break
        elif choice == 'u' and breadcrumb:
            breadcrumb.pop()
            current_path = DB_DIR
            for b in breadcrumb:
                current_path = os.path.join(current_path, b)
        elif choice == 'n':
            new_cat = input("Enter new category name: ")
            if new_cat and not os.path.exists(os.path.join(current_path, new_cat)):
                os.makedirs(os.path.join(current_path, new_cat), exist_ok=True)
                breadcrumb.append(new_cat)
                current_path = os.path.join(current_path, new_cat)
            else:
                print_colored("Invalid or existing category name", Colors.RED)
                input("Press Enter to continue...")
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(items):
                    breadcrumb.append(items[idx])
                    current_path = os.path.join(current_path, items[idx])
                else:
                    print_colored("Invalid choice", Colors.RED)
                    input("Press Enter to continue...")
            except ValueError:
                print_colored("Invalid choice", Colors.RED)
                input("Press Enter to continue...")
    
    # Now we have our destination path in current_path and breadcrumb
    category = breadcrumb[0] if breadcrumb else None
    subcategory = "/".join(breadcrumb[1:]) if len(breadcrumb) > 1 else None
    
    # Now let's select files to add
    print_header("Select Files to Add")
    print(f"Adding files to: {' > '.join(breadcrumb) if breadcrumb else 'root'}")
    
    # Use system file selection dialog if possible, otherwise fallback to manual input
    try:
        import tkinter as tk
        from tkinter import filedialog
        
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        
        file_paths = filedialog.askopenfilenames(
            title="Select files to add to Faxmachine",
            multiple=True
        )
        
        if not file_paths:
            print_colored("No files selected", Colors.YELLOW)
            return
            
        files_to_add = list(file_paths)
        
    except (ImportError, Exception):
        # Fallback to manual input
        print_colored("File selection dialog not available, using manual input", Colors.YELLOW)
        files_to_add = []
        
        while True:
            file_path = input("Enter path to file (or 'done' to finish): ")
            if file_path.lower() == 'done':
                break
                
            if os.path.exists(file_path):
                files_to_add.append(file_path)
            else:
                print_colored(f"File not found: {file_path}", Colors.RED)
    
    if not files_to_add:
        print_colored("No files to add", Colors.YELLOW)
        return
    
    # Prompt for common metadata for all files
    print_header(f"Adding {len(files_to_add)} Files")
    
    # Ask if user wants to use smart preview
    use_smart_preview = input("Use smart content analysis to generate summaries and tag suggestions? [Y/n] ")
    use_preview = use_smart_preview.lower() != 'n'
    
    common_desc = input("Enter common description for all files (optional, press Enter to set individually): ")
    common_tags = input("Enter common tags for all files (comma-separated, optional, press Enter to set individually): ")
    common_tags_list = [t.strip() for t in common_tags.split(',')] if common_tags else None
    
    # Process each file
    success_count = 0
    
    for i, file_path in enumerate(files_to_add):
        print_colored(f"\nProcessing file {i+1}/{len(files_to_add)}: {os.path.basename(file_path)}", Colors.BOLD)
        
        # Ask for file-specific metadata if common metadata wasn't provided
        desc = common_desc
        tags_list = common_tags_list
        
        # If using smart preview and no common description/tags set
        auto_summary = None
        suggested_tags = []
        
        if use_preview:
            try:
                summary, suggested_tags, preview, error = smart_preview_file(file_path)
                
                if error:
                    print_colored(f"Warning: {error}", Colors.YELLOW)
                
                if summary:
                    print_colored("\nFile Analysis:", Colors.BOLD)
                    print(f"Summary: {summary}")
                    
                    if suggested_tags:
                        print(f"Suggested tags: {', '.join(suggested_tags)}")
                    
                    # Only show preview option for this specific file
                    if preview:
                        preview_choice = input("Show content preview? [y/N] ")
                        if preview_choice.lower() == 'y':
                            print_colored("\nContent Preview:", Colors.BOLD)
                            print(preview)
                    
                    auto_summary = summary
            except Exception as e:
                print_colored(f"Warning: Preview generation failed: {str(e)}", Colors.YELLOW)
        
        if desc is None or desc == "":
            if auto_summary:
                desc = input(f"Enter description (suggested: '{auto_summary}'): ")
                if not desc:
                    desc = auto_summary
            else:
                desc = input(f"Enter description for '{os.path.basename(file_path)}' (optional): ")
        
        if tags_list is None:
            if suggested_tags:
                tags = input(f"Enter tags (suggested: {', '.join(suggested_tags)}): ")
                if not tags:
                    tags_list = suggested_tags
                else:
                    tags_list = [t.strip() for t in tags.split(',')] if tags else []
            else:
                tags = input(f"Enter tags for '{os.path.basename(file_path)}' (comma-separated, optional): ")
                tags_list = [t.strip() for t in tags.split(',')] if tags else []
        
        name = input(f"Enter name for '{os.path.basename(file_path)}' (leave blank for original): ")
        if not name:
            name = os.path.basename(file_path)
        
        # Add the file
        if add_file(file_path, category, name, subcategory, desc, tags_list, preview_content=False):
            success_count += 1
    
    print_colored(f"\nAdded {success_count} out of {len(files_to_add)} files successfully", Colors.GREEN)
    input("Press Enter to continue...")

def display_help():
    """Display detailed help information"""
    print_header(f"Faxmachine v{VERSION} - Help")
    
    print("\nCOMMANDS:")
    print("  browse       Browse and manage files with interactive browser")
    print("  add          Add a file to the database")
    print("  search       Search for files")
    print("  show         Display a file's contents")
    print("  inject       Insert a file into current directory")
    print("  list         List all files by category")
    print("  mass-add     Add multiple files at once")
    print("  recent       Show recently accessed files")
    print("  delete       Remove a file from the database")
    print("  init         Initialize or reset the database\n")
    
    print("EXAMPLES:")
    print("  faxmachine browse                   # Interactive browser")
    print("  faxmachine add myfile.txt           # Add a file interactively")
    print("  faxmachine add config.yml -c config # Add to the 'config' category")
    print("  faxmachine search gitignore         # Search for 'gitignore'")
    print("  faxmachine inject git/gitignore     # Inject a file")
    print("  faxmachine print git/gitignore      # Same as inject (alias)")
    
    print("\nConfiguration:")
    print(f"  Config directory: {CONFIG_DIR}")
    print(f"  Database directory: {DB_DIR}")
    
    print("\nMetadata:")
    print("  Files can have descriptions and tags for better searchability.")
    print("  Add tags when adding files or edit metadata in the browser.")
    
    print("\nFeatures:")
    print("  - Content-based search: search inside files")
    print("  - File preview before injection")
    print("  - Metadata for better organization")
    print("  - Tagging system for classification")

def main():
    """Main entry point for the application"""
    # Create argument parser
    parser = argparse.ArgumentParser(description='Faxmachine - File Template Manager')
    parser.add_argument('--version', action='store_true', help='Show version information')
    parser.add_argument('--detailed-help', action='store_true', dest='show_help', help='Show detailed help')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Init command
    init_parser = subparsers.add_parser('init', help='Initialize the database')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List available files')
    list_parser.add_argument('category', nargs='?', help='Category to list')
    
    # Add command
    add_parser = subparsers.add_parser('add', help='Add a file to the database')
    add_parser.add_argument('file', help='File to add')
    add_parser.add_argument('-c', '--category', help='Category to add the file to')
    add_parser.add_argument('-s', '--subcategory', help='Subcategory to add the file to')
    add_parser.add_argument('-n', '--name', help='Name for the stored file')
    add_parser.add_argument('-d', '--description', help='Description of the file')
    add_parser.add_argument('-t', '--tags', help='Comma-separated tags')
    
    # Inject command with print alias
    inject_parser = subparsers.add_parser('inject', aliases=['print'], help='Inject a file from the database')
    inject_parser.add_argument('file', help='File path within the database')
    inject_parser.add_argument('-n', '--name', help='Name for the injected file')
    inject_parser.add_argument('--no-preview', action='store_true', help='Skip preview when injecting')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search for files')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('-c', '--content-search', action='store_true', help='Search in file contents')
    search_parser.add_argument('-t', '--tags', help='Filter by comma-separated tags')
    search_parser.add_argument('--list-only', action='store_true', help='Only list results, no prompts')
    search_parser.add_argument('--show-index', help='Show file at specified index')
    search_parser.add_argument('--inject-index', help='Inject file at specified index')
    search_parser.add_argument('--delete-index', help='Delete file at specified index')
    search_parser.add_argument('-n', '--name', help='Name for injected file (with --inject-index)')
    
    # Show command
    show_parser = subparsers.add_parser('show', help='Show file contents')
    show_parser.add_argument('file', help='File path within the database')
    
    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete a file from the database')
    delete_parser.add_argument('file', help='File path within the database')
    
    # Interactive command
    interactive_parser = subparsers.add_parser('browse', help='Interactive browser')
    
    # Recent command
    recent_parser = subparsers.add_parser('recent', help='Show recently accessed files')
    
    # Mass add command
    mass_add_parser = subparsers.add_parser('mass-add', help='Add multiple files at once')
    
    # Document viewer command
    doc_viewer_parser = subparsers.add_parser('browser', aliases=['view'], help='Browse files with smart preview')
    doc_viewer_parser.add_argument('file', nargs='?', help='Path to the document to view')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Handle version display
    if args.version:
        print(f"Faxmachine v{VERSION}")
        return 0
        
    # Handle detailed help
    if args.show_help:
        display_help()
        return 0
    
    # Ensure config directory exists
    os.makedirs(CONFIG_DIR, exist_ok=True)
    
    # Handle commands
    if args.command == 'init' or not os.path.exists(DB_DIR):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        os.makedirs(DB_DIR, exist_ok=True)
        os.makedirs(METADATA_DIR, exist_ok=True)
        init_db()
        print_colored("Faxmachine database initialized", Colors.GREEN)
        return 0
    elif args.command == 'list':
        print_header("Faxmachine Database Contents")
        list_items()
        return 0
    elif args.command == 'add':
        tags = [t.strip() for t in args.tags.split(',')] if args.tags else None
        success = add_file(args.file, args.category, args.name, args.subcategory, args.description, tags)
        return 0 if success else 1
    elif args.command == 'inject' or args.command == 'print':
        preview = not args.no_preview
        success = inject_file(args.file, args.name, preview)
        return 0 if success else 1
    elif args.command == 'search':
        return process_search_command(args)
    elif args.command == 'show':
        success = show_file(args.file)
        return 0 if success else 1
    elif args.command == 'delete':
        success = delete_file(args.file)
        return 0 if success else 1
    elif args.command == 'mass-add':
        mass_add_files()
        return 0
    elif args.command == 'view' or args.command == 'browser':
        if args.file:
            if not os.path.exists(args.file):
                print_colored(f"Error: File '{args.file}' not found", Colors.RED)
                return 1
            vim_view_with_preview(args.file)
        else:
            interactive_file_browser()
        return 0
    elif args.command == 'browse':
        interactive_file_browser()
    elif args.command == 'recent':
        config = load_config()
        if config["last_accessed"]:
            print_header("Recently Accessed Files")
            for i, file in enumerate(config["last_accessed"]):
                print(f"{i+1}. {file}")
            
            choice = input("\nEnter number to inject file, v+number to view, or Enter to cancel: ")
            
            if choice.startswith('v') and choice[1:].isdigit():
                idx = int(choice[1:]) - 1
                if 0 <= idx < len(config["last_accessed"]):
                    show_file(config["last_accessed"][idx])
            elif choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(config["last_accessed"]):
                    dest_name = input("Enter destination filename (leave blank for original): ")
                    if not dest_name:
                        dest_name = None
                    inject_file(config["last_accessed"][idx], dest_name)
        else:
            print_colored("No recently accessed files", Colors.YELLOW)
    else:
        # Display a welcome message and brief help
        print_header(f"Faxmachine v{VERSION}")
        print("\nCommon Commands:")
        print("\nUsage: faxmachine <command> [options]")
        print("\nCOMMANDS:")
        print("  browse     Browse files interactively")
        print("  add        Add a file to the database")
        print("  mass-add   Add multiple files at once")
        print("  search     Search for files")
        print("  inject     Insert a file into current directory")
        print("  list       List all files by category")
        print("  recent     Show recently accessed files")
        print("  delete     Remove a file")
        print("  init       Initialize the database")
        print("\nUse 'faxmachine <command> --help' for more information on a command")
        print("Use 'faxmachine --detailed-help' for detailed help information")
        
        # Offer to initialize if not yet initialized
        if not os.path.exists(DB_DIR):
            print_colored("\nDatabase not initialized. Initialize now? [Y/n] ", Colors.YELLOW)
            choice = input()
            if choice.lower() != 'n':
                init_db()
                print_colored("Database initialized", Colors.GREEN)
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print_colored(f"Error: {e}", Colors.RED)
        sys.exit(1)