#!/usr/bin/env python3
"""
Quick configuration validation utility for 4-model architecture.

Usage:
  python validate_config.py                    # Validate current configuration
  python validate_config.py --mode dev        # Development mode validation
  python validate_config.py --migrate         # Generate migration script
  python validate_config.py --fix-env         # Update .env with recommended values
"""

import os
from deep_researcher.config_validator import ConfigurationValidator, ConfigurationMode


def update_env_file(env_file_path: str = ".env"):
    """Update .env file with proper 4-model configuration."""
    print(f"Updating {env_file_path} with 4-model architecture...")
    
    # Read existing file
    existing_vars = {}
    if os.path.exists(env_file_path):
        with open(env_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    existing_vars[key] = value
    
    # Define new 4-model variables with fallbacks to legacy
    new_vars = {
        'PLANNER_MODEL_PROVIDER': existing_vars.get('PLANNER_MODEL_PROVIDER') or existing_vars.get('REASONING_MODEL_PROVIDER', 'local'),
        'PLANNER_MODEL': existing_vars.get('PLANNER_MODEL') or existing_vars.get('REASONING_MODEL', 'hermes3:8b'),
        'TOOL_CALLING_MODEL_PROVIDER': existing_vars.get('TOOL_CALLING_MODEL_PROVIDER', 'local'),
        'TOOL_CALLING_MODEL': existing_vars.get('TOOL_CALLING_MODEL', 'hf.co/NousResearch/Hermes-2-Pro-Llama-3-8B-GGUF:Q8_0'),
        'SUMMARISER_MODEL_PROVIDER': existing_vars.get('SUMMARISER_MODEL_PROVIDER') or existing_vars.get('MAIN_MODEL_PROVIDER', 'local'),
        'SUMMARISER_MODEL': existing_vars.get('SUMMARISER_MODEL') or existing_vars.get('MAIN_MODEL', 'qwen2.5-coder:latest'),
        'WRITER_MODEL_PROVIDER': existing_vars.get('WRITER_MODEL_PROVIDER') or existing_vars.get('FAST_MODEL_PROVIDER', 'local'),
        'WRITER_MODEL': existing_vars.get('WRITER_MODEL') or existing_vars.get('FAST_MODEL', 'llama3.2:latest')
    }
    
    # Read the full file content to preserve comments and structure
    lines = []
    if os.path.exists(env_file_path):
        with open(env_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    
    # Add 4-model section if not exists
    has_4model_section = any('4-Model Architecture' in line for line in lines)
    
    if not has_4model_section:
        lines.extend([
            '\n',
            '# ————————————————————\n',
            '# 4-Model Architecture Configuration\n',
            '# Replaces the legacy 3-model setup with role-specific assignments\n',
            '\n'
        ])
        
        for var, value in new_vars.items():
            lines.append(f'{var}={value}\n')
        
        lines.extend([
            '\n',
            '# Legacy variables (can be removed after migration):\n',
            '# REASONING_MODEL_PROVIDER -> PLANNER_MODEL_PROVIDER\n',
            '# REASONING_MODEL -> PLANNER_MODEL\n',
            '# MAIN_MODEL_PROVIDER -> SUMMARISER_MODEL_PROVIDER\n',
            '# MAIN_MODEL -> SUMMARISER_MODEL\n',
            '# FAST_MODEL_PROVIDER -> WRITER_MODEL_PROVIDER\n',
            '# FAST_MODEL -> WRITER_MODEL\n'
        ])
    
    # Write updated file
    with open(env_file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print(f"[SUCCESS] Updated {env_file_path} with 4-model configuration")
    print("Review the changes and remove legacy variables if desired.")


def main():
    """Main CLI interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate and fix 4-model architecture configuration")
    parser.add_argument("--mode", choices=['production', 'development', 'testing', 'legacy'],
                       default='production', help="Validation mode (default: production)")
    parser.add_argument("--migrate", action='store_true',
                       help="Generate migration script")
    parser.add_argument("--fix-env", action='store_true',
                       help="Update .env file with 4-model configuration")
    parser.add_argument("--env-file", default=".env",
                       help="Path to environment file (default: .env)")
    
    args = parser.parse_args()
    
    if args.fix_env:
        update_env_file(args.env_file)
        return
    
    mode = ConfigurationMode(args.mode)
    validator = ConfigurationValidator(mode)
    
    if args.migrate:
        migration_script = validator.generate_migration_script(args.env_file)
        script_path = "migrate_to_4model.sh"
        
        with open(script_path, 'w') as f:
            f.write(migration_script)
        
        print(f"[MIGRATION] Migration script generated: {script_path}")
        print("Run with: bash migrate_to_4model.sh")
        print("")
        print("Or use: python validate_config.py --fix-env")
        return
    
    print("[VALIDATION] 4-Model Architecture Configuration...")
    print("=" * 55)
    
    # Run validation
    is_valid = validator.validate_environment()
    print(validator.get_validation_report())
    
    if not is_valid:
        print("\n[SUGGESTIONS] Quick fixes:")
        print("  python validate_config.py --fix-env    # Update .env automatically")
        print("  python validate_config.py --migrate    # Generate migration script")
        print("  python validate_config.py --mode dev   # Use development mode")


if __name__ == "__main__":
    main()