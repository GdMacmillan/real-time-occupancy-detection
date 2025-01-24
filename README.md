# Real-Time Occupancy Detection System with iOS Integration
## Project Architecture and Implementation Guide

## 1. System Architecture

### 1.1 Computer Vision Module (Python)
- **Core Components:**
  - Real-time video capture (OpenCV/RealSense)
  - Person detection model (YOLOv8)
  - WebSocket server for real-time communication
  - Configuration management system
- **Key Features:**
  - Frame processing pipeline
  - Model inference optimization
  - Detection event management
  - Environment-based configuration
  - Performance monitoring
- **Sub-modules:**
  - `camera.py`: Camera abstraction for WebCam and RealSense
  - `detector.py`: Person detection with YOLO models
  - `websocket_server.py`: Real-time event broadcasting
  - `config.py`: Configuration management
  - `service.py`: Main service orchestration
- **Dependencies:**
  - opencv-python
  - pyrealsense2 (optional)
  - ultralytics
  - numpy
  - websockets
  - pydantic
  - python-dotenv
  - PyYAML

### 1.2 Backend Server (FastAPI)
- **Core Components:**
  - RESTful API endpoints
  - WebSocket handler
  - Data persistence layer
- **Key Features:**
  - Authentication and security
  - Event logging
  - Configuration management
- **Dependencies:**
  - fastapi
  - uvicorn
  - sqlalchemy
  - pydantic

### 1.3 iOS Application (Swift)
- **Core Components:**
  - SwiftUI interface
  - WebSocket client
  - Local notification system
- **Key Features:**
  - Real-time alerts
  - Configuration interface
  - Historical data visualization
- **Dependencies:**
  - SwiftUI
  - Starscream (WebSocket)
  - CoreData

## 2. Technical Implementation Details

### 2.1 Project Structure

```
occupancy-detection/
├── src/
│ ├── cv_module/
│ │ ├── camera.py
│ │ ├── detector.py
│ │ └── websocket_server.py
│ ├── backend/
│ │ ├── api/
│ │ ├── models/
│ │ └── services/
│ └── ios_app/
│   ├── Views/
│   ├── Models/
│   └── Services/
├── notebooks/
│ ├── 01_camera_setup.ipynb
│ ├── 02_model_testing.ipynb
│ └── 03_performance_analysis.ipynb
├── tests/
├── config/
└── requirements.txt
```

### 2.1 Configuration Management

The project uses a hierarchical configuration system with environment-specific profiles. Configuration files are stored in the `config/` directory.

#### CV Module Configuration Structure
```yaml
# config/service_config_development.yaml
service:
  host: "localhost"
  port: 8765
  log_dir: "logs/dev"  # Will be created automatically if it doesn't exist

camera:
  type: "webcam"  # or "realsense"
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
    params:
      iou_threshold: 0.45
      max_det: 300

websocket:
  max_clients: 10
  message_queue_size: 100
  ping_interval: 30
  ping_timeout: 10
```

#### Directory Structure
```
occupancy-detection/
├── config/
│   ├── service_config_development.yaml
│   └── service_config_production.yaml
├── logs/
│   ├── dev/    # Created automatically for development profile
│   └── prod/   # Created automatically for production profile
```

#### Environment Variables
Configuration can be overridden using environment variables:
```bash
OCCUPANCY_PROFILE=development
OCCUPANCY_WEBSOCKET_HOST=localhost
OCCUPANCY_CAMERA_ID=0
```

## 3. Development Phases

### Phase 1: Core CV System Setup
- **Objectives:**
  1. Set up development environment
  2. Test basic camera input and person detection
  3. Test service and configuration system

- **Deliverables:**
  - Working camera setup notebook
  - Person detection testing notebook
  - Initial CV module implementation:
    - Camera abstraction layer
    - Detection pipeline
    - WebSocket server
    - Configuration system
  - Basic service functionality
  - Development and production configurations

- **Testing:**
  1. Run camera setup notebook (`01_camera_setup.ipynb`)
  2. Run model testing notebook (`02_model_testing.ipynb`)
  3. Test service with development configuration:
     ```bash
     # Set up environment
     cp .env.template .env
     # Edit .env as needed

     # Run service
     python -m src.cv_module.service
     ```

### Phase 2: Backend Development
- **Objectives:**
  1. Create FastAPI server
  2. Implement WebSocket endpoints
  3. Set up database schema
  4. Create API documentation

- **Deliverables:**
  - Running API server
  - WebSocket communication
  - Database integration
  - API documentation

### Phase 3: iOS Application
- **Objectives:**
  1. Set up iOS development environment
  2. Create basic UI
  3. Implement WebSocket client
  4. Add notification system

- **Deliverables:**
  - Working iOS application
  - Real-time notifications
  - Basic configuration interface
  - Historical data view

### Phase 4: Integration and Testing
- **Objectives:**
  1. End-to-end system testing
  2. Performance optimization
  3. Cross-domain testing
  4. Bug fixing and refinement

- **Deliverables:**
  - Integrated system
  - Performance reports
  - Test documentation
  - Deployment guide

## 4. Getting Started

1. Clone the repository
2. Create a Python virtual environment
3. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up configuration:
   ```bash
   # Copy configuration templates
   cp config/service_config_development.yaml.template config/service_config_development.yaml
   cp config/service_config_production.yaml.template config/service_config_production.yaml
   cp .env.template .env

   # Edit configurations as needed
   # The service will automatically create required directories
   ```
5. Run Jupyter notebooks for initial testing
6. Start the CV service:
   ```bash
   python -m src.cv_module.service
   ```

### Troubleshooting

Common configuration issues:
1. Log directory permissions: Ensure the user running the service has write permissions to create log directories
2. Configuration file not found: Verify the config files exist in the `config/` directory
3. Invalid configuration values: Check the configuration validation errors for details about missing or incorrect values

## 5. Development Guidelines

### Code Style
- Follow PEP 8 for Python code
- Use SwiftLint for iOS development
- Document all public functions and classes
- Write unit tests for core functionality

### Git Workflow
- Use feature branches
- Write descriptive commit messages
- Create pull requests for major changes
- Tag releases with semantic versioning

### Documentation
- Update README.md with new features
- Document API changes
- Maintain changelog
- Include setup instructions for new dependencies

### Configuration Management
- Use YAML for configuration files
- Follow the established configuration structure
- Document all configuration options
- Use environment variables for sensitive data
- Test with both development and production profiles
