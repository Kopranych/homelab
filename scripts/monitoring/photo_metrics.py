#!/usr/bin/env python3
"""
Photo Consolidation Metrics Collector
Outputs metrics in InfluxDB line protocol format for Telegraf
"""

import os
import json
import glob
from pathlib import Path

def get_directory_size(path):
    """Calculate total size of directory in bytes"""
    total = 0
    try:
        for entry in os.scandir(path):
            if entry.is_file(follow_symlinks=False):
                total += entry.stat().st_size
            elif entry.is_dir(follow_symlinks=False):
                total += get_directory_size(entry.path)
    except (OSError, PermissionError):
        pass
    return total

def count_files(path, extensions=None):
    """Count files in directory, optionally filtered by extensions"""
    count = 0
    try:
        for entry in os.scandir(path):
            if entry.is_file(follow_symlinks=False):
                if extensions is None:
                    count += 1
                elif any(entry.name.lower().endswith(ext) for ext in extensions):
                    count += 1
            elif entry.is_dir(follow_symlinks=False):
                count += count_files(entry.path, extensions)
    except (OSError, PermissionError):
        pass
    return count

def get_photo_consolidation_metrics():
    """Collect photo consolidation metrics"""
    metrics = []

    # Base paths
    data_root = "/data"
    incoming_path = f"{data_root}/incoming"
    duplicates_path = f"{data_root}/duplicates"
    final_path = f"{data_root}/final"
    manifests_path = f"{data_root}/manifests"

    # Photo extensions
    photo_exts = ['.jpg', '.jpeg', '.png', '.heic', '.cr2', '.nef', '.arw', '.dng']
    video_exts = ['.mp4', '.mov', '.avi', '.mkv']

    # Collect metrics for each directory
    directories = {
        'incoming': incoming_path,
        'duplicates': duplicates_path,
        'final': final_path
    }

    for name, path in directories.items():
        if os.path.exists(path):
            # Directory size
            size_bytes = get_directory_size(path)
            metrics.append(f'photo_consolidation,directory={name} size_bytes={size_bytes}i')

            # File counts
            photo_count = count_files(path, photo_exts)
            video_count = count_files(path, video_exts)
            total_count = count_files(path)

            metrics.append(f'photo_consolidation,directory={name} photo_count={photo_count}i')
            metrics.append(f'photo_consolidation,directory={name} video_count={video_count}i')
            metrics.append(f'photo_consolidation,directory={name} total_files={total_count}i')

    # Check for manifest files
    if os.path.exists(manifests_path):
        manifest_files = glob.glob(f"{manifests_path}/*.sha256") + glob.glob(f"{manifests_path}/*.json")
        metrics.append(f'photo_consolidation,type=manifests count={len(manifest_files)}i')

    # Check for log files
    logs_path = f"{data_root}/logs/photo-consolidation"
    if os.path.exists(logs_path):
        log_files = glob.glob(f"{logs_path}/*.log")
        if log_files:
            # Get most recent log file size
            latest_log = max(log_files, key=os.path.getctime)
            log_size = os.path.getsize(latest_log)
            metrics.append(f'photo_consolidation,type=logs latest_size_bytes={log_size}i')

    # Disk space specifically for /data
    try:
        stat = os.statvfs(data_root)
        free_bytes = stat.f_bavail * stat.f_frsize
        total_bytes = stat.f_blocks * stat.f_frsize
        used_bytes = total_bytes - free_bytes
        used_percent = (used_bytes / total_bytes) * 100

        metrics.append(f'photo_consolidation,type=storage free_bytes={free_bytes}i')
        metrics.append(f'photo_consolidation,type=storage used_bytes={used_bytes}i')
        metrics.append(f'photo_consolidation,type=storage total_bytes={total_bytes}i')
        metrics.append(f'photo_consolidation,type=storage used_percent={used_percent:.2f}')
    except OSError:
        pass

    return metrics

def main():
    """Main function"""
    try:
        metrics = get_photo_consolidation_metrics()
        for metric in metrics:
            print(metric)
    except Exception as e:
        # Output error as metric
        print(f'photo_consolidation,type=error value=1i')
        # Log error to stderr (Telegraf will capture it)
        import sys
        print(f"Error collecting photo metrics: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
