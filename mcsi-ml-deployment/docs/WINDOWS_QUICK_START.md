# AgriGuard Quick Start Guide for Windows

**Your Directory:** `C:\Users\artyb\OneDrive\Documents\PERSONAL\HES\AC215_E115\Project\agriguard\AgriGuard`

---

## 🚀 Three Ways to Set Up

### Option 1: Automated Setup (Easiest - 5 minutes)

1. **Download all files** from the outputs directory to a folder (e.g., `Downloads\agriguard_outputs`)

2. **Run PowerShell as Administrator**
   - Press Windows Key
   - Type "PowerShell"
   - Right-click "Windows PowerShell"
   - Select "Run as Administrator"

3. **Run the setup script:**
   ```powershell
   cd Downloads  # or wherever you saved the files
   .\setup_complete.ps1
   ```
   
4. **Done!** All files are organized. Jump to "Testing Locally" below.

---

### Option 2: Batch Script (Quick - 10 minutes)

1. **Download all files** to a folder

2. **Double-click** `setup_windows.bat`

3. **Manually copy files** following `FILE_ORGANIZATION_GUIDE.txt`

4. **Done!** Jump to "Testing Locally" below.

---

### Option 3: Manual Setup (Most Control - 20 minutes)

1. **Create directory structure:**
   ```cmd
   cd C:\Users\artyb\OneDrive\Documents\PERSONAL\HES\AC215_E115\Project\agriguard
   mkdir AgriGuard
   cd AgriGuard
   mkdir src tests models containers .github
   mkdir containers\mcsi_processing containers\model_training containers\model_serving
   mkdir containers\mcsi_processing\src containers\model_training\src containers\model_serving\src
   ```

2. **Copy files** according to `FILE_ORGANIZATION_GUIDE.txt`

3. **Done!** Continue to "Testing Locally" below.

---

## 🧪 Testing Locally (After Setup)

### 1. Open Command Prompt

```cmd
cd C:\Users\artyb\OneDrive\Documents\PERSONAL\HES\AC215_E115\Project\agriguard\AgriGuard
```

### 2. Create Virtual Environment

```cmd
python -m venv venv
```

### 3. Activate Virtual Environment

**Command Prompt:**
```cmd
venv\Scripts\activate.bat
```

**PowerShell:**
```powershell
venv\Scripts\Activate.ps1
```

**If PowerShell gives error:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 4. Install Dependencies

```cmd
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-test.txt
```

### 5. Test MCSI Calculator

```cmd
cd src
python mcsi_calculator.py
```

**Expected Output:**
```
Loading data for 2024-XX-XX to 2024-XX-XX...
Loaded XXXXX records
Processing 99 counties...
MCSI CALCULATION SUMMARY
========================
Average MCSI: XX.XX
High stress counties: X
```

### 6. Test Feature Builder

```cmd
python feature_builder.py
```

**Expected:** Takes 5-10 minutes, creates ~150 features

### 7. Run Tests

```cmd
cd ..
pytest tests\ -v
```

**Expected:** All tests pass (some may skip if no GCS access)

### 8. Test API Locally

```cmd
cd src
uvicorn api:app --reload --port 8080
```

**Then open browser:** http://localhost:8080  
**Test health:** http://localhost:8080/health

**Press Ctrl+C to stop**

---

## 🐳 Docker on Windows

### 1. Install Docker Desktop

- Download from: https://www.docker.com/products/docker-desktop/
- Install and restart computer
- Enable WSL 2 backend (recommended)

### 2. Build Containers

**Open Command Prompt in AgriGuard directory:**

```cmd
cd containers\mcsi_processing
docker build -t mcsi-processor:test .

cd ..\model_training
docker build -t model-training:test .

cd ..\model_serving
docker build -t model-serving:test .
```

### 3. Test Container

```cmd
docker run -p 8080:8080 model-serving:test
```

**Visit:** http://localhost:8080/health

---

## ☁️ Deploy to GCP

### 1. Install Google Cloud SDK

- Download: https://cloud.google.com/sdk/docs/install
- Run installer
- Restart terminal

### 2. Authenticate

```cmd
gcloud auth login
gcloud config set project agriguard-ac215
```

### 3. Deploy (Using Git Bash or WSL)

**Option A: Git Bash**
```bash
cd /c/Users/artyb/OneDrive/Documents/PERSONAL/HES/AC215_E115/Project/agriguard/AgriGuard
./deploy.sh all
```

**Option B: WSL (Windows Subsystem for Linux)**
```bash
cd /mnt/c/Users/artyb/OneDrive/Documents/PERSONAL/HES/AC215_E115/Project/agriguard/AgriGuard
./deploy.sh all
```

**Option C: Manual Deployment (PowerShell)**
```powershell
# Build and push containers
gcloud builds submit --tag gcr.io/agriguard-ac215/mcsi-processor containers/mcsi_processing
gcloud builds submit --tag gcr.io/agriguard-ac215/model-training containers/model_training
gcloud builds submit --tag gcr.io/agriguard-ac215/model-serving containers/model_serving

# Deploy Cloud Run services
gcloud run deploy mcsi-api --image gcr.io/agriguard-ac215/mcsi-processor --region us-central1
gcloud run deploy yield-prediction-api --image gcr.io/agriguard-ac215/model-serving --region us-central1
```

---

## 🔧 Common Windows Issues

### Issue: Python not found
**Solution:**
```cmd
# Check Python is installed
python --version

# If not installed, download from:
# https://www.python.org/downloads/
```

### Issue: pip not found
**Solution:**
```cmd
python -m ensurepip --upgrade
python -m pip install --upgrade pip
```

### Issue: Virtual environment activation fails (PowerShell)
**Solution:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
venv\Scripts\Activate.ps1
```

### Issue: Docker not working
**Solution:**
1. Install Docker Desktop
2. Enable Hyper-V in Windows Features
3. Or use WSL 2 backend (recommended)

### Issue: Line ending problems in Git
**Solution:**
```cmd
git config --global core.autocrlf true
```

### Issue: Long path issues
**Solution:** Enable long paths in Windows
```cmd
# Run as Administrator
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

---

## 📁 Verify Your Setup

**Check you have these files:**

```
AgriGuard\
├── README.md                          ✓
├── requirements.txt                   ✓
├── src\
│   ├── mcsi_calculator.py             ✓
│   ├── feature_builder.py             ✓
│   ├── train_model.py                 ✓
│   └── api.py                         ✓
├── tests\
│   ├── test_mcsi_calculator.py        ✓
│   └── test_feature_builder.py        ✓
└── containers\
    ├── mcsi_processing\Dockerfile     ✓
    ├── model_training\Dockerfile      ✓
    └── model_serving\Dockerfile       ✓
```

**Run this in PowerShell to check:**
```powershell
$BASE = "C:\Users\artyb\OneDrive\Documents\PERSONAL\HES\AC215_E115\Project\agriguard\AgriGuard"
@(
    "README.md",
    "src\mcsi_calculator.py",
    "src\feature_builder.py",
    "src\train_model.py",
    "src\api.py",
    "containers\mcsi_processing\Dockerfile",
    "containers\model_training\Dockerfile",
    "containers\model_serving\Dockerfile"
) | ForEach-Object {
    $path = Join-Path $BASE $_
    if (Test-Path $path) {
        Write-Host "✓ $_" -ForegroundColor Green
    } else {
        Write-Host "✗ $_" -ForegroundColor Red
    }
}
```

---

## 🎯 Next Steps

After setup is complete:

1. ✅ **Read:** `STEP_BY_STEP_GUIDE.md` for detailed instructions
2. ✅ **Test locally** using commands above
3. ✅ **Run tests** to ensure everything works
4. ✅ **Deploy to GCP** when ready
5. ✅ **Train model** after deployment

---

## 📞 Getting Help

**Documentation in your AgriGuard folder:**
- `INDEX.md` - Start here for navigation
- `README.md` - Package overview
- `IMPLEMENTATION_GUIDE.md` - System architecture
- `STEP_BY_STEP_GUIDE.md` - Detailed instructions
- `FILE_ORGANIZATION_GUIDE.txt` - Where files go

**Quick Commands Reference:**
```cmd
# Activate environment
venv\Scripts\activate

# Test MCSI
python src\mcsi_calculator.py

# Run tests
pytest tests\ -v

# Start API
uvicorn src.api:app --reload

# Build Docker
docker build -t test .

# Deploy to GCP
./deploy.sh all  (Git Bash/WSL)
```

---

## ✅ Quick Checklist

- [ ] Downloaded all files
- [ ] Ran setup script OR created structure manually
- [ ] Created virtual environment
- [ ] Installed dependencies
- [ ] Tested MCSI calculator locally
- [ ] Tests pass
- [ ] API works locally
- [ ] Docker installed (for deployment)
- [ ] GCloud CLI installed (for deployment)

---

**Estimated Time:** 30-60 minutes for complete setup and testing

**Next:** Open `STEP_BY_STEP_GUIDE.md` for detailed implementation!

---

*Created: November 16, 2025*  
*For: Windows environment*  
*Path: C:\Users\artyb\OneDrive\Documents\PERSONAL\HES\AC215_E115\Project\agriguard\AgriGuard*
