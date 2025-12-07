"""Utility script to preview and optionally delete stored resume PDF files and clear DB entries.

Usage:
  # Dry run - list candidates with resume paths and check file existence
  python scripts/cleanup_resumes.py --dry-run

  # Delete files (prompt per-file unless --yes)
  python scripts/cleanup_resumes.py --delete --yes

  # Remove DB references without deleting files
  python scripts/cleanup_resumes.py --clear-db --yes

Be careful: deletion is irreversible. Always run with --dry-run first.
"""
import argparse
import sqlite3
from pathlib import Path
import os

DB_PATH = Path("hiring-ai-agent/data/hiring_agent.db")


def list_candidates_with_files():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT id, name, resume_file_path FROM candidates WHERE resume_file_path IS NOT NULL AND resume_file_path != ''")
    rows = cur.fetchall()
    conn.close()
    return rows


def delete_file(path: str):
    p = Path(path)
    if p.exists():
        p.unlink()
        return True
    return False


def clear_db_resume_path(candidate_id: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE candidates SET resume_file_path = NULL WHERE id = ?", (candidate_id,))
    conn.commit()
    conn.close()


def delete_candidate_row(candidate_id: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM candidates WHERE id = ?", (candidate_id,))
    conn.commit()
    conn.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--delete", action="store_true")
    parser.add_argument("--clear-db", action="store_true")
    parser.add_argument("--yes", action="store_true", help="Assume yes for deletions")
    args = parser.parse_args()

    rows = list_candidates_with_files()
    if not rows:
        print("No candidates with stored resume_file_path found.")
        return

    print(f"Found {len(rows)} candidates with resume_file_path:")
    for r in rows:
        cid = r['id']
        name = r['name'] or '<no name>'
        path = r['resume_file_path']
        exists = Path(path).exists() if path else False
        print(f"- {cid} | {name} | {path} | exists={exists}")

    if args.dry_run:
        print("Dry run complete. Use --delete or --clear-db to act.")
        return

    if args.delete:
        for r in rows:
            cid = r['id']
            path = r['resume_file_path']
            if not path:
                continue
            p = Path(path)
            if not p.exists():
                print(f"Skipping {cid} - file not found: {path}")
                continue
            if not args.yes:
                ans = input(f"Delete file {path}? [y/N]: ")
                if ans.lower() != 'y':
                    print("Skipping")
                    continue
            deleted = delete_file(path)
            print(f"Deleted {path}: {deleted}")
            # Optionally clear DB reference
            clear_db_resume_path(cid)
            print(f"Cleared DB resume_file_path for {cid}")
        print("Delete operation complete.")
        return

    if args.clear_db:
        for r in rows:
            cid = r['id']
            if not args.yes:
                ans = input(f"Clear resume_file_path for candidate {cid}? [y/N]: ")
                if ans.lower() != 'y':
                    print("Skipping")
                    continue
            clear_db_resume_path(cid)
            print(f"Cleared DB resume_file_path for {cid}")
        print("DB clear operation complete.")
        return


if __name__ == '__main__':
    main()
