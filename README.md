# Telegram Data Gatherer (DTG)

A specialized tool to collect messages, images, and videos from Telegram groups/channels/chats.

## Features
- **Account Login**: Uses your personal Telegram account.
- **Selective Download**: Choose specific chats to scrape.
- **Media Download**: Downloads images and videos (even from restricted content channels).
- **H5 Export**: Exports message history to H5 format for analysis.
- **Concurrency**: Multi-threaded downloading with rate limiting.

## Architecture
- **Backend (Go)**: Handles Telegram connection (MTProto), message fetching, and high-concurrency media downloading.
- **Processor (Python)**: Handles data transformation and H5 file generation.

## Setup

### Prerequisites
- Go 1.21+
- Python 3.8+
- Telegram API ID and Hash (Get from https://my.telegram.org)

### Installation

1.  **Configure**: Edit `config.yaml` with your credentials.
2.  **Install Go Deps**:
    ```bash
    cd backend
    go mod tidy
    ```
3.  **Install Python Deps**:
    ```bash
    cd processor
    pip install -r requirements.txt
    ```

## Usage

1.  Run the backend to fetch data:
    ```bash
    cd backend
    go run main.go
    ```
2.  (Optional) Run the processor manually if needed (Backend should trigger it automatically).

## Structure
- `backend/`: Go source code.
- `processor/`: Python scripts.
- `output/`: Downloaded media and exported files.
