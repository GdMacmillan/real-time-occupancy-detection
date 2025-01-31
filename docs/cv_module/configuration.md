# CV Module Configuration

## Overview
The CV module uses a hierarchical configuration system with the following priority (highest to lowest):

1. Environment variables (`.env`)
2. Environment-specific config (`development.yaml`, `production.yaml`)
3. Default config (`default.yaml`)
4. Shared config (`shared.yaml`)

## Directory Structure
```
cv_module/
├── config/
│   ├── default.yaml        # Base configuration
│   ├── development.yaml    # Development overrides
│   └── production.yaml     # Production overrides
├── .env.example        # Environment variables template
```

## Configuration Files

### Default Configuration (default.yaml)
```yaml
service:
  host: "localhost"
  port: 8765
  log_dir: "logs/dev"

camera:
  type: "webcam"
  params:
    camera_id: 0
    resolution:
      width: 640
      height: 480
    fps: 30

detector:
  type: "yolo"
  model:
    name: "yolov8n.pt"
    confidence_threshold: 0.4
    verbose: false
    summary_interval: 30
    params:
      iou_threshold: 0.45
      max_det: 300

websocket:
  max_clients: 10
  message_queue_size: 100
  ping_interval: 30
  ping_timeout: 10
```

### Environment-Specific Configuration
Development (`development.yaml`) and production (`production.yaml`) configurations override specific values from the default configuration.

Example production overrides:
```yaml
service:
  host: "0.0.0.0"
  log_dir: "logs/prod"

camera:
  type: "realsense"
  params:
    resolution:
      width: 1280
      height: 720

detector:
  model:
    name: "yolov8m.pt"
    confidence_threshold: 0.5
```

### Environment Variables (.env)
Environment variables can override any configuration value. Available variables:

| Variable | Description | Default |
|----------|-------------|---------|
| CV_MODULE_ENV | Environment name | development |
| CV_MODULE_HOST | Service host | localhost |
| CV_MODULE_PORT | Service port | 8765 |
| CV_MODULE_CAMERA_TYPE | Camera type | webcam |
| CV_MODULE_CAMERA_ID | Camera device ID | 0 |
| CV_MODULE_MODEL_NAME | YOLO model name | yolov8n.pt |
| CV_MODULE_MODEL_CONFIDENCE | Detection confidence | 0.4 |
| CV_MODULE_LOG_LEVEL | Logging level | INFO |
| CV_MODULE_LOG_DIR | Log directory | logs/dev |

## Usage

```python
from cv_module.config import ConfigLoader

# Load configuration
config_loader = ConfigLoader()
config = config_loader.load_config()

# Access configuration
camera_type = config['camera']['type']
model_path = config['detector']['model']['name']
```

## Best Practices
1. Never commit `.env` files to version control
2. Use `.env.example` as a template
3. Keep sensitive information in environment variables
4. Document all configuration changes
5. Test configuration changes in development first 