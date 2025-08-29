#!/usr/bin/env python3
"""
Kubernetes StatefulSet Management Script

This script automates the process of:
1. Getting a StatefulSet manifest from Kubernetes and creating a backup
2. Cleaning the manifest by removing Kubernetes-generated fields
3. Allowing modification of persistent volume size
4. Deleting the StatefulSet with non-cascading behavior (pods remain)
5. Running in dry-run mode for safety

Usage:
    python manage_statefulset.py --statefulset-name prod-cid1025-data --namespace default --dry-run
"""

import argparse
import subprocess
import sys
import yaml
import json
import tempfile
import os
from typing import Dict, Any, Optional
from datetime import datetime


def run_kubectl_command(args: list, capture_output: bool = True) -> subprocess.CompletedProcess:
    """Run a kubectl command and return the result."""
    try:
        result = subprocess.run(['kubectl'] + args, capture_output=capture_output, text=True, check=True)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error running kubectl command: {' '.join(['kubectl'] + args)}")
        print(f"Error: {e}")
        sys.exit(1)


def get_statefulset_manifest(statefulset_name: str, namespace: str) -> Dict[str, Any]:
    """Get the current StatefulSet manifest from Kubernetes."""
    print(f"Getting manifest for StatefulSet '{statefulset_name}' in namespace '{namespace}'...")
    
    result = run_kubectl_command(['get', 'statefulset', statefulset_name, '-n', namespace, '-o', 'yaml'])
    return yaml.safe_load(result.stdout)


def create_backup(manifest: Dict[str, Any], statefulset_name: str, namespace: str) -> str:
    """Create a backup of the StatefulSet manifest."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"{statefulset_name}_{namespace}_{timestamp}_backup.yaml"
    
    print(f"Creating backup: {backup_filename}")
    
    with open(backup_filename, 'w') as backup_file:
        yaml.dump(manifest, backup_file, default_flow_style=False)
    
    print(f"✅ Backup created successfully: {backup_filename}")
    return backup_filename


def clean_manifest(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Clean the manifest by removing Kubernetes-generated fields."""
    print("Cleaning manifest by removing Kubernetes-generated fields...")
    
    # Create a deep copy to avoid modifying the original
    cleaned_manifest = yaml.safe_load(yaml.dump(manifest))
    
    # Clean metadata
    if 'metadata' in cleaned_manifest:
        metadata = cleaned_manifest['metadata']
        # Remove fields that would prevent recreation
        metadata.pop('creationTimestamp', None)
        metadata.pop('resourceVersion', None)
        metadata.pop('uid', None)
        metadata.pop('generation', None)
        metadata.pop('managedFields', None)
        
        # Clean up annotations
        if 'annotations' in metadata:
            annotations = metadata['annotations']
            annotations.pop('kubectl.kubernetes.io/last-applied-configuration', None)
            annotations.pop('deployment.kubernetes.io/revision', None)
            annotations.pop('kubernetes.io/change-cause', None)
            
            # Remove empty annotations section
            if not annotations:
                metadata.pop('annotations')
    
    # Clean spec.template.metadata
    if 'spec' in cleaned_manifest and 'template' in cleaned_manifest['spec']:
        template_metadata = cleaned_manifest['spec']['template'].get('metadata', {})
        template_metadata.pop('creationTimestamp', None)
        template_metadata.pop('resourceVersion', None)
        template_metadata.pop('uid', None)
        template_metadata.pop('generation', None)
        template_metadata.pop('managedFields', None)
        
        # Clean up template annotations
        if 'annotations' in template_metadata:
            template_annotations = template_metadata['annotations']
            template_annotations.pop('kubectl.kubernetes.io/last-applied-configuration', None)
            template_annotations.pop('deployment.kubernetes.io/revision', None)
            template_annotations.pop('kubernetes.io/change-cause', None)
            
            # Remove empty annotations section
            if not template_annotations:
                template_metadata.pop('annotations')
    
    # Clean spec
    if 'spec' in cleaned_manifest:
        spec = cleaned_manifest['spec']
        spec.pop('currentReplicas', None)
        spec.pop('updatedReplicas', None)
        spec.pop('readyReplicas', None)
        spec.pop('availableReplicas', None)
        spec.pop('observedGeneration', None)
        spec.pop('collisionCount', None)
        spec.pop('conditions', None)
    
    # Remove status section completely
    cleaned_manifest.pop('status', None)
    
    print("✅ Manifest cleaned successfully")
    return cleaned_manifest


def update_persistent_volume_size(manifest: Dict[str, Any], new_size: str) -> Dict[str, Any]:
    """Update the persistent volume size in the StatefulSet manifest."""
    print(f"Updating persistent volume size to: {new_size}")
    
    # Create a deep copy
    updated_manifest = yaml.safe_load(yaml.dump(manifest))
    
    # Find and update PVC templates
    if 'spec' in updated_manifest and 'volumeClaimTemplates' in updated_manifest['spec']:
        volume_claim_templates = updated_manifest['spec']['volumeClaimTemplates']
        
        for template in volume_claim_templates:
            if 'spec' in template and 'resources' in template['spec']:
                resources = template['spec']['resources']
                if 'requests' in resources and 'storage' in resources['requests']:
                    old_size = resources['requests']['storage']
                    resources['requests']['storage'] = new_size
                    print(f"Updated PVC template storage from '{old_size}' to '{new_size}'")
    
    # Also check for any inline volume definitions
    if 'spec' in updated_manifest and 'template' in updated_manifest['spec']:
        template = updated_manifest['spec']['template']
        if 'spec' in template and 'volumes' in template['spec']:
            volumes = template['spec']['volumes']
            for volume in volumes:
                if 'persistentVolumeClaim' in volume:
                    pvc = volume['persistentVolumeClaim']
                    if 'claimName' in pvc:
                        print(f"Found inline PVC reference: {pvc['claimName']}")
                        print("Note: Inline PVCs need to be updated separately")
    
    print("✅ Persistent volume size updated successfully")
    return updated_manifest


def delete_statefulset_non_cascading(statefulset_name: str, namespace: str, dry_run: bool = False) -> None:
    """Delete the StatefulSet with non-cascading behavior (pods remain)."""
    print(f"Deleting StatefulSet '{statefulset_name}' with non-cascading behavior...")
    
    if dry_run:
        print("🔍 DRY RUN: Would delete StatefulSet with --cascade=false")
        return
    
    # Use --cascade=false to keep pods running
    run_kubectl_command(['delete', 'statefulset', statefulset_name, '-n', namespace, '--cascade=false'], capture_output=False)
    print(f"✅ StatefulSet '{statefulset_name}' deleted successfully (pods remain running)")


def apply_statefulset_manifest(manifest: Dict[str, Any], namespace: str) -> None:
    """Apply the updated StatefulSet manifest."""
    print(f"Applying updated StatefulSet manifest to namespace '{namespace}'...")
    
    # Convert to YAML
    yaml_content = yaml.dump(manifest, default_flow_style=False)
    
    # Create a temporary file to store the manifest
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
        temp_file.write(yaml_content)
        temp_file_path = temp_file.name
    
    try:
        # Apply using kubectl with the temporary file
        result = run_kubectl_command(['apply', '-f', temp_file_path, '-n', namespace], capture_output=False)
        print("✅ StatefulSet manifest applied successfully")
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


def get_current_pods(statefulset_name: str, namespace: str) -> list:
    """Get current pods associated with the StatefulSet."""
    print(f"Getting current pods for StatefulSet '{statefulset_name}'...")
    
    result = run_kubectl_command(['get', 'pods', '-n', namespace, '-l', f'app={statefulset_name}', '-o', 'json'])
    pods = json.loads(result.stdout)
    
    pod_names = [pod['metadata']['name'] for pod in pods['items']]
    print(f"Found {len(pod_names)} pods: {', '.join(pod_names)}")
    
    return pod_names


def main():
    parser = argparse.ArgumentParser(description='Manage Kubernetes StatefulSet with backup and non-cascading deletion')
    parser.add_argument('--statefulset-name', required=True, help='Name of the StatefulSet to manage')
    parser.add_argument('--namespace', required=True, help='Namespace of the StatefulSet')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without executing')
    parser.add_argument('--new-pv-size', help='New persistent volume size (e.g., 100Gi)')
    
    args = parser.parse_args()
    
    print(f"🚀 Starting StatefulSet management process...")
    print(f"StatefulSet: {args.statefulset_name}")
    print(f"Namespace: {args.namespace}")
    print(f"Dry Run: {args.dry_run}")
    if args.new_pv_size:
        print(f"New PV Size: {args.new_pv_size}")
    print("-" * 50)
    
    try:
        # Get current StatefulSet manifest
        manifest = get_statefulset_manifest(args.statefulset_name, args.namespace)
        
        # Create backup
        backup_filename = create_backup(manifest, args.statefulset_name, args.namespace)
        
        # Clean the manifest
        cleaned_manifest = clean_manifest(manifest)
        
        # Get current pods
        current_pods = get_current_pods(args.statefulset_name, args.namespace)
        
        # Ask for new PV size if not provided
        new_pv_size = args.new_pv_size
        if not new_pv_size:
            new_pv_size = input("Enter new persistent volume size (e.g., 100Gi): ").strip()
            if not new_pv_size:
                print("No PV size provided, keeping original size")
                new_pv_size = None
        
        # Update PV size if specified
        if new_pv_size:
            cleaned_manifest = update_persistent_volume_size(cleaned_manifest, new_pv_size)
        
        # Show cleaned manifest
        print("\n📋 Cleaned manifest:")
        print(yaml.dump(cleaned_manifest, default_flow_style=False))
        
        if args.dry_run:
            print("\n🔍 DRY RUN MODE - No changes will be made")
            print("Actions that would be performed:")
            print(f"1. ✅ Backup created: {backup_filename}")
            print(f"2. ✅ Manifest cleaned and PV size updated to: {new_pv_size or 'original'}")
            print(f"3. 🔍 Would delete StatefulSet '{args.statefulset_name}' with --cascade=false")
            print(f"4. 🔍 Would apply cleaned manifest with new configuration")
            print(f"5. 🔍 Pods would remain running: {', '.join(current_pods)}")
            print("\nDry run completed. No changes were made.")
            return
        
        # Confirm before proceeding
        print(f"\n⚠️  WARNING: This will delete StatefulSet '{args.statefulset_name}' while keeping pods running!")
        print(f"Pods that will remain: {', '.join(current_pods)}")
        confirm = input("Are you sure you want to proceed? (yes/no): ").strip().lower()
        
        if confirm != 'yes':
            print("Operation cancelled by user")
            return
        
        # Delete StatefulSet (non-cascading)
        delete_statefulset_non_cascading(args.statefulset_name, args.namespace, args.dry_run)
        
        # Apply the cleaned manifest
        apply_statefulset_manifest(cleaned_manifest, args.namespace)
        
        print(f"\n✅ StatefulSet management completed successfully!")
        print(f"Backup saved as: {backup_filename}")
        print(f"StatefulSet deleted and recreated with new configuration")
        print(f"Pods remain running: {', '.join(current_pods)}")
        print(f"New persistent volume size: {new_pv_size or 'original'}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
