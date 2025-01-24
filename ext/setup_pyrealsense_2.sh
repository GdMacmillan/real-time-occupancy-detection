#!/bin/bash

# Default version if not specified
REALSENSE_VERSION="${1:-2.55.1}"
COPY_LIBS="${2:-false}"  # Optional argument for copying libraries

# Determine install prefix
INSTALL_PREFIX=${CONDA_PREFIX:-/usr/local}
echo "Using install prefix: $INSTALL_PREFIX"

# Set non-interactive frontend for apt
export DEBIAN_FRONTEND=noninteractive

# Combine update commands, install libusb, and cleanup
sudo -E apt-get update && \
    sudo -E apt-get upgrade -y && \
    sudo -E apt-get install -y libusb-1.0-0-dev && \
    sudo -E apt-get clean && \
    sudo -E rm -rf /var/lib/apt/lists/* || {
        echo "Error: Failed to update system packages or install libusb"
        exit 1
    }

# Download and extract librealsense source code only if not already present
TARBALL="v${REALSENSE_VERSION}.tar.gz"
if [ ! -f "$TARBALL" ]; then
    echo "Downloading librealsense v${REALSENSE_VERSION}..."
    wget "https://github.com/IntelRealSense/librealsense/archive/refs/tags/${TARBALL}" || {
        echo "Error: Failed to download librealsense v${REALSENSE_VERSION}"
        exit 1
    }
else
    echo "Using existing download: ${TARBALL}"
fi

# Extract only if the directory doesn't exist
if [ ! -d "librealsense-${REALSENSE_VERSION}" ]; then
    echo "Extracting ${TARBALL}..."
    tar -xvzf "$TARBALL" || {
        echo "Error: Failed to extract archive"
        exit 1
    }
else
    echo "Using existing directory: librealsense-${REALSENSE_VERSION}"
fi

# Combined directory operations with error checking
cd "librealsense-${REALSENSE_VERSION}" && \
    mkdir -p build && \
    cd build || {
        echo "Error: Failed to create and enter build directory"
        exit 1
    }

# Run CMake with Python bindings
cmake ../ \
    -DBUILD_PYTHON_BINDINGS:bool=true \
    -DPYTHON_EXECUTABLE=$(which python3) \
    -DFORCE_RSUSB_BACKEND=true \
    -DCMAKE_INSTALL_PREFIX=$INSTALL_PREFIX || {
        echo "Error: CMake configuration failed"
        exit 1
    }

# Build and install
echo "Building librealsense..."
make -j4 || {
    echo "Error: Build failed"
    exit 1
}

echo "Installing librealsense..."
sudo make install || {
    echo "Error: Installation failed"
    exit 1
}

# Print PYTHONPATH to add to nodebooks if not set
PYTHONPATH_LINE="export PYTHONPATH=\$PYTHONPATH:$INSTALL_PREFIX/lib"
echo "PYTHONPATH to add for lib: "
echo "$PYTHONPATH_LINE"

cd ../..

# Optional: Copy library files to script directory
if [ "$COPY_LIBS" = "true" ]; then
    SOURCE_DIR="$(dirname "$(dirname "$0")")"
    echo "Copying library files to ssource directory: $SOURCE_DIR"

    # Find and copy the built libraries
    find . -name "librealsense2.so*" -exec cp {} "$SOURCE_DIR" \;
    find . -name "pyrealsense2*.so*" -exec cp {} "$SOURCE_DIR" \;
    echo "Library files have been copied to: $SOURCE_DIR"
fi

echo "Successfully built and installed librealsense v${REALSENSE_VERSION}"
echo "Note: You may need to restart your terminal for PYTHONPATH changes to take effect"

# Print Python package location
echo "Checking pyrealsense2 installation..."
python3 -c "import pyrealsense2; print(f\"pyrealsense2 installed at: {pyrealsense2.__path__[0]}\")" || {
    echo "Warning: Unable to import pyrealsense2. You may need to restart your terminal or check the installation."
}
