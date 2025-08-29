#!/usr/bin/env python3
"""
Kubernetes Job Update and Rerun Script

This script automates the process of:
1. Getting a job manifest from Kubernetes
2. Updating the image tag to 'latest'
3. Updating or adding any environment variable
4. Deleting the old job and creating a new one with updated configuration

Usage Examples:
    # Update image only
    python rerun_job.py --job-name myjob --namespace <namespace>
    
    # Update image and environment variable
    python rerun_job.py --job-name myjob --namespace <namespace> --env-var-name <var_name> --env-var-value <value>
    
    # Update any environment variable
    python rerun_job.py --job-name myjob --namespace default --env-var-name <var_name> --env-var-value <value>
    
    # Monitor job execution
    python rerun_job.py --job-name myjob --namespace <namespace> --env-var-name <var_name> --env-var-value <value> --monitor
"""

import argparse
from curses import meta
import subprocess
import sys
import yaml
import json
import tempfile
import os
from typing import Dict, Any, Optional


def run_kubectl_command(args: list, capture_output: bool = True) -> subprocess.CompletedProcess:
    """Run a kubectl command and return the result."""
    try:
        result = subprocess.run(['kubectl'] + args, capture_output=capture_output, text=True, check=True)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error running kubectl command: {' '.join(['kubectl'] + args)}")
        print(f"Error: {e}")
        sys.exit(1)


def get_job_manifest(job_name: str, namespace: str) -> Dict[str, Any]:
    """Get the current job manifest from Kubernetes."""
    print(f"Getting manifest for job '{job_name}' in namespace '{namespace}'...")
    
    result = run_kubectl_command(['get', 'job', job_name, '-n', namespace, '-o', 'yaml'])
    return yaml.safe_load(result.stdout)


def update_job_manifest(manifest: Dict[str, Any], env_var_name: str = None, env_var_value: str = None) -> Dict[str, Any]:
    """Update the job manifest with latest image tag and environment variable."""
    print("Updating job manifest...")
    
    # Find the container spec
    containers = manifest['spec']['template']['spec']['containers']
    if not containers:
        raise ValueError("No containers found in job manifest")
    
    container = containers[0]
    
    # Update image tag to latest
    current_image = container['image']
    if ':' in current_image:
        base_image = current_image.split(':')[0]
        container['image'] = f"{base_image}:latest"
        print(f"Updated image from '{current_image}' to '{container['image']}'")
    else:
        container['image'] = f"{current_image}:latest"
        print(f"Updated image to '{container['image']}'")
    
    # Update environment variable if specified
    if env_var_name and env_var_value:
        env_vars = container.get('env', [])
        target_env_var = None
        
        # Find the specified environment variable
        for env_var in env_vars:
            if env_var['name'] == env_var_name:
                target_env_var = env_var
                break
        
        if target_env_var:
            current_value = target_env_var['value']
            # Check if the value already exists (for space-separated values)
            if ' ' in current_value:
                values_list = current_value.split()
                if env_var_value not in values_list:
                    target_env_var['value'] = f"{current_value} {env_var_value}"
                    print(f"Updated {env_var_name} from '{current_value}' to '{target_env_var['value']}'")
                else:
                    print(f"Value '{env_var_value}' already exists in {env_var_name}")
            else:
                # Single value, replace it
                target_env_var['value'] = env_var_value
                print(f"Updated {env_var_name} from '{current_value}' to '{env_var_value}'")
        else:
            # Environment variable doesn't exist, add it
            new_env_var = {'name': env_var_name, 'value': env_var_value}
            container['env'].append(new_env_var)
            print(f"Added new environment variable {env_var_name} with value '{env_var_value}'")
    
    # Clean up metadata for recreation
    if 'metadata' in manifest:
        # Remove fields that would prevent recreation
        metadata = manifest['metadata']
        metadata.pop('creationTimestamp', None)
        metadata.pop('resourceVersion', None)
        metadata.pop('uid', None)
        metadata.pop('generation', None)
        metadata.pop('labels',None)
        metadata = manifest['spec']['template']['metadata']
        metadata.pop('labels',None)
        metadata = manifest['spec']
        metadata.pop('selector',None)
        metadata = manifest['metadata']
        # Clean up annotations
        if 'annotations' in metadata:
            metadata['annotations'].pop('kubectl.kubernetes.io/last-applied-configuration', None)
    
    # Remove status section
    manifest.pop('status', None)
    
    manifest.pop('matchLabels',None)
    manifest.pop('selector',None)
    return manifest


def delete_job(job_name: str, namespace: str) -> None:
    """Delete the existing job."""
    print(f"Deleting existing job '{job_name}'...")
    run_kubectl_command(['delete', 'job', job_name, '-n', namespace], capture_output=False)


def apply_job_manifest(manifest: Dict[str, Any], namespace: str) -> None:
    """Apply the updated job manifest."""
    print(f"Applying updated job manifest to namespace '{namespace}'...")
    
    # Convert to YAML
    yaml_content = yaml.dump(manifest, default_flow_style=False)
    
    # Create a temporary file to store the manifest
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
        temp_file.write(yaml_content)
        temp_file_path = temp_file.name
    
    try:
        # Apply using kubectl with the temporary file
        result = run_kubectl_command(['apply', '-f', temp_file_path, '-n', namespace], capture_output=False)
        print("Job manifest applied successfully")
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


def check_job_status(job_name: str, namespace: str, timeout_minutes: int = 10) -> None:
    """Check and monitor job status."""
    print(f"Monitoring job status for up to {timeout_minutes} minutes...")
    
    import time
    start_time = time.time()
    timeout_seconds = timeout_minutes * 60
    
    while time.time() - start_time < timeout_seconds:
        result = run_kubectl_command(['get', 'job', job_name, '-n', namespace, '-o', 'json'])
        job_status = json.loads(result.stdout)
        
        status = job_status.get('status', {})
        completions = status.get('succeeded', 0)
        failed = status.get('failed', 0)
        active = status.get('active', 0)
        
        print(f"Status: {completions} completed, {failed} failed, {active} active")
        
        if completions > 0:
            print("✅ Job completed successfully!")
            return
        elif failed > 0:
            print("❌ Job failed!")
            return
        
        time.sleep(10)
    
    print(f"⏰ Timeout reached ({timeout_minutes} minutes). Job may still be running.")


def main():
    parser = argparse.ArgumentParser(description='Update and rerun a Kubernetes job with latest image and environment variable')
    parser.add_argument('--job-name', required=True, help='Name of the job to update')
    parser.add_argument('--namespace', required=True, help='Namespace of the job')
    parser.add_argument('--env-var-name', required=False, help='Name of the environment variable to update (e.g., CUSTOMER_INDEXES)')
    parser.add_argument('--env-var-value', required=False, help='Value to set for the environment variable')
    parser.add_argument('--monitor', action='store_true', help='Monitor job status after creation')
    parser.add_argument('--timeout', type=int, default=10, help='Timeout in minutes for job monitoring')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without executing')
    
    args = parser.parse_args()
    
    # Validate environment variable arguments
    if args.env_var_name and not args.env_var_value:
        print("❌ Error: --env-var-name requires --env-var-value")
        sys.exit(1)
    if args.env_var_value and not args.env_var_name:
        print("❌ Error: --env-var-value requires --env-var-name")
        sys.exit(1)
    
    print(f"🚀 Starting job update process...")
    print(f"Job: {args.job_name}")
    print(f"Namespace: {args.namespace}")
    if args.env_var_name and args.env_var_value:
        print(f"Environment Variable: {args.env_var_name} = {args.env_var_value}")
    else:
        print(f"Environment Variable: None (only updating image to latest)")
    print(f"Dry Run: {args.dry_run}")
    print("-" * 50)
    
    try:
        # Get current job manifest
        manifest = get_job_manifest(args.job_name, args.namespace)
        
        # Update manifest
        updated_manifest = update_job_manifest(manifest, args.env_var_name, args.env_var_value)
        
        if args.dry_run:
            print("\n📋 DRY RUN - Updated manifest:")
            print(yaml.dump(updated_manifest, default_flow_style=False))
            print("Dry run completed. No changes were made.")
            return
        
        # Delete existing job
        delete_job(args.job_name, args.namespace)
        
        # Apply updated manifest
        apply_job_manifest(updated_manifest, args.namespace)
        
        print(f"\n✅ Job '{args.job_name}' has been successfully updated and started!")
        
        # Monitor job status if requested
        if args.monitor:
            check_job_status(args.job_name, args.namespace, args.timeout)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 