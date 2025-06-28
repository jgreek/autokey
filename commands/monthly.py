from pathlib import Path
from datetime import datetime
import re
from dataclasses import dataclass
from typing import Set, Dict, List


@dataclass
class MonthlyReport:
    month: str
    files_in_folder: Set[str]
    files_in_playlist: Set[str]
    missing_from_playlist: Set[str]
    missing_from_folder: Set[str]

    @property
    def folder_count(self) -> int:
        return len(self.files_in_folder)

    @property
    def playlist_count(self) -> int:
        return len(self.files_in_playlist)


class MoviePlaylistGenerator:
    def __init__(self, base_dir):
        """
        Initialize with the base movies directory

        Args:
            base_dir (str): Path to the main movies directory
        """
        self.base_dir = Path(base_dir)
        self.movie_files = set()
        self.monthly_folders = {}
        self.month_names = {
            '1': 'January', '2': 'February', '3': 'March',
            '4': 'April', '5': 'May', '6': 'June',
            '7': 'July', '10': 'October', '11': 'November',
            '12': 'December'
        }

    def _is_movie_file(self, file_path):
        """Check if file is a movie based on extension"""
        movie_extensions = {'.mp4', '.mkv', '.avi', '.mov', '.wmv'}
        return file_path.suffix.lower() in movie_extensions

    def scan_directory(self):
        """Scan the base directory for movie files and monthly folders"""
        # First get all movie files in the main directory
        self.movie_files = {
            f for f in self.base_dir.glob('*')
            if f.is_file() and self._is_movie_file(f)
        }

        # Then scan monthly folders
        folder_pattern = re.compile(r'folder_(\d{1,2})')
        for folder in self.base_dir.glob('folder_*'):
            if not folder.is_dir():
                continue

            match = folder_pattern.match(folder.name)
            if match:
                month_num = match.group(1)
                self.monthly_folders[month_num] = set()

                # Get all aliases/files in this monthly folder
                for file in folder.glob('*'):
                    if file.is_symlink() or file.is_file():
                        self.monthly_folders[month_num].add(file)

    def generate_playlists(self):
        """Generate monthly playlists in the base directory"""
        self.scan_directory()

        for month_num, monthly_files in self.monthly_folders.items():
            playlist_path = self.base_dir / f'playlist_{month_num}.m3u'

            # Create playlist content
            playlist_content = []

            # For each alias in the monthly folder, find the corresponding real file
            for monthly_file in monthly_files:
                filename = monthly_file.name
                matching_files = [
                    str(f.relative_to(self.base_dir))
                    for f in self.movie_files
                    if f.name == filename
                ]

                if matching_files:
                    playlist_content.extend(matching_files)

            # Write playlist file
            if playlist_content:
                with open(playlist_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(playlist_content))
                print(f"Created playlist: {playlist_path}")
            else:
                print(f"No files found for month {month_num}")

    def generate_report(self) -> Dict[str, MonthlyReport]:
        """Generate a comprehensive report for all months"""
        self.scan_directory()
        reports = {}

        for month_num in self.month_names.keys():
            # Get files in monthly folder
            folder_files = set()
            if month_num in self.monthly_folders:
                folder_files = {f.name for f in self.monthly_folders[month_num]}

            # Get files in playlist
            playlist_path = self.base_dir / f'playlist_{month_num}.m3u'
            playlist_files = set()
            if playlist_path.exists():
                with open(playlist_path, 'r', encoding='utf-8') as f:
                    playlist_files = {Path(line.strip()).name for line in f if line.strip()}

            # Find discrepancies
            missing_from_playlist = folder_files - playlist_files
            missing_from_folder = playlist_files - folder_files

            # Create report
            reports[month_num] = MonthlyReport(
                month=self.month_names[month_num],
                files_in_folder=folder_files,
                files_in_playlist=playlist_files,
                missing_from_playlist=missing_from_playlist,
                missing_from_folder=missing_from_folder
            )

        return reports

    def print_report(self, reports: Dict[str, MonthlyReport]):
        """Print a formatted report to the console"""
        print("\n=== Movie Playlist Validation Report ===\n")

        for month_num, report in sorted(reports.items()):
            print(f"\n{report.month} (folder_{month_num}):")
            print("-" * 40)
            print(f"Files in folder: {report.folder_count}")
            print(f"Files in playlist: {report.playlist_count}")

            if report.missing_from_playlist:
                print("\nFiles in folder but missing from playlist:")
                for file in sorted(report.missing_from_playlist):
                    print(f"  - {file}")

            if report.missing_from_folder:
                print("\nFiles in playlist but missing from folder:")
                for file in sorted(report.missing_from_folder):
                    print(f"  - {file}")

            if not report.missing_from_playlist and not report.missing_from_folder:
                print("\nAll files match! ✓")

            print("\n" + "=" * 40)


def main():
    """Main function to demonstrate usage"""
    movies_dir = '/Users/johngreek/Archives/movies'

    print(f"Processing directory: {movies_dir}")

    try:
        generator = MoviePlaylistGenerator(movies_dir)

        # Generate all playlists
        print("\nGenerating monthly playlists...")
        generator.generate_playlists()

        # Generate and print comprehensive report
        print("\nGenerating validation report...")
        reports = generator.generate_report()
        generator.print_report(reports)

    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return 1

    print("\nProcess completed successfully!")
    return 0


if __name__ == '__main__':
    exit(main())