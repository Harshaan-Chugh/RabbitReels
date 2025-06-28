# Video Creator Service

## Overview

The video creator service is responsible for generating short-form videos using AI-generated scripts and character voices.

## Features

- Processes video generation requests from the message queue
- Downloads and combines character voice files
- Adds background music and visual elements
- Outputs MP4 videos ready for consumption
- Supports Family Guy and Rick & Morty character themes

## Dependencies

- Python 3.11+
- MoviePy for video editing
- PIL for image processing
- Redis for job status tracking
- RabbitMQ for message queue processing

## Configuration

The service reads configuration from environment variables and connects to Redis and RabbitMQ services defined in the Docker Compose setup.

## Output

Generated videos are saved to the configured output directory and made available for download through the API service.
