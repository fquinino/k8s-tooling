# 🚀 Kubernetes Management Tools

A collection of powerful Python scripts for managing Kubernetes resources, with a focus on solving common operational challenges and limitations.

## 🎯 What This Repository Solves

Kubernetes has some inherent limitations that can make certain operations challenging in production environments:

- **StatefulSets can't change disk size** after creation
- **Jobs need manual recreation** for configuration updates
- **Complex resource management** requires multiple kubectl commands
- **No built-in backup/restore** for resource configurations

This repository provides production-ready solutions for these challenges.

## 🛠️ Tools Included

### 1. **StatefulSet Disk Size Manager** (`manage_statefulset.py`)
**Solves**: StatefulSet storage size limitations

**What it does**:
- Creates automatic backups of StatefulSet configurations
- Deletes StatefulSet controller while keeping pods running
- Reapplies configuration with new persistent volume sizes
- Maintains data integrity and service continuity

**Use case**: Increase OpenSearch/PostgreSQL storage without downtime

### 2. **Job Update & Rerun Manager** (`update_and_rerun_job.py`)
**Solves**: Manual job recreation for configuration changes

**What it does**:
- Updates container images to latest versions
- Modifies environment variables (e.g., CUSTOMER_INDEXES)
- Automatically deletes old jobs and creates new ones
- Monitors job execution status

**Use case**: Update data processing jobs with new configurations

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- `kubectl` configured and accessible
- Access to target Kubernetes cluster

### Installation
```bash
# Clone the repository
git clone <repository-url>
cd kubernetes-management-tools

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Basic Usage

#### StatefulSet Disk Size Management
```bash
# Test run (safe)
python manage_statefulset.py \
  --statefulset-name <name> \
  --namespace <namespace> \
  --dry-run

# Actual execution
python manage_statefulset.py \
  --statefulset-name <name> \
  --namespace <namespace> \
  --new-pv-size 500Gi
```

#### Job Update & Rerun
```bash
# Update job with new index
python update_and_rerun_job.py \
  --job-name <job_name> \
  --namespace <name_space> \
  --new-index <index_name>

# Monitor job execution
python rerun_job.py \
  --job-name kickstart \
  --namespace opensearch \
  --monitor
```

## 📚 Detailed Documentation

- **[StatefulSet Management Guide](sts_resizer.md)** - Comprehensive explanation of StatefulSet limitations and solutions
- **[Job Management Guide](rerun_job.py)** - Job update and monitoring capabilities

## 🔧 How It Works

### StatefulSet Management Process
1. **Backup Creation** → Timestamped YAML backup
2. **Manifest Cleaning** → Remove Kubernetes runtime fields
3. **Non-Cascading Deletion** → Delete controller, keep pods running
4. **Configuration Update** → Modify persistent volume size
5. **Manifest Reapplication** → Apply updated configuration

### Job Management Process
1. **Manifest Retrieval** → Get current job configuration
2. **Configuration Update** → Update image tags and environment variables
3. **Resource Cleanup** → Remove old job
4. **New Job Creation** → Apply updated configuration
5. **Status Monitoring** → Track job execution progress

## 🎯 Use Cases

### Production Scenarios
- **Database Storage Expansion**: Increase PostgreSQL/MySQL storage without downtime
- **Search Engine Scaling**: Expand OpenSearch/Elasticsearch data node storage
- **Data Pipeline Updates**: Modify job configurations for new data sources
- **Configuration Management**: Update resource configurations across environments

### Development Scenarios
- **Local Development**: Test configuration changes before production
- **CI/CD Integration**: Automate resource updates in deployment pipelines
- **Testing**: Validate configuration changes in test environments

## 🚨 Safety Features

### Built-in Protections
- **Dry-Run Mode**: Test all operations before execution
- **Automatic Backups**: Timestamped backup files for every operation
- **User Confirmation**: Explicit confirmation required for destructive operations
- **Error Handling**: Comprehensive error checking and graceful failure handling
- **Rollback Ready**: Full backup available for quick restoration

### Best Practices
- Always test with `--dry-run` first
- Run in test environments before production
- Keep backup files accessible
- Monitor operations in real-time
- Have rollback procedures ready

## 🔍 Troubleshooting

### Common Issues

#### StatefulSet Not Found
```bash
# Check all namespaces
kubectl get statefulsets --all-namespaces | grep <name>

# Verify namespace
kubectl get statefulsets -n <namespace>
```

#### Permission Errors
```bash
# Check RBAC permissions
kubectl auth can-i delete statefulsets -n <namespace>
kubectl auth can-i create statefulsets -n <namespace>
```

#### Pod Termination Issues
```bash
# Verify non-cascading deletion
kubectl get pods -n <namespace> -l app=<statefulset-name>

# Check StatefulSet status
kubectl get statefulset <name> -n <namespace> -o yaml
```

### Recovery Procedures
```bash
# Restore from backup
kubectl apply -f <backup_file.yaml>

# Check resource status
kubectl get all -n <namespace>

# Verify data integrity
kubectl exec -it <pod-name> -n <namespace> -- <command>
```

## 🏗️ Architecture

### Script Structure
```
k8s-tooling/
├── sts_resizer.py
├── rerun_job.py
├── requirements.txt
├── README.md
└── docs/
    ├── sts_resizer.md
    └── rerun_job.py
```

### Dependencies
- **PyYAML**: YAML parsing and generation
- **subprocess**: Kubernetes command execution
- **argparse**: Command-line argument parsing
- **datetime**: Timestamp generation for backups

## 🤝 Contributing

### Development Setup
```bash
# Fork the repository
git clone <your-fork-url>
cd kubernetes-management-tools

# Create feature branch
git checkout -b feature/new-tool

# Make changes and test
python manage_statefulset.py --help

# Commit and push
git commit -m "Add new feature"
git push origin feature/new-tool
```

### Code Standards
- Follow PEP 8 Python style guidelines
- Add comprehensive docstrings
- Include error handling for all operations
- Test with `--dry-run` mode
- Update documentation for new features

### Testing
```bash
# Run in dry-run mode
python manage_statefulset.py --dry-run

# Test with different namespaces
python manage_statefulset.py -n test-namespace --dry-run

# Validate backup creation
ls -la *_backup.yaml
```

## 📋 Roadmap

### Planned Features
- [ ] **Deployment Manager**: Update deployment configurations
- [ ] **ConfigMap Synchronizer**: Sync ConfigMaps across namespaces
- [ ] **Secret Rotator**: Automated secret rotation
- [ ] **Resource Monitor**: Real-time resource monitoring
- [ ] **Backup Manager**: Automated backup scheduling

### Enhancement Ideas
- **Web UI**: Browser-based management interface
- **API Endpoints**: REST API for tool integration
- **Multi-Cluster Support**: Manage multiple Kubernetes clusters
- **Audit Logging**: Comprehensive operation logging
- **Integration Hooks**: Webhook support for external systems

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

**Important**: These tools perform operations on Kubernetes clusters that can affect production workloads. Always:

1. Test in non-production environments first
2. Use `--dry-run` mode to preview changes
3. Ensure you have proper backups
4. Follow your organization's change management procedures
5. Have rollback procedures ready

## 🆘 Support

### Getting Help
- **Issues**: Create GitHub issues for bugs or feature requests
- **Documentation**: Check the detailed guides in this repository
- **Examples**: Review the example configurations
- **Testing**: Always test with dry-run mode first

### Community
- **Discussions**: Use GitHub Discussions for questions
- **Contributions**: Pull requests welcome for improvements
- **Feedback**: Share your use cases and success stories

---

**Made with ❤️ for Kubernetes operators who need practical solutions to real-world problems.**
