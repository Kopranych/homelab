#!/usr/bin/env python3
"""Tests for photo consolidation configuration using should/when pattern."""

import sys
import subprocess
import yaml
from pathlib import Path
from photo_consolidator.config import Config


def test_should_load_configuration_when_config_file_exists():
    """Should successfully load configuration when config file exists."""
    # When loading configuration
    config = Config()
    
    # Should have a valid config path
    assert config.config_path is not None, "Config path should not be None"
    assert Path(config.config_path).exists(), "Config file should exist"
    print(f"✅ Configuration loaded from: {config.config_path}")
    print("📋 Full configuration:")
    import yaml
    print(yaml.dump(config.config, default_flow_style=False, indent=2))

def test_should_provide_data_root_when_configuration_loaded():
    """Should provide data root directory when configuration is loaded."""

    # When configuration is loaded
    config = Config()
    
    # Should provide data root
    data_root = config.get_data_root()
    assert data_root, "Data root should not be empty"
    assert isinstance(data_root, str), "Data root should be a string"
    print(f"✅ Data root: {data_root}")

def test_should_provide_source_drives_when_configuration_loaded():
    """Should provide source drives list when configuration is loaded."""

    # When configuration is loaded
    config = Config()
    
    # Should provide source drives
    source_drives = config.get_source_drives()
    assert isinstance(source_drives, list), "Source drives should be a list"
    print(f"✅ Source drives: {len(source_drives)} configured")

def test_should_provide_supported_extensions_when_configuration_loaded():
    """Should provide supported file extensions when configuration is loaded."""

    # When configuration is loaded
    config = Config()
    
    # Should provide extensions dictionary
    extensions = config.get_supported_extensions()
    assert isinstance(extensions, dict), "Extensions should be a dictionary"
    assert 'photos' in extensions, "Should have photos extensions"
    assert 'videos' in extensions, "Should have videos extensions"
    assert isinstance(extensions['photos'], list), "Photo extensions should be a list"
    assert isinstance(extensions['videos'], list), "Video extensions should be a list"
    print(f"✅ Extensions: {len(extensions.get('photos', []))} photo, {len(extensions.get('videos', []))} video")

def test_should_validate_configuration_when_loaded():
    """Should validate configuration settings when loaded."""

    # When configuration is loaded
    config = Config()
    
    # Should perform validation
    errors = config.validate_config()
    assert isinstance(errors, list), "Validation should return a list"
    
    # Note: Validation warnings are expected during development
    if errors:
        print("⚠️  Configuration validation warnings (expected in dev):")
        for error in errors:
            print(f"    • {error}")
    else:
        print("✅ Configuration validation passed")

def test_should_import_all_modules_when_package_loaded():
    """Should successfully import all modules when package is loaded."""
    modules = [
        'photo_consolidator.config',
        'photo_consolidator.utils', 
        'photo_consolidator.file_copier',
        'photo_consolidator.media_scanner',
        'photo_consolidator.duplicates',
        'photo_consolidator.consolidator',
        'photo_consolidator.reporter'
    ]
    
    # When importing each module
    for module in modules:
        # Should import without exception
        imported_module = __import__(module)
        assert imported_module is not None, f"Module {module} should import successfully"
        print(f"✅ {module}")

def test_should_load_cli_module_when_imported():
    """Should load CLI module successfully when imported."""
    # When importing CLI module
    import consolidate
    
    # Should import without exception
    assert consolidate is not None, "CLI module should import successfully"
    print("✅ CLI module loads successfully")

def test_should_show_help_when_cli_help_requested():
    """Should show help information when CLI help is requested."""
    # When requesting CLI help
    result = subprocess.run([sys.executable, 'consolidate.py', '--help'], 
                          capture_output=True, text=True, 
                          cwd=Path(__file__).parent.parent)
    
    # Should return success
    assert result.returncode == 0, f"CLI help should succeed: {result.stderr}"
    
    # Should contain expected content
    assert "Photo Consolidation Tool" in result.stdout, "Help should contain tool description"
    assert "workflow" in result.stdout, "Help should contain workflow command"
    assert "scan" in result.stdout, "Help should contain scan command"
    print("✅ CLI help works correctly")

def test_should_provide_quality_config_when_configuration_loaded():
    """Should provide quality configuration when configuration is loaded."""

    # When configuration is loaded
    config = Config()
    
    # Should provide quality configuration
    quality_config = config.get_quality_config()
    assert isinstance(quality_config, dict), "Quality config should be a dictionary"
    print(f"✅ Quality config available with {len(quality_config)} settings")

def test_should_provide_safety_config_when_configuration_loaded():
    """Should provide safety configuration when configuration is loaded."""

    # When configuration is loaded
    config = Config()
    
    # Should provide safety configuration
    safety_config = config.get_safety_config()
    assert isinstance(safety_config, dict), "Safety config should be a dictionary"
    
    # Should provide specific safety settings
    min_free_space = config.get_min_free_space_gb()
    assert isinstance(min_free_space, int), "Min free space should be an integer"
    assert min_free_space > 0, "Min free space should be positive"
    
    backup_before_removal = config.should_backup_before_removal()
    assert isinstance(backup_before_removal, bool), "Backup setting should be boolean"
    
    print(f"✅ Safety config: {min_free_space}GB min space, backup={backup_before_removal}")

def test_should_provide_process_config_when_configuration_loaded():
    """Should provide process configuration when configuration is loaded."""

    # When configuration is loaded
    config = Config()
    
    # Should provide process configuration
    parallel_jobs = config.get_parallel_jobs()
    assert isinstance(parallel_jobs, int), "Parallel jobs should be an integer"
    assert 1 <= parallel_jobs <= 32, "Parallel jobs should be reasonable (1-32)"
    
    preserve_structure = config.should_preserve_structure()
    assert isinstance(preserve_structure, bool), "Preserve structure should be boolean"
    
    is_dry_run = config.is_dry_run()
    assert isinstance(is_dry_run, bool), "Dry run should be boolean"
    
    print(f"✅ Process config: {parallel_jobs} jobs, preserve={preserve_structure}, dry_run={is_dry_run}")


# ===========================================================================
# Incremental mode config accessors
# ===========================================================================

def _write_config(tmp_path, data):
    config_path = tmp_path / 'config.yml'
    with open(config_path, 'w') as f:
        yaml.dump(data, f)
    return Config(str(config_path))


def test_should_return_run_id_when_incremental_run_id_configured(tmp_path):
    """Should return the run_id string when photo_consolidation.incremental.run_id is set."""
    config = _write_config(tmp_path, {
        'photo_consolidation': {'incremental': {'run_id': '2026-03-02', 'compare_final': ''}}
    })
    assert config.get_run_id() == '2026-03-02'


def test_should_return_none_when_run_id_not_set(tmp_path):
    """Should return None when the incremental section is absent."""
    config = _write_config(tmp_path, {'photo_consolidation': {}})
    assert config.get_run_id() is None


def test_should_return_none_when_run_id_is_empty_string(tmp_path):
    """Should return None when run_id is explicitly set to empty string."""
    config = _write_config(tmp_path, {
        'photo_consolidation': {'incremental': {'run_id': '', 'compare_final': ''}}
    })
    assert config.get_run_id() is None


def test_should_return_compare_final_dir_when_configured(tmp_path):
    """Should return the path string when compare_final is set."""
    config = _write_config(tmp_path, {
        'photo_consolidation': {
            'incremental': {'run_id': 'run1', 'compare_final': '/data/photo-consolidation/final'}
        }
    })
    assert config.get_compare_final_dir() == '/data/photo-consolidation/final'


def test_should_return_none_when_compare_final_is_empty_string(tmp_path):
    """Should return None when compare_final is explicitly set to empty string."""
    config = _write_config(tmp_path, {
        'photo_consolidation': {'incremental': {'run_id': 'run1', 'compare_final': ''}}
    })
    assert config.get_compare_final_dir() is None


def test_should_return_none_when_compare_final_not_set(tmp_path):
    """Should return None when the incremental section has no compare_final key."""
    config = _write_config(tmp_path, {'photo_consolidation': {'incremental': {'run_id': 'run1'}}})
    assert config.get_compare_final_dir() is None