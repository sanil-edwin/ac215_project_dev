# AgriGuard MCSI + ML Model - Deployment Package

**Created:** November 16, 2025  
**Location:** `C:\Users\artyb\OneDrive\Documents\PERSONAL\HES\AC215_E115\Project\agriguard\AgriGuard\mcsi-ml-deployment`

---

## 📁 What's Inside

This folder contains everything needed to deploy the AgriGuard MCSI and ML model system:

```
mcsi-ml-deployment/
├── src/                    # Source code
├── tests/                  # Unit tests
├── containers/             # Docker configurations
├── docs/                   # Documentation
├── scripts/                # Helper scripts
├── config/                 # Configuration files
├── models/                 # Trained models (after training)
└── venv/                   # Python virtual environment (after setup)
```

---

## 🚀 Quick Start (4 Steps)

### Step 1: Organize Files (5 min)
```bash
cd mcsi-ml-deployment
bash organize_files.sh
```

### Step 2: Setup Python Environment (5 min)
```bash
bash setup_python_env.sh
```

### Step 3: Test Locally (10 min)
```bash
bash run_tests.sh
```

### Step 4: Deploy to GCP (60 min)
```bash
# Authenticate
gcloud auth login
gcloud config set project agriguard-ac215

# Deploy
bash deploy.sh all
```

---

## 📚 Documentation

All documentation is in the `docs/` folder:

- **START HERE:** `docs/INDEX.md`
- **System Overview:** `docs/IMPLEMENTATION_GUIDE.md`
- **Step-by-Step:** `docs/STEP_BY_STEP_GUIDE.md`
- **Windows Setup:** `docs/WINDOWS_QUICK_START.md`

---

## 🔧 Helper Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `organize_files.sh` | Copy files from prep/ | `bash organize_files.sh` |
| `setup_python_env.sh` | Create venv and install deps | `bash setup_python_env.sh` |
| `run_tests.sh` | Run all tests | `bash run_tests.sh` |
| `verify_deployment.sh` | Check setup | `bash verify_deployment.sh` |
| `deploy.sh` | Deploy to GCP | `bash deploy.sh all` |

---

## ✅ Verification Checklist

After running organize_files.sh:
- [ ] All source files in src/
- [ ] All tests in tests/
- [ ] All Dockerfiles in containers/
- [ ] Documentation in docs/

After running setup_python_env.sh:
- [ ] venv/ directory exists
- [ ] Dependencies installed
- [ ] Can import pandas, lightgbm, etc.

After running run_tests.sh:
- [ ] MCSI calculator works
- [ ] Feature builder works
- [ ] Unit tests pass

After deployment:
- [ ] Services deployed to Cloud Run
- [ ] APIs responding
- [ ] Scheduled jobs configured

---

## 🆘 Need Help?

1. **File organization:** See `FILE_PLACEMENT_GUIDE.txt`
2. **Setup issues:** See `docs/WINDOWS_QUICK_START.md`
3. **Deployment:** See `docs/STEP_BY_STEP_GUIDE.md`

---

## 📞 Support

For questions or issues, refer to the documentation in `docs/` or check:
- `docs/IMPLEMENTATION_GUIDE.md` - Architecture
- `docs/STEP_BY_STEP_GUIDE.md` - Detailed instructions

---

*Deployment package created: November 16, 2025*
