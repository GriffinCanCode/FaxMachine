#!/usr/bin/env python3
"""QGit statistics module for generating repository analytics and insights."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict

from qgits.qgit_git import GitCommand
from qgits.qgit_errors import GitCommandError
from qgits.qgit_logger import logger

def get_commit_stats(author: Optional[str] = None, 
                    start_date: Optional[str] = None,
                    end_date: Optional[str] = None) -> Dict[str, Any]:
    """Get commit statistics for the repository.
    
    Args:
        author: Optional author to filter commits
        start_date: Optional start date in YYYY-MM-DD format
        end_date: Optional end date in YYYY-MM-DD format
        
    Returns:
        Dictionary containing commit statistics
    """
    try:
        # Build git log command with filters
        cmd = ["git log", "--pretty=format:%H|%an|%ae|%at|%s"]
        
        if author:
            cmd.append(f"--author={author}")
        if start_date:
            cmd.append(f"--since={start_date}")
        if end_date:
            cmd.append(f"--until={end_date}")
            
        # Get commit data
        log_output = GitCommand.run(" ".join(cmd))
        commits = []
        authors = defaultdict(int)
        dates = defaultdict(int)
        
        for line in log_output.split("\n"):
            if not line:
                continue
            hash_, author_name, author_email, timestamp, message = line.split("|")
            commits.append({
                "hash": hash_,
                "author": author_name,
                "email": author_email,
                "timestamp": datetime.fromtimestamp(int(timestamp)),
                "message": message
            })
            authors[author_name] += 1
            dates[datetime.fromtimestamp(int(timestamp)).date()] += 1
            
        # Calculate statistics
        total_commits = len(commits)
        unique_authors = len(authors)
        commit_dates = sorted(dates.keys())
        
        # Calculate daily/weekly/monthly averages
        if commit_dates:
            date_range = (commit_dates[-1] - commit_dates[0]).days + 1
            daily_avg = total_commits / date_range if date_range > 0 else 0
            weekly_avg = daily_avg * 7
            monthly_avg = daily_avg * 30
        else:
            daily_avg = weekly_avg = monthly_avg = 0
            
        return {
            "total_commits": total_commits,
            "unique_authors": unique_authors,
            "authors": dict(authors),
            "daily_average": round(daily_avg, 2),
            "weekly_average": round(weekly_avg, 2),
            "monthly_average": round(monthly_avg, 2),
            "commit_dates": {d.isoformat(): count for d, count in dates.items()}
        }
        
    except GitCommandError as e:
        logger.log(
            level="error",
            command="stats",
            message="Failed to get commit statistics",
            metadata={"error": str(e)}
        )
        return {}

def get_churn_stats() -> Dict[str, Any]:
    """Get code churn statistics for the repository.
    
    Returns:
        Dictionary containing code churn statistics
    """
    try:
        # Get file change statistics
        cmd = "git log --numstat --pretty=format:"
        output = GitCommand.run(cmd)
        
        file_changes = defaultdict(lambda: {"additions": 0, "deletions": 0})
        current_commit = None
        
        for line in output.split("\n"):
            if not line:
                continue
                
            # Skip commit messages
            if not line[0].isdigit():
                continue
                
            additions, deletions, filename = line.split("\t")
            if additions.isdigit() and deletions.isdigit():
                file_changes[filename]["additions"] += int(additions)
                file_changes[filename]["deletions"] += int(deletions)
                
        # Calculate total changes
        total_additions = sum(f["additions"] for f in file_changes.values())
        total_deletions = sum(f["deletions"] for f in file_changes.values())
        
        # Find most changed files
        sorted_files = sorted(
            file_changes.items(),
            key=lambda x: x[1]["additions"] + x[1]["deletions"],
            reverse=True
        )[:10]
        
        return {
            "total_additions": total_additions,
            "total_deletions": total_deletions,
            "total_changes": total_additions + total_deletions,
            "most_changed_files": [
                {
                    "file": filename,
                    "additions": stats["additions"],
                    "deletions": stats["deletions"]
                }
                for filename, stats in sorted_files
            ]
        }
        
    except GitCommandError as e:
        logger.log(
            level="error",
            command="stats",
            message="Failed to get churn statistics",
            metadata={"error": str(e)}
        )
        return {}

def get_team_stats() -> Dict[str, Any]:
    """Get team collaboration statistics.
    
    Returns:
        Dictionary containing team collaboration statistics
    """
    try:
        # Get commit data for all authors
        cmd = "git log --pretty=format:%an|%ae|%at"
        output = GitCommand.run(cmd)
        
        authors = defaultdict(lambda: {
            "commits": 0,
            "first_commit": None,
            "last_commit": None,
            "active_days": set()
        })
        
        for line in output.split("\n"):
            if not line:
                continue
                
            author_name, author_email, timestamp = line.split("|")
            commit_date = datetime.fromtimestamp(int(timestamp))
            
            author_stats = authors[author_name]
            author_stats["commits"] += 1
            author_stats["active_days"].add(commit_date.date())
            
            if not author_stats["first_commit"] or commit_date < author_stats["first_commit"]:
                author_stats["first_commit"] = commit_date
            if not author_stats["last_commit"] or commit_date > author_stats["last_commit"]:
                author_stats["last_commit"] = commit_date
                
        # Calculate additional metrics
        for author_stats in authors.values():
            author_stats["active_days"] = len(author_stats["active_days"])
            if author_stats["first_commit"] and author_stats["last_commit"]:
                author_stats["commit_span_days"] = (
                    author_stats["last_commit"] - author_stats["first_commit"]
                ).days + 1
            else:
                author_stats["commit_span_days"] = 0
                
        # Convert datetime objects to ISO format for JSON serialization
        for author_stats in authors.values():
            if author_stats["first_commit"]:
                author_stats["first_commit"] = author_stats["first_commit"].isoformat()
            if author_stats["last_commit"]:
                author_stats["last_commit"] = author_stats["last_commit"].isoformat()
                
        return {
            "total_authors": len(authors),
            "authors": dict(authors)
        }
        
    except GitCommandError as e:
        logger.log(
            level="error",
            command="stats",
            message="Failed to get team statistics",
            metadata={"error": str(e)}
        )
        return {}

def get_leaderboard_stats() -> Dict[str, Any]:
    """Get leaderboard statistics showing line-by-line changes per author.
    
    Returns:
        Dictionary containing leaderboard statistics
    """
    try:
        # Get detailed change statistics per author
        cmd = "git log --numstat --pretty=format:%an|%ae|%at"
        output = GitCommand.run(cmd)
        
        author_stats = defaultdict(lambda: {
            "additions": 0,
            "deletions": 0,
            "commits": 0,
            "files_changed": defaultdict(lambda: {"additions": 0, "deletions": 0})
        })
        
        current_author = None
        current_email = None
        
        for line in output.split("\n"):
            if not line:
                continue
                
            # Check if line is author info
            if "|" in line:
                current_author, current_email, _ = line.split("|")
                author_stats[current_author]["commits"] += 1
                continue
                
            # Skip empty lines and non-numeric lines
            if not line or not line[0].isdigit():
                continue
                
            # Parse file changes
            additions, deletions, filename = line.split("\t")
            if additions.isdigit() and deletions.isdigit():
                author_stats[current_author]["additions"] += int(additions)
                author_stats[current_author]["deletions"] += int(deletions)
                author_stats[current_author]["files_changed"][filename]["additions"] += int(additions)
                author_stats[current_author]["files_changed"][filename]["deletions"] += int(deletions)
        
        # Calculate total changes and sort authors
        for author in author_stats:
            author_stats[author]["total_changes"] = (
                author_stats[author]["additions"] + author_stats[author]["deletions"]
            )
            # Convert files_changed to list for sorting
            author_stats[author]["files_changed"] = [
                {"file": f, "additions": s["additions"], "deletions": s["deletions"]}
                for f, s in author_stats[author]["files_changed"].items()
            ]
            # Sort files by total changes
            author_stats[author]["files_changed"].sort(
                key=lambda x: x["additions"] + x["deletions"],
                reverse=True
            )
        
        # Sort authors by total changes
        sorted_authors = sorted(
            author_stats.items(),
            key=lambda x: x[1]["total_changes"],
            reverse=True
        )
        
        return {
            "authors": [
                {
                    "name": author,
                    "email": author_stats[author].get("email", ""),
                    "commits": stats["commits"],
                    "additions": stats["additions"],
                    "deletions": stats["deletions"],
                    "total_changes": stats["total_changes"],
                    "files_changed": stats["files_changed"]
                }
                for author, stats in sorted_authors
            ]
        }
        
    except GitCommandError as e:
        logger.log(
            level="error",
            command="stats",
            message="Failed to get leaderboard statistics",
            metadata={"error": str(e)}
        )
        return {}
