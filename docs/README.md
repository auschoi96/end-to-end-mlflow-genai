# DC Assistant Demo - Documentation

This folder contains all documentation for deploying and configuring the DC Assistant demo.

## Quick Start - Read These 3 Files

### 1. 📦 [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
**Start here** - How to deploy the app

- Current status (what works, what doesn't)
- Quick deploy steps (5 minutes)
- Local development setup
- Troubleshooting

### 2. ⚙️ [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md)
**Configuration reference** - How to update experiment IDs and settings

- What was changed from email demo to DC Assistant
- Where experiment IDs are configured (`app.yaml`, `.env.local`)
- How to reconfigure for a different experiment
- Complete file reference map
- Common configuration scenarios

### 3. ✅ [TODO_REMAINING_WORK.md](TODO_REMAINING_WORK.md)
**Implementation TODO** - What backend work remains

- 8 API endpoints needed (with exact response formats)
- Preloaded demo data structure
- Validation script requirements
- Implementation priority and quick start
- Estimated effort for each task

## Documentation Structure

```
docs/
├── README.md                    # This file
├── DEPLOYMENT_GUIDE.md         # How to deploy
├── CONFIGURATION_GUIDE.md      # How to configure
├── TODO_REMAINING_WORK.md      # What's left to build
└── refs/                        # Reference materials
    ├── 05-JudgeAlignment.ipynb
    ├── 06-PromptOptimization.ipynb
    ├── Defensive Coordinator Chatbot Blog.pdf
    ├── MemAlign blog.txt
    └── mlflow side pane.png
```

## For Deployment

1. Read [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
2. Edit `app.yaml` with your experiment details
3. Push to git and create Databricks App

**Time**: 5 minutes

## For Configuration Changes

1. Read [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md)
2. Find the "How to Update for Your Experiment" section
3. Update environment variables as needed

**Time**: 5 minutes

## For Backend Implementation

1. Read [TODO_REMAINING_WORK.md](TODO_REMAINING_WORK.md)
2. Start with Phase 1: Create endpoints with hardcoded data
3. Follow the quick start guide

**Time**: 4-6 hours for fully functional demo

## Reference Materials

The `refs/` folder contains:
- MLflow notebooks showing judge alignment and prompt optimization
- Blog post about the DC Assistant use case
- MLflow UI screenshots
- MemAlign algorithm details

These are for understanding the use case and MLflow features being demonstrated.
